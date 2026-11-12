"""Testes de integração da configuração remota com o banco temporário."""

import os
import tempfile
import unittest

import backend.database as database
from backend.config import DEFAULT_REMOTE_CONFIG_PATH
from backend.remote_config import (
    RemoteConfigConflict,
    RemoteConfigEmpty,
    RemoteConfigInvalid,
    RemoteConfigManager,
    SCHEMA,
    SCHEMA_VERSION,
    config_hash,
)


class FakeClient:
    async def ensure_token(self, *args, **kwargs):
        return None

    async def refresh_token(self, *args, **kwargs):
        return None

    async def close(self):
        return None


def make_config(entries, machines=None, updated_at="2026-11-12T10:00:00"):
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "updated_at": updated_at,
        "updated_by_machine": "outra-maquina",
        "machines": machines or {
            "outra-maquina": {
                "name": "PC-Outro",
                "last_seen": "2026-11-12T09:00:00",
            }
        },
        "mappings": entries,
    }


def make_entry(uid, remote_path, local_paths, is_file=False):
    return {
        "uid": uid,
        "name": os.path.basename(remote_path.rstrip("/")) or uid,
        "remote_path": remote_path,
        "is_file": is_file,
        "enabled": True,
        "include_subfolders": not is_file,
        "encrypted": False,
        "local_paths": local_paths,
    }


class RemoteConfigServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "app.db")
        self.original_db_path = database.DB_PATH
        database.DB_PATH = self.db_path
        await database.init_db()
        self.manager = RemoteConfigManager()
        self.machine = await database.get_machine_identity()

    async def asyncTearDown(self):
        database.DB_PATH = self.original_db_path
        self._tmp.cleanup()

    async def _insert_mapping(
        self,
        uid,
        local_path,
        remote_path="/Backup/Fotos",
        is_file=False,
        name="Fotos",
    ):
        return await database.execute(
            """INSERT INTO mappings
               (uid, name, local_path, remote_path, include_subfolders,
                encrypt, enabled, is_file, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 0, 1, ?, ?, ?)""",
            (
                uid,
                name,
                local_path,
                remote_path,
                int(not is_file),
                int(is_file),
                "2026-11-12T10:00:00",
                "2026-11-12T10:00:00",
            ),
        )

    async def test_apply_import_cria_mapeamento_de_pasta(self):
        folder = os.path.join(self._tmp.name, "Fotos")
        os.makedirs(folder)
        config = make_config(
            [
                make_entry(
                    "u1",
                    "/Backup/Fotos",
                    {"outra-maquina": folder},
                )
            ]
        )

        async def fake_load_remote(preferred_path=None):
            return {
                "exists": True,
                "path": "/config/backup.json",
                "source": "configured",
                "config": config,
                "error": None,
                "hash": config_hash(config, ignore_volatile=True),
            }

        self.manager.load_remote = fake_load_remote
        result = await self.manager.apply_import(
            config_hash(config, ignore_volatile=True),
            [{"uid": "u1", "local_path": folder}],
        )

        self.assertEqual(len(result["created"]), 1)
        row = await database.fetch_one("SELECT * FROM mappings")
        self.assertEqual(row["uid"], "u1")
        self.assertEqual(row["local_path"], folder)
        self.assertEqual(row["is_file"], 0)
        self.assertEqual(row["include_subfolders"], 1)

    async def test_apply_import_atualiza_por_fingerprint_e_troca_uid(self):
        old_folder = os.path.join(self._tmp.name, "Antiga")
        new_folder = os.path.join(self._tmp.name, "Nova")
        os.makedirs(old_folder)
        os.makedirs(new_folder)
        mapping_id = await self._insert_mapping(
            "uid-antigo", old_folder, "/Backup/Fotos"
        )
        config = make_config(
            [
                make_entry(
                    "uid-remoto",
                    "/Backup/Fotos",
                    {"outra-maquina": new_folder},
                )
            ]
        )

        async def fake_load_remote(preferred_path=None):
            return {
                "exists": True,
                "path": "/config/backup.json",
                "source": "configured",
                "config": config,
                "error": None,
                "hash": config_hash(config, ignore_volatile=True),
            }

        self.manager.load_remote = fake_load_remote
        result = await self.manager.apply_import(
            config_hash(config, ignore_volatile=True),
            [{"uid": "uid-remoto", "local_path": new_folder}],
        )

        self.assertEqual(len(result["updated"]), 1)
        row = await database.fetch_one(
            "SELECT * FROM mappings WHERE id = ?", (mapping_id,)
        )
        self.assertEqual(row["uid"], "uid-remoto")
        self.assertEqual(row["local_path"], new_folder)

    async def test_apply_import_rejeita_hash_desatualizado(self):
        config = make_config(
            [make_entry("u1", "/Backup/Fotos", {"outra-maquina": "C:/Fotos"})]
        )

        async def fake_load_remote(preferred_path=None):
            return {
                "exists": True,
                "path": "/config/backup.json",
                "source": "configured",
                "config": config,
                "error": None,
                "hash": config_hash(config, ignore_volatile=True),
            }

        self.manager.load_remote = fake_load_remote
        with self.assertRaises(RemoteConfigConflict):
            await self.manager.apply_import("hash-errado", [])

    async def test_apply_import_cria_pasta_local_inexistente(self):
        folder = os.path.join(self._tmp.name, "Nova", "Sub")
        config = make_config(
            [
                make_entry(
                    "u1",
                    "/Backup/Nova",
                    {"outra-maquina": folder},
                )
            ]
        )

        async def fake_load_remote(preferred_path=None):
            return {
                "exists": True,
                "path": "/config/backup.json",
                "source": "configured",
                "config": config,
                "error": None,
                "hash": config_hash(config, ignore_volatile=True),
            }

        self.manager.load_remote = fake_load_remote
        result = await self.manager.apply_import(
            config_hash(config, ignore_volatile=True),
            [{"uid": "u1", "local_path": folder}],
        )

        self.assertEqual(len(result["created"]), 1)
        self.assertTrue(os.path.isdir(folder))

    async def test_apply_import_de_arquivo_cria_so_pasta_pai(self):
        target = os.path.join(self._tmp.name, "Saves", "level.dat")
        config = make_config(
            [
                make_entry(
                    "u1",
                    "/Backup/level.dat",
                    {"outra-maquina": target},
                    is_file=True,
                )
            ]
        )

        async def fake_load_remote(preferred_path=None):
            return {
                "exists": True,
                "path": "/config/backup.json",
                "source": "configured",
                "config": config,
                "error": None,
                "hash": config_hash(config, ignore_volatile=True),
            }

        self.manager.load_remote = fake_load_remote
        result = await self.manager.apply_import(
            config_hash(config, ignore_volatile=True),
            [{"uid": "u1", "local_path": target}],
        )

        self.assertEqual(len(result["created"]), 1)
        self.assertTrue(os.path.isdir(os.path.dirname(target)))
        self.assertFalse(os.path.exists(target))

    async def test_apply_import_de_arquivo_unico_aceita_arquivo_inexistente(self):
        target = os.path.join(self._tmp.name, "docs", "contrato.pdf")
        os.makedirs(os.path.dirname(target))
        config = make_config(
            [
                make_entry(
                    "u1",
                    "/Backup/contrato.pdf",
                    {"outra-maquina": target},
                    is_file=True,
                )
            ]
        )

        async def fake_load_remote(preferred_path=None):
            return {
                "exists": True,
                "path": "/config/backup.json",
                "source": "configured",
                "config": config,
                "error": None,
                "hash": config_hash(config, ignore_volatile=True),
            }

        self.manager.load_remote = fake_load_remote
        result = await self.manager.apply_import(
            config_hash(config, ignore_volatile=True),
            [{"uid": "u1", "local_path": target}],
        )

        self.assertEqual(len(result["created"]), 1)
        row = await database.fetch_one("SELECT * FROM mappings")
        self.assertEqual(row["is_file"], 1)
        self.assertEqual(row["include_subfolders"], 0)
        self.assertFalse(os.path.exists(target))

    async def test_save_mescla_caminho_de_outra_maquina(self):
        local_path = os.path.join(self._tmp.name, "Fotos")
        os.makedirs(local_path)
        await self._insert_mapping("u1", local_path, "/Backup/Fotos")

        previous = make_config(
            [
                make_entry(
                    "u1",
                    "/Backup/Fotos",
                    {
                        self.machine["machine_id"]: "C:\\Antigo\\Fotos",
                        "outra-maquina": "D:\\Fotos",
                    },
                )
            ]
        )
        written = {}

        async def fake_read_remote(client, path):
            return {
                "exists": True,
                "path": path,
                "config": previous,
                "error": None,
                "hash": config_hash(previous, ignore_volatile=True),
            }

        async def fake_write(client, path, payload):
            written["config"] = payload

        async def fake_shortcut(client, path):
            written["shortcut"] = path

        self.manager._read_remote = fake_read_remote
        self.manager._write_remote_file = fake_write
        self.manager._write_shortcut = fake_shortcut

        result = await self.manager.save_now(
            client=FakeClient(), reason="test"
        )

        self.assertTrue(result["changed"])
        self.assertEqual(written["shortcut"], DEFAULT_REMOTE_CONFIG_PATH)
        paths = written["config"]["mappings"][0]["local_paths"]
        self.assertEqual(paths["outra-maquina"], "D:\\Fotos")
        self.assertEqual(paths[self.machine["machine_id"]], local_path)

    async def test_save_bloqueia_lista_vazia_sobre_configuracao_existente(self):
        previous = make_config(
            [
                make_entry(
                    "u1",
                    "/Backup/Fotos",
                    {"outra-maquina": "D:\\Fotos"},
                )
            ]
        )

        async def fake_read_remote(client, path):
            return {
                "exists": True,
                "path": path,
                "config": previous,
                "error": None,
                "hash": config_hash(previous, ignore_volatile=True),
            }

        self.manager._read_remote = fake_read_remote

        with self.assertRaises(RemoteConfigEmpty):
            await self.manager.save_now(client=FakeClient(), reason="test")

    async def test_save_bloqueia_configuracao_invalida_sem_force(self):
        async def fake_read_remote(client, path):
            return {
                "exists": True,
                "path": path,
                "config": None,
                "error": "schema inválido",
                "hash": None,
            }

        self.manager._read_remote = fake_read_remote

        with self.assertRaises(RemoteConfigInvalid):
            await self.manager.save_now(client=FakeClient(), reason="test")


if __name__ == "__main__":
    unittest.main()
