"""Configuração remota de mapeamentos no Terabox.

O arquivo remoto é um cadastro compartilhado dos mapeamentos. Ele permite que
um PC novo descubra para onde cada pasta remota deve voltar, sem copiar o banco
local. Regras principais:

- cada mapeamento tem um ``uid`` estável;
- cada máquina grava somente o seu caminho em ``local_paths``;
- o app baixa e mescla o arquivo antes de gravar, preservando outros PCs;
- nunca grava cookies, tokens, senhas ou a chave de criptografia;
- configuração remota vazia/inválida não é sobrescrita sem confirmação.

As funções puras (schema, merge, plano de importação) não tocam no banco nem na
rede. A classe ``RemoteConfigManager`` faz a parte assíncrona.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from backend.config import (
    DEFAULT_REMOTE_CONFIG_PATH,
    REMOTE_CONFIG_SHORTCUT_PATH,
    TEMP_DIR,
)
from backend.local_paths import (
    LocalPathError,
    detect_foreign_profile,
    validate_local_mapping_path,
)
from backend.paths import (
    normalize_remote,
    remote_parent,
    sanitize_remote_path,
)

SCHEMA = "terabox-auto-backup/remote-config"
SCHEMA_VERSION = 1
SHORTCUT_SCHEMA = "terabox-auto-backup/remote-config-shortcut"
MAX_CONFIG_BYTES = 2 * 1024 * 1024
MAX_LOCAL_PATH_LENGTH = 4096


class RemoteConfigError(Exception):
    """Erro de configuração remota."""


class RemoteConfigInvalid(RemoteConfigError):
    """Arquivo remoto inválido ou incompatível."""


class RemoteConfigEmpty(RemoteConfigError):
    """Tentativa de substituir uma configuração não vazia por uma vazia."""


class RemoteConfigConflict(RemoteConfigError):
    """Conflito entre o plano revisado e o arquivo remoto atual."""


class RemoteConfigNotAuthenticated(RemoteConfigError):
    """Sem cookies/jsToken para acessar o Terabox."""


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _machine_name(value: str) -> str:
    name = " ".join(str(value or "").split())[:80].strip()
    return name or "PC"


def normalize_config_path(path: str) -> str:
    """Valida e normaliza o caminho remoto do arquivo de configuração."""
    raw = normalize_remote(str(path or "").strip())
    if raw in ("", "/"):
        raise RemoteConfigInvalid(
            "Informe um arquivo .json dentro do Terabox (não a raiz)."
        )
    if not raw.lower().endswith(".json"):
        raise RemoteConfigInvalid(
            "O caminho da configuração remota precisa terminar em .json."
        )
    normalized = sanitize_remote_path(raw)
    if normalized == "/" or not normalized.lower().endswith(".json"):
        raise RemoteConfigInvalid(
            "O caminho da configuração remota ficou inválido depois da "
            "sanitização."
        )
    parts = normalized.strip("/").split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise RemoteConfigInvalid(
            "O caminho da configuração remota contém segmentos inseguros."
        )
    return normalized


# ── Schema e merge (funções puras) ──


def _normalize_entry(entry: dict) -> dict:
    is_file = bool(entry.get("is_file"))
    return {
        **entry,
        "uid": str(entry.get("uid") or "").strip(),
        "name": str(entry.get("name") or "").strip(),
        "remote_path": normalize_remote(entry.get("remote_path") or ""),
        "is_file": is_file,
        "enabled": bool(entry.get("enabled", True)),
        "include_subfolders": bool(
            entry.get("include_subfolders", not is_file)
        ),
        "encrypted": bool(entry.get("encrypted", False)),
        "local_paths": {
            str(key): str(value)
            for key, value in (entry.get("local_paths") or {}).items()
        },
    }


def validate_config(config: Any) -> dict:
    """Valida o schema do arquivo remoto. Levanta ``RemoteConfigInvalid``."""
    if not isinstance(config, dict):
        raise RemoteConfigInvalid("A configuração remota não é um objeto JSON.")

    if config.get("schema") != SCHEMA:
        raise RemoteConfigInvalid(
            "O arquivo remoto não é uma configuração do Terabox "
            "Auto-Backuper."
        )

    try:
        version = int(config.get("schema_version"))
    except (TypeError, ValueError) as exc:
        raise RemoteConfigInvalid(
            "A versão do schema da configuração remota é inválida."
        ) from exc

    if version < 1:
        raise RemoteConfigInvalid("Versão de schema inválida.")
    if version > SCHEMA_VERSION:
        raise RemoteConfigInvalid(
            f"Esta configuração usa o schema {version}, mas este app só "
            f"entende até o schema {SCHEMA_VERSION}."
        )

    mappings = config.get("mappings")
    if not isinstance(mappings, list):
        raise RemoteConfigInvalid(
            "O campo 'mappings' da configuração remota precisa ser uma lista."
        )

    seen_uids = set()
    for index, entry in enumerate(mappings):
        if not isinstance(entry, dict):
            raise RemoteConfigInvalid(
                f"O mapeamento #{index + 1} da configuração remota é inválido."
            )
        uid = str(entry.get("uid") or "").strip()
        if not uid:
            raise RemoteConfigInvalid(
                f"O mapeamento #{index + 1} não tem uid."
            )
        if uid in seen_uids:
            raise RemoteConfigInvalid(
                f"O uid '{uid}' aparece mais de uma vez na configuração."
            )
        seen_uids.add(uid)

        remote = normalize_remote(entry.get("remote_path") or "")
        if remote == "/":
            raise RemoteConfigInvalid(
                f"O mapeamento '{uid}' aponta para a raiz do Terabox."
            )
        remote_parts = remote.strip("/").split("/")
        if any(part in ("", ".", "..") for part in remote_parts):
            raise RemoteConfigInvalid(
                f"O mapeamento '{uid}' tem um caminho remoto inseguro."
            )

        if "is_file" not in entry or not isinstance(entry.get("is_file"), bool):
            raise RemoteConfigInvalid(
                f"O mapeamento '{uid}' não informa corretamente se é arquivo."
            )

        local_paths = entry.get("local_paths")
        if local_paths is None:
            local_paths = {}
        if not isinstance(local_paths, dict):
            raise RemoteConfigInvalid(
                f"O campo local_paths do mapeamento '{uid}' é inválido."
            )
        for machine_id, local_path in local_paths.items():
            if not isinstance(machine_id, str) or not machine_id.strip():
                raise RemoteConfigInvalid(
                    f"O mapeamento '{uid}' tem uma máquina sem identificação."
                )
            if not isinstance(local_path, str) or not local_path.strip():
                raise RemoteConfigInvalid(
                    f"O mapeamento '{uid}' tem um caminho local vazio."
                )
            if len(local_path) > MAX_LOCAL_PATH_LENGTH:
                raise RemoteConfigInvalid(
                    f"O mapeamento '{uid}' tem um caminho local muito longo."
                )

        for flag in ("enabled", "include_subfolders", "encrypted"):
            if flag in entry and not isinstance(entry.get(flag), bool):
                raise RemoteConfigInvalid(
                    f"O campo '{flag}' do mapeamento '{uid}' precisa ser "
                    "verdadeiro ou falso."
                )

    machines = config.get("machines")
    if machines is not None:
        if not isinstance(machines, dict):
            raise RemoteConfigInvalid("O campo 'machines' é inválido.")
        for machine_id, data in machines.items():
            if not isinstance(machine_id, str) or not machine_id.strip():
                raise RemoteConfigInvalid("Há uma máquina sem identificação.")
            if data is not None and not isinstance(data, dict):
                raise RemoteConfigInvalid(
                    f"Os dados da máquina '{machine_id}' são inválidos."
                )

    return config


def _entry_from_mapping(mapping: dict, machine_id: str) -> dict:
    uid = str(mapping.get("uid") or "").strip()
    if not uid:
        raise RemoteConfigInvalid(
            f"O mapeamento '{mapping.get('name') or mapping.get('id')}' não "
            "tem uid. Reinicie o app para concluir a migração."
        )
    local_path = str(mapping.get("local_path") or "").strip()
    if not local_path:
        raise RemoteConfigInvalid(
            f"O mapeamento '{mapping.get('name') or uid}' não tem caminho local."
        )
    remote_path = normalize_remote(mapping.get("remote_path") or "")
    if remote_path == "/":
        raise RemoteConfigInvalid(
            f"O mapeamento '{mapping.get('name') or uid}' aponta para a raiz "
            "do Terabox."
        )
    is_file = bool(mapping.get("is_file"))
    return {
        "uid": uid,
        "name": str(mapping.get("name") or "").strip(),
        "remote_path": remote_path,
        "is_file": is_file,
        "enabled": bool(mapping.get("enabled", True)),
        "include_subfolders": bool(
            mapping.get("include_subfolders", not is_file)
        ),
        "encrypted": bool(mapping.get("encrypt", False)),
        "local_paths": {machine_id: local_path},
    }


def build_config(
    mappings: Iterable[dict],
    machine_id: str,
    machine_name: str,
    previous: Optional[dict] = None,
    force: bool = False,
    now: Optional[str] = None,
) -> dict:
    """Monta o arquivo remoto mesclando com a versão anterior.

    ``previous`` deve ter sido validado antes (ou ser ``None``). ``force``
    permite gravar uma lista vazia por cima de uma configuração não vazia.
    """
    machine_id = str(machine_id or "").strip()
    if not machine_id:
        raise RemoteConfigInvalid("A identificação desta máquina está vazia.")
    machine_name = _machine_name(machine_name)
    now = now or _now_iso()
    mappings = list(mappings or [])

    if previous is not None:
        validate_config(previous)

    previous_entries = {}
    if previous:
        for entry in previous.get("mappings") or []:
            normalized = _normalize_entry(entry)
            previous_entries[normalized["uid"]] = normalized

    if not mappings and previous_entries and not force:
        raise RemoteConfigEmpty(
            "A lista local está vazia e a configuração remota tem "
            f"{len(previous_entries)} mapeamento(s). Para evitar apagar o "
            "cadastro de outros computadores, a gravação foi bloqueada. "
            "Confirme a substituição para continuar."
        )

    result_entries: List[dict] = []
    seen_uids = set()

    for mapping in mappings:
        entry = _entry_from_mapping(mapping, machine_id)
        uid = entry["uid"]
        if uid in seen_uids:
            raise RemoteConfigInvalid(
                f"Dois mapeamentos locais usam o mesmo uid '{uid}'."
            )
        seen_uids.add(uid)

        previous_entry = previous_entries.get(uid)
        if previous_entry:
            merged = dict(previous_entry)
            merged.update(entry)
            local_paths = dict(previous_entry.get("local_paths") or {})
            local_paths[machine_id] = entry["local_paths"][machine_id]
            merged["local_paths"] = local_paths
        else:
            merged = entry
        result_entries.append(merged)

    # Entradas que não existem mais nesta máquina: remove só o vínculo desta
    # máquina. Se outro PC ainda usa, a entrada continua no arquivo.
    for uid, previous_entry in previous_entries.items():
        if uid in seen_uids:
            continue
        local_paths = dict(previous_entry.get("local_paths") or {})
        local_paths.pop(machine_id, None)
        if local_paths:
            kept = dict(previous_entry)
            kept["local_paths"] = local_paths
            result_entries.append(kept)

    machines: Dict[str, dict] = {}
    if previous:
        for key, value in (previous.get("machines") or {}).items():
            if isinstance(value, dict):
                machines[str(key)] = dict(value)
    machines[machine_id] = {"name": machine_name, "last_seen": now}

    config = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "updated_at": now,
        "updated_by_machine": machine_id,
        "machines": machines,
        "mappings": result_entries,
    }
    validate_config(config)
    return config


def _canonical_config(config: dict, ignore_volatile: bool) -> dict:
    data = dict(config or {})
    if ignore_volatile:
        data.pop("updated_at", None)
        data.pop("updated_by_machine", None)
        machines = {}
        for key, value in (data.get("machines") or {}).items():
            if isinstance(value, dict):
                value = {
                    field: field_value
                    for field, field_value in value.items()
                    if field != "last_seen"
                }
            machines[key] = value
        data["machines"] = machines
    return data


def config_hash(config: dict, ignore_volatile: bool = False) -> str:
    """Hash estável do conteúdo da configuração."""
    payload = json.dumps(
        _canonical_config(config, ignore_volatile),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_shortcut(data: Any) -> str:
    """Lê o atalho fixo da raiz e devolve o caminho da configuração."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as exc:
            raise RemoteConfigInvalid("O atalho da configuração não é JSON.") from exc
    if not isinstance(data, dict):
        raise RemoteConfigInvalid("O atalho da configuração é inválido.")
    schema = data.get("schema")
    if schema not in (None, SHORTCUT_SCHEMA):
        raise RemoteConfigInvalid(
            "O atalho da raiz não aponta para uma configuração deste app."
        )
    path = data.get("config_path") or data.get("path")
    return normalize_config_path(path)


