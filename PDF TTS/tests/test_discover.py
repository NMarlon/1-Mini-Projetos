"""Testes da detecção genérica de capítulos e do modo de conteúdo."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from pdf_tts.discover import discover_pdf
from pdf_tts.extract import RawBlock, classify_block
from pdf_tts.generic import ConvertOptions, make_project


def _make_pdf(path: Path, headings: bool) -> Path:
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("Heading", parent=styles["Heading1"], fontSize=24, leading=30, spaceAfter=18)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=11, leading=16)
    document = SimpleDocTemplate(str(path), pagesize=A4)
    story = []
    if headings:
        story += [Paragraph("Livro de Teste", heading), Spacer(1, 10)]
    for number in range(1, 4):
        if headings:
            story += [Paragraph(f"Capítulo {number} — Parte {number}", heading), Spacer(1, 8)]
        for paragraph in range(2):
            story.append(
                Paragraph(
                    f"Parágrafo {paragraph + 1} do bloco {number}. "
                    "Texto suficiente para simular um livro real com algumas frases.",
                    body,
                )
            )
            story.append(Spacer(1, 8))
        story.append(PageBreak())
    document.build(story)
    return path


def test_detects_headings(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "com-capítulos.pdf", headings=True)
    discovery = discover_pdf(pdf)
    titles = [chapter.title for chapter in discovery.chapters]
    assert discovery.total_pages == 3
    assert any("Capítulo 1" in title for title in titles)
    assert any("Capítulo 2" in title for title in titles)
    assert any("Capítulo 3" in title for title in titles)
    assert discovery.chapters[0].start_page == 1
    assert discovery.chapters[-1].end_page == discovery.total_pages


def test_fallback_without_headings(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "sem-capítulos.pdf", headings=False)
    discovery = discover_pdf(pdf, chapter_size=2)
    assert discovery.structure == "fallback"
    assert len(discovery.chapters) == 2
    assert discovery.chapters[0].start_page == 1
    assert discovery.chapters[-1].end_page == discovery.total_pages
    assert all(chapter.title.startswith("Parte") for chapter in discovery.chapters)


def test_no_chapters_mode(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "livro.pdf", headings=False)
    discovery = discover_pdf(pdf, chapter_mode="none")
    assert len(discovery.chapters) == 1
    assert discovery.chapters[0].start_page == 1
    assert discovery.chapters[0].end_page == discovery.total_pages


def test_manual_chapters(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "manual.pdf", headings=False)
    discovery = discover_pdf(
        pdf,
        chapter_mode="manual",
        manual_chapters=[
            {"title": "Primeira parte", "start_page": 1, "end_page": 2},
            {"title": "Segunda parte", "start_page": 3, "end_page": 3},
        ],
    )
    assert [chapter.title for chapter in discovery.chapters] == ["Primeira parte", "Segunda parte"]


def test_all_mode_keeps_reference() -> None:
    block = RawBlock(
        page=1,
        text="1 Élder Jeffrey R. Holland, Conferência Geral de Abril de 2007",
        size=9.0,
        fontname="Roboto-Regular",
        top=0.0,
        x0=0.0,
    )
    auto = classify_block(block, 9.0, "x", content_mode="auto")
    all_mode = classify_block(block, 9.0, "x", content_mode="all")
    assert auto.drop_reason == "reference"
    assert all_mode.drop_reason is None


def test_project_is_dynamic(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "dinamico.pdf", headings=True)
    discovery = discover_pdf(pdf)
    project = make_project(pdf, discovery, ConvertOptions(content_mode="all"))
    assert len(project.weeks) == len(discovery.chapters)
    assert project.weeks[0].start_page == 1
    assert project.settings["chapter_label"] == "Parte"
    assert project.settings["content_mode"] == "all"
