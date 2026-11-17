"""Estado persistente dos chunks (SQLite) para retomada."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class StateStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                key TEXT PRIMARY KEY,
                lesson_id TEXT,
                chunk_id TEXT,
                status TEXT NOT NULL,
                audio_path TEXT,
                duration REAL,
                attempts INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_lesson ON chunks(lesson_id)"
        )
        self.connection.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def get(self, key: str) -> dict[str, Any] | None:
        row = self.connection.execute("SELECT * FROM chunks WHERE key = ?", (key,)).fetchone()
        return dict(row) if row else None

    def mark_running(self, key: str, lesson_id: str, chunk_id: str) -> None:
        self.connection.execute(
            """
            INSERT INTO chunks (key, lesson_id, chunk_id, status, updated_at)
            VALUES (?, ?, ?, 'running', ?)
            ON CONFLICT(key) DO UPDATE SET
                lesson_id = excluded.lesson_id,
                chunk_id = excluded.chunk_id,
                status = 'running',
                updated_at = excluded.updated_at
            """,
            (key, lesson_id, chunk_id, self._now()),
        )
        self.connection.commit()

    def mark_done(self, key: str, lesson_id: str, chunk_id: str, audio_path: Path, duration: float, attempts: int) -> None:
        self.connection.execute(
            """
            INSERT INTO chunks (key, lesson_id, chunk_id, status, audio_path, duration, attempts, updated_at)
            VALUES (?, ?, ?, 'done', ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                status = 'done',
                audio_path = excluded.audio_path,
                duration = excluded.duration,
                attempts = excluded.attempts,
                error = NULL,
                updated_at = excluded.updated_at
            """,
            (key, lesson_id, chunk_id, str(audio_path), duration, attempts, self._now()),
        )
        self.connection.commit()

    def mark_failed(self, key: str, lesson_id: str, chunk_id: str, error: str, attempts: int) -> None:
        self.connection.execute(
            """
            INSERT INTO chunks (key, lesson_id, chunk_id, status, attempts, error, updated_at)
            VALUES (?, ?, ?, 'failed', ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                status = 'failed',
                attempts = excluded.attempts,
                error = excluded.error,
                updated_at = excluded.updated_at
            """,
            (key, lesson_id, chunk_id, attempts, error[:2000], self._now()),
        )
        self.connection.commit()

    def counts(self, lesson_id: str | None = None) -> dict[str, int]:
        if lesson_id:
            rows = self.connection.execute(
                "SELECT status, COUNT(*) AS n FROM chunks WHERE lesson_id = ? GROUP BY status",
                (lesson_id,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT status, COUNT(*) AS n FROM chunks GROUP BY status"
            ).fetchall()
        return {str(row["status"]): int(row["n"]) for row in rows}

    def failed(self, lesson_id: str | None = None) -> list[dict[str, Any]]:
        if lesson_id:
            rows = self.connection.execute(
                "SELECT * FROM chunks WHERE status = 'failed' AND lesson_id = ?", (lesson_id,)
            ).fetchall()
        else:
            rows = self.connection.execute("SELECT * FROM chunks WHERE status = 'failed'").fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> StateStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