def _unique_paths(paths: Iterable[str]) -> List[str]:
    result = []
    seen = set()
    for path in paths:
        value = str(path or "").strip()
        if not value:
            continue
        key = value.replace("/", "\\").casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _validate_local_path(local_path: str, is_file: bool) -> Tuple[str, List[str]]:
    """Valida o caminho local escolhido para um mapeamento importado.

    Para arquivo único, o arquivo pode não existir: ele é o resultado da
    restauração. A pasta pai pode ser criada na importação. Para pasta, o
    diretório também pode não existir ainda e será criado na importação.
    """
    raw = str(local_path or "").strip().strip('"')
    if len(raw) > MAX_LOCAL_PATH_LENGTH:
        raise RemoteConfigInvalid("O caminho local é muito longo.")

    try:
        path_info = validate_local_mapping_path(raw, is_file)
    except LocalPathError as exc:
        raise RemoteConfigInvalid(str(exc)) from exc

    return path_info.path, list(path_info.warnings)


def _local_fingerprint(remote_path: str, is_file: bool) -> Tuple[str, bool]:
    return (normalize_remote(remote_path).casefold(), bool(is_file))


def _index_local_mappings(local_mappings: Iterable[dict]) -> Tuple[dict, dict, dict]:
    by_uid: Dict[str, List[dict]] = {}
    by_fingerprint: Dict[Tuple[str, bool], List[dict]] = {}
    by_remote: Dict[str, List[dict]] = {}
    for mapping in local_mappings or []:
        uid = str(mapping.get("uid") or "").strip()
        if uid:
            by_uid.setdefault(uid, []).append(mapping)
        remote = normalize_remote(mapping.get("remote_path") or "")
        if remote and remote != "/":
            by_remote.setdefault(remote.casefold(), []).append(mapping)
            by_fingerprint.setdefault(
                _local_fingerprint(remote, bool(mapping.get("is_file"))),
                [],
            ).append(mapping)
    return by_uid, by_fingerprint, by_remote


