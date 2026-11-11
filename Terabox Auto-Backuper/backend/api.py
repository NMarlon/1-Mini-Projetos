"""Rotas da API FastAPI."""

import asyncio
import json
import os
import posixpath
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend import database
from backend.models import (
    Mapping, MappingCreate, MappingUpdate, MappingBulkEnabled,
    SyncStatus, SyncRequest, Settings, SettingsUpdate,
    AuthStatus, AuthConnect, AuthConnectManual, BrowserProfile, HealthResponse,
    RestoreRequest, CsvImportRequest,
)
from backend import auth
from backend.sync_engine import sync_engine
from backend.file_monitor import FileMonitor
from backend.scheduler import SyncScheduler
from backend import windows_startup
from backend.process_utils import run_hidden
from backend.csv_import import parse_mapping_csv
from backend.paths import (
    is_safe_relative_path,
    normalize_local,
    normalize_remote,
    sanitize_remote_path,
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
    data["is_file"] = os.path.isfile(data.get("local_path") or "")
    return Mapping(**data)


@router.get("/mappings", response_model=List[Mapping])
async def list_mappings():
    rows = await database.fetch_all("SELECT * FROM mappings ORDER BY id")
    return [_mapping_model(r) for r in rows]


@router.post("/mappings", response_model=Mapping)
async def create_mapping(body: MappingCreate):
    local_path = normalize_local(body.local_path)
    remote_path = sanitize_remote_path(normalize_remote(body.remote_path))
    if remote_path == "/":
        raise HTTPException(status_code=400, detail="O destino remoto não pode ser a raiz do Terabox.")
    if not os.path.exists(local_path):
        raise HTTPException(status_code=400, detail=f"Origem não encontrada: {local_path}")

    # Verificar duplicado (sem diferenciar maiúsculas/minúsculas)
    existing = await database.fetch_one(
        "SELECT * FROM mappings WHERE local_path = ? COLLATE NOCASE AND remote_path = ? COLLATE NOCASE",
        (local_path, remote_path),
    )
    if existing:
        return _mapping_model(existing)
    now = datetime.now().isoformat()
    mid = await database.execute(
        """INSERT INTO mappings (name, local_path, remote_path, include_subfolders, encrypt, enabled, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (body.name.strip() or os.path.basename(local_path.rstrip("\\/")), local_path, remote_path,
         int(bool(body.include_subfolders) and not os.path.isfile(local_path)),
         int(body.encrypt), int(body.enabled), now, now),
    )
    row = await database.fetch_one("SELECT * FROM mappings WHERE id = ?", (mid,))
    await _reload_file_monitor()
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
    if body.name is not None:
        updates["name"] = body.name
    if body.local_path is not None:
        local_path = normalize_local(body.local_path)
        if not os.path.exists(local_path):
            raise HTTPException(status_code=400, detail=f"Origem não encontrada: {local_path}")
        updates["local_path"] = local_path
    if body.remote_path is not None:
        remote_path = sanitize_remote_path(normalize_remote(body.remote_path))
        if remote_path == "/":
            raise HTTPException(status_code=400, detail="O destino remoto não pode ser a raiz do Terabox.")
        updates["remote_path"] = remote_path
    if body.include_subfolders is not None:
        updates["include_subfolders"] = int(body.include_subfolders)
    # Um mapeamento de arquivo único não tem subpastas
    final_local = updates.get("local_path", existing.get("local_path"))
    if final_local and os.path.isfile(final_local):
        updates["include_subfolders"] = 0
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
    return _mapping_model(row)


@router.delete("/mappings/{mapping_id}")
async def delete_mapping(mapping_id: int):
    # Excluir o cache antes do mapeamento (funciona mesmo se FK estiver off)
    await database.execute("DELETE FROM files WHERE mapping_id = ?", (mapping_id,))
    await database.execute("DELETE FROM mappings WHERE id = ?", (mapping_id,))
    await _reload_file_monitor()
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

        now = datetime.now().isoformat()
        mid = await database.execute(
            """INSERT INTO mappings
               (name, local_path, remote_path, include_subfolders, encrypt, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                entry.source,
                entry.destination,
                int(body.include_subfolders and not entry.source_is_file),
                int(body.encrypt),
                int(body.enabled),
                now,
                now,
            ),
        )
        row = await database.fetch_one("SELECT * FROM mappings WHERE id = ?", (mid,))
        created.append(_mapping_model(row))

    if created:
        await _reload_file_monitor()

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
        mappings = await database.fetch_all("SELECT local_path FROM mappings WHERE enabled = 1")
        paths = [m["local_path"] for m in mappings]
        async def _cb():
            auto = await database.get_setting("auto_sync")
            if auto == "true":
                await sync_engine.start_sync()
        file_monitor.start(paths, _cb, debounce_seconds=2.0)
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


@router.post("/restore/download")
async def restore_download(body: RestoreRequest):
    auth_data = await auth.get_cached_auth()
    if not auth_data:
        raise HTTPException(status_code=401, detail="Não autenticado")
    from backend.terabox_client import TeraboxClient
    client = TeraboxClient(auth_data["cookies"], auth_data["jstoken"])
    dest = Path(normalize_local(body.destination))
    dest.mkdir(parents=True, exist_ok=True)

    manifest = await _download_manifest(client)
    manifest_map = {}
    if manifest:
        manifest_map = {
            normalize_remote(f.get("remote_path")): f
            for f in manifest.get("files", [])
            if f.get("remote_path")
        }

    results = []
    try:
        for remote_path in body.files:
            remote_path = normalize_remote(remote_path)
            entry = manifest_map.get(remote_path, {})
            original_rel = entry.get("local_rel_path") or posixpath.basename(remote_path)
            rel = original_rel
            if not body.preserve_structure or not is_safe_relative_path(rel):
                # Mesmo sem preservar a estrutura, mantém o nome local original
                # (importante para arquivos com emoji que foram sanitizados no remoto).
                rel = posixpath.basename(original_rel)

            local_path = dest / Path(rel)
            try:
                local_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                results.append({
                    "remote_path": remote_path,
                    "local_path": str(local_path),
                    "success": False,
                    "error": f"não foi possível criar a pasta: {exc}",
                })
                continue

            ok = False
            error = None
            try:
                if entry.get("encrypted"):
                    key = await database.get_setting("encryption_key")
                    if not key:
                        raise RuntimeError("arquivo criptografado, mas a chave de criptografia não está configurada")
                    from backend.encryption import decrypt_file
                    import tempfile
                    import uuid
                    tmp_path = os.path.join(
                        tempfile.gettempdir(), f"_restore_{uuid.uuid4().hex[:8]}.enc"
                    )
                    ok = await client.download_file(remote_path, tmp_path)
                    if ok:
                        await asyncio.to_thread(
                            decrypt_file, key, tmp_path, str(local_path)
                        )
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                else:
                    ok = await client.download_file(remote_path, str(local_path))
            except Exception as exc:
                error = str(exc)
                ok = False

            results.append({
                "remote_path": remote_path,
                "local_path": str(local_path),
                "success": bool(ok),
                "error": error,
            })
    finally:
        await client.close()
    return {"results": results}


# ── Settings ──

@router.get("/settings", response_model=Settings)
async def get_settings():
    data = {}
    for key in ("sync_interval_minutes", "auto_sync", "notifications", "max_concurrent_uploads", "autostart", "browser_preference"):
        val = await database.get_setting(key)
        data[key] = val
    return Settings(
        sync_interval_minutes=int(data.get("sync_interval_minutes", 30)),
        auto_sync=data.get("auto_sync", "true") == "true",
        notifications=data.get("notifications", "true") == "true",
        max_concurrent_uploads=int(data.get("max_concurrent_uploads", 3)),
        autostart=data.get("autostart", "false") == "true",
        browser_preference=data.get("browser_preference", "auto"),
        encryption_key=data.get("encryption_key"),
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