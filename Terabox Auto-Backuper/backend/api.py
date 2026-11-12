"""Rotas da API FastAPI."""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend import database
from backend.models import (
    Mapping, MappingCreate, MappingUpdate, MappingBulkEnabled,
    SyncStatus, SyncRequest, Settings, SettingsUpdate,
    AuthStatus, AuthConnect, AuthConnectManual, BrowserProfile, HealthResponse,
    RestorePlanRequest, RestoreRequest, CsvImportRequest,
    RemoteConfigSaveRequest, RemoteConfigImportRequest,
)
from backend import auth
from backend.remote_config import (
    RemoteConfigConflict,
    RemoteConfigEmpty,
    RemoteConfigError,
    RemoteConfigInvalid,
    RemoteConfigNotAuthenticated,
    normalize_config_path,
    remote_config_manager,
)
from backend.config import DEFAULT_REMOTE_CONFIG_PATH
from backend.sync_engine import sync_engine
from backend.file_monitor import FileMonitor
from backend.scheduler import SyncScheduler
from backend import windows_startup
from backend.process_utils import run_hidden
from backend.csv_import import parse_mapping_csv
from backend.local_paths import LocalPathError, validate_local_mapping_path
from backend.paths import (
    normalize_remote,
    sanitize_remote_path,
)
from backend.restore import (
    build_restore_plan,
    compute_file_metadata,
)

router = APIRouter()

# Instâncias globais
file_monitor = FileMonitor()
sync_scheduler = SyncScheduler()

# ── Health ──

@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


# ── Auth ──

# Estado global do processo de conexão (roda em background para sobreviver
# ao fechamento do navegador que hospeda a UI, ex.: Dia)
_auth_task: Optional[asyncio.Task] = None
_auth_state = {"connecting": False, "error": None}


async def _do_connect(browser: str, profile: Optional[str]):
    global _auth_state
    try:
        result = await auth.connect(browser, profile)
        _auth_state["error"] = result.get("error") if result.get("status") == "error" else None
    except Exception as e:
        _auth_state["error"] = str(e)
    finally:
        _auth_state["connecting"] = False


@router.post("/auth/connect", response_model=AuthStatus)
async def auth_connect(body: AuthConnect):
    global _auth_task, _auth_state
    if _auth_task and not _auth_task.done():
        # Já está conectando
        current = await auth.get_status()
        return AuthStatus(**current, connecting=True)
    _auth_state = {"connecting": True, "error": None}
    _auth_task = asyncio.create_task(_do_connect(body.browser, body.profile))
    current = await auth.get_status()
    return AuthStatus(**current, connecting=True, error=None)


@router.get("/auth/profiles")
async def auth_profiles(browser: str = "chrome"):
    profiles = auth.list_browser_profiles(browser)
    # Verificar quais têm cookie Terabox
    result = []
    for p in profiles:
        has_tb = auth.check_profile_has_terabox(browser, p["name"])
        result.append({
            "name": p["name"],
            "path": p["path"],
            "is_default": p["is_default"],
            "has_terabox": has_tb,
        })
    return result


@router.post("/auth/connect-manual", response_model=AuthStatus)
async def auth_connect_manual(body: AuthConnectManual):
    result = await auth.connect_manual(body.cookies)
    if result.get("status") == "error":
        return AuthStatus(authenticated=False, error=result.get("error"))
    status = await auth.get_status()
    return AuthStatus(**status)


@router.get("/auth/status", response_model=AuthStatus)
async def auth_status():
    status = await auth.get_status()
    return AuthStatus(**status, connecting=_auth_state.get("connecting", False), error=_auth_state.get("error"))


@router.post("/auth/disconnect")
async def auth_disconnect():
    await auth.disconnect()
    return {"status": "ok"}


# ── Mappings ──

def _mapping_model(row: dict) -> Mapping:
    data = dict(row)
    data["include_subfolders"] = bool(data.get("include_subfolders"))
    data["encrypt"] = bool(data.get("encrypt"))
    data["enabled"] = bool(data.get("enabled"))
    data["is_file"] = bool(data.get("is_file"))
    return Mapping(**data)


