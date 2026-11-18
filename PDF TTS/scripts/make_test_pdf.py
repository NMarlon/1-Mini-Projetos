"""Gera um PDF sintético pequeno para testar o modo genérico.

Uso:
    python scripts/make_test_pdf.py "C:\caminho\teste.pdf"
"""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("teste-generico.pdf")
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("Heading", parent=styles["Heading1"], fontSize=24, leading=30, spaceAfter=18)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=11, leading=16)
    document = SimpleDocTemplate(str(output), pagesize=A4)
    story = [
        Paragraph("Livro de Teste Genérico", heading),
        Spacer(1, 12),
        Paragraph(
            "Este é um livro curto para testar a conversão automática. "
            "Ele tem três capítulos e algum texto em cada um.",
            body,
        ),
        PageBreak(),
    ]
    for number, title in [(1, "Introdução"), (2, "Desenvolvimento"), (3, "Conclusão")]:
        story += [Paragraph(f"Capítulo {number} — {title}", heading), Spacer(1, 10)]
        for paragraph in range(2):
            story.append(
                Paragraph(
                    f"Este é o parágrafo {paragraph + 1} do capítulo {number}. "
                    "Ele contém uma frase sobre comunicação, outra sobre estudo e uma terceira sobre tecnologia. "
                    "No dia 17 de novembro de 2026, às 9h30, o valor era R$ 12,50. "
                    "As siglas SWOT e CRM aparecem aqui.",
                    body,
                )
            )
            story.append(Spacer(1, 8))
        story.append(PageBreak())
    document.build(story)
    print(output, output.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