def build_import_plan(
    config: dict,
    local_mappings: Iterable[dict],
    machine_id: str,
    encryption_key_available: bool = True,
) -> dict:
    """Monta a revisão de importação para esta máquina, sem alterar nada."""
    validate_config(config)
    machine_id = str(machine_id or "").strip()
    local_mappings = list(local_mappings or [])
    by_uid, by_fingerprint, by_remote = _index_local_mappings(local_mappings)
    machines = config.get("machines") or {}

    rows = []
    for raw_entry in config.get("mappings") or []:
        entry = _normalize_entry(raw_entry)
        uid = entry["uid"]
        remote_path = entry["remote_path"]
        is_file = entry["is_file"]
        local_paths = dict(entry.get("local_paths") or {})

        conflicts: List[str] = []
        existing = None
        match_reason = None

        uid_matches = by_uid.get(uid) or []
        if len(uid_matches) == 1:
            existing = uid_matches[0]
            match_reason = "uid"
        elif len(uid_matches) > 1:
            conflicts.append(
                "Há mais de um mapeamento local com o mesmo uid."
            )

        if existing is None and not conflicts:
            fingerprint_matches = by_fingerprint.get(
                _local_fingerprint(remote_path, is_file), []
            ) or []
            if len(fingerprint_matches) == 1:
                existing = fingerprint_matches[0]
                match_reason = "fingerprint"
            elif len(fingerprint_matches) > 1:
                conflicts.append(
                    "Há mais de um mapeamento local com o mesmo caminho "
                    "remoto e tipo."
                )

        same_remote = by_remote.get(remote_path.casefold()) or []
        if existing is None and not conflicts and same_remote:
            different_type = [
                mapping
                for mapping in same_remote
                if bool(mapping.get("is_file")) != is_file
            ]
            if different_type:
                conflicts.append(
                    "Já existe um mapeamento local para este caminho remoto "
                    "com outro tipo (arquivo x pasta)."
                )
            elif len(same_remote) == 1:
                existing = same_remote[0]
                match_reason = "remote_path"
            else:
                conflicts.append(
                    "Há mais de um mapeamento local para este caminho remoto."
                )

        own_path = str(local_paths.get(machine_id) or "").strip()
        other_paths = _unique_paths(
            path
            for key, path in local_paths.items()
            if key != machine_id
        )
        existing_local = (
            str(existing.get("local_path") or "").strip() if existing else ""
        )

        local_path = ""
        suggestion_source = "none"
        if own_path:
            local_path = own_path
            suggestion_source = "this_machine"
        elif existing_local:
            local_path = existing_local
            suggestion_source = "existing_mapping"
        elif len(other_paths) == 1:
            local_path = other_paths[0]
            suggestion_source = "other_machine"

        # Sugestões vindas de outro computador podem apontar para o perfil de
        # outro usuário do Windows (ex.: C:\Users\marlo). O mapeamento será
        # importado no perfil atual, nunca criando pasta no perfil errado.
        original_local_path = local_path
        rebase = None
        rebase_warning = None
        if local_path and suggestion_source in (
            "existing_mapping",
            "other_machine",
        ):
            rebase = detect_foreign_profile(local_path)
            if rebase:
                local_path = rebase["suggested_path"]
                rebase_warning = (
                    "O caminho sugerido usava o perfil do usuário "
                    f"'{rebase['foreign_user']}' de outro computador. "
                    f"Foi ajustado para o seu perfil "
                    f"'{rebase['current_user']}': {rebase['suggested_path']}"
                )

        path_error = None
        warnings: List[str] = []
        normalized_local = ""
        if not local_path:
            path_error = (
                "Escolha a pasta/arquivo local que será usado neste computador."
            )
        else:
            try:
                normalized_local, warnings = _validate_local_path(
                    local_path, is_file
                )
            except RemoteConfigInvalid as exc:
                path_error = str(exc)

        if rebase_warning:
            warnings.insert(0, rebase_warning)

        if entry.get("encrypted") and not encryption_key_available:
            warnings.append(
                "Este mapeamento é criptografado e a chave não está "
                "configurada neste PC. Configure a chave antes de restaurar."
            )

        needs_update = False
        if existing:
            desired_remote = normalize_remote(existing.get("remote_path") or "")
            desired_name = str(existing.get("name") or "").strip()
            entry_name = str(entry.get("name") or "").strip() or desired_name
            needs_update = any(
                [
                    desired_remote != remote_path,
                    bool(existing.get("is_file")) != is_file,
                    desired_name != entry_name,
                    bool(existing.get("enabled", True)) != entry["enabled"],
                    bool(existing.get("include_subfolders", True))
                    != entry["include_subfolders"],
                    bool(existing.get("encrypt", False)) != entry["encrypted"],
                    bool(normalized_local)
                    and os.path.normcase(normalized_local)
                    != os.path.normcase(existing_local),
                ]
            )

        if conflicts:
            status = "conflict"
        elif existing:
            status = "existing"
        else:
            status = "new"

        other_machines = []
        for other_id, other_path in local_paths.items():
            if other_id == machine_id:
                continue
            machine_data = machines.get(other_id) or {}
            other_machines.append(
                {
                    "machine_id": other_id,
                    "machine_name": str(machine_data.get("name") or other_id),
                    "local_path": str(other_path),
                }
            )

        row = {
            "uid": uid,
            "name": entry.get("name") or (
                os.path.basename(remote_path.rstrip("/")) or remote_path
            ),
            "remote_path": remote_path,
            "is_file": is_file,
            "enabled": entry["enabled"],
            "include_subfolders": entry["include_subfolders"],
            "encrypted": entry["encrypted"],
            "status": status,
            "match_reason": match_reason,
            "existing_id": existing.get("id") if existing else None,
            "current_local_path": existing_local or None,
            "local_path": local_path,
            "original_local_path": original_local_path or None,
            "rebase": rebase,
            "normalized_local_path": normalized_local or None,
            "suggestion_source": suggestion_source,
            "needs_update": bool(needs_update),
            "path_error": path_error,
            "warnings": warnings,
            "conflicts": conflicts,
            "other_machines": other_machines,
            "selected": status == "new" and not path_error and not conflicts,
            "blocked": bool(conflicts),
        }
        rows.append(row)

    summary = {
        "total": len(rows),
        "new": sum(1 for row in rows if row["status"] == "new"),
        "existing": sum(1 for row in rows if row["status"] == "existing"),
        "conflicts": sum(1 for row in rows if row["status"] == "conflict"),
        "needs_update": sum(1 for row in rows if row["needs_update"]),
        "with_path_error": sum(1 for row in rows if row["path_error"]),
        "encrypted": sum(1 for row in rows if row["encrypted"]),
        "selected": sum(1 for row in rows if row["selected"]),
    }

    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "config_hash": config_hash(config, ignore_volatile=True),
        "updated_at": config.get("updated_at"),
        "mappings": rows,
        "summary": summary,
    }


