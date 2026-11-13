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

# Perfis do Windows que são compartilhados ou de sistema. Um caminho neles não
# pertence a "outro usuário" e não deve ser rebaseado para o perfil atual.
_SHARED_PROFILE_NAMES = {
    "public",
    "default",
    "default user",
    "all users",
}


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
        target = (
            os.path.dirname(normalized)
            if resolved_is_file
            else normalized
        )
        if not os.path.isdir(target):
            foreign = detect_foreign_profile(target)
            if foreign:
                raise LocalPathError(
                    "O caminho pertence ao perfil do usuário "
                    f"'{foreign['foreign_user']}', não ao seu perfil "
                    f"'{foreign['current_user']}'. A pasta não foi criada "
                    "no perfil errado. Sugestão de caminho: "
                    f"{foreign['suggested_path']}"
                )
        try:
            os.makedirs(target, exist_ok=True)
        except OSError as exc:
            raise LocalPathError(
                f"Não foi possível criar a pasta '{target}': {exc}"
            ) from exc

    return LocalPathResult(
        path=normalized,
        is_file=resolved_is_file,
        warnings=warnings,
    )


def current_windows_user() -> str:
    """Nome do usuário Windows atual (vazio quando não identificável)."""
    return str(os.environ.get("USERNAME") or "").strip()


def current_user_profile() -> Optional[str]:
    """Raiz do perfil do usuário atual, quando identificável."""
    profile = str(os.environ.get("USERPROFILE") or "").strip()
    if profile and os.path.isabs(profile):
        return os.path.abspath(profile)
    user = current_windows_user()
    drive = str(os.environ.get("SystemDrive") or "C:").strip() or "C:"
    if not user:
        return None
    return os.path.join(drive + os.sep, "Users", user)


def detect_foreign_profile(
    path: str, current_user: Optional[str] = None
) -> Optional[dict]:
    """Detecta ``...\\Users\\<outro usuário>\\...`` e sugere o rebase.

    Retorna ``None`` quando o caminho não é de um perfil de usuário ou quando
    já pertence ao usuário atual. Perfis compartilhados (Public, Default etc.)
    também são ignorados.
    """
    raw = _clean_raw_path(path)
    if not raw:
        return None

    expanded = os.path.expandvars(os.path.expanduser(raw))
    if not os.path.isabs(expanded):
        return None

    normalized = os.path.abspath(expanded)
    drive, tail = os.path.splitdrive(normalized)
    parts = [part for part in tail.replace("/", "\\").split("\\") if part]
    if len(parts) < 2 or parts[0].casefold() != "users":
        return None

    foreign_user = parts[1]
    if foreign_user.casefold() in _SHARED_PROFILE_NAMES:
        return None

    current = str(current_user or current_windows_user()).strip()
    if not current or foreign_user.casefold() == current.casefold():
        return None

    profile = current_user_profile()
    profile_drive = os.path.splitdrive(profile or "")[0]
    profile_name = (
        os.path.basename((profile or "").rstrip("\\/")) if profile else ""
    )
    if (
        not profile
        or profile_drive.casefold() != drive.casefold()
        or profile_name.casefold() != current.casefold()
    ):
        profile = os.path.join(drive + os.sep, "Users", current)

    remainder = parts[2:]
    suggested = (
        os.path.normpath(os.path.join(profile, *remainder))
        if remainder
        else os.path.normpath(profile)
    )
    return {
        "foreign_user": foreign_user,
        "current_user": current,
        "foreign_root": os.path.join(drive + os.sep, "Users", foreign_user),
        "current_root": os.path.normpath(profile),
        "suggested_path": suggested,
    }
