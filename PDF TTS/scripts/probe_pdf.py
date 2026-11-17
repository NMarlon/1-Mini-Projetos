"""Ferramenta de diagnóstico: inspeciona páginas de um PDF com pdfplumber.

Uso:
    python scripts/probe_pdf.py "input/MKT 120.pdf" 10 12 13 18

Não faz parte do pipeline; serve para depurar layout/fonte/tabelas.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pdfplumber

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def group_lines(chars: list[dict], tol: float = 2.5) -> list[dict]:
    """Agrupa chars em linhas por `top` (tolerância em pontos)."""
    chars = sorted(chars, key=lambda c: (round(c["top"], 1), c["x0"]))
    lines: list[dict] = []
    for ch in chars:
        placed = False
        for line in lines:
            if abs(line["top"] - ch["top"]) <= tol:
                line["chars"].append(ch)
                line["top"] = min(line["top"], ch["top"])
                line["bottom"] = max(line["bottom"], ch["bottom"])
                placed = True
                break
        if not placed:
            lines.append(
                {
                    "top": ch["top"],
                    "bottom": ch["bottom"],
                    "chars": [ch],
                }
            )
    for line in lines:
        line["chars"].sort(key=lambda c: c["x0"])
        line["text"] = "".join(c["text"] for c in line["chars"])
        line["size"] = Counter(round(c["size"], 1) for c in line["chars"]).most_common(1)[0][0]
        line["fontname"] = Counter(c["fontname"] for c in line["chars"]).most_common(1)[0][0]
    return sorted(lines, key=lambda line: line["top"])


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    pdf_path = Path(sys.argv[1])
    pages = [int(x) for x in sys.argv[2:]]
    with pdfplumber.open(pdf_path) as pdf:
        for page_number in pages:
            page = pdf.pages[page_number - 1]
            print("=" * 100)
            print(f"PAGE {page_number}  size={page.width:.1f}x{page.height:.1f}")
            print("chars:", len(page.chars))
            sizes = Counter(round(c["size"], 1) for c in page.chars)
            print("font sizes:", sizes.most_common(8))
            fonts = Counter(c["fontname"] for c in page.chars)
            print("fonts:", fonts.most_common(6))
            lines = group_lines(page.chars)
            print(f"lines={len(lines)}")
            for line in lines[:40]:
                print(
                    f"  top={line['top']:6.1f} size={line['size']:4.1f} "
                    f"font={line['fontname'][:28]:28s} | {line['text'][:120]}"
                )
            tables = page.find_tables()
            print(f"tables={len(tables)}")
            for table in tables[:5]:
                print("  bbox=", table.bbox, "rows=", len(table.rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
