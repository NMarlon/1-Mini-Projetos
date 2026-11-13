"""Testes de progresso, cancelamento e erros persistentes do sync."""

import asyncio
import os
import tempfile
import unittest
from unittest import mock

import backend.database as database
from backend.config import CHUNK_SIZE_BYTES, UPLOAD_MAX_TIME_SECONDS
from backend.sync_engine import SyncEngine, composite_multipart_md5
from backend.terabox_client import TeraboxClient, parse_curl_progress


class CurlProgressTest(unittest.TestCase):
    def test_extrai_percentual_da_barra(self):
        self.assertEqual(parse_curl_progress("##### 42.5%")[0], 42.5)
        self.assertEqual(parse_curl_progress("100.0%")[0], 100.0)

    def test_composite_multipart_md5_do_terabox(self):
        md5s = [
            "23d260ddf341b8c37159a0b11a084cab",
            "98f0fa9a606765163f5779f6a7f20056",
            "b9359369568298310d912951d8997870",
            "3fd1051d8d1e506e0781dfe61de4d037",
        ]
        self.assertEqual(
            composite_multipart_md5(md5s),
            "36199479611b51caebf39b65ebae20b1",
        )

    def test_linha_sem_percentual_e_ignorada(self):
        self.assertIsNone(parse_curl_progress(""))
        self.assertIsNone(parse_curl_progress("sem progresso"))

    def test_max_time_cresce_com_o_tamanho_e_tem_teto(self):
        with mock.patch(
            "backend.terabox_client.os.path.getsize",
            return_value=CHUNK_SIZE_BYTES,
        ):
            self.assertGreaterEqual(TeraboxClient.upload_max_time("x"), 1800)
        with mock.patch(
            "backend.terabox_client.os.path.getsize",
            return_value=10 * 1024 ** 3,
        ):
            self.assertEqual(
                TeraboxClient.upload_max_time("x"), UPLOAD_MAX_TIME_SECONDS
            )


class SyncProgressTest(unittest.TestCase):
    def test_callback_converte_bloco_em_progresso_total(self):
        engine = SyncEngine()
        engine._status = {}
        cb = engine._make_progress_cb(
            base_bytes=100, total_bytes=1000, chunk_index=2
        )
        cb(250, 500, 1024.0)

        self.assertEqual(engine._status["upload_bytes_done"], 350)
        self.assertEqual(engine._status["upload_bytes_total"], 1000)
        self.assertEqual(engine._status["upload_percent"], 35.0)
        self.assertEqual(engine._status["upload_speed_bps"], 1024.0)
        self.assertIsNotNone(engine._status["upload_eta_seconds"])
        self.assertEqual(engine._status["upload_chunk"], 2)

    def test_reset_limpa_estado_do_arquivo_anterior(self):
        engine = SyncEngine()
        engine._status = {"upload_percent": 80, "upload_bytes_done": 10}
        engine._reset_upload_progress()
        self.assertEqual(engine._status["upload_percent"], 0.0)
        self.assertEqual(engine._status["upload_bytes_done"], 0)
        self.assertIsNone(engine._status["upload_eta_seconds"])


class CurlSpeedTest(unittest.IsolatedAsyncioTestCase):
    async def test_calcula_velocidade_por_delta_de_bytes(self):
        fd, path = tempfile.mkstemp()
        try:
            os.write(fd, b"x" * 1000)
            os.close(fd)

            class Proc:
                def __init__(self):
                    self.stderr = self

                async def read(self, _n):
                    return b""

            proc = Proc()
            chunks = [b"##### 50.0%\r", b"########## 100.0%\r", b""]

            async def fake_read(_n):
                return chunks.pop(0) if chunks else b""

            proc.read = fake_read
            updates = []

            client = TeraboxClient({}, "fake")
            try:
                with mock.patch(
                    "backend.terabox_client.time.monotonic",
                    side_effect=[0.0, 1.0, 2.0],
                ):
                    await client._consume_curl_progress(
                        proc,
                        path,
                        lambda done, total, speed: updates.append(
                            (done, total, speed)
                        ),
                    )
            finally:
                await client.close()

            self.assertEqual(updates[0][0], 500)
            self.assertEqual(updates[1][0], 1000)
            self.assertGreater(updates[0][2], 0)
            self.assertGreater(updates[1][2], 0)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass


class SyncCancelTest(unittest.IsolatedAsyncioTestCase):
    async def test_start_recusa_quando_ja_esta_rodando(self):
        engine = SyncEngine()
        engine._running = True
        with self.assertRaises(RuntimeError):
            await engine.start_sync()

    async def test_stop_mata_upload_e_cancela_task(self):
        engine = SyncEngine()
        engine._running = True
        engine._current_run_id = 1
        engine._status = {"running": True, "phase": "uploading"}

        cancel_called = asyncio.Event()

        class FakeClient:
            async def cancel_active_upload(self):
                cancel_called.set()

        async def slow_task():
            await asyncio.sleep(60)

        engine._client = FakeClient()
        engine._task = asyncio.create_task(slow_task())
        engine._finish_run = mock.AsyncMock()

        await engine.stop_sync(timeout=0.1)

        self.assertTrue(cancel_called.is_set())
        self.assertFalse(engine._running)
        engine._finish_run.assert_awaited()


class SyncRunErrorsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._original_db_path = database.DB_PATH
        database.DB_PATH = os.path.join(self._tmp.name, "app.db")
        await database.init_db()

    async def asyncTearDown(self):
        database.DB_PATH = self._original_db_path
        self._tmp.cleanup()

    async def test_persiste_erro_e_incrementa_contador_do_run(self):
        run_id = await database.execute(
            "INSERT INTO sync_runs (started_at, status) VALUES (?, 'running')",
            ("2026-11-12T23:00:00",),
        )
        engine = SyncEngine()
        engine._current_run_id = run_id
        engine._status = {"errors": [], "errors_total": 0}

        await engine._persist_run_error(
            "file", "C:\\pasta\\arquivo.bin", "falha de teste", 7, "Teste"
        )

        rows = await database.fetch_all(
            "SELECT * FROM sync_run_errors WHERE run_id = ?", (run_id,)
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "file")
        self.assertEqual(rows[0]["path"], "C:\\pasta\\arquivo.bin")
        self.assertEqual(rows[0]["mapping_name"], "Teste")
        self.assertEqual(rows[0]["error"], "falha de teste")

        run = await database.fetch_one(
            "SELECT errors_total, errors_truncated FROM sync_runs WHERE id = ?",
            (run_id,),
        )
        self.assertEqual(run["errors_total"], 1)
        self.assertEqual(run["errors_truncated"], 0)
        self.assertEqual(engine._status["errors_total"], 1)

    async def test_erro_de_varredura_tambem_e_persistido(self):
        run_id = await database.execute(
            "INSERT INTO sync_runs (started_at, status) VALUES (?, 'running')",
            ("2026-11-12T23:00:00",),
        )
        engine = SyncEngine()
        engine._current_run_id = run_id
        engine._status = {"errors": [], "errors_total": 0}

        await engine._record_status_error(
            "C:\\Program Files (x86)\\Steam\\userdata",
            "WinError 5",
            kind="scan",
            mapping_id=34,
            mapping_name="userdata",
        )

        rows = await database.fetch_all(
            "SELECT * FROM sync_run_errors WHERE run_id = ?", (run_id,)
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "scan")
        self.assertEqual(rows[0]["mapping_name"], "userdata")
        self.assertEqual(engine._status["errors"][0]["kind"], "scan")


if __name__ == "__main__":
    unittest.main()
