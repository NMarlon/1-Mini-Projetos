"""Testes de limpeza e heurísticas de texto (sem PDFs reais)."""

from __future__ import annotations

from pdf_tts.clean import (
    clean_text,
    is_caption,
    is_section_heading,
    is_small_print_drop,
    join_lines,
    looks_like_reference,
    reference_score,
    strip_attribution,
    strip_urls,
)


def test_ligatures_and_pua_are_removed() -> None:
    text = "proﬁssional ﬂexível \uf584 opção"
    cleaned = clean_text(text)
    assert "ﬁ" not in cleaned
    assert "ﬂ" not in cleaned
    assert "\uf584" not in cleaned
    assert "profissional" in cleaned
    assert "flexível" in cleaned


def test_urls_are_removed() -> None:
    text = "Acesso em https://example.com/abc e www.example.org."
    cleaned = strip_urls(text)
    assert "http" not in cleaned
    assert "www." not in cleaned
    assert "Acesso em" in cleaned


def test_join_lines_dehyphenates_words() -> None:
    assert join_lines(["impedi-", "am o avanço"]) == "impediam o avanço"
    assert join_lines(["torná-", "los realidade"]) == "torná-los realidade"
    assert join_lines(["e-", "mail"]) == "e-mail"


def test_section_heading_patterns() -> None:
    assert is_section_heading("S01 Participação") == (True, "sxx")
    assert is_section_heading("Introdução") == (True, "introduction")
    assert is_section_heading("Verificação de Conhecimento") == (True, "quiz")
    assert is_section_heading("Texto comum") == (False, "")


def test_captions() -> None:
    assert is_caption("Imagem 1.1 Etapas do Processo")
    assert is_caption("Tabela 4.1 Quatro opções")
    assert not is_caption("Tabela de preços")


def test_small_print_sources_are_dropped_but_content_is_kept() -> None:
    assert is_small_print_drop("Fonte: Pexels.com")
    assert is_small_print_drop("Atributo: Todas as definições foram retiradas do Oxford Dictionary")
    assert not is_small_print_drop(
        "Percepção é como você organiza o mundo. Fonte: Pexels.com"
    )


def test_strip_attribution_keeps_content() -> None:
    text = "Percepção é como você organiza o mundo. Fonte: Pexels.com"
    assert strip_attribution(text) == "Percepção é como você organiza o mundo"


def test_reference_heuristics() -> None:
    assert looks_like_reference("1 Élder Jeffrey R. Holland, Conferência Geral de Abril de 2007")
    assert looks_like_reference("5 John Gottman, “Por que os Casamentos Fracassam”, Simon & Schuster, 1995")
    assert not looks_like_reference(
        "Compartilhe sua opinião ao reconhecer que esta é uma questão pequena. "
        "Compartilhe uma percepção do livro didático. Citações formais não são necessárias."
    )
    assert reference_score("Conferência Geral de 2023") >= 4
    assert looks_like_reference("Jan. 13, 2008).")