def _find_existing_for_entry(
    entry: dict,
    by_uid: Dict[str, List[dict]],
    by_fingerprint: Dict[Tuple[str, bool], List[dict]],
) -> Tuple[Optional[dict], Optional[str], List[str]]:
    uid = entry["uid"]
    uid_matches = by_uid.get(uid) or []
    if len(uid_matches) == 1:
        return uid_matches[0], "uid", []
    if len(uid_matches) > 1:
        return None, None, ["Há mais de um mapeamento local com o mesmo uid."]

    fingerprint = _local_fingerprint(entry["remote_path"], entry["is_file"])
    matches = by_fingerprint.get(fingerprint) or []
    if len(matches) == 1:
        return matches[0], "fingerprint", []
    if len(matches) > 1:
        return None, None, [
            "Há mais de um mapeamento local com o mesmo caminho remoto e tipo."
        ]
    return None, None, []


def build_import_operations(
    config: dict,
    local_mappings: Iterable[dict],
    selections: Iterable[dict],
) -> dict:
    """Converte a seleção revisada em operações de banco (sem executar)."""
    validate_config(config)
    local_mappings = list(local_mappings or [])
    by_uid, by_fingerprint, _ = _index_local_mappings(local_mappings)
    entries = {
        _normalize_entry(entry)["uid"]: _normalize_entry(entry)
        for entry in (config.get("mappings") or [])
    }

    create = []
    update = []
    skipped = []
    errors = []

    for selection in selections or []:
        uid = str(selection.get("uid") or "").strip()
        entry = entries.get(uid)
        if not entry:
            errors.append(
                {"uid": uid, "error": "O mapeamento não existe mais na configuração remota."}
            )
            continue

        try:
            local_path, warnings = _validate_local_path(
                selection.get("local_path"), entry["is_file"]
            )
        except RemoteConfigInvalid as exc:
            errors.append({"uid": uid, "error": str(exc)})
            continue

        existing, match_reason, conflicts = _find_existing_for_entry(
            entry, by_uid, by_fingerprint
        )
        if conflicts:
            errors.append({"uid": uid, "error": conflicts[0]})
            continue

        name = (
            str(entry.get("name") or "").strip()
            or str(existing.get("name") if existing else "").strip()
            or os.path.basename(local_path.rstrip("\\/"))
            or uid
        )
        desired = {
            "uid": uid,
            "name": name,
            "local_path": local_path,
            "remote_path": entry["remote_path"],
            "is_file": entry["is_file"],
            "include_subfolders": (
                False if entry["is_file"] else entry["include_subfolders"]
            ),
            "encrypt": entry["encrypted"],
            "enabled": entry["enabled"],
            "warnings": warnings,
            "match_reason": match_reason,
        }

        if existing:
            changed = any(
                [
                    str(existing.get("uid") or "") != uid,
                    str(existing.get("name") or "") != name,
                    os.path.normcase(str(existing.get("local_path") or ""))
                    != os.path.normcase(local_path),
                    normalize_remote(existing.get("remote_path") or "")
                    != entry["remote_path"],
                    bool(existing.get("is_file")) != entry["is_file"],
                    bool(existing.get("include_subfolders", True))
                    != desired["include_subfolders"],
                    bool(existing.get("encrypt", False)) != entry["encrypted"],
                    bool(existing.get("enabled", True)) != entry["enabled"],
                ]
            )
            if not changed:
                skipped.append({**desired, "reason": "já está igual"})
                continue
            update.append({**desired, "id": existing.get("id")})
        else:
            # Evita criar um segundo mapeamento para o mesmo caminho remoto,
            # inclusive com tipo diferente (arquivo x pasta).
            remote_conflicts = [
                mapping
                for mapping in local_mappings
                if normalize_remote(mapping.get("remote_path") or "").casefold()
                == entry["remote_path"].casefold()
            ]
            if remote_conflicts:
                errors.append(
                    {
                        "uid": uid,
                        "error": (
                            "Já existe um mapeamento local para este caminho "
                            "remoto. Selecione-o na revisão em vez de criar "
                            "outro."
                        ),
                    }
                )
                continue
            create.append(desired)

    return {
        "create": create,
        "update": update,
        "skipped": skipped,
        "errors": errors,
        "config_hash": config_hash(config, ignore_volatile=True),
    }


