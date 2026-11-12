"""Motor de sincronização: plano, fila, retry, rate-limit e manifesto.

O fluxo é dividido em duas etapas:

1. ``_build_plan``: lista o local, lista o remoto (paginado), compara tamanho
   + MD5 e decide ``upload`` / ``replace`` / ``skip`` / ``error``.
2. ``_run_sync``: executa o plano, garantindo que cada pasta seja criada uma
   única vez e que arquivos alterados sejam sobrescritos no mesmo caminho
   (``rtype=3``), sem criar pastas/arquivos com data no nome.
"""

import asyncio
import hashlib
import json
import os
import random
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from backend.config import (
    CHUNK_SIZE_BYTES,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_RATE_LIMIT_MS,
    LARGE_FILE_THRESHOLD,
    MAX_RETRIES,
    TEMP_DIR,
)
from backend import auth, database, notifications
from backend.paths import (
    join_remote,
    normalize_remote,
    remote_parent,
    sanitize_remote_path,
    sanitize_remote_relative,
)
from backend.sync_plan import (
    LocalEntry,
    PlanItem,
    RemoteSnapshot,
    SyncPlan,
    decide_action,
)
from backend.terabox_client import (
    TeraboxAuthError,
    TeraboxClient,
    TeraboxError,
    TeraboxTransientError,
)


