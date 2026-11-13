"""Execução do Restaurar com progresso por arquivo.

O planejamento fica em ``backend.restore``. Este módulo só baixa, grava e
atualiza o cache local. Ele é usado tanto pela rota bloqueante
``/api/restore/download`` quanto pelo job em background de
``/api/restore/start``.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from datetime import datetime
from typing import Optional

from backend import database
from backend.restore import (
    RestorePlan,
    RestoreTarget,
    compute_file_metadata,
)

MAX_PROGRESS_ERRORS = 200


def _failure(target: RestoreTarget, error: str) -> dict:
    return {
        "remote_path": target.remote_path,
        "local_path": target.local_path,
        "success": False,
        "overwritten": False,
        "action": "error",
        "error": error or "erro desconhecido",
    }


def _record_progress_error(progress: Optional[dict], target: RestoreTarget, error: str):
    if progress is None:
        return
    errors = progress.setdefault("errors", [])
    if len(errors) < MAX_PROGRESS_ERRORS:
        errors.append(
            {
                "remote_path": target.remote_path,
                "local_path": target.local_path,
                "mapping_name": target.mapping_name,
                "error": error,
            }
        )
    else:
        progress["errors_truncated"] = True


def _elapsed_seconds(progress: Optional[dict]) -> float:
    if not progress or not progress.get("started_at"):
        return 0.0
    try:
        started = datetime.fromisoformat(progress["started_at"])
        return max(0.0, (datetime.now() - started).total_seconds())
    except Exception:
        return 0.0


async def execute_restore(
    client,
    plan: RestorePlan,
    encryption_key: Optional[str],
    *,
    progress: Optional[dict] = None,
    cancel_event: Optional[asyncio.Event] = None,
) -> dict:
    """Executa o plano e devolve ``{"summary": ..., "results": [...]}``."""

    results = []
    plain_updates = []
    encrypted_updates = []
    now = datetime.now().isoformat()

    valid_targets = [
        target
        for target in plan.targets
        if target.action != "error" and target.local_path
    ]
    invalid_targets = [
        target
        for target in plan.targets
        if target.action == "error" or not target.local_path
    ]

    if progress is not None:
        progress.update(
            {
                "phase": "downloading",
                "started_at": progress.get("started_at")
                or datetime.now().isoformat(),
                "files_total": len(valid_targets),
                "files_done": 0,
                "files_created": 0,
                "files_replaced": 0,
                "files_failed": 0,
                "files_invalid": len(invalid_targets),
                "current_index": 0,
                "current_file": None,
                "current_mapping": None,
                "current_remote_path": None,
                "error": None,
                "errors": [],
                "errors_truncated": False,
                "summary": None,
            }
        )

    for target in invalid_targets:
        error = target.error or "erro desconhecido"
        results.append(_failure(target, error))
        _record_progress_error(progress, target, error)

    cancelled = False
    for index, target in enumerate(valid_targets, start=1):
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            break

        if progress is not None:
            progress.update(
                {
                    "phase": "downloading",
                    "current_index": index,
                    "current_file": target.local_path,
                    "current_mapping": target.mapping_name,
                    "current_remote_path": target.remote_path,
                }
            )

        local_path = target.local_path
        parent = os.path.dirname(local_path)
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception as exc:
            error = f"não foi possível criar a pasta: {exc}"
            results.append(_failure(target, error))
            _record_progress_error(progress, target, error)
            if progress is not None:
                progress["files_done"] += 1
                progress["files_failed"] += 1
            continue

        existed = os.path.exists(local_path)
        ok = False
        error = None
        try:
            if target.encrypted:
                if not encryption_key:
                    raise RuntimeError(
                        "arquivo criptografado, mas a chave de "
                        "criptografia não está configurada"
                    )
                from backend.encryption import decrypt_file

                tmp_enc = os.path.join(
                    tempfile.gettempdir(),
                    f"_restore_{uuid.uuid4().hex[:8]}.enc",
                )
                # O arquivo final é montado como .restore-part na mesma
                # pasta para que o os.replace seja atômico.
                part_path = local_path + ".restore-part"
                try:
                    ok = await client.download_file(
                        target.remote_path, tmp_enc
                    )
                    if ok:
                        await asyncio.to_thread(
                            decrypt_file,
                            encryption_key,
                            tmp_enc,
                            part_path,
                        )
                        os.replace(part_path, local_path)
                finally:
                    for path in (tmp_enc, part_path):
                        try:
                            if os.path.exists(path):
                                os.remove(path)
                        except Exception:
                            pass
            else:
                ok = await client.download_file(
                    target.remote_path, local_path
                )
        except Exception as exc:
            error = str(exc)
            ok = False

        if not ok:
            failure_error = error or "falha no download"
            results.append(_failure(target, failure_error))
            _record_progress_error(progress, target, failure_error)
            if progress is not None:
                progress["files_done"] += 1
                progress["files_failed"] += 1
            continue

        # Atualiza o cache local para o próximo sync não reenviar um
        # arquivo que já é idêntico ao que está no Terabox.
        size = target.size
        md5 = None
        mtime_ns = None
        try:
            metadata = await asyncio.to_thread(
                compute_file_metadata, local_path
            )
            size = metadata["size"]
            md5 = metadata["md5"]
            mtime_ns = metadata["mtime_ns"]
        except Exception:
            pass

        if target.mapping_id is not None and target.local_rel_path:
            if target.encrypted:
                if md5:
                    encrypted_updates.append(
                        (
                            size,
                            md5,
                            mtime_ns,
                            now,
                            target.mapping_id,
                            target.local_rel_path,
                        )
                    )
            elif md5:
                plain_updates.append(
                    (
                        size,
                        md5,
                        md5,
                        mtime_ns,
                        now,
                        target.mapping_id,
                        target.local_rel_path,
                    )
                )

        results.append(
            {
                "remote_path": target.remote_path,
                "local_path": local_path,
                "success": True,
                "overwritten": bool(existed),
                "action": "replaced" if existed else "created",
                "error": None,
            }
        )
        if progress is not None:
            progress["files_done"] += 1
            if existed:
                progress["files_replaced"] += 1
            else:
                progress["files_created"] += 1

    # A atualização do cache é secundária: os arquivos já foram
    # restaurados. Se o banco falhar, o próximo sync apenas reavalia.
    try:
        if plain_updates:
            await database.execute_many(
                """UPDATE files
                   SET size = ?, md5 = ?, remote_md5 = ?, mtime_ns = ?,
                       status = 'uploaded', last_synced_at = ?, error = NULL
                   WHERE mapping_id = ? AND local_rel_path = ?""",
                plain_updates,
            )
        if encrypted_updates:
            await database.execute_many(
                """UPDATE files
                   SET size = ?, md5 = ?, mtime_ns = ?,
                       status = 'uploaded', last_synced_at = ?, error = NULL
                   WHERE mapping_id = ? AND local_rel_path = ?""",
                encrypted_updates,
            )
    except Exception:
        pass

    restored = sum(1 for result in results if result["success"])
    replaced = sum(
        1
        for result in results
        if result["success"] and result["overwritten"]
    )
    summary = {
        "total": len(plan.targets),
        "restored": restored,
        "created": restored - replaced,
        "replaced": replaced,
        "failed": len(results) - restored,
        "invalid": len(invalid_targets),
        "cancelled": cancelled,
    }

    if progress is not None:
        progress["files_done"] = len(results) - len(invalid_targets)
        progress["summary"] = summary
        progress["finished_at"] = datetime.now().isoformat()
        progress["elapsed_seconds"] = _elapsed_seconds(progress)
        progress["phase"] = "cancelled" if cancelled else "finished"
        progress["current_file"] = None
        progress["current_mapping"] = None
        progress["current_remote_path"] = None
        progress["current_index"] = 0
        if cancelled:
            progress["cancel_requested"] = True

    return {"summary": summary, "results": results}