@router.get("/mappings", response_model=List[Mapping])
async def list_mappings():
    rows = await database.fetch_all("SELECT * FROM mappings ORDER BY id")
    return [_mapping_model(r) for r in rows]


@router.post("/mappings", response_model=Mapping)
async def create_mapping(body: MappingCreate):
    try:
        path_info = validate_local_mapping_path(
            body.local_path, body.is_file
        )
    except LocalPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    local_path = path_info.path
    remote_path = sanitize_remote_path(normalize_remote(body.remote_path))
    if remote_path == "/":
        raise HTTPException(status_code=400, detail="O destino remoto não pode ser a raiz do Terabox.")

    # Verificar duplicado (sem diferenciar maiúsculas/minúsculas)
    existing = await database.fetch_one(
        "SELECT * FROM mappings WHERE local_path = ? COLLATE NOCASE AND remote_path = ? COLLATE NOCASE",
        (local_path, remote_path),
    )
    if existing:
        if (
            body.is_file is not None
            and bool(existing.get("is_file")) != path_info.is_file
        ):
            kind = "arquivo" if existing.get("is_file") else "pasta"
            raise HTTPException(
                status_code=409,
                detail=(
                    "Já existe um mapeamento deste caminho como "
                    f"{kind}. Edite o mapeamento existente em vez de criar "
                    "outro."
                ),
            )
        return _mapping_model(existing)

    # Só cria a pasta depois de todas as validações e da checagem de duplicado.
    try:
        path_info = validate_local_mapping_path(
            local_path, path_info.is_file, create=True
        )
    except LocalPathError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    is_file = path_info.is_file
    now = datetime.now().isoformat()
    mid = await database.execute(
        """INSERT INTO mappings
           (uid, name, local_path, remote_path, include_subfolders, encrypt,
            enabled, is_file, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()),
         body.name.strip() or os.path.basename(local_path.rstrip("\\/")), local_path, remote_path,
         int(bool(body.include_subfolders) and not is_file),
         int(body.encrypt), int(body.enabled), int(is_file), now, now),
    )
    row = await database.fetch_one("SELECT * FROM mappings WHERE id = ?", (mid,))
    await _reload_file_monitor()
    remote_config_manager.request_save("mapping_created")
    return _mapping_model(row)


@router.put("/mappings/bulk-enabled")
async def bulk_enable_mappings(body: MappingBulkEnabled):
    """Liga/desliga vários mapeamentos de uma vez.

    A seleção é persistida no campo ``enabled``. O sync manual envia apenas os
    IDs marcados e o Auto-sync lê ``enabled = 1`` do banco, então os dois usam
    exatamente a mesma seleção.
    """
    if not body.ids:
        return {
            "updated": 0,
            "enabled": body.enabled,
            "mappings": [_mapping_model(r) for r in await database.fetch_all(
                "SELECT * FROM mappings ORDER BY id"
            )],
        }

    placeholders = ",".join("?" * len(body.ids))
    now = datetime.now().isoformat()
    await database.execute(
        f"UPDATE mappings SET enabled = ?, updated_at = ? WHERE id IN ({placeholders})",
        (int(body.enabled), now, *body.ids),
    )
    await _reload_file_monitor()
    remote_config_manager.request_save("mappings_enabled")

    rows = await database.fetch_all("SELECT * FROM mappings ORDER BY id")
    return {
        "updated": len(body.ids),
        "enabled": body.enabled,
        "mappings": [_mapping_model(r) for r in rows],
    }


@router.put("/mappings/{mapping_id}", response_model=Mapping)
async def update_mapping(mapping_id: int, body: MappingUpdate):
    existing = await database.fetch_one("SELECT * FROM mappings WHERE id = ?", (mapping_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Mapeamento não encontrado")
    updates = {}
    path_changed = False
    type_changed = False
    target_is_file = bool(existing.get("is_file"))

    if body.name is not None:
        updates["name"] = body.name
    if body.local_path is not None:
        try:
            path_info = validate_local_mapping_path(
                body.local_path,
                body.is_file,
                fallback_is_file=(
                    bool(existing.get("is_file"))
                    if body.is_file is None
                    else None
                ),
            )
        except LocalPathError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        target_is_file = path_info.is_file
        type_changed = bool(existing.get("is_file")) != target_is_file
        path_changed = True
        updates["local_path"] = path_info.path
        updates["is_file"] = int(target_is_file)
    elif body.is_file is not None:
        try:
            path_info = validate_local_mapping_path(
                existing.get("local_path") or "", body.is_file
            )
        except LocalPathError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        target_is_file = path_info.is_file
        type_changed = bool(existing.get("is_file")) != target_is_file
        updates["is_file"] = int(target_is_file)

    if body.remote_path is not None:
        remote_path = sanitize_remote_path(normalize_remote(body.remote_path))
        if remote_path == "/":
            raise HTTPException(status_code=400, detail="O destino remoto não pode ser a raiz do Terabox.")
        updates["remote_path"] = remote_path
    if body.include_subfolders is not None:
        updates["include_subfolders"] = int(body.include_subfolders)
    # Um mapeamento de arquivo único não tem subpastas
    if target_is_file:
        updates["include_subfolders"] = 0
    elif type_changed and body.include_subfolders is None:
        updates["include_subfolders"] = 1

    if path_changed or type_changed:
        try:
            validate_local_mapping_path(
                updates.get("local_path", existing.get("local_path")),
                target_is_file,
                create=True,
            )
        except LocalPathError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if body.encrypt is not None:
        updates["encrypt"] = int(body.encrypt)
    if body.enabled is not None:
        updates["enabled"] = int(body.enabled)
    updates["updated_at"] = datetime.now().isoformat()

    # Se origem/destino/criptografia mudou, o cache de arquivos não vale mais
    if any(k in updates for k in ("local_path", "remote_path", "encrypt")):
        await database.execute("DELETE FROM files WHERE mapping_id = ?", (mapping_id,))

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [mapping_id]
    await database.execute(f"UPDATE mappings SET {set_clause} WHERE id = ?", tuple(values))

    row = await database.fetch_one("SELECT * FROM mappings WHERE id = ?", (mapping_id,))
    await _reload_file_monitor()
    remote_config_manager.request_save("mapping_updated")
    return _mapping_model(row)


@router.delete("/mappings/{mapping_id}")
async def delete_mapping(mapping_id: int):
    # Excluir o cache antes do mapeamento (funciona mesmo se FK estiver off)
    await database.execute("DELETE FROM files WHERE mapping_id = ?", (mapping_id,))
    await database.execute("DELETE FROM mappings WHERE id = ?", (mapping_id,))
    await _reload_file_monitor()
    remote_config_manager.request_save("mapping_deleted")
    return {"status": "ok"}


@router.post("/mappings/import-csv")
async def import_mappings_csv(body: CsvImportRequest):
    """Importa uma lista colada no formato ``origem; destino``.

    Com ``dry_run=true`` apenas valida e devolve o que seria criado.
    """
    entries, errors = parse_mapping_csv(body.csv)
    parsed = []
    created = []
    would_create = []
    skipped = []
    seen = set()

    for entry in entries:
        name = os.path.basename(entry.source.rstrip("\\/")) or "Importado"
        if entry.source_is_file:
            name = f"Arquivo: {name}"
        item = {
            "line": entry.line,
            "name": name,
            "local_path": entry.source,
            "remote_path": entry.destination,
            "is_file": entry.source_is_file,
            "warnings": list(getattr(entry, "warnings", []) or []),
        }
        parsed.append(item)

        key = (entry.source.lower(), entry.destination.lower())
        if key in seen:
            skipped.append({**item, "reason": "duplicado na lista"})
            continue
        seen.add(key)

        existing = await database.fetch_one(
            "SELECT * FROM mappings WHERE local_path = ? COLLATE NOCASE AND remote_path = ? COLLATE NOCASE",
            (entry.source, entry.destination),
        )
        if existing:
            skipped.append({**item, "reason": "já existe"})
            continue

        if body.dry_run:
            would_create.append(item)
            continue

        try:
            path_info = validate_local_mapping_path(
                entry.source, entry.source_is_file, create=True
            )
        except LocalPathError as exc:
            errors.append({"line": entry.line, "error": str(exc)})
            continue

        now = datetime.now().isoformat()
        mid = await database.execute(
            """INSERT INTO mappings
               (uid, name, local_path, remote_path, include_subfolders, encrypt,
                enabled, is_file, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                name,
                path_info.path,
                entry.destination,
                int(body.include_subfolders and not path_info.is_file),
                int(body.encrypt),
                int(body.enabled),
                int(path_info.is_file),
                now,
                now,
            ),
        )
        row = await database.fetch_one("SELECT * FROM mappings WHERE id = ?", (mid,))
        created.append(_mapping_model(row))

    if created:
        await _reload_file_monitor()
        remote_config_manager.request_save("mappings_imported")

    return {
        "dry_run": body.dry_run,
        "parsed": parsed,
        "created": created,
        "would_create": would_create,
        "skipped": skipped,
        "errors": errors,
    }