class SyncEngine:
    """Motor de sync com plano, retry e rate-limit."""

    def __init__(self):
        self._running = False
        self._cancelled = False
        self._current_run_id: Optional[int] = None
        self._status = {
            "running": False,
            "run_id": None,
            "files_total": 0,
            "files_uploaded": 0,
            "files_failed": 0,
            "files_skipped": 0,
            "current_file": None,
            "error": None,
            "errors": [],
        }
        self._listeners: List[Callable] = []
        self._lock = asyncio.Lock()
        self._preview_lock = asyncio.Lock()
        self._rate_limit_ms = DEFAULT_RATE_LIMIT_MS
        self._max_concurrent = DEFAULT_MAX_CONCURRENT
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._last_api_call = 0.0
        self._remote_verified: Set[str] = set()

    # ── Eventos/status ──

    def add_listener(self, cb: Callable):
        self._listeners.append(cb)

    def remove_listener(self, cb: Callable):
        if cb in self._listeners:
            self._listeners.remove(cb)

    async def _notify(self, event: str, data: dict):
        for cb in self._listeners:
            try:
                await cb(event, data)
            except Exception:
                pass

    async def _rate_limit(self):
        """Pacing entre chamadas à API."""
        now = time.monotonic() * 1000
        elapsed = now - self._last_api_call
        if elapsed < self._rate_limit_ms:
            await asyncio.sleep((self._rate_limit_ms - elapsed) / 1000.0)
        self._last_api_call = time.monotonic() * 1000

    def get_status(self) -> dict:
        return dict(self._status)

    # ── Entrada pública ──

    async def start_sync(self, mapping_ids: Optional[List[int]] = None) -> int:
        """Inicia um sync. Retorna run_id."""
        async with self._lock:
            if self._running:
                return self._current_run_id or 0
            self._running = True
            self._cancelled = False
            self._semaphore = asyncio.Semaphore(self._max_concurrent)

        run_id = await database.execute(
            "INSERT INTO sync_runs (started_at, status) VALUES (?, 'running')",
            (datetime.now().isoformat(),),
        )
        self._current_run_id = run_id
        self._status = {
            "running": True,
            "run_id": run_id,
            "files_total": 0,
            "files_uploaded": 0,
            "files_failed": 0,
            "files_skipped": 0,
            "current_file": None,
            "error": None,
            "errors": [],
        }
        self._remote_verified = set()

        asyncio.create_task(self._run_sync(run_id, mapping_ids))
        return run_id

    async def stop_sync(self):
        self._cancelled = True

    async def preview(self, mapping_ids: Optional[List[int]] = None) -> dict:
        """Calcula o plano sem enviar, criar pastas ou alterar o banco."""
        if self._running:
            raise RuntimeError("Já existe um sync em andamento. Aguarde ou pare o sync atual.")
        async with self._preview_lock:
            auth_data = await auth.get_cached_auth()
            if not auth_data:
                raise RuntimeError("Não autenticado no Terabox. Conecte-se primeiro.")
            mappings = await self._get_mappings(mapping_ids)
            client = TeraboxClient(auth_data["cookies"], auth_data["jstoken"])
            try:
                plan = await self._build_plan(client, mappings)
                return self._plan_to_dict(plan, include_items=True)
            finally:
                await client.close()

    # ── Mapeamentos ──

    async def _get_mappings(self, mapping_ids: Optional[List[int]]) -> List[dict]:
        # ``None`` = todos os habilitados (Auto-sync). Lista vazia = nada
        # selecionado; não deve cair no caso "todos".
        if mapping_ids is not None:
            if not mapping_ids:
                return []
            placeholders = ",".join("?" * len(mapping_ids))
            return await database.fetch_all(
                f"SELECT * FROM mappings WHERE id IN ({placeholders}) AND enabled = 1",
                tuple(mapping_ids),
            )
        return await database.fetch_all("SELECT * FROM mappings WHERE enabled = 1")

    # ── Planejamento ──

    async def _fetch_snapshot(self, client: TeraboxClient, root: str) -> RemoteSnapshot:
        """Lista o remoto com uma segunda tentativa em caso de erro temporário."""
        for attempt in range(2):
            try:
                await client.ensure_token()
                return await client.fetch_remote_snapshot(root)
            except TeraboxAuthError:
                await client.refresh_token()
                if attempt == 1:
                    raise
            except TeraboxTransientError:
                if attempt == 1:
                    raise
                await asyncio.sleep(1.5 + random.random())
        return RemoteSnapshot()

    async def _local_md5(self, entry: LocalEntry, db_row: Optional[dict]) -> Optional[str]:
        """Usa o cache do banco quando tamanho/mtime não mudaram; senão calcula."""
        if (
            db_row
            and db_row.get("md5")
            and int(db_row.get("size") or -1) == entry.size
            and int(db_row.get("mtime_ns") or -1) == entry.mtime_ns
        ):
            return str(db_row["md5"]).lower()
        return await asyncio.to_thread(TeraboxClient.compute_md5, entry.full_path)

    async def _build_plan(self, client: TeraboxClient, mappings: List[dict]) -> SyncPlan:
        plan = SyncPlan(mappings=mappings)
        seen_remote: Dict[str, str] = {}

        for mapping in mappings:
            mapping_id = int(mapping["id"])
            remote_root = sanitize_remote_path(mapping["remote_path"])
            encrypted = bool(mapping.get("encrypt"))

            files, dirs, scan_errors = await asyncio.to_thread(
                TeraboxClient.collect_local_entries,
                mapping["local_path"],
                bool(mapping.get("include_subfolders", 1)),
                mapping.get("is_file"),
            )
            for err in scan_errors:
                plan.errors.append(
                    {
                        "mapping_id": mapping_id,
                        "mapping_name": mapping.get("name"),
                        "file": err.get("file"),
                        "error": err.get("error"),
                    }
                )

            # Se não for possível listar o remoto, abortar é mais seguro do
            # que assumir que está vazio e reenviar tudo por cima.
            snapshot = await self._fetch_snapshot(client, remote_root)
            plan.snapshots[mapping_id] = snapshot

            db_rows = await database.fetch_all(
                "SELECT * FROM files WHERE mapping_id = ?", (mapping_id,)
            )
            db_by_rel = {row["local_rel_path"]: row for row in db_rows}

            for entry in files:
                safe_rel = sanitize_remote_relative(entry.rel_path)
                cloud_rel = f"{safe_rel}.enc" if encrypted else safe_rel
                remote_path = join_remote(remote_root, cloud_rel)
                if not encrypted and not cloud_rel:
                    continue
                if remote_path in seen_remote:
                    plan.errors.append(
                        {
                            "mapping_id": mapping_id,
                            "mapping_name": mapping.get("name"),
                            "file": entry.rel_path,
                            "error": f"dois arquivos locais apontam para o mesmo caminho remoto: {remote_path}",
                        }
                    )
                    continue
                seen_remote[remote_path] = entry.full_path

                remote = snapshot.files.get(remote_path)
                db_row = db_by_rel.get(entry.rel_path)
                local_md5 = None

                need_hash = False
                if encrypted:
                    need_hash = True
                elif remote is not None and not remote.is_dir and remote.size == entry.size:
                    need_hash = True

                if need_hash:
                    try:
                        local_md5 = await self._local_md5(entry, db_row)
                    except OSError as exc:
                        plan.errors.append(
                            {
                                "mapping_id": mapping_id,
                                "mapping_name": mapping.get("name"),
                                "file": entry.rel_path,
                                "error": f"não foi possível ler o arquivo: {exc}",
                            }
                        )
                        continue

                action, reason = decide_action(
                    entry.size, local_md5, remote, db_row, encrypted
                )
                plan.items.append(
                    PlanItem(
                        mapping_id=mapping_id,
                        mapping_name=mapping.get("name") or "",
                        local_path=entry.full_path,
                        local_rel_path=entry.rel_path,
                        remote_path=remote_path,
                        size=entry.size,
                        mtime_ns=entry.mtime_ns,
                        action=action,
                        reason=reason,
                        encrypted=encrypted,
                        md5=local_md5,
                        remote_size=remote.size if remote else None,
                        remote_md5=remote.md5 if remote else None,
                    )
                )

            # Pastas: inclui a raiz, subpastas vazias e todos os pais dos arquivos
            dirs_to_ensure: Set[str] = {remote_root}
            for rel_dir in dirs:
                dirs_to_ensure.add(
                    join_remote(remote_root, sanitize_remote_relative(rel_dir))
                )
            for item in plan.items:
                if item.mapping_id != mapping_id:
                    continue
                parent = remote_parent(item.remote_path)
                while parent and parent != "/":
                    dirs_to_ensure.add(parent)
                    if parent == remote_root:
                        break
                    parent = remote_parent(parent)

            for remote_dir in sorted(dirs_to_ensure):
                if remote_dir not in snapshot.dirs:
                    plan.directories.append((mapping_id, remote_dir))

        return plan

    def _plan_to_dict(self, plan: SyncPlan, include_items: bool = True) -> dict:
        counts = {"upload": 0, "replace": 0, "skip": 0, "error": 0}
        for item in plan.items:
            counts[item.action] = counts.get(item.action, 0) + 1

        items = []
        if include_items:
            for item in plan.items[:500]:
                items.append(
                    {
                        "mapping_id": item.mapping_id,
                        "mapping_name": item.mapping_name,
                        "local_path": item.local_path,
                        "local_rel_path": item.local_rel_path,
                        "remote_path": item.remote_path,
                        "size": item.size,
                        "action": item.action,
                        "reason": item.reason,
                        "encrypted": item.encrypted,
                        "md5": item.md5,
                        "remote_md5": item.remote_md5,
                    }
                )

        return {
            "files_total": len(plan.items),
            "counts": counts,
            "items": items,
            "truncated": len(plan.items) > len(items),
            "directories": len(plan.directories),
            "errors": plan.errors[:200],
            "mappings": [
                {
                    "id": m["id"],
                    "name": m.get("name"),
                    "local_path": m.get("local_path"),
                    "remote_path": normalize_remote(m.get("remote_path")),
                }
                for m in plan.mappings
            ],
        }

    # ── Execução ──

    async def _run_sync(self, run_id: int, mapping_ids: Optional[List[int]]):
        auth_data = await auth.get_cached_auth()
        if not auth_data:
            await self._finish_run(run_id, "failed", error="Não autenticado no Terabox")
            self._running = False
            return

        client = TeraboxClient(auth_data["cookies"], auth_data["jstoken"])
        run_started = datetime.now().isoformat()
        try:
            mappings = await self._get_mappings(mapping_ids)
            if not mappings:
                # Nenhum mapeamento selecionado: atualiza o manifesto para
                # vazio, senão o Restaurar continuaria listando arquivos de
                # mapeamentos que foram desmarcados.
                try:
                    await self._update_manifest(
                        client, SyncPlan(mappings=[]), run_started
                    )
                except Exception as exc:
                    self._record_status_error(
                        "manifesto", f"falha ao atualizar manifesto: {exc}"
                    )
                await self._save_remote_config(client)
                await self._finish_run(run_id, "completed")
                return

            await self._notify("planning_started", {})
            plan = await self._build_plan(client, mappings)
            for err in plan.errors[:100]:
                self._record_status_error(
                    err.get("file") or err.get("mapping_name"),
                    err.get("error") or "erro de varredura",
                )
            self._status["files_total"] = len(plan.items)
            await database.execute(
                "UPDATE sync_runs SET files_total = ? WHERE id = ?",
                (len(plan.items), run_id),
            )

            # Diretórios conhecidos (snapshot) + criados nesta execução
            known_dirs: Set[str] = set()
            for snapshot in plan.snapshots.values():
                known_dirs.update(snapshot.dirs)
            ensured: Set[str] = set()

            for mapping in mappings:
                if self._cancelled:
                    await self._finish_run(run_id, "cancelled")
                    return
                try:
                    await self._ensure_directory_chain(
                        client,
                        sanitize_remote_path(mapping["remote_path"]),
                        known_dirs,
                        ensured,
                    )
                except Exception as exc:
                    self._record_status_error(
                        mapping.get("local_path"), f"falha ao criar pasta remota: {exc}"
                    )

            for mapping_id, remote_dir in plan.directories:
                if self._cancelled:
                    await self._finish_run(run_id, "cancelled")
                    return
                try:
                    await self._ensure_directory_chain(
                        client, remote_dir, known_dirs, ensured
                    )
                except Exception as exc:
                    self._record_status_error(remote_dir, f"falha ao criar subpasta: {exc}")

            await self._notify(
                "sync_started",
                {"run_id": run_id, "files_total": len(plan.items)},
            )

            for item in plan.items:
                if self._cancelled:
                    await self._finish_run(run_id, "cancelled")
                    return

                self._status["current_file"] = item.local_rel_path
                await self._notify("file_processing", {"file": item.local_rel_path})

                if item.action == "skip":
                    try:
                        await self._mark_skipped(item)
                        self._remote_verified.add(item.remote_path)
                    except Exception as exc:
                        await self._record_failure(item, run_id, exc)
                    continue

                if item.action == "error":
                    await self._record_failure(item, run_id, TeraboxError(item.reason))
                    continue

                try:
                    await self._process_file_with_retry(client, item, run_id)
                    self._remote_verified.add(item.remote_path)
                except Exception as exc:
                    await self._record_failure(item, run_id, exc)

            # Manifesto (não falha o sync inteiro se der erro)
            try:
                await self._update_manifest(client, plan, run_started)
            except Exception as exc:
                self._record_status_error("manifesto", f"falha ao atualizar manifesto: {exc}")

            await self._save_remote_config(client)
            await self._finish_run(run_id, "completed")

        except Exception as exc:
            await self._finish_run(run_id, "failed", error=str(exc))
        finally:
            await client.close()
            self._running = False
            self._status["running"] = False
            self._status["current_file"] = None

    async def _ensure_directory_chain(
        self,
        client: TeraboxClient,
        remote_dir: str,
        known_dirs: Set[str],
        ensured: Set[str],
    ):
        """Cria cada componente do caminho uma única vez, com ``rtype=0``."""
        path = normalize_remote(remote_dir)
        if path == "/":
            return
        current = ""
        for part in path.strip("/").split("/"):
            if not part:
                continue
            current = f"{current}/{part}"
            if current in ensured:
                continue
            if current in known_dirs:
                ensured.add(current)
                continue
            await self._rate_limit()
            await self._retry_operation(
                client,
                lambda p=current: client.create_directory(p),
                f"criar pasta {current}",
            )
            ensured.add(current)
            known_dirs.add(current)

    async def _retry_operation(self, client: TeraboxClient, operation: Callable, description: str):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                await client.ensure_token()
                return await operation()
            except TeraboxAuthError as exc:
                last_error = exc
                if attempt >= MAX_RETRIES - 1:
                    raise
                await client.refresh_token()
                await asyncio.sleep(0.5)
            except TeraboxTransientError as exc:
                last_error = exc
                if attempt >= MAX_RETRIES - 1:
                    raise
                await asyncio.sleep((2 ** attempt) + random.random())
            except TeraboxError as exc:
                # Erros permanentes (quota, caminho inválido etc.) não repetem
                if getattr(exc, "transient", False) and attempt < MAX_RETRIES - 1:
                    last_error = exc
                    await asyncio.sleep((2 ** attempt) + random.random())
                    continue
                raise
        if last_error:
            raise last_error
        raise TeraboxError(f"Falha em {description}")

    async def _process_file_with_retry(
        self, client: TeraboxClient, item: PlanItem, run_id: int
    ):
        """Repete o arquivo inteiro em erros temporários/autenticação.

        Um upload pode falhar no meio de vários chunks; repetir só o chunk não
        resolve, então criamos um novo uploadid e reenviamos o arquivo.
        """
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                await self._process_file(client, item, run_id)
                return
            except TeraboxAuthError as exc:
                last_error = exc
                if attempt >= MAX_RETRIES - 1:
                    raise
                await client.refresh_token()
                await asyncio.sleep(0.5)
            except TeraboxTransientError as exc:
                last_error = exc
                if attempt >= MAX_RETRIES - 1:
                    raise
                await asyncio.sleep((2 ** attempt) + random.random())
            except TeraboxError:
                raise
        if last_error:
            raise last_error
        raise TeraboxError(f"Falha ao processar {item.local_rel_path}")

    async def _process_file(self, client: TeraboxClient, item: PlanItem, run_id: int):
        local_path = item.local_path
        encrypted = item.encrypted
        overwrite = item.action == "replace"
        temp_dir = Path(TEMP_DIR) / f"run_{run_id}_{uuid.uuid4().hex[:8]}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        try:
            # Re-stat: o arquivo pode ter mudado entre o planejamento e o upload
            st = os.stat(local_path)
            local_size = st.st_size
            local_mtime_ns = st.st_mtime_ns
            if local_size != item.size or local_mtime_ns != item.mtime_ns:
                item.size = local_size
                item.mtime_ns = local_mtime_ns
                item.md5 = await asyncio.to_thread(TeraboxClient.compute_md5, local_path)

            local_md5 = item.md5 or await asyncio.to_thread(
                TeraboxClient.compute_md5, local_path
            )

            upload_path = local_path
            upload_size = local_size
            if encrypted:
                from backend.encryption import encrypt_file, generate_key

                key = await database.get_setting("encryption_key")
                if not key:
                    key = generate_key()
                    await database.set_setting("encryption_key", key)
                enc_path = temp_dir / (Path(local_path).name + ".enc")
                await asyncio.to_thread(encrypt_file, key, local_path, str(enc_path))
                upload_path = str(enc_path)
                upload_size = os.path.getsize(upload_path)

            pieces: List[str] = []
            md5_list: List[str] = []
            if upload_size >= LARGE_FILE_THRESHOLD:
                num_chunks = (upload_size + CHUNK_SIZE_BYTES - 1) // CHUNK_SIZE_BYTES
                for i in range(num_chunks):
                    chunk_path = temp_dir / f".chunk_{i:04d}"
                    with open(upload_path, "rb") as src, open(chunk_path, "wb") as dst:
                        src.seek(i * CHUNK_SIZE_BYTES)
                        data = src.read(CHUNK_SIZE_BYTES)
                        dst.write(data)
                        md5_list.append(hashlib.md5(data).hexdigest())
                    pieces.append(str(chunk_path))
            else:
                md5 = await asyncio.to_thread(TeraboxClient.compute_md5, upload_path)
                md5_list = [md5]
                pieces = [upload_path]

            md5_json = json.dumps(md5_list)
            cloud_path = item.remote_path

            await self._rate_limit()
            pre = await self._retry_operation(
                client,
                lambda: client.precreate_file(cloud_path, md5_json),
                f"precreate {cloud_path}",
            )
            if not pre.get("ok"):
                # Pode acontecer quando o servidor já tem exatamente o mesmo
                # conteúdo. Nesse caso, confirmamos e tratamos como skip.
                if pre.get("already_exists") and not encrypted:
                    remote = await client.find_remote_file(cloud_path)
                    if (
                        remote
                        and remote.size == upload_size
                        and (
                            not remote.md5
                            or (len(md5_list) == 1 and remote.md5.lower() == md5_list[0].lower())
                        )
                    ):
                        await self._mark_skipped(item)
                        return
                raise TeraboxError(pre.get("error") or "precreate falhou", errno=pre.get("errno"))
            uploadid = pre["uploadid"]

            for idx, piece in enumerate(pieces):
                await self._rate_limit()
                async with self._semaphore:
                    result = await client.upload_file(
                        piece, cloud_path, uploadid, md5_list[idx], idx
                    )
                if result in ("failed", "mismatch"):
                    raise TeraboxTransientError(
                        f"upload do bloco {idx} falhou ({result})", transient=True
                    )

            await self._rate_limit()
            await self._retry_operation(
                client,
                lambda: client.create_file(
                    cloud_path,
                    uploadid,
                    upload_size,
                    md5_json,
                    overwrite=overwrite,
                ),
                f"criar arquivo {cloud_path}",
            )

            # Verificação pós-upload: obrigatória em substituições (para
            # garantir que o arquivo antigo foi realmente sobrescrito). Para
            # arquivos novos, o MD5 do upload já foi conferido pelo servidor;
            # evitar uma listagem extra por arquivo deixa o 1º backup viável.
            remote_md5 = None
            if overwrite:
                remote = await client.find_remote_file(cloud_path)
                if remote is None:
                    raise TeraboxTransientError(
                        f"arquivo não apareceu no remoto após upload: {cloud_path}",
                        transient=True,
                    )
                if remote.size != upload_size:
                    raise TeraboxTransientError(
                        f"tamanho remoto diferente após upload: {remote.size} != {upload_size}",
                        transient=True,
                    )
                remote_md5 = remote.md5
                if (
                    remote.md5
                    and len(pieces) == 1
                    and not encrypted
                    and remote.md5.lower() != md5_list[0].lower()
                ):
                    raise TeraboxTransientError(
                        "MD5 remoto diferente após upload", transient=True
                    )
            elif len(pieces) == 1 and not encrypted:
                remote_md5 = md5_list[0]

            # Confere se o arquivo local não mudou durante o upload
            st_after = os.stat(local_path)
            if st_after.st_size != local_size or st_after.st_mtime_ns != local_mtime_ns:
                raise TeraboxTransientError(
                    "o arquivo local mudou durante o upload; será reenviado",
                    transient=True,
                )

            await self._upsert_file(
                mapping_id=item.mapping_id,
                rel_path=item.local_rel_path,
                remote_path=cloud_path,
                size=local_size,
                md5=local_md5,
                remote_md5=remote_md5 or (md5_list[0] if len(md5_list) == 1 and not encrypted else None),
                mtime_ns=local_mtime_ns,
                encrypted=encrypted,
                status="uploaded",
                error=None,
            )

            self._status["files_uploaded"] += 1
            await database.execute(
                "UPDATE sync_runs SET files_uploaded = files_uploaded + 1 WHERE id = ?",
                (run_id,),
            )
            await self._notify("file_uploaded", {"file": item.local_rel_path})
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _mark_skipped(self, item: PlanItem):
        await self._upsert_file(
            mapping_id=item.mapping_id,
            rel_path=item.local_rel_path,
            remote_path=item.remote_path,
            size=item.size,
            md5=item.md5,
            remote_md5=item.remote_md5,
            mtime_ns=item.mtime_ns,
            encrypted=item.encrypted,
            status="uploaded",
            error=None,
        )
        self._status["files_skipped"] += 1
        await database.execute(
            "UPDATE sync_runs SET files_skipped = files_skipped + 1 WHERE id = ?",
            (self._current_run_id,),
        )
        await self._notify(
            "file_skipped", {"file": item.local_rel_path, "reason": item.reason}
        )

    async def _upsert_file(
        self,
        mapping_id: int,
        rel_path: str,
        remote_path: str,
        size: int,
        md5: Optional[str],
        remote_md5: Optional[str],
        mtime_ns: Optional[int],
        encrypted: bool,
        status: str,
        error: Optional[str],
    ):
        await database.execute(
            """INSERT INTO files
               (mapping_id, local_rel_path, remote_path, size, md5, remote_md5,
                mtime_ns, encrypted, status, last_synced_at, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(mapping_id, local_rel_path) DO UPDATE SET
                 remote_path = excluded.remote_path,
                 size = excluded.size,
                 md5 = excluded.md5,
                 remote_md5 = excluded.remote_md5,
                 mtime_ns = excluded.mtime_ns,
                 encrypted = excluded.encrypted,
                 status = excluded.status,
                 last_synced_at = excluded.last_synced_at,
                 error = excluded.error""",
            (
                mapping_id,
                rel_path,
                remote_path,
                int(size),
                md5,
                remote_md5,
                int(mtime_ns) if mtime_ns is not None else None,
                int(encrypted),
                status,
                datetime.now().isoformat(),
                error,
            ),
        )

    def _record_status_error(self, file: str, error: str):
        errors = self._status.setdefault("errors", [])
        if len(errors) < 100:
            errors.append({"file": file, "error": str(error)})

    async def _record_failure(self, item: PlanItem, run_id: int, exc: Exception):
        message = str(exc)
        self._status["files_failed"] += 1
        self._record_status_error(item.local_rel_path, message)
        try:
            await self._upsert_file(
                mapping_id=item.mapping_id,
                rel_path=item.local_rel_path,
                remote_path=item.remote_path,
                size=item.size,
                md5=item.md5,
                remote_md5=item.remote_md5,
                mtime_ns=item.mtime_ns,
                encrypted=item.encrypted,
                status="failed",
                error=message,
            )
            await database.execute(
                "UPDATE sync_runs SET files_failed = files_failed + 1 WHERE id = ?",
                (run_id,),
            )
        except Exception:
            pass
        try:
            await self._notify(
                "file_failed",
                {"file": item.local_rel_path, "error": message},
            )
        except Exception:
            pass

    # ── Manifesto ──

    async def _update_manifest(self, client: TeraboxClient, plan: SyncPlan, run_started: str):
        """Gera manifesto v2 apenas com arquivos que existem no remoto.

        Inclui todos os mapeamentos habilitados (não só os sincronizados nesta
        execução), conferindo a existência remota. Assim, arquivos apagados
        manualmente do Terabox não ficam "fantasmas" no Restaurar.
        """
        verified: Set[str] = set(self._remote_verified)
        try:
            all_mappings = await database.fetch_all(
                "SELECT * FROM mappings WHERE enabled = 1"
            )
        except Exception:
            all_mappings = plan.mappings

        for mapping in all_mappings:
            snapshot = plan.snapshots.get(int(mapping["id"]))
            if snapshot is None:
                try:
                    snapshot = await self._fetch_snapshot(
                        client, sanitize_remote_path(mapping["remote_path"])
                    )
                except Exception:
                    continue
            verified.update(snapshot.files.keys())

        rows = await database.fetch_all(
            """SELECT f.*, m.name AS mapping_name, m.uid AS mapping_uid,
                      m.remote_path AS mapping_remote_path
               FROM files f JOIN mappings m ON f.mapping_id = m.id
               WHERE f.status = 'uploaded'"""
        )
        files = []
        for row in rows:
            remote_path = normalize_remote(row["remote_path"])
            if remote_path not in verified:
                continue
            files.append(
                {
                    "local_rel_path": row["local_rel_path"],
                    "remote_path": remote_path,
                    "size": row["size"],
                    "md5": row["md5"],
                    "remote_md5": row.get("remote_md5"),
                    "mapping_id": row["mapping_id"],
                    "mapping_uid": row.get("mapping_uid"),
                    "mapping_name": row["mapping_name"],
                    "mapping_remote_path": normalize_remote(
                        row.get("mapping_remote_path") or ""
                    ),
                    "synced_at": row["last_synced_at"],
                    "encrypted": bool(row.get("encrypted")),
                }
            )

        directories = []
        for mapping_id, remote_dir in plan.directories:
            directories.append({"mapping_id": mapping_id, "remote_path": remote_dir})

        manifest = {
            "version": "2.0",
            "generated_at": datetime.now().isoformat(),
            "run_started_at": run_started,
            "files": files,
            "directories": directories,
        }

        tmp = Path(TEMP_DIR) / f"_manifest_{uuid.uuid4().hex[:8]}.json"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(manifest, fh, indent=2, ensure_ascii=False)
            md5 = TeraboxClient.compute_md5(str(tmp))
            size = os.path.getsize(tmp)
            md5_json = json.dumps([md5])
            manifest_path = "/_terabox_autobackup_manifest.json"

            pre = await self._retry_operation(
                client,
                lambda: client.precreate_file(manifest_path, md5_json),
                "precreate manifesto",
            )
            if not pre.get("ok"):
                # Manifesto antigo pode estar bloqueando; remove e tenta de novo
                await client.delete_remote(manifest_path)
                pre = await self._retry_operation(
                    client,
                    lambda: client.precreate_file(manifest_path, md5_json),
                    "precreate manifesto (retry)",
                )
            if not pre.get("ok"):
                raise TeraboxError(pre.get("error") or "não foi possível criar o manifesto")

            uploadid = pre["uploadid"]
            result = await client.upload_file(str(tmp), manifest_path, uploadid, md5, 0)
            if result in ("failed", "mismatch"):
                raise TeraboxTransientError("upload do manifesto falhou", transient=True)
            await self._retry_operation(
                client,
                lambda: client.create_file(
                    manifest_path, uploadid, size, md5_json, overwrite=True
                ),
                "criar manifesto",
            )
            await self._notify("manifest_updated", {"files": len(files)})
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass

    async def _save_remote_config(self, client: TeraboxClient):
        """Atualiza o cadastro remoto no fim do sync, sem falhar o backup."""
        try:
            from backend.remote_config import remote_config_manager

            await remote_config_manager.save_now(
                client=client, reason="sync_finished"
            )
        except Exception as exc:
            self._record_status_error(
                "configuração remota",
                f"falha ao salvar configuração remota: {exc}",
            )

    # ── Finalização ──

    async def _finish_run(self, run_id: int, status: str, error: str = None):
        await database.execute(
            "UPDATE sync_runs SET finished_at = ?, status = ?, error = ? WHERE id = ?",
            (datetime.now().isoformat(), status, error, run_id),
        )
        self._status["running"] = False
        if error:
            self._status["error"] = error

        try:
            notify = await database.get_setting("notifications")
            if notify == "true":
                if status == "completed":
                    await notifications.notify_success(
                        "Sync concluído",
                        f"{self._status['files_uploaded']} enviados, "
                        f"{self._status['files_skipped']} ignorados, "
                        f"{self._status['files_failed']} falhas.",
                    )
                elif status == "failed":
                    await notifications.notify_error(
                        "Sync falhou", error or "Erro desconhecido"
                    )
        except Exception:
            pass

        await self._notify("sync_finished", {"run_id": run_id, "status": status})


# Instância global
sync_engine = SyncEngine()