# ── Parte assíncrona ──


class RemoteConfigManager:
    """Baixa, mescla e grava a configuração remota."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._save_task: Optional[asyncio.Task] = None
        self._dirty = False
        self._shortcut_verified = False
        self._last_error: Optional[str] = None

    @property
    def dirty(self) -> bool:
        return self._dirty

    def request_save(self, reason: str = "change", delay: float = 4.0):
        """Agenda um salvamento com debounce (não bloqueia a requisição)."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._dirty = True
        if self._save_task and not self._save_task.done():
            return
        self._save_task = loop.create_task(
            self._debounced_save(reason, max(0.0, float(delay)))
        )

    async def _debounced_save(self, reason: str, delay: float):
        try:
            await asyncio.sleep(delay)
            auto_save = await database.get_setting("remote_config_auto_save")
            if auto_save == "false":
                return
            attempts = 0
            while self._dirty and attempts < 2:
                self._dirty = False
                attempts += 1
                try:
                    await self.save_now(reason=reason)
                except Exception as exc:
                    self._last_error = str(exc)
                    break
        finally:
            self._dirty = False

    # ── Leitura remota ──

    async def _read_remote_once(self, client, remote_path: str) -> dict:
        entry = await client.find_remote_file(remote_path)
        if entry is None:
            return {
                "exists": False,
                "path": remote_path,
                "config": None,
                "error": None,
                "hash": None,
                "size": 0,
            }
        if getattr(entry, "is_dir", False):
            return {
                "exists": True,
                "path": remote_path,
                "config": None,
                "error": "O caminho configurado é uma pasta, não um arquivo .json.",
                "hash": None,
                "size": 0,
                "is_directory": True,
            }
        if int(getattr(entry, "size", 0) or 0) > MAX_CONFIG_BYTES:
            return {
                "exists": True,
                "path": remote_path,
                "config": None,
                "error": "O arquivo de configuração remota é grande demais.",
                "hash": None,
                "size": int(getattr(entry, "size", 0) or 0),
            }

        tmp = os.path.join(
            tempfile.gettempdir(),
            f"_remote_config_{uuid.uuid4().hex[:8]}.json",
        )
        try:
            ok = await client.download_file(remote_path, tmp)
            if not ok:
                return {
                    "exists": True,
                    "path": remote_path,
                    "config": None,
                    "error": "Não foi possível baixar o arquivo de configuração.",
                    "hash": None,
                    "size": int(getattr(entry, "size", 0) or 0),
                }
            try:
                with open(tmp, "r", encoding="utf-8") as fh:
                    config = json.load(fh)
                validate_config(config)
            except RemoteConfigInvalid as exc:
                return {
                    "exists": True,
                    "path": remote_path,
                    "config": None,
                    "error": str(exc),
                    "hash": None,
                    "size": os.path.getsize(tmp),
                }
            except Exception as exc:
                return {
                    "exists": True,
                    "path": remote_path,
                    "config": None,
                    "error": f"JSON inválido: {exc}",
                    "hash": None,
                    "size": os.path.getsize(tmp),
                }
            return {
                "exists": True,
                "path": remote_path,
                "config": config,
                "error": None,
                "hash": config_hash(config, ignore_volatile=True),
                "size": os.path.getsize(tmp),
            }
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass

    async def _read_remote(self, client, remote_path: str) -> dict:
        last_error = None
        for attempt in range(2):
            try:
                await client.ensure_token()
                return await self._read_remote_once(client, remote_path)
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    try:
                        await client.refresh_token()
                    except Exception:
                        pass
                    continue
                break
        if isinstance(last_error, TeraboxAuthError):
            raise last_error
        return {
            "exists": False,
            "path": remote_path,
            "config": None,
            "error": str(last_error or "falha ao ler a configuração remota"),
            "hash": None,
            "size": 0,
        }

    async def _read_shortcut(self, client) -> dict:
        entry = await client.find_remote_file(REMOTE_CONFIG_SHORTCUT_PATH)
        if entry is None:
            return {"exists": False, "path": None, "error": None}
        if getattr(entry, "is_dir", False):
            return {
                "exists": True,
                "path": None,
                "error": "O atalho fixo da raiz é uma pasta.",
            }
        tmp = os.path.join(
            tempfile.gettempdir(),
            f"_remote_config_link_{uuid.uuid4().hex[:8]}.json",
        )
        try:
            if not await client.download_file(
                REMOTE_CONFIG_SHORTCUT_PATH, tmp
            ):
                return {
                    "exists": True,
                    "path": None,
                    "error": "Não foi possível baixar o atalho da configuração.",
                }
            try:
                with open(tmp, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                return {"exists": True, "path": parse_shortcut(data), "error": None}
            except Exception as exc:
                return {
                    "exists": True,
                    "path": None,
                    "error": f"Atalho inválido: {exc}",
                }
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass

    async def load_remote(self, preferred_path: Optional[str] = None) -> dict:
        """Descobre a configuração: caminho configurado e, se faltar, atalho."""
        if preferred_path is None:
            preferred_path = (
                await database.get_setting("remote_config_path")
                or DEFAULT_REMOTE_CONFIG_PATH
            )
        preferred_path = normalize_config_path(preferred_path)

        auth_data = await auth.get_cached_auth()
        if not auth_data:
            raise RemoteConfigNotAuthenticated(
                "Não autenticado no Terabox. Conecte-se primeiro."
            )

        client = TeraboxClient(auth_data["cookies"], auth_data["jstoken"])
        try:
            loaded = await self._read_remote(client, preferred_path)
            loaded["source"] = "configured"
            if loaded.get("exists") or loaded.get("error"):
                return loaded

            shortcut = await self._read_shortcut(client)
            if shortcut.get("error"):
                loaded["error"] = shortcut["error"]
                loaded["source"] = "shortcut"
                return loaded
            shortcut_path = shortcut.get("path")
            if shortcut_path and shortcut_path != preferred_path:
                found = await self._read_remote(client, shortcut_path)
                found["source"] = "shortcut"
                return found
            return loaded
        except TeraboxAuthError as exc:
            raise RemoteConfigNotAuthenticated(
                "A autenticação do Terabox expirou. Reconecte e tente novamente."
            ) from exc
        finally:
            await client.close()

    # ── Escrita remota ──

    async def _ensure_parent_directories(self, client, remote_path: str):
        parent = remote_parent(remote_path)
        if parent == "/":
            return
        current = ""
        for part in parent.strip("/").split("/"):
            if not part:
                continue
            current = f"{current}/{part}"
            await client.create_directory(current)

    async def _write_remote_file(self, client, remote_path: str, payload: dict):
        remote_path = normalize_config_path(remote_path)
        raw = json.dumps(
            payload, indent=2, ensure_ascii=False, sort_keys=False
        ).encode("utf-8")
        if len(raw) > MAX_CONFIG_BYTES:
            raise RemoteConfigInvalid(
                "O arquivo de configuração ficou grande demais."
            )

        await self._ensure_parent_directories(client, remote_path)
        existing = await client.find_remote_file(remote_path)
        if existing is not None and getattr(existing, "is_dir", False):
            raise RemoteConfigError(
                f"O caminho {remote_path} é uma pasta no Terabox e não será "
                "substituído. Escolha outro caminho para o arquivo de "
                "configuração."
            )

        tmp = os.path.join(
            TEMP_DIR, f"_remote_config_{uuid.uuid4().hex[:8]}.json"
        )
        try:
            with open(tmp, "wb") as fh:
                fh.write(raw)
            md5 = TeraboxClient.compute_md5(tmp)
            size = os.path.getsize(tmp)
            md5_json = json.dumps([md5])

            await client.ensure_token()
            pre = await client.precreate_file(remote_path, md5_json)
            if not pre.get("ok"):
                message = str(pre.get("error") or "").lower()
                if pre.get("already_exists") or "already exist" in message:
                    await client.delete_remote(remote_path)
                    pre = await client.precreate_file(remote_path, md5_json)
            if not pre.get("ok"):
                raise RemoteConfigError(
                    pre.get("error")
                    or "não foi possível preparar o arquivo de configuração"
                )

            uploadid = pre["uploadid"]
            result = await client.upload_file(
                tmp, remote_path, uploadid, md5, 0
            )
            if result in ("failed", "mismatch"):
                raise RemoteConfigError(
                    "O upload do arquivo de configuração falhou."
                )
            await client.create_file(
                remote_path, uploadid, size, md5_json, overwrite=True
            )

            remote = await client.find_remote_file(remote_path)
            if remote is None or getattr(remote, "is_dir", False):
                raise RemoteConfigError(
                    "O arquivo de configuração não apareceu no Terabox "
                    "depois do upload."
                )
            if int(getattr(remote, "size", 0) or 0) != size:
                raise RemoteConfigError(
                    "O tamanho do arquivo de configuração no Terabox não "
                    "confere com o enviado."
                )
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass

    async def _write_shortcut(self, client, config_path: str):
        payload = {
            "schema": SHORTCUT_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "config_path": config_path,
            "updated_at": _now_iso(),
        }
        await self._write_remote_file(
            client, REMOTE_CONFIG_SHORTCUT_PATH, payload
        )
        self._shortcut_verified = True

    async def _ensure_shortcut(self, client, config_path: str) -> bool:
        try:
            entry = await client.find_remote_file(REMOTE_CONFIG_SHORTCUT_PATH)
        except Exception:
            entry = None
        if entry is not None and not getattr(entry, "is_dir", False):
            tmp = os.path.join(
                tempfile.gettempdir(),
                f"_remote_config_link_{uuid.uuid4().hex[:8]}.json",
            )
            try:
                if await client.download_file(
                    REMOTE_CONFIG_SHORTCUT_PATH, tmp
                ):
                    with open(tmp, "r", encoding="utf-8") as fh:
                        if parse_shortcut(json.load(fh)) == config_path:
                            self._shortcut_verified = True
                            return False
            except Exception:
                pass
            finally:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        await self._write_shortcut(client, config_path)
        return True

    async def save_now(
        self,
        force: bool = False,
        client=None,
        reason: str = "manual",
    ) -> dict:
        """Baixa, mescla, grava e atualiza o atalho fixo."""
        async with self._lock:
            enabled = await database.get_setting("remote_config_enabled")
            if enabled == "false":
                return {
                    "saved": False,
                    "skipped": True,
                    "reason": "A configuração remota está desativada.",
                }

            path = normalize_config_path(
                await database.get_setting("remote_config_path")
                or DEFAULT_REMOTE_CONFIG_PATH
            )
            owns_client = client is None
            if owns_client:
                auth_data = await auth.get_cached_auth()
                if not auth_data:
                    raise RemoteConfigNotAuthenticated(
                        "Não autenticado no Terabox. Conecte-se primeiro."
                    )
                client = TeraboxClient(
                    auth_data["cookies"], auth_data["jstoken"]
                )

            try:
                await client.ensure_token()
                loaded = await self._read_remote(client, path)
                if loaded.get("is_directory"):
                    raise RemoteConfigInvalid(
                        "O caminho configurado é uma pasta no Terabox. "
                        "Escolha outro caminho para o arquivo .json."
                    )
                if loaded.get("error") and not loaded.get("exists"):
                    raise RemoteConfigInvalid(
                        "Não foi possível ler a configuração remota existente: "
                        + str(loaded["error"])
                        + ". A gravação foi bloqueada para não sobrescrever "
                        "dados de outro computador."
                    )
                previous = None
                if loaded.get("exists"):
                    if loaded.get("config") is None:
                        if not force:
                            raise RemoteConfigInvalid(
                                "A configuração remota existente está inválida: "
                                + str(
                                    loaded.get("error")
                                    or "formato desconhecido"
                                )
                                + ". A gravação automática foi bloqueada. "
                                "Confirme a substituição para continuar."
                            )
                    else:
                        previous = loaded["config"]

                local_mappings = await database.fetch_all(
                    "SELECT * FROM mappings ORDER BY id"
                )
                machine = await database.get_machine_identity()
                config = build_config(
                    local_mappings,
                    machine["machine_id"],
                    machine["machine_name"],
                    previous=previous,
                    force=force,
                )

                previous_hash = (
                    config_hash(previous, ignore_volatile=True)
                    if previous
                    else None
                )
                new_hash = config_hash(config, ignore_volatile=True)
                changed = force or previous is None or previous_hash != new_hash
                shortcut_written = False
                if changed:
                    await self._write_remote_file(client, path, config)
                    await self._write_shortcut(client, path)
                    shortcut_written = True
                elif not self._shortcut_verified:
                    shortcut_written = await self._ensure_shortcut(
                        client, path
                    )

                now = _now_iso()
                if changed:
                    await database.set_setting(
                        "remote_config_last_saved_at", now
                    )
                await database.set_setting(
                    "remote_config_last_hash", new_hash
                )
                await database.set_setting("remote_config_last_error", "")
                self._last_error = None

                return {
                    "saved": True,
                    "changed": changed,
                    "skipped": False,
                    "reason": reason,
                    "path": path,
                    "config_hash": new_hash,
                    "shortcut_path": REMOTE_CONFIG_SHORTCUT_PATH,
                    "shortcut_written": shortcut_written,
                    "mappings": len(config.get("mappings") or []),
                    "updated_at": config.get("updated_at"),
                }
            except TeraboxAuthError as exc:
                self._last_error = str(exc)
                try:
                    await database.set_setting(
                        "remote_config_last_error", str(exc)[:500]
                    )
                except Exception:
                    pass
                raise RemoteConfigNotAuthenticated(
                    "A autenticação do Terabox expirou. Reconecte e tente "
                    "novamente."
                ) from exc
            except Exception as exc:
                self._last_error = str(exc)
                try:
                    await database.set_setting(
                        "remote_config_last_error", str(exc)[:500]
                    )
                except Exception:
                    pass
                raise
            finally:
                if owns_client and client is not None:
                    await client.close()

    # ── Status e importação ──

    async def status(self, check_remote: bool = False) -> dict:
        enabled = (
            await database.get_setting("remote_config_enabled") or "true"
        ) == "true"
        auto_save = (
            await database.get_setting("remote_config_auto_save") or "true"
        ) == "true"
        path = (
            await database.get_setting("remote_config_path")
            or DEFAULT_REMOTE_CONFIG_PATH
        )
        machine = await database.get_machine_identity()
        mappings = await database.fetch_all("SELECT * FROM mappings ORDER BY id")
        last_saved = await database.get_setting(
            "remote_config_last_saved_at"
        )
        last_error = await database.get_setting("remote_config_last_error")

        result = {
            "enabled": enabled,
            "auto_save": auto_save,
            "path": path,
            "default_path": DEFAULT_REMOTE_CONFIG_PATH,
            "shortcut_path": REMOTE_CONFIG_SHORTCUT_PATH,
            "machine_id": machine["machine_id"],
            "machine_name": machine["machine_name"],
            "mapping_count": len(mappings),
            "enabled_mapping_count": sum(
                1 for mapping in mappings if mapping.get("enabled")
            ),
            "dirty": self._dirty,
            "last_saved_at": last_saved,
            "last_error": last_error or self._last_error,
            "remote": {
                "checked": False,
                "exists": None,
                "error": None,
            },
        }

        if not check_remote:
            return result

        auth_data = await auth.get_cached_auth()
        if not auth_data:
            result["remote"] = {
                "checked": True,
                "exists": None,
                "error": "Não autenticado no Terabox.",
            }
            return result

        try:
            loaded = await self.load_remote(path)
            remote = {
                "checked": True,
                "exists": bool(loaded.get("exists")),
                "path": loaded.get("path"),
                "source": loaded.get("source"),
                "error": loaded.get("error"),
                "config_hash": loaded.get("hash"),
                "updated_at": (
                    (loaded.get("config") or {}).get("updated_at")
                    if loaded.get("config")
                    else None
                ),
                "mappings_total": (
                    len((loaded.get("config") or {}).get("mappings") or [])
                    if loaded.get("config")
                    else 0
                ),
                "needs_import": False,
                "import_summary": None,
            }
            if loaded.get("config"):
                key = await database.get_setting("encryption_key")
                plan = build_import_plan(
                    loaded["config"],
                    mappings,
                    machine["machine_id"],
                    encryption_key_available=bool(key),
                )
                remote["import_summary"] = plan["summary"]
                remote["needs_import"] = (
                    plan["summary"]["new"] > 0
                    or plan["summary"]["conflicts"] > 0
                )
                remote["config_hash"] = plan["config_hash"]
            result["remote"] = remote
        except Exception as exc:
            result["remote"] = {
                "checked": True,
                "exists": None,
                "error": str(exc),
            }
        return result

    async def import_plan(self) -> dict:
        loaded = await self.load_remote()
        if loaded.get("error"):
            raise RemoteConfigInvalid(str(loaded["error"]))
        if not loaded.get("exists") or not loaded.get("config"):
            return {
                "exists": False,
                "path": loaded.get("path"),
                "source": loaded.get("source"),
                "config_hash": None,
                "mappings": [],
                "summary": {
                    "total": 0,
                    "new": 0,
                    "existing": 0,
                    "conflicts": 0,
                    "needs_update": 0,
                    "with_path_error": 0,
                    "encrypted": 0,
                    "selected": 0,
                },
            }

        machine = await database.get_machine_identity()
        mappings = await database.fetch_all("SELECT * FROM mappings ORDER BY id")
        key = await database.get_setting("encryption_key")
        plan = build_import_plan(
            loaded["config"],
            mappings,
            machine["machine_id"],
            encryption_key_available=bool(key),
        )
        plan.update(
            {
                "exists": True,
                "path": loaded.get("path"),
                "source": loaded.get("source"),
                "machine_id": machine["machine_id"],
                "machine_name": machine["machine_name"],
            }
        )
        return plan

    async def apply_import(
        self, expected_hash: str, selections: Iterable[dict]
    ) -> dict:
        loaded = await self.load_remote()
        if loaded.get("error"):
            raise RemoteConfigInvalid(str(loaded["error"]))
        if not loaded.get("exists") or not loaded.get("config"):
            raise RemoteConfigInvalid(
                "A configuração remota não existe mais. Recarregue a revisão."
            )

        current_hash = config_hash(
            loaded["config"], ignore_volatile=True
        )
        if expected_hash and expected_hash != current_hash:
            raise RemoteConfigConflict(
                "A configuração remota mudou desde a revisão. Recarregue o "
                "plano de importação e confirme novamente."
            )

        mappings = await database.fetch_all("SELECT * FROM mappings ORDER BY id")
        operations = build_import_operations(
            loaded["config"], mappings, selections
        )
        created = []
        updated = []
        errors = list(operations["errors"])
        # A criação da pasta é melhor-esforço: se o Windows bloquear (ACL,
        # perfil de outro usuário etc.), o mapeamento é importado mesmo assim
        # e o usuário recebe um aviso amigável.
        warnings = []
        now = _now_iso()

        # Cria as pastas/pasta-pai dos itens selecionados, inclusive os que já
        # estão iguais no banco mas cujo caminho local foi apagado.
        for item in operations["skipped"]:
            try:
                validate_local_mapping_path(
                    item["local_path"], item["is_file"], create=True
                )
            except LocalPathError as exc:
                warnings.append({"uid": item["uid"], "warning": str(exc)})

        for item in operations["create"]:
            try:
                validate_local_mapping_path(
                    item["local_path"], item["is_file"], create=True
                )
            except LocalPathError as exc:
                warnings.append({"uid": item["uid"], "warning": str(exc)})
            try:
                mapping_id = await database.execute(
                    """INSERT INTO mappings
                       (uid, name, local_path, remote_path, include_subfolders,
                        encrypt, enabled, is_file, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item["uid"],
                        item["name"],
                        item["local_path"],
                        item["remote_path"],
                        int(item["include_subfolders"]),
                        int(item["encrypt"]),
                        int(item["enabled"]),
                        int(item["is_file"]),
                        now,
                        now,
                    ),
                )
                row = await database.fetch_one(
                    "SELECT * FROM mappings WHERE id = ?", (mapping_id,)
                )
                created.append(row)
            except Exception as exc:
                errors.append({"uid": item["uid"], "error": str(exc)})

        for item in operations["update"]:
            try:
                validate_local_mapping_path(
                    item["local_path"], item["is_file"], create=True
                )
            except LocalPathError as exc:
                warnings.append({"uid": item["uid"], "warning": str(exc)})
            try:
                await database.execute(
                    """UPDATE mappings
                       SET uid = ?, name = ?, local_path = ?, remote_path = ?,
                           include_subfolders = ?, encrypt = ?, enabled = ?,
                           is_file = ?, updated_at = ?
                       WHERE id = ?""",
                    (
                        item["uid"],
                        item["name"],
                        item["local_path"],
                        item["remote_path"],
                        int(item["include_subfolders"]),
                        int(item["encrypt"]),
                        int(item["enabled"]),
                        int(item["is_file"]),
                        now,
                        item["id"],
                    ),
                )
                await database.execute(
                    "DELETE FROM files WHERE mapping_id = ?", (item["id"],)
                )
                row = await database.fetch_one(
                    "SELECT * FROM mappings WHERE id = ?", (item["id"],)
                )
                updated.append(row)
            except Exception as exc:
                errors.append({"uid": item["uid"], "error": str(exc)})

        return {
            "created": created,
            "updated": updated,
            "skipped": operations["skipped"],
            "errors": errors,
            "warnings": warnings,
            "config_path": loaded.get("path"),
            "source": loaded.get("source"),
            "config_hash": current_hash,
        }


# Importações tardias evitam um ciclo entre api/database/auth e este módulo.
from backend import auth, database  # noqa: E402
from backend.terabox_client import TeraboxAuthError, TeraboxClient  # noqa: E402


remote_config_manager = RemoteConfigManager()