async def _reload_file_monitor():
    """Recarrega o file monitor com os mapeamentos atuais."""
    try:
        mappings = await database.fetch_all(
            "SELECT local_path, is_file FROM mappings WHERE enabled = 1"
        )
        async def _cb():
            auto = await database.get_setting("auto_sync")
            if auto == "true":
                await sync_engine.start_sync()
        file_monitor.start(mappings, _cb, debounce_seconds=2.0)
    except Exception:
        pass


# ── Sync ──

@router.post("/sync/preview")
async def sync_preview(body: Optional[SyncRequest] = None):
    """Calcula o que será enviado/substituído/ignorado, sem alterar nada."""
    try:
        return await sync_engine.preview(body.mapping_ids if body else None)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha ao gerar prévia: {exc}")


@router.post("/sync/start")
async def sync_start(body: Optional[SyncRequest] = None):
    run_id = await sync_engine.start_sync(body.mapping_ids if body else None)
    return {"run_id": run_id, "status": "started"}


@router.post("/sync/stop")
async def sync_stop():
    await sync_engine.stop_sync()
    return {"status": "ok"}


@router.get("/sync/status", response_model=SyncStatus)
async def sync_status():
    s = sync_engine.get_status()
    return SyncStatus(**s)


@router.get("/sync/history")
async def sync_history(limit: int = 20, offset: int = 0):
    rows = await database.fetch_all(
        "SELECT * FROM sync_runs ORDER BY id DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    return rows


@router.get("/sync/stream")
async def sync_stream():
    """SSE stream de eventos de sync."""
    async def event_generator():
        queue = asyncio.Queue()
        async def listener(event, data):
            await queue.put({"event": event, "data": data})
        sync_engine.add_listener(listener)
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            sync_engine.remove_listener(listener)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Restaurar ──

async def _download_manifest(client) -> Optional[dict]:
    """Baixa o manifesto remoto para um arquivo temporário e devolve o JSON."""
    import tempfile
    import uuid

    tmp = os.path.join(tempfile.gettempdir(), f"_manifest_{uuid.uuid4().hex[:8]}.json")
    try:
        ok = await client.download_file("/_terabox_autobackup_manifest.json", tmp)
        if not ok:
            return None
        with open(tmp, "r", encoding="utf-8") as f:
            return json.load(f)
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


@router.get("/restore/manifest")
async def restore_manifest():
    """Baixa e retorna o manifesto do Terabox."""
    auth_data = await auth.get_cached_auth()
    if not auth_data:
        raise HTTPException(status_code=401, detail="Não autenticado")
    from backend.terabox_client import TeraboxClient
    client = TeraboxClient(auth_data["cookies"], auth_data["jstoken"])
    try:
        manifest = await _download_manifest(client)
        if manifest is None:
            return {"version": "2.0", "files": [], "directories": [],
                    "error": "Manifesto não encontrado no Terabox"}
        return manifest
    finally:
        await client.close()


async def _load_restore_context(client):
    """Baixa o manifesto e carrega os mapeamentos atuais."""
    manifest = await _download_manifest(client)
    if manifest is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Manifesto não encontrado no Terabox. "
                "Faça um backup antes de restaurar."
            ),
        )
    mappings = await database.fetch_all("SELECT * FROM mappings ORDER BY id")
    return manifest, mappings


