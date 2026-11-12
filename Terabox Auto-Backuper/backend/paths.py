r"""Normalização de caminhos locais e remotos.

O Terabox usa caminhos POSIX (barras ``/``). O app roda no Windows, então é
preciso converter ``\`` para ``/`` antes de enviar qualquer caminho à API.
"""

import hashlib
import os
import posixpath
import re
import unicodedata


def to_posix(path: str) -> str:
    """Converte barras invertidas do Windows em barras POSIX."""
    return str(path).replace("\\", "/")


def normalize_remote(path: str, ensure_leading: bool = True) -> str:
    """Normaliza um caminho remoto.

    - remove barras duplicadas;
    - garante uma única barra inicial;
    - remove a barra final (exceto para a raiz ``/``).
    """
    p = to_posix(path or "").strip()
    if not p:
        return "/" if ensure_leading else ""
    p = re.sub(r"/+", "/", p)
    if ensure_leading and not p.startswith("/"):
        p = "/" + p
    if p != "/":
        p = p.rstrip("/")
    return p


def join_remote(base: str, *parts: str) -> str:
    """Junta partes de um caminho remoto usando POSIX."""
    pieces = [to_posix(p).strip("/") for p in parts if p is not None and str(p) != ""]
    base = normalize_remote(base)
    joined = base.rstrip("/") + ("/" + "/".join(pieces) if pieces else "")
    return normalize_remote(joined)


def remote_parent(path: str) -> str:
    """Retorna o diretório pai de um caminho remoto (POSIX)."""
    p = normalize_remote(path)
    parent = posixpath.dirname(p)
    return parent if parent else "/"


def normalize_local(path: str) -> str:
    """Expande variáveis de ambiente e devolve caminho absoluto local."""
    expanded = os.path.expandvars(os.path.expanduser(str(path).strip()))
    return os.path.abspath(expanded)


def is_safe_relative_path(rel_path: str) -> bool:
    """True se o caminho relativo não tenta sair do diretório de destino."""
    rel = to_posix(rel_path)
    if not rel or rel.startswith("/") or re.match(r"^[A-Za-z]:", rel):
        return False
    parts = [p for p in rel.split("/") if p not in ("", ".")]
    return bool(parts) and ".." not in parts


def resolve_restore_relative(
    rel_path: str, preserve_structure: bool = True
) -> str:
    """Define o caminho relativo usado ao restaurar um arquivo.

    Quando ``preserve_structure`` é verdadeiro e o caminho é seguro, mantém as
    subpastas originais. Caso contrário, usa apenas o nome do arquivo. Isso
    impede que caminhos absolutos ou com ``..`` escapem da pasta de destino.
    """
    rel = to_posix(rel_path or "").strip().rstrip("/")
    original_parts = rel.split("/")
    if (
        preserve_structure
        and is_safe_relative_path(rel)
        and original_parts
        and original_parts[-1] not in ("", ".", "..")
    ):
        parts = [part for part in original_parts if part not in ("", ".")]
        return "/".join(parts)

    name = posixpath.basename(rel)
    # basename("..") ainda seria "..", que escaparia do destino. Nunca
    # devolver um componente especial para o download.
    if name in ("", ".", ".."):
        return "arquivo_restaurado"
    return name


# Caracteres que o Terabox recusa em nomes (emoji/símbolos) ou que não são
# seguros em caminhos. Letras acentuadas, números, espaços e pontuação comum
# continuam permitidos.
_SAFE_PUNCT = set("-_.()[]{},;@#&+=!~'")
_STRIP_CODEPOINTS = {"\ufe0e", "\ufe0f", "\u200c", "\u200d", "\u20e3"}


def _short_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:6]


def sanitize_remote_component(name: str, fallback: str = "item") -> str:
    """Sanitiza um componente de caminho remoto.

    Emojis e símbolos que o Terabox rejeita são substituídos. Quando o nome
    muda, um hash curto e determinístico é anexado para evitar colisões entre
    pastas como ``📁 A`` e ``📂 A``. O nome local original fica no manifesto,
    então o Restaurar devolve o nome correto.
    """
    original = unicodedata.normalize("NFC", str(name))
    changed = False
    chars = []
    for ch in original:
        if ch in _STRIP_CODEPOINTS:
            changed = True
            continue
        category = unicodedata.category(ch)
        if category[0] in ("L", "N", "M") or ch == " " or ch in _SAFE_PUNCT:
            chars.append(ch)
        else:
            chars.append(" ")
            changed = True

    cleaned = re.sub(r"\s+", " ", "".join(chars))
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    cleaned = cleaned.strip(" .")
    if not cleaned:
        cleaned = fallback
        changed = True

    if changed:
        stem, ext = os.path.splitext(cleaned)
        if not stem:
            stem = fallback
        cleaned = f"{stem}_{_short_hash(original)}{ext}"

    if len(cleaned) > 150:
        stem, ext = os.path.splitext(cleaned)
        cleaned = f"{stem[:130]}_{_short_hash(original)}{ext}"
    return cleaned


def sanitize_remote_relative(rel_path: str) -> str:
    """Sanitiza um caminho relativo (sem barra inicial)."""
    rel = to_posix(rel_path).strip("/")
    parts = [sanitize_remote_component(part) for part in rel.split("/") if part]
    return "/".join(parts)


def sanitize_remote_path(path: str) -> str:
    """Sanitiza todos os componentes de um caminho remoto absoluto."""
    p = normalize_remote(path)
    if p == "/":
        return "/"
    parts = [sanitize_remote_component(part) for part in p.strip("/").split("/")]
    return "/" + "/".join(parts)
