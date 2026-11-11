"""Camada de acesso ao SQLite via aiosqlite."""

import aiosqlite
from datetime import datetime
from backend.config import DB_PATH
from backend.paths import sanitize_remote_path


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA journal_mode = WAL")
    return db


async def init_db():
    """Cria todas as tabelas se não existirem."""
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS mappings (
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

            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mapping_id INTEGER NOT NULL,
                local_rel_path TEXT NOT NULL,
                remote_path TEXT NOT NULL,
                size INTEGER NOT NULL DEFAULT 0,
                md5 TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                last_synced_at TEXT,
                error TEXT,
                FOREIGN KEY (mapping_id) REFERENCES mappings(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sync_runs (
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

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                browser TEXT NOT NULL,
                cookies_json TEXT NOT NULL,
                jstoken TEXT,
                jstoken_expires_at TEXT,
                updated_at TEXT NOT NULL
            );
        """)
        await db.commit()

        # Migrações incrementais (idempotentes)
        await _migrate_schema(db)

        # Inserir settings padrão se não existirem
        defaults = {
            "sync_interval_minutes": "30",
            "auto_sync": "true",
            "notifications": "true",
            "max_concurrent_uploads": "3",
            "autostart": "false",
            "browser_preference": "auto",
        }
        for key, value in defaults.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        await db.commit()
    finally:
        await db.close()


async def _table_columns(db: aiosqlite.Connection, table: str) -> set:
    cursor = await db.execute(f"PRAGMA table_info({table})")
    rows = await cursor.fetchall()
    return {row[1] for row in rows}


async def _migrate_schema(db: aiosqlite.Connection):
    """Adiciona colunas novas, remove duplicatas e cria índice único.

    Tudo aqui é idempotente: pode rodar em todo startup sem perder dados.
    """
    columns = await _table_columns(db, "files")
    new_columns = {
        "remote_md5": "TEXT",
        "mtime_ns": "INTEGER",
        "encrypted": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, definition in new_columns.items():
        if name not in columns:
            await db.execute(f"ALTER TABLE files ADD COLUMN {name} {definition}")

    # Remover linhas órfãs (mapeamento apagado)
    await db.execute(
        "DELETE FROM files WHERE mapping_id NOT IN (SELECT id FROM mappings)"
    )

    # Remover duplicatas antigas, mantendo a linha mais recente (maior id)
    await db.execute(
        """DELETE FROM files
           WHERE id NOT IN (
               SELECT MAX(id) FROM files GROUP BY mapping_id, local_rel_path
           )"""
    )

    # Runs que ficaram "running" após fechar o app/crash não devem aparecer
    # como eternamente em andamento no histórico.
    await db.execute(
        """UPDATE sync_runs
           SET status = 'cancelled', finished_at = COALESCE(finished_at, ?)
           WHERE status = 'running' AND finished_at IS NULL""",
        (datetime.now().isoformat(),),
    )

    # Normalizar caminhos remotos antigos (barra final, barras invertidas)
    cursor = await db.execute("SELECT id, remote_path FROM mappings")
    for row in await cursor.fetchall():
        raw = row[1] or ""
        normalized = "/" + raw.replace("\\", "/").strip().strip("/")
        normalized = sanitize_remote_path(normalized)
        if normalized != "/" and raw != normalized:
            await db.execute(
                "UPDATE mappings SET remote_path = ? WHERE id = ?",
                (normalized, row[0]),
            )

    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_files_mapping_rel "
        "ON files(mapping_id, local_rel_path)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_mapping_id ON files(mapping_id)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_remote_path ON files(remote_path)"
    )
    await db.commit()


# ── Helpers genéricos ──

async def fetch_one(query: str, params: tuple = ()):
    db = await get_db()
    try:
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def fetch_all(query: str, params: tuple = ()):
    db = await get_db()
    try:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def execute(query: str, params: tuple = ()):
    db = await get_db()
    try:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_setting(key: str) -> str | None:
    row = await fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else None


async def set_setting(key: str, value: str):
    await execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
        (key, value, value),
    )