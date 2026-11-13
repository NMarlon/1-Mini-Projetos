"""Camada de acesso ao SQLite via aiosqlite."""

import os
import socket
import uuid

import aiosqlite
from datetime import datetime
from backend.config import DB_PATH, DEFAULT_REMOTE_CONFIG_PATH
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
                is_file INTEGER NOT NULL DEFAULT 0,
                uid TEXT,
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
                errors_total INTEGER NOT NULL DEFAULT 0,
                errors_truncated INTEGER NOT NULL DEFAULT 0,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS sync_run_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                kind TEXT NOT NULL DEFAULT 'error',
                mapping_id INTEGER,
                mapping_name TEXT,
                path TEXT,
                error TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES sync_runs(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sync_run_errors_run
                ON sync_run_errors(run_id);

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
            "upload_chunked": "true",
            "autostart": "false",
            "browser_preference": "auto",
            "restore_confirm_overwrite": "true",
            "remote_config_enabled": "true",
            "remote_config_path": DEFAULT_REMOTE_CONFIG_PATH,
            "remote_config_auto_save": "true",
        }
        for key, value in defaults.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )

        # Identidade estável desta instalação. O nome é editável; o ID nunca
        # muda, para que o arquivo remoto não confunda dois computadores.
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('machine_id', ?)",
            (str(uuid.uuid4()),),
        )
        await db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('machine_name', ?)",
            (socket.gethostname() or "PC",),
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

    # Tipo original do mapeamento (arquivo único x pasta). É persistido para
    # que o Restaurar recrie o arquivo no caminho certo mesmo que ele tenha
    # sido apagado depois do backup.
    mapping_columns = await _table_columns(db, "mappings")
    if "is_file" not in mapping_columns:
        await db.execute(
            "ALTER TABLE mappings ADD COLUMN is_file INTEGER NOT NULL DEFAULT 0"
        )

    cursor = await db.execute(
        "SELECT value FROM settings WHERE key = 'mappings_is_file_backfilled'"
    )
    if await cursor.fetchone() is None:
        cursor = await db.execute("SELECT id, local_path FROM mappings")
        for row in await cursor.fetchall():
            await db.execute(
                "UPDATE mappings SET is_file = ? WHERE id = ?",
                (int(os.path.isfile(row[1] or "")), row[0]),
            )
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) "
            "VALUES ('mappings_is_file_backfilled', 'true')"
        )

    # Identificador estável por mapeamento. É a chave usada pelo arquivo de
    # configuração remota e pelo manifesto, independente dos IDs locais.
    mapping_columns = await _table_columns(db, "mappings")
    if "uid" not in mapping_columns:
        await db.execute("ALTER TABLE mappings ADD COLUMN uid TEXT")
    cursor = await db.execute(
        "SELECT id FROM mappings WHERE uid IS NULL OR TRIM(uid) = ''"
    )
    for row in await cursor.fetchall():
        await db.execute(
            "UPDATE mappings SET uid = ? WHERE id = ?",
            (str(uuid.uuid4()), row[0]),
        )
    await db.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_mappings_uid ON mappings(uid)"
    )

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
           SET status = 'cancelled',
               finished_at = COALESCE(finished_at, ?),
               error = COALESCE(error, 'app encerrado durante o sync')
           WHERE status = 'running' AND finished_at IS NULL""",
        (datetime.now().isoformat(),),
    )

    # Contadores de erros detalhados por run (migração de bancos antigos).
    run_columns = await _table_columns(db, "sync_runs")
    for name, definition in {
        "errors_total": "INTEGER NOT NULL DEFAULT 0",
        "errors_truncated": "INTEGER NOT NULL DEFAULT 0",
    }.items():
        if name not in run_columns:
            await db.execute(
                f"ALTER TABLE sync_runs ADD COLUMN {name} {definition}"
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


async def execute_many(query: str, params_list) -> int:
    """Executa a mesma query para várias linhas em uma única conexão."""
    params_list = list(params_list or [])
    if not params_list:
        return 0
    db = await get_db()
    try:
        await db.executemany(query, params_list)
        await db.commit()
        return len(params_list)
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


async def get_machine_identity() -> dict:
    """Retorna (e cria, se necessário) a identidade desta instalação."""
    machine_id = (await get_setting("machine_id") or "").strip()
    if not machine_id:
        machine_id = str(uuid.uuid4())
        await set_setting("machine_id", machine_id)

    machine_name = (await get_setting("machine_name") or "").strip()
    if not machine_name:
        machine_name = socket.gethostname() or "PC"
        await set_setting("machine_name", machine_name)

    return {"machine_id": machine_id, "machine_name": machine_name}