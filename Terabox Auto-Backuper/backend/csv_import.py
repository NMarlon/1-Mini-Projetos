"""Importação de mapeamentos colados em formato CSV.

Formato aceito (uma linha por mapeamento)::

    C:\\Minha Pasta; /Backup/Minha Pasta
    C:\\Users\\marlo\\Documentos\\arquivo.pdf; /Backup/Documentos
    C:\\Saves\\Meu Mundo; /Backup/Saves; pasta
    C:\\Saves\\Meu Mundo\\level.dat; /Backup/Saves; arquivo

O terceiro campo é opcional e serve para informar o tipo quando o caminho
ainda não existe. Sem ele, o app detecta pelo filesystem; se não existir,
assume pasta. A origem pode ser uma pasta ou um arquivo. O destino é sempre
uma pasta remota. Também aceitamos tabulação e vírgula (com aspas) como
separadores.
"""

import csv
from dataclasses import dataclass, field
from typing import List, Tuple

from backend.local_paths import LocalPathError, validate_local_mapping_path
from backend.paths import normalize_remote, sanitize_remote_path


@dataclass
class CsvEntry:
    line: int
    source: str
    destination: str
    source_is_file: bool
    warnings: List[str] = field(default_factory=list)


def _split_fields(line: str) -> Tuple[List[str], str]:
    """Divide uma linha em até três campos, devolvendo (campos, erro)."""
    # Permite origem entre aspas quando o caminho contém ';'
    if line[:1] in ('"', "'"):
        try:
            row = next(csv.reader([line], delimiter=";"))
        except Exception as exc:
            return [], f"CSV inválido: {exc}"
        if len(row) >= 2:
            return [part.strip() for part in row[:3]], ""
    if ";" in line:
        return [part.strip() for part in line.split(";", 2)], ""
    if "\t" in line:
        return [part.strip() for part in line.split("\t", 2)], ""
    if "," in line:
        try:
            row = next(csv.reader([line], delimiter=","))
        except Exception as exc:
            return [], f"CSV inválido: {exc}"
        return [part.strip() for part in row[:3]], ""
    return [], "use 'origem; destino' (ponto e vírgula)"


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1].strip()
    return value


def _parse_type(value: str) -> Tuple[bool | None, str]:
    """Converte o terceiro campo em tipo explícito.

    Retorna ``(is_file, erro)``. ``None`` significa detectar automaticamente.
    """
    text = _unquote(value).strip().lower()
    if not text or text in {"auto", "detectar", "detect"}:
        return None, ""
    if text in {"arquivo", "file", "f"}:
        return True, ""
    if text in {"pasta", "folder", "d"}:
        return False, ""
    return None, "tipo inválido: use 'pasta' ou 'arquivo'"


def parse_mapping_csv(text: str, limit: int = 2000) -> Tuple[List[CsvEntry], List[dict]]:
    """Converte o texto colado em entradas de mapeamento.

    Retorna ``(entradas, erros)``. Linhas vazias e comentários com ``#`` são
    ignorados. Caminhos inexistentes são aceitos; o tipo é inferido ou
    informado no terceiro campo.
    """
    entries: List[CsvEntry] = []
    errors: List[dict] = []
    seen = set()

    for line_no, raw_line in enumerate((text or "").splitlines(), start=1):
        line = raw_line.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        if len(entries) >= limit:
            errors.append({"line": line_no, "error": f"limite de {limit} mapeamentos por importação"})
            break

        fields, split_error = _split_fields(line)
        if split_error:
            errors.append({"line": line_no, "error": split_error})
            continue
        if len(fields) < 2:
            errors.append({"line": line_no, "error": "faltou o destino depois do separador"})
            continue

        first = _unquote(fields[0]).strip().lower()
        second = _unquote(fields[1]).strip().lower()
        if first in {"origem", "source", "local", "pasta local"} and second in {
            "destino",
            "destination",
            "remote",
            "remoto",
            "pasta remota",
        }:
            continue  # cabeçalho

        source_raw = _unquote(fields[0])
        dest_raw = _unquote(fields[1])
        if not source_raw:
            errors.append({"line": line_no, "error": "origem vazia"})
            continue
        if not dest_raw:
            errors.append({"line": line_no, "error": "destino vazio"})
            continue

        requested_is_file = None
        if len(fields) >= 3:
            requested_is_file, type_error = _parse_type(fields[2])
            if type_error:
                errors.append({"line": line_no, "error": type_error})
                continue

        try:
            path_info = validate_local_mapping_path(
                source_raw, requested_is_file
            )
        except LocalPathError as exc:
            errors.append({"line": line_no, "error": str(exc)})
            continue

        destination = sanitize_remote_path(normalize_remote(dest_raw))
        if destination == "/":
            errors.append({"line": line_no, "error": "o destino não pode ser a raiz do Terabox"})
            continue

        key = (path_info.path.lower(), destination.lower())
        if key in seen:
            errors.append({"line": line_no, "error": "mapeamento duplicado na lista"})
            continue
        seen.add(key)

        entries.append(
            CsvEntry(
                line=line_no,
                source=path_info.path,
                destination=destination,
                source_is_file=path_info.is_file,
                warnings=path_info.warnings,
            )
        )

    return entries, errors
