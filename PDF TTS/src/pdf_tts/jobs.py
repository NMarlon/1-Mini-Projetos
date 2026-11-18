"""Fila persistente de conversões para a interface local."""

from __future__ import annotations

import json
import logging
import queue
import sqlite3
import threading
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pdf_tts.config import ROOT
from pdf_tts.discover import Chapter, Discovery
from pdf_tts.generic import ConvertOptions, convert_pdf

logger = logging.getLogger("pdf_tts.jobs")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class JobManager:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._lock = threading.Lock()
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._queue: queue.Queue[str] = queue.Queue()
        self._create_schema()
        self._mark_interrupted()
        self._thread = threading.Thread(target=self._worker, name="pdf-tts-jobs", daemon=True)
        self._thread.start()

    def _create_schema(self) -> None:
        with self._lock:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    pdf_name TEXT NOT NULL,
                    pdf_path TEXT NOT NULL,
                    title TEXT,
                    status TEXT NOT NULL,
                    stage TEXT,
                    current INTEGER NOT NULL DEFAULT 0,
                    total INTEGER NOT NULL DEFAULT 0,
                    message TEXT,
                    output_dir TEXT,
                    manifest TEXT,
                    options_json TEXT NOT NULL,
                    coverage_json TEXT,
                    error TEXT,
                    log_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self.connection.commit()

    def _mark_interrupted(self) -> None:
        with self._lock:
            self.connection.execute(
                "UPDATE jobs SET status = 'interrupted', message = ?, updated_at = ? "
                "WHERE status IN ('queued', 'running')",
                ("O aplicativo foi fechado antes de terminar. Gere novamente para retomar do cache.", _now()),
            )
            self.connection.commit()

    def create(
        self,
        pdf_path: Path,
        analysis_path: Path,
        discovery: Discovery,
        options: ConvertOptions,
    ) -> str:
        job_id = uuid.uuid4().hex[:12]
        log_path = ROOT / "logs" / f"job-{job_id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chapter_mode": options.chapter_mode,
            "chapter_size": options.chapter_size,
            "manual_chapters": options.manual_chapters,
            "content_mode": options.content_mode,
            "voice": options.voice,
            "rate": options.rate,
            "analysis_path": str(analysis_path),
        }
        with self._lock:
            self.connection.execute(
                """
                INSERT INTO jobs
                (id, pdf_name, pdf_path, title, status, stage, current, total, message,
                 options_json, log_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'queued', 'na fila', 0, 0, 'Aguardando na fila.',
                        ?, ?, ?, ?)
                """,
                (
                    job_id,
                    pdf_path.name,
                    str(pdf_path),
                    discovery.title,
                    json.dumps(payload, ensure_ascii=False),
                    str(log_path),
                    _now(),
                    _now(),
                ),
            )
            self.connection.commit()
        self._queue.put(job_id)
        return job_id

    def _update(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = _now()
        columns = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [job_id]
        with self._lock:
            self.connection.execute(f"UPDATE jobs SET {columns} WHERE id = ?", values)
            self.connection.commit()

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def _worker(self) -> None:
        while True:
            job_id = self._queue.get()
            try:
                self._run(job_id)
            except Exception:  # noqa: BLE001 - o worker não pode morrer
                logger.exception("falha inesperada no job %s", job_id)
            finally:
                self._queue.task_done()

    def _run(self, job_id: str) -> None:
        job = self.get(job_id)
        if job is None:
            return
        options_data = json.loads(job["options_json"])
        analysis_path = Path(options_data["analysis_path"])
        discovery = Discovery.from_dict(json.loads(analysis_path.read_text(encoding="utf-8")))
        manual = options_data.get("manual_chapters")
        if manual:
            discovery.chapters = [
                Chapter(
                    number=index + 1,
                    title=str(item.get("title") or f"Parte {index + 1:02d}").strip(),
                    start_page=int(item["start_page"]),
                    end_page=int(item.get("end_page") or item["start_page"]),
                    confidence="manual",
                )
                for index, item in enumerate(manual)
            ]
        options = ConvertOptions(
            chapter_mode=options_data.get("chapter_mode", "auto"),
            chapter_size=int(options_data.get("chapter_size", 10)),
            manual_chapters=manual,
            content_mode=options_data.get("content_mode", "auto"),
            voice=options_data.get("voice"),
            rate=options_data.get("rate"),
        )
        self._update(
            job_id,
            status="running",
            stage="iniciando",
            message="Preparando a conversão…",
            current=0,
            total=0,
        )
        last = {"stage": "", "current": -1}

        def progress(stage: str, current: int, total: int, message: str) -> None:
            if stage == last["stage"] and current == last["current"]:
                return
            if stage == last["stage"] and current % 5 != 0 and current != total:
                return
            last["stage"] = stage
            last["current"] = current
            self._update(
                job_id,
                stage=stage,
                current=current,
                total=total,
                message=message,
            )

        try:
            result = convert_pdf(
                Path(job["pdf_path"]),
                options,
                progress_cb=progress,
                discovery=discovery,
            )
            coverage = result["coverage"]
            self._update(
                job_id,
                status="done",
                stage="concluído",
                current=coverage.get("chunks", 0),
                total=coverage.get("chunks", 0),
                message="Áudios gerados com sucesso.",
                output_dir=str(result["output_dir"]),
                manifest=str(result["manifest"]),
                coverage_json=json.dumps(coverage, ensure_ascii=False),
            )
        except Exception as exc:  # noqa: BLE001 - mostramos o erro na interface
            error = f"{type(exc).__name__}: {exc}"
            logger.error("job %s falhou: %s\n%s", job_id, error, traceback.format_exc())
            self._update(
                job_id,
                status="error",
                stage="erro",
                message=error,
                error=traceback.format_exc()[-4000:],
            )
