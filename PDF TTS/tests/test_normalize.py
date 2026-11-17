"""Testes de normalização pt-BR para fala."""

from __future__ import annotations

from pdf_tts.config import load_lexicon
from pdf_tts.normalize import normalize_text


def _norm(text: str, kind: str = "paragraph") -> str:
    return normalize_text(text, load_lexicon(), kind=kind)


def test_section_and_course_names() -> None:
    assert "Semana um" in _norm("S01 Participação")
    assert "M K T, cento e vinte" in _norm("MKT 120")
    assert "C O M, cento e cinquenta" in _norm("COM 150")


def test_common_com_is_not_an_acronym() -> None:
    result = _norm("Use com cuidado e COM 150.")
    assert "Use com cuidado" in result
    assert "C O M, cento e cinquenta" in result


def test_numbers_currency_dates_and_percent() -> None:
    assert "dois mil e vinte e seis" in _norm("Em 2026.")
    assert "doze reais e cinquenta centavos" in _norm("R$ 12,50")
    assert "mil e duzentos reais" in _norm("R$ 1.200,00")
    assert "dezoito mil dólares" in _norm("US$ 18,000")
    assert "quinze por cento" in _norm("15%")
    assert "dezessete de novembro de dois mil e vinte e seis" in _norm("17/11/2026")
    assert "nove horas e trinta minutos" in _norm("9h30")


def test_ordinals_abbreviations_and_ranges() -> None:
    result = _norm("1º lugar, 2ª edição, p. 51, nº 5, § 2, 10-20.")
    assert "primeiro lugar" in result
    assert "segunda edição" in result
    assert "página cinquenta e um" in result
    assert "número cinco" in result
    assert "seção dois" in result
    assert "dez a vinte" in result


def test_section_numbers_and_thousands() -> None:
    result = _norm("Tabela 1.1 com 1.200 clientes.")
    assert "um ponto um" in result
    assert "mil e duzentos" in result


def test_lacuna_and_options() -> None:
    assert "lacuna" in _norm("Preencha ________ com cuidado.")
    assert "lacuna" in _norm("A resposta é _.")


def test_list_marker_is_removed() -> None:
    assert _norm("1. Compreender as necessidades", kind="list_item") == "Compreender as necessidades."


def test_quotes_do_not_get_double_period() -> None:
    result = _norm('Ele disse: “Olá.”')
    assert result.endswith(".”")
    assert "..”" not in result


def test_scripture_reference_is_spoken_naturally() -> None:
    result = _norm("(D&C 46:12.)")
    assert "Doutrina e Convênios" in result
    assert "capítulo quarenta e seis" in result
    assert "versículo doze" in result


def test_section_colon_is_cleaned() -> None:
    assert "Semana seis:" in _norm("Semana 06.:")


def test_period_before_word_gets_space() -> None:
    assert "favor. onze" in _norm("favor.11 Essas mensagens")
