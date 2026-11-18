"""Gera o tutorial em PDF: como baixar o PDF do livro pelo site.

Uso:
    python scripts/build_download_tutorial.py

Lê as imagens de DOCS/assets/como-baixar-pdf/ e grava
DOCS/13-COMO-BAIXAR-O-PDF.pdf.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "DOCS" / "assets" / "como-baixar-pdf"
OUTPUT = ROOT / "DOCS" / "13-COMO-BAIXAR-O-PDF.pdf"

STEPS = [
    (
        "01-curso.png",
        "Passo 1 — Abra o curso e entre em “Informações do livro didático”",
        "Na página inicial do curso, clique em <b>Informações do livro didático</b> "
        "e depois em <b>Sobre o livro didático — Comunicação interpessoal: Teoria e Prática</b>.",
        "Página inicial do curso",
    ),
    (
        "02-livro.png",
        "Passo 2 — Abra o link do livro",
        "Na página “Sobre o livro didático”, clique no link "
        "<b>Comunicação Interpessoal: Teoria e Prática</b>.",
        "Página “Sobre o livro didático”",
    ),
    (
        "03-pdf.png",
        "Passo 3 — Clique no ícone de PDF",
        "Na página do livro, clique no <b>ícone de documento/PDF</b> "
        "(o terceiro ícone, ao lado da capa). O aviso “currently unlisted” é normal.",
        "Página do livro no site",
    ),
    (
        "04-download.png",
        "Passo 4 — Baixe o arquivo",
        "O PDF abre no navegador. Clique no <b>ícone de download</b> no canto "
        "superior direito e salve o arquivo no computador.",
        "PDF aberto no navegador",
    ),
]


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(42, 18 * mm, "Pathway PDF TTS — tutorial")
    canvas.drawRightString(A4[0] - 42, 18 * mm, f"Página {doc.page}")
    canvas.restoreState()


def _image(path: Path, max_width: float, max_height: float) -> Image:
    from PIL import Image as PILImage

    with PILImage.open(path) as img:
        width, height = img.size
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def build() -> int:
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#172033"),
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    subtitle = ParagraphStyle(
        "SubtitleCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=17,
        textColor=colors.HexColor("#2457d6"),
        spaceAfter=12,
    )
    body = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#333b4f"),
        alignment=TA_LEFT,
        spaceAfter=8,
    )
    step_title = ParagraphStyle(
        "StepTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#172033"),
        spaceAfter=8,
    )
    caption = ParagraphStyle(
        "CaptionCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#667085"),
        alignment=TA_CENTER,
    )
    note = ParagraphStyle(
        "NoteCustom",
        parent=body,
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#667085"),
    )

    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=21 * mm,
        rightMargin=21 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title="Como baixar o PDF do livro — Pathway PDF TTS",
        author="Pathway PDF TTS",
        subject="Tutorial para baixar o PDF do livro didático pelo site do curso",
    )
    story = [
        Paragraph("Como baixar o PDF do livro", title),
        Paragraph("Guia rápido para o site do Pathway", subtitle),
        Paragraph(
            "Entre com sua conta do Pathway e abra o curso. As imagens usam o "
            "<b>COM 150</b> como exemplo; o caminho é o mesmo para outros cursos "
            "que usam o livro didático no site.",
            body,
        ),
        Spacer(1, 4),
        Paragraph("<b>Em 4 passos:</b>", body),
        Paragraph("1. Abra o curso e clique em <b>Informações do livro didático</b>.", body),
        Paragraph("2. Clique em <b>Sobre o livro didático</b>.", body),
        Paragraph("3. Clique no <b>ícone de PDF</b> ao lado da capa.", body),
        Paragraph("4. Clique no <b>ícone de download</b> para salvar.", body),
        Spacer(1, 8),
        Paragraph(
            "<b>Dica:</b> o arquivo pode ser baixado com um nome como "
            "<font face='Courier'>_2226.pdf</font>. Renomeie para algo fácil, "
            "como <font face='Courier'>COM 150.pdf</font>, e guarde em uma pasta "
            "que você encontre depois.",
            note,
        ),
        Spacer(1, 6),
        Paragraph(
            "<b>Depois de baixar:</b> abra o Pathway PDF TTS, escolha "
            "<b>Automático — Pathway primeiro</b>, arraste o PDF, confira os "
            "capítulos e clique em <b>Gerar áudios</b>.",
            note,
        ),
        Spacer(1, 14),
        Paragraph("<b>Se algo der errado</b>", step_title),
        Paragraph(
            "• O link não abriu? Permita pop-ups para o site do curso.<br/>"
            "• O ícone de download não apareceu? Abra o PDF em uma nova aba.<br/>"
            "• O arquivo baixou como “_2226.pdf”? Renomeie para “COM 150.pdf”.",
            body,
        ),
        PageBreak(),
    ]

    max_width = A4[0] - (42 * mm)
    max_height = 150 * mm
    for filename, heading, description, caption_text in STEPS:
        story.append(Paragraph(heading, step_title))
        story.append(Paragraph(description, body))
        story.append(Spacer(1, 4))
        story.append(_image(ASSETS / filename, max_width, max_height))
        story.append(Spacer(1, 4))
        story.append(Paragraph(caption_text, caption))
        story.append(PageBreak())

    story.append(Paragraph("Pronto para ouvir", title))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "Com o PDF salvo, arraste-o para o app. O perfil "
            "<b>Automático — Pathway primeiro</b> procura “Semana 1”…“Semana 7” "
            "e “S01”…“S07”. Se o PDF não tiver esses títulos, o app avisa e divide "
            "em blocos de páginas.",
            body,
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Checklist rápido</b>", step_title))
    story.append(
        Paragraph(
            "<font face='Courier'>[ ]</font> PDF baixado e guardado em uma pasta fácil.<br/>"
            "<font face='Courier'>[ ]</font> Pasta do Pathway PDF TTS aberta.<br/>"
            "<font face='Courier'>[ ]</font> Duplo clique em <b>Pathway PDF TTS.exe</b>.<br/>"
            "<font face='Courier'>[ ]</font> Perfil <b>Automático — Pathway primeiro</b> selecionado.<br/>"
            "<font face='Courier'>[ ]</font> PDF arrastado e capítulos conferidos.<br/>"
            "<font face='Courier'>[ ]</font> Botão <b>Gerar áudios</b> clicado.",
            body,
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Use o PDF apenas para estudo pessoal. Não redistribua o arquivo nem "
            "o áudio gerado.",
            note,
        )
    )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