@router.post("/restore/plan")
async def restore_plan(body: RestorePlanRequest):
    """Prévia da restauração: destinos, conflitos e erros, sem baixar nada."""
    auth_data = await auth.get_cached_auth()
    if not auth_data:
        raise HTTPException(status_code=401, detail="Não autenticado")
    from backend.terabox_client import TeraboxClient
    client = TeraboxClient(auth_data["cookies"], auth_data["jstoken"])
    try:
        manifest, mappings = await _load_restore_context(client)
        plan = build_restore_plan(body.files, manifest, mappings)
        return plan.to_dict()
    finally:
        await client.close()


def _restore_result_failure(target, error: str) -> dict:
    return {
        "remote_path": target.remote_path,
        "local_path": target.local_path,
        "success": False,
        "overwritten": False,
        "action": "error",
        "error": error or "erro desconhecido",
    }


@router.post("/restore/download")
async def restore_download(body: RestoreRequest):
    auth_data = await auth.get_cached_auth()
    if not auth_data:
        raise HTTPException(status_code=401, detail="Não autenticado")
    from backend.terabox_client import TeraboxClient
    client = TeraboxClient(auth_data["cookies"], auth_data["jstoken"])
    try:
        manifest, mappings = await _load_restore_context(client)
        plan = build_restore_plan(body.files, manifest, mappings)

        conflicts = [
            target for target in plan.targets if target.action == "replace"
        ]
        if conflicts and not body.allow_overwrite:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": (
                        f"{len(conflicts)} arquivo(s) já existem e precisam "
                        "de confirmação para serem substituídos."
                    ),
                    "summary": plan.summary,
                    "conflicts": [
                        target.to_dict() for target in conflicts[:100]
                    ],
                },
            )

        needs_key = any(
            target.encrypted and target.action != "error"
            for target in plan.targets
        )
        encryption_key = (
            await database.get_setting("encryption_key") if needs_key else None
        )

        results = []
        plain_updates = []
        encrypted_updates = []
        now = datetime.now().isoformat()

        for target in plan.targets:
            if target.action == "error" or not target.local_path:
                results.append(
                    _restore_result_failure(
                        target, target.error or "erro desconhecido"
                    )
                )
                continue

            local_path = target.local_path
            parent = os.path.dirname(local_path)
            try:
                os.makedirs(parent, exist_ok=True)
            except Exception as exc:
                results.append(
                    _restore_result_failure(
                        target, f"não foi possível criar a pasta: {exc}"
                    )
                )
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
                    import tempfile
                    import uuid

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
                results.append(
                    _restore_result_failure(
                        target, error or "falha no download"
                    )
                )
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
        return {
            "summary": {
                "restored": restored,
                "created": restored - replaced,
                "replaced": replaced,
                "failed": len(results) - restored,
            },
            "results": results,
        }
    finally:
        await client.close()


