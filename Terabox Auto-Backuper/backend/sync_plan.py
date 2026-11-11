"""Modelos e decisão pura do plano de sincronização.

Este módulo não faz chamadas de rede nem altera arquivos. Ele apenas decide,
para cada arquivo local, o que o sync deve fazer: enviar, substituir, ignorar
ou reportar erro. Assim a prévia (dry-run) e o sync real usam exatamente a
mesma lógica.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Set


@dataclass
class RemoteEntry:
    """Entrada de arquivo ou pasta no Terabox."""

    path: str
    name: str = ""
    size: int = 0
    md5: Optional[str] = None
    is_dir: bool = False
    mtime: Optional[int] = None


@dataclass
class RemoteSnapshot:
    """Índice remoto de um mapeamento."""

    files: Dict[str, RemoteEntry] = field(default_factory=dict)
    dirs: Set[str] = field(default_factory=set)


@dataclass
class LocalEntry:
    """Arquivo local encontrado na varredura."""

    rel_path: str
    full_path: str
    size: int
    mtime_ns: int
    md5: Optional[str] = None


@dataclass
class PlanItem:
    """Uma decisão do plano para um arquivo local."""

    mapping_id: int
    mapping_name: str
    local_path: str
    local_rel_path: str
    remote_path: str
    size: int
    mtime_ns: int
    action: str  # upload | replace | skip | error
    reason: str = ""
    encrypted: bool = False
    md5: Optional[str] = None
    remote_size: Optional[int] = None
    remote_md5: Optional[str] = None


@dataclass
class SyncPlan:
    """Resultado completo do planejamento."""

    items: list = field(default_factory=list)
    directories: list = field(default_factory=list)  # [(mapping_id, remote_dir)]
    errors: list = field(default_factory=list)  # [{mapping, file, error}]
    mappings: list = field(default_factory=list)
    snapshots: dict = field(default_factory=dict)  # mapping_id -> RemoteSnapshot


def decide_action(
    local_size: int,
    local_md5: Optional[str],
    remote: Optional[RemoteEntry],
    db_row: Optional[dict],
    encrypted: bool = False,
) -> tuple:
    """Decide a ação para um arquivo.

    Retorna ``(acao, motivo)``.

    Regras:
    - remoto ausente -> upload;
    - remoto é pasta -> error;
    - criptografado -> compara com o MD5 do plaintext guardado no banco;
    - não criptografado -> tamanho + MD5 remoto (ou banco, se o remoto não
      informar MD5);
    - conteúdo igual -> skip;
    - conteúdo diferente -> replace.
    """
    if remote is None:
        return "upload", "não existe no Terabox"

    if remote.is_dir:
        return "error", "existe uma pasta no caminho onde deveria haver um arquivo"

    if encrypted:
        if (
            db_row
            and db_row.get("md5")
            and int(db_row.get("size") or 0) == local_size
            and str(db_row.get("md5")).lower() == (local_md5 or "").lower()
        ):
            return "skip", "conteúdo original igual ao registrado"
        return "replace", "arquivo criptografado novo ou alterado"

    if int(remote.size or 0) != local_size:
        return "replace", f"tamanho diferente ({remote.size} != {local_size})"

    if remote.md5 and local_md5:
        if remote.md5.lower() == local_md5.lower():
            return "skip", "MD5 igual"
        return "replace", "MD5 diferente"

    # O Terabox nem sempre devolve MD5. Nesse caso usamos o cache local.
    if (
        db_row
        and db_row.get("md5")
        and int(db_row.get("size") or 0) == local_size
        and str(db_row.get("md5")).lower() == (local_md5 or "").lower()
    ):
        return "skip", "sem MD5 remoto; cache local confere"

    return "replace", "sem MD5 remoto e cache local diferente"
