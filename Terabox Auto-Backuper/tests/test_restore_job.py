"""Testes do job de restauração em background.

O cliente Terabox, o manifesto e o banco são simulados. Arquivos reais são
gravados apenas em pastas temporárias.
"""

import asyncio
import os
import shutil
import tempfile
import time
import unittest

import backend.api as api
import backend.database as database
import backend.terabox_client as terabox_client
from backend.models import RestoreRequest


class SlowFakeClient:
    def __init__(self, source_map, delay=0.0):
        self.source_map = source_map
        self.delay = delay
        self.downloads = []
        self.closed = False

    async def download_file(self, remote_path, local_path):
        if self.delay:
            await asyncio.sleep(self.delay)
        self.downloads.append(remote_path)
        source = self.source_map.get(remote_path)
        if not source:
            return False
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copyfile(source, local_path)
        return True

    async def close(self):
        self.closed = True


class RestoreJobTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.base = os.path.join(self.root, "original")
        os.makedirs(self.base, exist_ok=True)

        self._original_auth = api.auth.get_cached_auth
        self._original_context = api._load_restore_context
        self._original_client = terabox_client.TeraboxClient
        self._original_get_setting = database.get_setting
        self._original_execute_many = database.execute_many
        self._original_job = api._restore_job
        self._clients = []

        async def fake_auth():
            return {"cookies": [], "jstoken": "fake"}

        async def fake_get_setting(key):
            return None

        async def fake_execute_many(query, params):
            return len(params)

        api.auth.get_cached_auth = fake_auth
        database.get_setting = fake_get_setting
        database.execute_many = fake_execute_many
        api._restore_job = {
            "task": None,
            "cancel_event": None,
            "progress": self._idle_progress(),
        }

    def _idle_progress(self):
        progress = api._new_restore_progress("setup")
        progress["running"] = False
        progress["phase"] = "idle"
        progress["started_at"] = None
        return progress

    def tearDown(self):
        task = api._restore_job.get("task")
        if task is not None and not task.done():
            task.cancel()
        api.auth.get_cached_auth = self._original_auth
        api._load_restore_context = self._original_context
        terabox_client.TeraboxClient = self._original_client
        database.get_setting = self._original_get_setting
        database.execute_many = self._original_execute_many
        api._restore_job = self._original_job
        self._tmp.cleanup()

    def _install(self, manifest, mappings, source_map, delay=0.0):
        client = SlowFakeClient(source_map, delay=delay)
        self._clients.append(client)

        async def fake_context(_client):
            return manifest, mappings

        api._load_restore_context = fake_context
        terabox_client.TeraboxClient = lambda *args, **kwargs: client
        return client

    def _mapping(self, **overrides):
        data = {
            "id": 1,
            "name": "saves",
            "local_path": self.base,
            "remote_path": "/Backup/saves",
            "is_file": False,
            "enabled": True,
            "include_subfolders": True,
            "encrypt": False,
        }
        data.update(overrides)
        return data

    def _entry(self, rel_path, remote_path, **overrides):
        data = {
            "local_rel_path": rel_path,
            "remote_path": remote_path,
            "mapping_id": 1,
            "mapping_name": "saves",
            "size": 10,
            "encrypted": False,
        }
        data.update(overrides)
        return data

    async def _wait_task(self, timeout=5.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            task = api._restore_job.get("task")
            if task is None:
                return
            if task.done():
                # O finally já zerou a referência; aguarda o encerramento.
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                return
            await asyncio.sleep(0.01)
        self.fail("o job de restauração não terminou a tempo")

    async def test_job_restaura_e_reporta_progresso_final(self):
        source = os.path.join(self.root, "source.bin")
        with open(source, "wb") as fh:
            fh.write(b"conteudo restaurado")
        remote = "/Backup/saves/sub/0.msav"
        manifest = {"files": [self._entry("sub/0.msav", remote)]}
        client = self._install(manifest, [self._mapping()], {remote: source})

        started = await api.restore_start(
            RestoreRequest(files=[remote], allow_overwrite=True)
        )
        self.assertEqual(started["status"], "started")
        await self._wait_task()

        status = await api.restore_status()
        target = os.path.join(self.base, "sub", "0.msav")
        self.assertTrue(os.path.isfile(target))
        self.assertFalse(status.running)
        self.assertEqual(status.phase, "finished")
        self.assertEqual(status.files_total, 1)
        self.assertEqual(status.files_done, 1)
        self.assertEqual(status.files_created, 1)
        self.assertEqual(status.current_file, None)
        self.assertEqual(status.summary["restored"], 1)
        self.assertEqual(client.downloads, [remote])
        self.assertTrue(client.closed)

    async def test_job_cancela_entre_arquivos(self):
        source = os.path.join(self.root, "source.bin")
        with open(source, "wb") as fh:
            fh.write(b"x")
        remotes = [f"/Backup/saves/{i}.bin" for i in range(4)]
        manifest = {
            "files": [
                self._entry(f"{i}.bin", remote)
                for i, remote in enumerate(remotes)
            ]
        }
        self._install(
            manifest, [self._mapping()], {r: source for r in remotes}, delay=0.05
        )

        await api.restore_start(
            RestoreRequest(files=remotes, allow_overwrite=True)
        )
        await asyncio.sleep(0.02)
        stopped = await api.restore_stop()
        self.assertEqual(stopped["status"], "cancelling")
        await self._wait_task()

        status = await api.restore_status()
        self.assertFalse(status.running)
        self.assertEqual(status.phase, "cancelled")
        self.assertTrue(status.cancel_requested)
        self.assertTrue(status.summary["cancelled"])
        self.assertLess(status.files_done, len(remotes))

    async def test_job_falha_sem_confirmacao_de_conflito(self):
        source = os.path.join(self.root, "source.bin")
        with open(source, "wb") as fh:
            fh.write(b"novo")
        target = os.path.join(self.base, "0.msav")
        with open(target, "wb") as fh:
            fh.write(b"atual")
        remote = "/Backup/saves/0.msav"
        manifest = {"files": [self._entry("0.msav", remote)]}
        client = self._install(manifest, [self._mapping()], {remote: source})

        await api.restore_start(
            RestoreRequest(files=[remote], allow_overwrite=False)
        )
        await self._wait_task()

        status = await api.restore_status()
        with open(target, "rb") as fh:
            self.assertEqual(fh.read(), b"atual")
        self.assertEqual(client.downloads, [])
        self.assertEqual(status.phase, "failed")
        self.assertIn("confirma", status.error)

    async def test_status_inicial_nao_esta_rodando(self):
        status = await api.restore_status()
        self.assertFalse(status.running)
        self.assertEqual(status.phase, "idle")
        self.assertEqual(status.files_done, 0)

    async def test_start_recusa_job_duplicado(self):
        source = os.path.join(self.root, "source.bin")
        with open(source, "wb") as fh:
            fh.write(b"x")
        remote = "/Backup/saves/0.msav"
        manifest = {"files": [self._entry("0.msav", remote)]}
        self._install(
            manifest, [self._mapping()], {remote: source}, delay=0.05
        )

        await api.restore_start(
            RestoreRequest(files=[remote], allow_overwrite=True)
        )
        with self.assertRaises(Exception) as ctx:
            await api.restore_start(
                RestoreRequest(files=[remote], allow_overwrite=True)
            )
        self.assertEqual(getattr(ctx.exception, "status_code", None), 409)
        await self._wait_task()


if __name__ == "__main__":
    unittest.main()