# ── Configuração remota de mapeamentos ──

def _remote_config_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, RemoteConfigNotAuthenticated):
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, RemoteConfigError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(
        status_code=500,
        detail=f"Falha na configuração remota: {exc}",
    )


@router.get("/remote-config")
async def remote_config_status(check_remote: bool = False):
    """Status do cadastro remoto. ``check_remote=true`` consulta o Terabox."""
    return await remote_config_manager.status(check_remote=check_remote)


@router.post("/remote-config/save")
async def remote_config_save(body: Optional[RemoteConfigSaveRequest] = None):
    """Salva agora, mesclando com o arquivo remoto existente."""
    try:
        return await remote_config_manager.save_now(
            force=bool(body and body.force),
            reason="manual",
        )
    except Exception as exc:
        raise _remote_config_http_error(exc) from exc


@router.post("/remote-config/import/plan")
async def remote_config_import_plan():
    """Baixa a configuração remota e monta a revisão de importação."""
    try:
        return await remote_config_manager.import_plan()
    except Exception as exc:
        raise _remote_config_http_error(exc) from exc


@router.post("/remote-config/import")
async def remote_config_import(body: RemoteConfigImportRequest):
    """Importa somente os mapeamentos confirmados na revisão."""
    try:
        result = await remote_config_manager.apply_import(
            body.config_hash,
            [item.model_dump() for item in body.mappings],
        )
    except Exception as exc:
        raise _remote_config_http_error(exc) from exc

    if body.adopt_path and result.get("config_path"):
        try:
            discovered = normalize_config_path(result["config_path"])
        except RemoteConfigError:
            discovered = None
        current = (
            await database.get_setting("remote_config_path")
            or DEFAULT_REMOTE_CONFIG_PATH
        )
        if discovered and discovered != current:
            await database.set_setting("remote_config_path", discovered)
            result["adopted_path"] = discovered

    await _reload_file_monitor()

    if body.mappings and (result.get("created") or result.get("updated")):
        remote_config_manager.request_save("remote_config_imported")
        try:
            saved = await remote_config_manager.save_now(
                reason="remote_config_imported"
            )
            result["remote_config_saved"] = bool(saved.get("saved"))
        except Exception as exc:
            result["remote_config_save_error"] = str(exc)

    return result


