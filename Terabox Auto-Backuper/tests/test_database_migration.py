"""Testes da migração de `mappings.is_file` e do setting de restauração."""

import os
import tempfile
import unittest

import aiosqlite

import backend.database as database


class DatabaseMigrationTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "app.db")
        self.original_db_path = database.DB_PATH
        database.DB_PATH = self.db_path

        self.folder = os.path.join(self._tmp.name, "pasta")
        os.makedirs(self.folder)
        self.file_path = os.path.join(self._tmp.name, "arquivo.bin")
        with open(self.file_path, "wb") as fh:
            fh.write(b"x")

        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(
                """
                CREATE TABLE mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    remote_path TEXT NOT NULL,
                    include_subfolders INTEGER NOT NULL DEFAULT 1,
                    encrypt INTEGER NOT NULL DEFAULT 0,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mapping_id INTEGER NOT NULL,
                    local_rel_path TEXT NOT NULL,
                    remote_path TEXT NOT NULL,
                    size INTEGER NOT NULL DEFAULT 0,
                    md5 TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    last_synced_at TEXT,
                    error TEXT
                );
                CREATE TABLE sync_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL DEFAULT 'running',
                    files_total INTEGER NOT NULL DEFAULT 0,
                    files_uploaded INTEGER NOT NULL DEFAULT 0,
                    files_failed INTEGER NOT NULL DEFAULT 0,
                    files_skipped INTEGER NOT NULL DEFAULT 0,
                    error TEXT
                );
                CREATE TABLE settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE auth_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    browser TEXT NOT NULL,
                    cookies_json TEXT NOT NULL,
                    jstoken TEXT,
                    jstoken_expires_at TEXT,
                    updated_at TEXT NOT NULL
                );
                """
            )
            now = "2026-11-12T00:00:00"
            await db.execute(
                """INSERT INTO mappings
                   (name, local_path, remote_path, include_subfolders,
                    encrypt, enabled, created_at, updated_at)
                   VALUES (?, ?, ?, 1, 0, 1, ?, ?)""",
                ("pasta", self.folder, "/Backup/pasta", now, now),
            )
            await db.execute(
                """INSERT INTO mappings
                   (name, local_path, remote_path, include_subfolders,
                    encrypt, enabled, created_at, updated_at)
                   VALUES (?, ?, ?, 0, 0, 1, ?, ?)""",
                ("arquivo", self.file_path, "/Backup/arquivo", now, now),
            )
            await db.commit()

    async def asyncTearDown(self):
        database.DB_PATH = self.original_db_path
        self._tmp.cleanup()

    async def _rows(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, name, is_file, uid FROM mappings ORDER BY id"
            )
            return await cursor.fetchall()

    async def test_migracao_marca_pasta_e_arquivo(self):
        await database.init_db()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("PRAGMA table_info(mappings)")
            columns = {row[1] for row in await cursor.fetchall()}
            self.assertIn("is_file", columns)
            self.assertIn("uid", columns)

            cursor = await db.execute(
                "SELECT value FROM settings "
                "WHERE key = 'mappings_is_file_backfilled'"
            )
            self.assertIsNotNone(await cursor.fetchone())

            for key, expected in (
                ("restore_confirm_overwrite", "true"),
                ("remote_config_enabled", "true"),
                ("remote_config_auto_save", "true"),
                (
                    "remote_config_path",
                    "/config-terabox-auto-backup/terabox-auto-backup.json",
                ),
            ):
                cursor = await db.execute(
                    "SELECT value FROM settings WHERE key = ?", (key,)
                )
                row = await cursor.fetchone()
                self.assertEqual(row[0], expected)

            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND name = 'idx_mappings_uid'"
            )
            self.assertIsNotNone(await cursor.fetchone())

            cursor = await db.execute("SELECT value FROM settings WHERE key = 'machine_id'")
            self.assertTrue((await cursor.fetchone())[0])
            cursor = await db.execute("SELECT value FROM settings WHERE key = 'machine_name'")
            self.assertTrue((await cursor.fetchone())[0])

        rows = await self._rows()
        self.assertEqual(rows[0]["is_file"], 0)
        self.assertEqual(rows[1]["is_file"], 1)
        self.assertTrue(rows[0]["uid"])
        self.assertTrue(rows[1]["uid"])
        self.assertNotEqual(rows[0]["uid"], rows[1]["uid"])

    async def test_nao_reclassifica_arquivo_apagado_no_proximo_startup(self):
        await database.init_db()
        uid_before = (await self._rows())[1]["uid"]
        os.remove(self.file_path)

        await database.init_db()

        rows = await self._rows()
        self.assertEqual(rows[0]["is_file"], 0)
        self.assertEqual(rows[1]["is_file"], 1)
        self.assertEqual(rows[1]["uid"], uid_before)

    async def test_uid_e_estavel_entre_startups(self):
        await database.init_db()
        first = [row["uid"] for row in await self._rows()]

        await database.init_db()
        second = [row["uid"] for row in await self._rows()]

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
