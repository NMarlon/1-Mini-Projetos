"""Testes de integração do endpoint de download do Restaurar.

O cliente Terabox, o manifesto e o banco são simulados. Os arquivos são
gravados apenas em pastas temporárias.
"""

import os
import shutil
import tempfile
import unittest

from fastapi import HTTPException

import backend.api as api
import backend.database as database
import backend.terabox_client as terabox_client
from backend.encryption import encrypt_file, generate_key
from backend.models import RestoreRequest


class FakeTeraboxClient:
    def __init__(self, source_map):
        self.source_map = source_map
        self.downloads = []

    async def download_file(self, remote_path, local_path, progress_cb=None):
        self.downloads.append((remote_path, local_path))
        source = self.source_map.get(remote_path)
        if not source:
            return False
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        shutil.copyfile(source, local_path)
        if progress_cb:
            size = os.path.getsize(local_path)
            progress_cb(size, size, 0.0)
        return True

    async def close(self):
        pass


class RestoreDownloadTest(unittest.IsolatedAsyncioTestCase):
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
        self._original_get_setting = database.get_setting

        self.cache_calls = []
        self.setting_values = {}

        async def fake_auth():
            return {"cookies": [], "jstoken": "fake"}

        async def fake_get_setting(key):
            return self.setting_values.get(key)

        async def fake_execute_many(query, params):
            self.cache_calls.append((query, list(params)))
            return len(params)

        api.auth.get_cached_auth = fake_auth
        database.get_setting = fake_get_setting
        database.execute_many = fake_execute_many

    def tearDown(self):
        api.auth.get_cached_auth = self._original_auth
        api._load_restore_context = self._original_context
        terabox_client.TeraboxClient = self._original_client
        database.get_setting = self._original_get_setting
        database.execute_many = self._original_execute_many
        self._tmp.cleanup()

    def _install(self, manifest, mappings, source_map):
        client = FakeTeraboxClient(source_map)

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

    async def test_cria_arquivo_em_pasta_aninhada(self):
        source = os.path.join(self.root, "source.bin")
        with open(source, "wb") as fh:
            fh.write(b"conteudo novo")
        remote = "/Backup/saves/sub/0.msav"
        manifest = {"files": [self._entry("sub/0.msav", remote)]}
        self._install(manifest, [self._mapping()], {remote: source})

        result = await api.restore_download(
            RestoreRequest(files=[remote], allow_overwrite=True)
        )

        target = os.path.join(self.base, "sub", "0.msav")
        self.assertTrue(os.path.isfile(target))
        with open(target, "rb") as fh:
            self.assertEqual(fh.read(), b"conteudo novo")
        self.assertEqual(result["summary"]["created"], 1)
        self.assertFalse(result["results"][0]["overwritten"])

    async def test_substitui_arquivo_existente_com_backup_atomico(self):
        source = os.path.join(self.root, "source.bin")
        with open(source, "wb") as fh:
            fh.write(b"versao restaurada")
        target = os.path.join(self.base, "0.msav")
        with open(target, "wb") as fh:
            fh.write(b"versao atual")
        remote = "/Backup/saves/0.msav"
        manifest = {"files": [self._entry("0.msav", remote)]}
        self._install(manifest, [self._mapping()], {remote: source})

        result = await api.restore_download(
            RestoreRequest(files=[remote], allow_overwrite=True)
        )

        with open(target, "rb") as fh:
            self.assertEqual(fh.read(), b"versao restaurada")
        self.assertTrue(result["results"][0]["overwritten"])
        self.assertEqual(result["summary"]["replaced"], 1)

    async def test_409_nao_baixa_nem_altera_arquivo(self):
        source = os.path.join(self.root, "source.bin")
        with open(source, "wb") as fh:
            fh.write(b"nao deve ser gravado")
        target = os.path.join(self.base, "0.msav")
        with open(target, "wb") as fh:
            fh.write(b"original")
        remote = "/Backup/saves/0.msav"
        manifest = {"files": [self._entry("0.msav", remote)]}
        client = self._install(
            manifest, [self._mapping()], {remote: source}
        )

        with self.assertRaises(HTTPException) as ctx:
            await api.restore_download(
                RestoreRequest(files=[remote], allow_overwrite=False)
            )

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(client.downloads, [])
        with open(target, "rb") as fh:
            self.assertEqual(fh.read(), b"original")

    async def test_mapeamento_de_arquivo_unico_grava_no_proprio_arquivo(self):
        source = os.path.join(self.root, "source.bin")
        with open(source, "wb") as fh:
            fh.write(b"settings")
        file_path = os.path.join(self.base, "settings.bin")
        remote = "/Backup/settings.bin"
        manifest = {"files": [self._entry("settings.bin", remote)]}
        mapping = self._mapping(
            name="Arquivo: settings.bin",
            local_path=file_path,
            remote_path="/Backup",
            is_file=True,
            include_subfolders=False,
        )
        self._install(manifest, [mapping], {remote: source})

        result = await api.restore_download(
            RestoreRequest(files=[remote], allow_overwrite=True)
        )

        self.assertTrue(os.path.isfile(file_path))
        with open(file_path, "rb") as fh:
            self.assertEqual(fh.read(), b"settings")
        self.assertTrue(result["results"][0]["success"])

    async def test_arquivo_criptografado_e_descriptografado_no_destino(self):
        key = generate_key()
        plain = os.path.join(self.root, "plain.bin")
        encrypted = os.path.join(self.root, "plain.bin.enc")
        with open(plain, "wb") as fh:
            fh.write(b"conteudo secreto")
        encrypt_file(key, plain, encrypted)

        remote = "/Backup/saves/segredo.bin.enc"
        manifest = {
            "files": [
                self._entry(
                    "segredo.bin", remote, encrypted=True
                )
            ]
        }
        self.setting_values["encryption_key"] = key
        self._install(manifest, [self._mapping()], {remote: encrypted})

        result = await api.restore_download(
            RestoreRequest(files=[remote], allow_overwrite=True)
        )

        target = os.path.join(self.base, "segredo.bin")
        with open(target, "rb") as fh:
            self.assertEqual(fh.read(), b"conteudo secreto")
        self.assertFalse(os.path.exists(target + ".restore-part"))
        self.assertTrue(result["results"][0]["success"])

    async def test_cache_local_e_atualizado_apos_restaurar(self):
        source = os.path.join(self.root, "source.bin")
        with open(source, "wb") as fh:
            fh.write(b"cache")
        remote = "/Backup/saves/0.msav"
        manifest = {"files": [self._entry("0.msav", remote)]}
        self._install(manifest, [self._mapping()], {remote: source})

        await api.restore_download(
            RestoreRequest(files=[remote], allow_overwrite=True)
        )

        self.assertEqual(len(self.cache_calls), 1)
        query, rows = self.cache_calls[0]
        self.assertIn("UPDATE files", query)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row[5], 1)
        self.assertEqual(row[6], "0.msav")


if __name__ == "__main__":
    unittest.main()