# ── Settings ──

@router.get("/settings", response_model=Settings)
async def get_settings():
    data = {}
    for key in (
        "sync_interval_minutes",
        "auto_sync",
        "notifications",
        "max_concurrent_uploads",
        "autostart",
        "browser_preference",
        "restore_confirm_overwrite",
        "machine_name",
        "remote_config_enabled",
        "remote_config_path",
        "remote_config_auto_save",
    ):
        val = await database.get_setting(key)
        data[key] = val
    machine = await database.get_machine_identity()
    return Settings(
        sync_interval_minutes=int(data.get("sync_interval_minutes", 30)),
        auto_sync=data.get("auto_sync", "true") == "true",
        notifications=data.get("notifications", "true") == "true",
        max_concurrent_uploads=int(data.get("max_concurrent_uploads", 3)),
        autostart=data.get("autostart", "false") == "true",
        browser_preference=data.get("browser_preference", "auto"),
        encryption_key=data.get("encryption_key"),
        restore_confirm_overwrite=(
            data.get("restore_confirm_overwrite", "true") == "true"
        ),
        machine_name=data.get("machine_name") or machine["machine_name"],
        remote_config_enabled=(
            data.get("remote_config_enabled", "true") == "true"
        ),
        remote_config_path=(
            data.get("remote_config_path") or DEFAULT_REMOTE_CONFIG_PATH
        ),
        remote_config_auto_save=(
            data.get("remote_config_auto_save", "true") == "true"
        ),
    )


