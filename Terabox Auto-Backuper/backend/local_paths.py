"""Validação e criação de caminhos locais de mapeamento.

O caminho local pode não existir ainda: uma pasta nova, um save de Minecraft
com nome específico ou um arquivo único que só será criado na restauração.
Este módulo centraliza a decisão de tipo (pasta x arquivo) e a criação segura:

- pasta -> cria a pasta;
- arquivo único -> cria somente a pasta-pai (nunca um arquivo vazio).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


class LocalPathError(ValueError):
    """Caminho local inválido ou impossível de criar."""


@dataclass
class LocalPathResult:
    path: str
    is_file: bool
    warnings: List[str] = field(default_factory=list)


def _clean_raw_path(raw_path: str) -> str:
    raw = str(raw_path or "").strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
        raw = raw[1:-1].strip()
    return raw


def _nearest_existing_ancestor(start: str) -> Optional[str]:
    """Sobe até o primeiro ancestral existente e confere se é pasta."""
    current = start
    while current:
        if os.path.exists(current):
            if not os.path.isdir(current):
                raise LocalPathError(
                    f"O caminho pai é um arquivo: {current}."
                )
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent
    return None


def validate_local_mapping_path(
    raw_path: str,
    is_file: Optional[bool] = None,
    *,
    create: bool = False,
    fallback_is_file: Optional[bool] = None,
) -> LocalPathResult:
    """Valida e, opcionalmente, cria o caminho local de um mapeamento.

    ``is_file=None`` detecta o tipo quando o caminho existe. Se ainda não
    existe, usa ``fallback_is_file`` (edição de mapeamento) ou assume pasta.
    """
    raw = _clean_raw_path(raw_path)
    if not raw:
        raise LocalPathError("Informe o caminho local da pasta ou do arquivo.")

    expanded = os.path.expandvars(os.path.expanduser(raw))
    if not os.path.isabs(expanded):
        raise LocalPathError(
            "Informe um caminho local absoluto (ex.: C:\\Pasta ou "
            "D:\\Pasta\\arquivo.txt)."
        )

    normalized = os.path.abspath(expanded)
    drive, tail = os.path.splitdrive(normalized)
    if not tail or tail.strip("\\/") == "":
        raise LocalPathError(
            "A raiz de uma unidade não pode ser usada como mapeamento."
        )

    exists = os.path.exists(normalized)
    actual_is_file = os.path.isfile(normalized) if exists else None
    actual_is_dir = os.path.isdir(normalized) if exists else None

    if exists and not actual_is_file and not actual_is_dir:
        raise LocalPathError(
            f"O caminho existe, mas não é arquivo nem pasta: {normalized}."
        )

    if is_file is None:
        if exists:
            resolved_is_file = bool(actual_is_file)
        else:
            resolved_is_file = bool(fallback_is_file)
    else:
        resolved_is_file = bool(is_file)

    if resolved_is_file and raw.endswith(("\\", "/")):
        raise LocalPathError(
            "Um mapeamento de arquivo único não pode terminar com barra. "
            "Informe o arquivo completo."
        )

    if exists:
        if resolved_is_file and actual_is_dir:
            raise LocalPathError(
                f"Já existe uma pasta neste caminho: {normalized}. "
                "Escolha o arquivo, não a pasta."
            )
        if not resolved_is_file and actual_is_file:
            raise LocalPathError(
                f"Já existe um arquivo neste caminho: {normalized}. "
                "Escolha uma pasta."
            )

    warnings: List[str] = []
    if resolved_is_file:
        parent = os.path.dirname(normalized)
        _nearest_existing_ancestor(parent)
        if not os.path.isdir(parent):
            warnings.append(
                "A pasta pai ainda não existe; ela será criada."
            )
        if not exists:
            warnings.append(
                "O arquivo ainda não existe; ele não será criado vazio."
            )
    else:
        _nearest_existing_ancestor(normalized)
        if not exists:
            warnings.append("A pasta ainda não existe; ela será criada.")

    if create:
        try:
            if resolved_is_file:
                os.makedirs(os.path.dirname(normalized), exist_ok=True)
            else:
                os.makedirs(normalized, exist_ok=True)
        except OSError as exc:
            target = (
                os.path.dirname(normalized)
                if resolved_is_file
                else normalized
            )
            raise LocalPathError(
                f"Não foi possível criar a pasta '{target}': {exc}"
            ) from exc

    return LocalPathResult(
        path=normalized,
        is_file=resolved_is_file,
        warnings=warnings,
    )
