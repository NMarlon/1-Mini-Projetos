"""Manifesto global de restauração e mesclagem entre computadores.

O manifesto é um arquivo único no Terabox. Vários computadores podem
sincronizar para o mesmo backup, então a gravação nunca deve substituir o
arquivo inteiro por um subconjunto local. A regra é:

- entradas dos mapeamentos deste computador são reconstruídas a partir do
  banco local e dos arquivos confirmados no remoto;
- entradas de mapeamentos de outros computadores são preservadas;
- entradas de mapeamentos cuja verificação remota falhou também são
  preservadas, para não sumirem por um erro transitório;
- a deduplicação é feita pelo caminho remoto normalizado.

Este módulo concentra a decisão pura (``merge_manifest``) e a leitura/gravação
do arquivo remoto. O ``sync_engine`` e o script de reconstrução usam as mesmas
funções.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Callable, Iterable, Optional

from backend.config import TEMP_DIR
from backend.paths import normalize_remote
from backend.terabox_client import TeraboxClient

MANIFEST_PATH = "/_terabox_autobackup_manifest.json"
MANIFEST_VERSION = "2.1"


class ManifestReadError(RuntimeError):
    """O manifesto existe (ou pode existir), mas não pôde ser lido.

    Nesse caso é perigoso gravar um manifesto novo apenas com os dados locais:
    as entradas de outros computadores seriam perdidas.
    """


def _uid_value(value) -> str:
    return str(value or "").strip()


def _manifest_key(entry: dict) -> str:
    return normalize_remote(entry.get("remote_path") or "").casefold()


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _dedupe(entries: Iterable[dict]) -> list:
    """Mantém a primeira entrada de cada caminho remoto."""
    result = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = _manifest_key(entry)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return result


def merge_manifest(
    existing: Optional[dict],
    local_files: Iterable[dict],
    local_directories: Iterable[dict],
    local_mapping_uids: Iterable[str],
    *,
    preserve_local_uids: Optional[Iterable[str]] = None,
    known_mapping_uids: Optional[Iterable[str]] = None,
    machine_id: str = "",
    machine_name: str = "",
    run_started_at: Optional[str] = None,
    generated_at: Optional[str] = None,
) -> dict:
    """Mescla o manifesto existente com as entradas deste computador.

    ``local_mapping_uids`` identifica todos os mapeamentos que pertencem a este
    computador. ``preserve_local_uids`` são os mapeamentos locais que não foram
    verificados nesta execução (desativados ou com falha de snapshot): as
    entradas antigas deles são mantidas em vez de removidas.

    ``known_mapping_uids`` é opcional. Quando informado, entradas de
    mapeamentos que não existem mais no cadastro global são descartadas. Se for
    ``None``, todas as entradas externas são preservadas.
    """

    existing = existing if isinstance(existing, dict) else {}
    local_uids = {_uid_value(uid) for uid in local_mapping_uids if _uid_value(uid)}
    preserve_uids = {
        _uid_value(uid) for uid in (preserve_local_uids or []) if _uid_value(uid)
    }
    known_uids = (
        {_uid_value(uid) for uid in known_mapping_uids if _uid_value(uid)}
        if known_mapping_uids is not None
        else None
    )

    local_files_list = _dedupe(
        dict(entry)
        for entry in _as_list(local_files)
        if isinstance(entry, dict)
    )
    for entry in local_files_list:
        if machine_id:
            entry["manifest_machine_id"] = machine_id

    merged_files: dict[str, dict] = {
        _manifest_key(entry): entry for entry in local_files_list
    }

    for raw_entry in _as_list(existing.get("files")):
        if not isinstance(raw_entry, dict):
            continue
        entry = dict(raw_entry)
        key = _manifest_key(entry)
        if not key or key in merged_files:
            continue
        uid = _uid_value(entry.get("mapping_uid"))
        if uid and uid in local_uids and uid not in preserve_uids:
            # Este computador é dono do mapeamento e o reconstruiu; uma
            # entrada antiga que não foi confirmada no remoto é fantasma.
            continue
        if known_uids is not None and uid and uid not in known_uids:
            continue
        merged_files[key] = entry

    local_dirs_list = _dedupe(
        dict(entry)
        for entry in _as_list(local_directories)
        if isinstance(entry, dict)
    )
    for entry in local_dirs_list:
        if machine_id:
            entry["manifest_machine_id"] = machine_id

    merged_dirs: dict[str, dict] = {
        _manifest_key(entry): entry for entry in local_dirs_list
    }
    local_dir_uids = {
        _uid_value(entry.get("mapping_uid")) for entry in local_dirs_list
    }
    for raw_entry in _as_list(existing.get("directories")):
        if not isinstance(raw_entry, dict):
            continue
        entry = dict(raw_entry)
        key = _manifest_key(entry)
        if not key or key in merged_dirs:
            continue
        uid = _uid_value(entry.get("mapping_uid"))
        if uid and uid in local_dir_uids and uid not in preserve_uids:
            continue
        if known_uids is not None and uid and uid not in known_uids:
            continue
        merged_dirs[key] = entry

    files = sorted(
        merged_files.values(),
        key=lambda entry: _manifest_key(entry),
    )
    directories = sorted(
        merged_dirs.values(),
        key=lambda entry: _manifest_key(entry),
    )

    now = generated_at or datetime.now().isoformat()
    return {
        "version": MANIFEST_VERSION,
        "generated_at": now,
        "run_started_at": (
            run_started_at
            or existing.get("run_started_at")
            or now
        ),
        "machine_id": machine_id,
        "machine_name": machine_name,
        "updated_by": (
            f"{machine_name} ({machine_id})"
            if machine_name and machine_id
            else machine_id or machine_name or ""
        ),
        "files": files,
        "directories": directories,
    }


async def download_manifest(
    client: TeraboxClient,
    path: str = MANIFEST_PATH,
    *,
    strict: bool = False,
) -> Optional[dict]:
    """Baixa e valida o manifesto remoto.

    Retorna ``None`` quando o manifesto não existe. Com ``strict=True``,
    falhas de leitura (arquivo existe mas o download/JSON falhou) levantam
    ``ManifestReadError`` em vez de parecer "manifesto inexistente" — assim o
    sync não grava um manifesto truncado e perde as entradas de outros PCs.
    """
    tmp = os.path.join(TEMP_DIR, f"_manifest_read_{uuid.uuid4().hex[:8]}.json")
    try:
        if strict:
            entry = await client.find_remote_file(path)
            if entry is None:
                return None
            if getattr(entry, "is_dir", False):
                raise ManifestReadError(
                    "o caminho do manifesto é uma pasta, não um arquivo"
                )

        ok = await client.download_file(path, tmp)
        if not ok:
            if strict:
                raise ManifestReadError(
                    "não foi possível baixar o manifesto existente"
                )
            return None
        with open(tmp, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            if strict:
                raise ManifestReadError("o manifesto remoto não é um objeto JSON")
            return None
        return data
    except ManifestReadError:
        raise
    except Exception as exc:
        if strict:
            raise ManifestReadError(
                f"falha ao ler o manifesto remoto: {exc}"
            ) from exc
        return None
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


async def write_manifest(
    client: TeraboxClient,
    manifest: dict,
    *,
    path: str = MANIFEST_PATH,
    retry: Optional[Callable] = None,
) -> dict:
    """Grava o manifesto no Terabox de forma atômica (precreate/upload/create)."""

    async def _run(operation, description: str):
        if retry is not None:
            return await retry(client, operation, description)
        return await operation()

    tmp = os.path.join(TEMP_DIR, f"_manifest_{uuid.uuid4().hex[:8]}.json")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)
        md5 = TeraboxClient.compute_md5(tmp)
        size = os.path.getsize(tmp)
        md5_json = json.dumps([md5])

        pre = await _run(
            lambda: client.precreate_file(path, md5_json),
            "precreate manifesto",
        )
        if not pre.get("ok"):
            # Manifesto antigo pode estar bloqueando; remove e tenta de novo.
            await client.delete_remote(path)
            pre = await _run(
                lambda: client.precreate_file(path, md5_json),
                "precreate manifesto (retry)",
            )
        if not pre.get("ok"):
            raise RuntimeError(
                pre.get("error") or "não foi possível criar o manifesto"
            )

        uploadid = pre["uploadid"]
        result = await client.upload_file(str(tmp), path, uploadid, md5, 0)
        if result in ("failed", "mismatch"):
            raise RuntimeError("upload do manifesto falhou")

        await _run(
            lambda: client.create_file(
                path, uploadid, size, md5_json, overwrite=True
            ),
            "criar manifesto",
        )
        return {
            "path": path,
            "size": size,
            "md5": md5,
            "files": len(manifest.get("files") or []),
            "directories": len(manifest.get("directories") or []),
        }
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
