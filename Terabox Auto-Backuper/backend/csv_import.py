"""Importação de mapeamentos colados em formato CSV.

Formato aceito (uma linha por mapeamento)::

    C:\\Minha Pasta; /Backup/Minha Pasta
    C:\\Users\\marlo\\Documentos\\arquivo.pdf; /Backup/Documentos

A origem pode ser uma pasta ou um arquivo. O destino é sempre uma pasta
remota. Também aceitamos tabulação e vírgula (com aspas) como separadores.
"""

import csv
import os
from dataclasses import dataclass
from typing import List, Tuple

from backend.paths import normalize_local, normalize_remote, sanitize_remote_path


@dataclass
class CsvEntry:
    line: int
    source: str
    destination: str
    source_is_file: bool


def _split_fields(line: str) -> Tuple[List[str], str]:
    """Divide uma linha em campos, devolvendo (campos, erro)."""
    # Permite origem entre aspas quando o caminho contém ';'
    if line[:1] in ('"', "'"):
        try:
            row = next(csv.reader([line], delimiter=";"))
        except Exception as exc:
            return [], f"CSV inválido: {exc}"
        if len(row) >= 2:
            return [part.strip() for part in row], ""
    if ";" in line:
        return [part.strip() for part in line.split(";", 1)], ""
    if "\t" in line:
        return [part.strip() for part in line.split("\t", 1)], ""
    if "," in line:
        try:
            row = next(csv.reader([line], delimiter=","))
        except Exception as exc:
            return [], f"CSV inválido: {exc}"
        return [part.strip() for part in row], ""
    return [], "use 'origem; destino' (ponto e vírgula)"


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1].strip()
    return value


def parse_mapping_csv(text: str, limit: int = 2000) -> Tuple[List[CsvEntry], List[dict]]:
    """Converte o texto colado em entradas de mapeamento.

    Retorna ``(entradas, erros)``. Linhas vazias e comentários com ``#`` são
    ignorados. Caminhos inexistentes são reportados como erro.
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

        source = normalize_local(source_raw)
        destination = sanitize_remote_path(normalize_remote(dest_raw))
        if destination == "/":
            errors.append({"line": line_no, "error": "o destino não pode ser a raiz do Terabox"})
            continue
        if not os.path.exists(source):
            errors.append({"line": line_no, "error": f"origem não encontrada: {source}"})
            continue
        if not (os.path.isfile(source) or os.path.isdir(source)):
            errors.append({"line": line_no, "error": f"origem não é arquivo nem pasta: {source}"})
            continue

        key = (source.lower(), destination.lower())
        if key in seen:
            errors.append({"line": line_no, "error": "mapeamento duplicado na lista"})
            continue
        seen.add(key)

        entries.append(
            CsvEntry(
                line=line_no,
                source=source,
                destination=destination,
                source_is_file=os.path.isfile(source),
            )
        )

    return entries, errors
