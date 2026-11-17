"""Testes da classificação de blocos e formatação de tabelas."""

from __future__ import annotations

from pdf_tts.extract import RawBlock, classify_block, format_table


def _block(text: str, size: float = 9.0, marker: bool = False) -> RawBlock:
    return RawBlock(
        page=1,
        text=text,
        size=size,
        fontname="Roboto-Regular",
        top=0.0,
        x0=0.0,
        had_marker=marker,
    )


def test_heading_and_paragraph_classification() -> None:
    assert classify_block(_block("Semana 1: Noções Básicas", size=25.7), 9.0, "x").kind == "week_title"
    assert classify_block(_block("S01 Participação", size=10.5), 9.0, "x").kind == "section_heading"
    assert classify_block(_block("O que é Marketing?", size=21.4), 9.0, "x").kind == "heading"
    assert classify_block(_block("Texto normal."), 9.0, "x").kind == "paragraph"


def test_option_marker() -> None:
    block = classify_block(_block("Para maximizar as despesas", marker=True), 9.0, "x")
    assert block.kind == "option"
    assert block.text.startswith("Opção: ")


def test_small_print_content_and_source() -> None:
    source = classify_block(_block("Fonte: Pexels.com", size=7.2), 9.0, "x")
    assert source.drop_reason == "small_print"
    content = classify_block(_block("Uma frase de conteúdo. Fonte: Pexels.com", size=7.2), 9.0, "x")
    assert content.drop_reason is None
    assert "Fonte" not in content.text


def test_reference_block_is_dropped() -> None:
    block = classify_block(
        _block("1 Élder Jeffrey R. Holland, Conferência Geral de Abril de 2007"),
        9.0,
        "x",
    )
    assert block.kind == "reference"
    assert block.drop_reason == "reference"


def test_format_table_with_header() -> None:
    rows = [
        ["", "Pontos Fortes", "Pontos Fracos"],
        ["Pesquisas por e-mail", "- Alcance\n- Conveniência", "- Caro\n- Prazo"],
    ]
    text = format_table(rows)
    assert "Pesquisas por e-mail" in text
    assert "Pontos Fortes: Alcance; Conveniência" in text
    assert "Pontos Fracos: Caro; Prazo" in text


def test_format_table_without_header() -> None:
    rows = [
        ["Solteiros", "$18,000", "12", "$750"],
        ["Mães", "$22,000", "8", "$1,200"],
    ]
    text = format_table(rows)
    assert "Solteiros" in text
    assert "$22,000" in text