@router.put("/settings", response_model=Settings)
async def update_settings(body: SettingsUpdate):
    if body.sync_interval_minutes is not None:
        await database.set_setting("sync_interval_minutes", str(body.sync_interval_minutes))
    if body.auto_sync is not None:
        await database.set_setting("auto_sync", "true" if body.auto_sync else "false")
        try:
            await sync_scheduler.enable(body.auto_sync)
        except Exception:
            pass
    if body.notifications is not None:
        await database.set_setting("notifications", "true" if body.notifications else "false")
    if body.max_concurrent_uploads is not None:
        await database.set_setting("max_concurrent_uploads", str(body.max_concurrent_uploads))
        sync_engine._max_concurrent = body.max_concurrent_uploads
    if body.autostart is not None:
        await database.set_setting("autostart", "true" if body.autostart else "false")
        if body.autostart:
            windows_startup.enable()
        else:
            windows_startup.disable()
    if body.browser_preference is not None:
        await database.set_setting("browser_preference", body.browser_preference)
    if body.encryption_key is not None:
        await database.set_setting("encryption_key", body.encryption_key)
    if body.restore_confirm_overwrite is not None:
        await database.set_setting(
            "restore_confirm_overwrite",
            "true" if body.restore_confirm_overwrite else "false",
        )

    remote_config_changed = False
    if body.machine_name is not None:
        machine_name = " ".join(body.machine_name.split())[:80].strip()
        if not machine_name:
            raise HTTPException(
                status_code=400,
                detail="O nome deste computador não pode ficar vazio.",
            )
        await database.set_setting("machine_name", machine_name)
        remote_config_changed = True
    if body.remote_config_enabled is not None:
        await database.set_setting(
            "remote_config_enabled",
            "true" if body.remote_config_enabled else "false",
        )
        remote_config_changed = True
    if body.remote_config_path is not None:
        try:
            remote_path = normalize_config_path(body.remote_config_path)
        except RemoteConfigError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        await database.set_setting("remote_config_path", remote_path)
        remote_config_changed = True
    if body.remote_config_auto_save is not None:
        await database.set_setting(
            "remote_config_auto_save",
            "true" if body.remote_config_auto_save else "false",
        )

    if remote_config_changed:
        enabled = await database.get_setting("remote_config_enabled")
        if enabled != "false":
            remote_config_manager.request_save("settings_changed")

    # Atualizar scheduler se necessário
    if body.sync_interval_minutes is not None:
        await sync_scheduler.update_interval(body.sync_interval_minutes)

    return await get_settings()


# ── Status geral ──

@router.get("/system/pick-folder")
async def pick_folder():
    """Abre o seletor de pastas nativo do Windows e retorna o caminho escolhido."""
    import shutil as _shutil

    ps_script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$f = New-Object System.Windows.Forms.FolderBrowserDialog;"
        "$f.Description = 'Selecione a pasta';"
        "$f.ShowNewFolderButton = $true;"
        "$r = $f.ShowDialog();"
        "if ($r -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.SelectedPath }"
    )

    def _run_powershell() -> str:
        exe = _shutil.which("powershell") or "powershell"
        try:
            out = run_hidden(
                [exe, "-NoProfile", "-STA", "-Command", ps_script],
                capture_output=True, text=True, timeout=300,
            )
            return (out.stdout or "").strip()
        except Exception:
            return ""

    path = await asyncio.to_thread(_run_powershell)
    return {"path": path}


@router.get("/system/pick-file")
async def pick_file():
    """Abre o seletor de arquivos nativo do Windows."""
    import shutil as _shutil

    ps_script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$f = New-Object System.Windows.Forms.OpenFileDialog;"
        "$f.Title = 'Selecione o arquivo';"
        "$f.Filter = 'Todos os arquivos (*.*)|*.*';"
        "$r = $f.ShowDialog();"
        "if ($r -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $f.FileName }"
    )

    def _run_powershell() -> str:
        exe = _shutil.which("powershell") or "powershell"
        try:
            out = run_hidden(
                [exe, "-NoProfile", "-STA", "-Command", ps_script],
                capture_output=True, text=True, timeout=300,
            )
            return (out.stdout or "").strip()
        except Exception:
            return ""

    path = await asyncio.to_thread(_run_powershell)
    return {"path": path}


@router.get("/status")
async def general_status():
    auth_st = await auth.get_status()
    sync_st = sync_engine.get_status()
    return {
        "auth": auth_st,
        "sync": sync_st,
        "scheduler_running": sync_scheduler.scheduler.running if sync_scheduler.scheduler else False,
        "file_monitor_running": file_monitor.is_running(),
        "autostart_enabled": windows_startup.is_enabled(),
    }