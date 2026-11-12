"""Resolução de destinos e planejamento do Restaurar.

Este módulo não faz chamadas de rede nem altera arquivos. Ele decide, para cada
arquivo selecionado, qual mapeamento usar, qual caminho local será restaurado e
se o destino já existe. A rota ``/api/restore/download`` usa exatamente o mesmo
plano para executar os downloads.

Regras principais:

- mapeamento de pasta -> ``mapping.local_path / local_rel_path``;
- mapeamento de arquivo único -> ``mapping.local_path`` (o arquivo em si);
- pastas existentes são mescladas e nada é apagado;
- arquivo existente no mesmo caminho vira ``replace``;
- caminhos inseguros ou ambíguos viram erro, nunca fallback silencioso.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from backend.paths import (
    is_safe_relative_path,
    normalize_local,
    normalize_remote,
    to_posix,
)


class RestoreTargetError(Exception):
    """Erro de resolução de um destino individual."""

    def __init__(
        self,
        message: str,
        code: str = "invalid_target",
        local_path: Optional[str] = None,
    ):
        super().__init__(message)
        self.code = code
        self.local_path = local_path


@dataclass
class RestoreTarget:
    """Resultado do planejamento para um arquivo do manifesto."""

    remote_path: str
    mapping_id: Optional[int] = None
    mapping_name: str = ""
    local_path: Optional[str] = None
    local_rel_path: str = ""
    action: str = "error"  # create | replace | error
    exists: bool = False
    encrypted: bool = False
    error: Optional[str] = None
    error_code: Optional[str] = None
    mapping_is_file: bool = False
    size: int = 0

    def to_dict(self) -> dict:
        return {
            "remote_path": self.remote_path,
            "mapping_id": self.mapping_id,
            "mapping_name": self.mapping_name,
            "local_path": self.local_path,
            "local_rel_path": self.local_rel_path,
            "action": self.action,
            "exists": self.exists,
            "encrypted": self.encrypted,
            "error": self.error,
            "error_code": self.error_code,
            "mapping_is_file": self.mapping_is_file,
            "size": self.size,
        }


@dataclass
class RestorePlan:
    """Plano completo, com alvos e contadores."""

    targets: List[RestoreTarget] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "files": [target.to_dict() for target in self.targets],
        }


def _name_key(value) -> str:
    return str(value or "").strip().casefold()


def _id_value(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _size_value(value) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _remote_under(remote_path, root) -> bool:
    """True se ``remote_path`` está dentro de ``root`` (respeitando barras)."""
    remote = normalize_remote(remote_path or "")
    root = normalize_remote(root or "")
    if not root or root == "/":
        return False
    return remote == root or remote.startswith(root + "/")


def _mapping_matches_entry(mapping: dict, entry: dict) -> bool:
    if _remote_under(entry.get("remote_path"), mapping.get("remote_path")):
        return True
    entry_name = _name_key(entry.get("mapping_name"))
    return bool(entry_name) and entry_name == _name_key(mapping.get("name"))


def _filter_by_name(mappings, entry) -> list:
    name = _name_key(entry.get("mapping_name"))
    if not name:
        return []
    return [
        mapping
        for mapping in mappings
        if _name_key(mapping.get("name")) == name
    ]


def resolve_restore_mapping(entry: dict, mappings) -> Optional[dict]:
    """Descobre qual mapeamento atual corresponde a uma entrada do manifesto.

    Ordem:

    1. ``mapping_id`` exato, mas só se o caminho remoto ou o nome também
       confirmarem. Isso evita escrever no lugar errado quando o backup veio de
       outro PC e os IDs foram recriados.
    2. ``mapping_remote_path`` exato, se o manifesto novo trouxer esse campo.
    3. Prefixo remoto mais longo (o mapeamento cujo ``remote_path`` contém o
       arquivo).
    4. Nome do mapeamento, somente se for único.
    """

    mappings = list(mappings or [])
    entry_id = _id_value(entry.get("mapping_id"))
    if entry_id is not None:
        for mapping in mappings:
            if _id_value(mapping.get("id")) == entry_id and _mapping_matches_entry(
                mapping, entry
            ):
                return mapping

    entry_remote_root = entry.get("mapping_remote_path")
    if entry_remote_root:
        exact = [
            mapping
            for mapping in mappings
            if normalize_remote(mapping.get("remote_path") or "")
            == normalize_remote(entry_remote_root)
        ]
        if len(exact) == 1:
            return exact[0]
        exact_by_name = _filter_by_name(exact, entry)
        if len(exact_by_name) == 1:
            return exact_by_name[0]

    candidates = [
        mapping
        for mapping in mappings
        if _remote_under(entry.get("remote_path"), mapping.get("remote_path"))
    ]
    if candidates:
        ranked = [
            (len(normalize_remote(mapping.get("remote_path") or "")), mapping)
            for mapping in candidates
        ]
        max_len = max(length for length, _ in ranked)
        best = [mapping for length, mapping in ranked if length == max_len]
        if len(best) == 1:
            return best[0]
        best_by_name = _filter_by_name(best, entry)
        if len(best_by_name) == 1:
            return best_by_name[0]
        return None

    by_name = _filter_by_name(mappings, entry)
    if len(by_name) == 1:
        return by_name[0]
    return None


def _file_mapping_relative_matches(local_base: str, rel_path: str) -> bool:
    rel = to_posix(rel_path or "").strip().strip("/")
    if not rel or "/" in rel or rel in (".", ".."):
        return False
    return os.path.basename(local_base).casefold() == rel.casefold()


def _ensure_within_base(base: Path, target: Path):
    """Impede que ``target`` escape de ``base``, inclusive via symlink/junção."""
    try:
        base_res = Path(base).resolve(strict=False)
        target_res = Path(target).resolve(strict=False)
        base_norm = os.path.normcase(str(base_res))
        target_norm = os.path.normcase(str(target_res))
        if os.path.commonpath([base_norm, target_norm]) != base_norm:
            raise RestoreTargetError(
                "o destino sairia da pasta original do mapeamento",
                "path_escape",
                str(target),
            )
    except ValueError as exc:
        raise RestoreTargetError(
            "o destino está em uma unidade diferente da pasta original",
            "path_escape",
            str(target),
        ) from exc
    except OSError:
        # Resolução indisponível: comparação textual conservadora.
        base_norm = os.path.normcase(os.path.abspath(str(base)))
        target_norm = os.path.normcase(os.path.abspath(str(target)))
        if not (
            target_norm == base_norm
            or target_norm.startswith(base_norm + os.sep)
        ):
            raise RestoreTargetError(
                "o destino sairia da pasta original do mapeamento",
                "path_escape",
                str(target),
            )


def _ensure_parents_are_dirs(base: Path, target: Path):
    parent = target.parent
    while True:
        if parent.exists() and not parent.is_dir():
            raise RestoreTargetError(
                f"o caminho pai é um arquivo: {parent}",
                "parent_is_file",
                str(target),
            )
        if parent == base or parent.parent == parent:
            break
        parent = parent.parent


def resolve_restore_target(mapping: dict, entry: dict):
    """Calcula o caminho local final de uma entrada do manifesto.

    Retorna ``(Path, is_file_mapping)``. Levanta ``RestoreTargetError`` quando o
    caminho é inseguro, o tipo do mapeamento não corresponde ao manifesto ou o
    destino entra em conflito com uma pasta/arquivo existente.
    """

    raw_local_path = str(mapping.get("local_path") or "").strip()
    if not raw_local_path:
        raise RestoreTargetError(
            "o mapeamento não tem caminho local configurado",
            "invalid_mapping",
        )
    local_path = normalize_local(raw_local_path)

    rel_path = to_posix(entry.get("local_rel_path") or "").strip()
    is_file_mapping = mapping.get("is_file")
    if is_file_mapping is None:
        # Compatibilidade com bancos antigos antes da migração da coluna.
        is_file_mapping = os.path.isfile(local_path)
    else:
        is_file_mapping = bool(is_file_mapping)

    if is_file_mapping:
        if not _file_mapping_relative_matches(local_path, rel_path):
            raise RestoreTargetError(
                "o mapeamento é de arquivo único, mas o caminho do manifesto "
                "não corresponde ao arquivo configurado",
                "file_mapping_mismatch",
                local_path,
            )
        target = Path(local_path)
        if target.is_dir():
            raise RestoreTargetError(
                "existe uma pasta no lugar do arquivo original",
                "target_is_directory",
                str(target),
            )
        _ensure_parents_are_dirs(target.parent, target)
        return target, True

    if not is_safe_relative_path(rel_path):
        raise RestoreTargetError(
            "o caminho do manifesto é inseguro e não pode ser restaurado",
            "unsafe_path",
        )

    base = Path(local_path)
    if base.exists() and not base.is_dir():
        raise RestoreTargetError(
            "a origem configurada é um arquivo, mas o backup espera uma pasta",
            "mapping_is_file",
            str(base),
        )

    parts = [part for part in rel_path.split("/") if part not in ("", ".")]
    if not parts:
        raise RestoreTargetError(
            "o caminho do manifesto está vazio",
            "invalid_path",
            str(base),
        )

    target = base.joinpath(*parts)
    _ensure_within_base(base, target)

    if target.exists() and target.is_dir():
        raise RestoreTargetError(
            "existe uma pasta no caminho onde deveria haver um arquivo",
            "target_is_directory",
            str(target),
        )

    _ensure_parents_are_dirs(base, target)
    return target, False


def _normalize_selected(files) -> list:
    selected = []
    seen = set()
    for value in files or []:
        remote = normalize_remote(str(value or ""))
        if not remote or remote == "/" or remote in seen:
            continue
        seen.add(remote)
        selected.append(remote)
    return selected


def _manifest_index(manifest: dict) -> dict:
    index = {}
    for entry in (manifest or {}).get("files", []) or []:
        remote = normalize_remote(entry.get("remote_path") or "")
        if remote and remote != "/":
            index[remote] = entry
    return index


def _mark_duplicate_targets(targets: List[RestoreTarget]):
    groups = {}
    for target in targets:
        if target.action == "error" or not target.local_path:
            continue
        try:
            key = os.path.normcase(
                str(Path(target.local_path).resolve(strict=False))
            )
        except OSError:
            key = os.path.normcase(os.path.abspath(target.local_path))
        groups.setdefault(key, []).append(target)

    for group in groups.values():
        if len(group) <= 1:
            continue
        sample = group[0].local_path
        for target in group:
            target.action = "error"
            target.error = (
                "dois arquivos selecionados apontam para o mesmo destino: "
                + str(sample)
            )
            target.error_code = "duplicate_target"


def summarize_restore_plan(targets: List[RestoreTarget]) -> dict:
    summary = {
        "total": len(targets),
        "create": 0,
        "replace": 0,
        "errors": 0,
        "mappings": len(
            {
                target.mapping_id
                for target in targets
                if target.mapping_id is not None and target.action != "error"
            }
        ),
        "missing_mappings": 0,
        "duplicates": 0,
        "encrypted": 0,
    }
    for target in targets:
        if target.action == "create":
            summary["create"] += 1
        elif target.action == "replace":
            summary["replace"] += 1
        else:
            summary["errors"] += 1
        if target.error_code == "mapping_not_found":
            summary["missing_mappings"] += 1
        if target.error_code == "duplicate_target":
            summary["duplicates"] += 1
        if target.encrypted and target.action != "error":
            summary["encrypted"] += 1
    return summary


def build_restore_plan(files, manifest: dict, mappings) -> RestorePlan:
    """Monta o plano de restauração sem tocar no disco."""

    selected = _normalize_selected(files)
    manifest_index = _manifest_index(manifest)
    targets: List[RestoreTarget] = []

    for remote_path in selected:
        entry = manifest_index.get(remote_path)
        if not entry:
            targets.append(
                RestoreTarget(
                    remote_path=remote_path,
                    action="error",
                    error=(
                        "arquivo não está no manifesto atual; "
                        "recarregue o manifesto e tente novamente"
                    ),
                    error_code="manifest_missing",
                )
            )
            continue

        mapping = resolve_restore_mapping(entry, mappings)
        if not mapping:
            targets.append(
                RestoreTarget(
                    remote_path=remote_path,
                    mapping_id=_id_value(entry.get("mapping_id")),
                    mapping_name=str(entry.get("mapping_name") or ""),
                    local_rel_path=to_posix(entry.get("local_rel_path") or ""),
                    encrypted=bool(entry.get("encrypted")),
                    size=_size_value(entry.get("size")),
                    action="error",
                    error=(
                        "mapeamento não encontrado em Configuração; "
                        "recrie o mapeamento com o mesmo caminho remoto"
                    ),
                    error_code="mapping_not_found",
                )
            )
            continue

        try:
            target_path, is_file_mapping = resolve_restore_target(mapping, entry)
        except RestoreTargetError as exc:
            targets.append(
                RestoreTarget(
                    remote_path=remote_path,
                    mapping_id=_id_value(mapping.get("id")),
                    mapping_name=str(mapping.get("name") or ""),
                    local_path=exc.local_path,
                    local_rel_path=to_posix(entry.get("local_rel_path") or ""),
                    encrypted=bool(entry.get("encrypted")),
                    size=_size_value(entry.get("size")),
                    action="error",
                    error=str(exc),
                    error_code=exc.code,
                )
            )
            continue

        exists = target_path.exists()
        targets.append(
            RestoreTarget(
                remote_path=remote_path,
                mapping_id=_id_value(mapping.get("id")),
                mapping_name=str(mapping.get("name") or ""),
                local_path=str(target_path),
                local_rel_path=to_posix(entry.get("local_rel_path") or ""),
                action="replace" if exists else "create",
                exists=exists,
                encrypted=bool(entry.get("encrypted")),
                mapping_is_file=is_file_mapping,
                size=_size_value(entry.get("size")),
            )
        )

    _mark_duplicate_targets(targets)
    return RestorePlan(targets=targets, summary=summarize_restore_plan(targets))


def compute_file_metadata(path: str) -> dict:
    """Lê o arquivo restaurado e devolve tamanho, MD5 e mtime_ns."""
    stat = os.stat(path)
    digest = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "size": stat.st_size,
        "md5": digest.hexdigest(),
        "mtime_ns": stat.st_mtime_ns,
    }
