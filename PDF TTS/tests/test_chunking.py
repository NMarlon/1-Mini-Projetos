"""Testes de divisão em sentenças e chunks."""

from __future__ import annotations

from pdf_tts.chunking import merge_short, split_long, split_sentences


def test_split_simple_sentences() -> None:
    assert split_sentences("Olá. Tudo bem? Sim!") == ["Olá.", "Tudo bem?", "Sim!"]


def test_split_protects_abbreviations_and_initials() -> None:
    text = "O Dr. Silva chegou. M. Russell Ballard falou, etc. Fim."
    parts = split_sentences(text)
    assert parts[0] == "O Dr. Silva chegou."
    assert any("M. Russell" in part for part in parts)
    assert "etc." in parts[-1]
    assert parts[-1].endswith("Fim.")


def test_split_keeps_quotes() -> None:
    parts = split_sentences('Ele disse: "Olá." Ela saiu.')
    assert parts[0] == 'Ele disse: "Olá."'
    assert parts[1] == "Ela saiu."


def test_split_protects_table_number() -> None:
    parts = split_sentences("Tabela6.2 Venda Pessoal. Exemplos: x.")
    assert parts[0] == "Tabela6.2 Venda Pessoal."
    assert parts[1] == "Exemplos: x."


def test_split_long() -> None:
    text = "a " * 200
    parts = split_long(text.strip(), max_chars=100)
    assert len(parts) > 1
    assert all(len(part) <= 101 for part in parts)


def test_merge_short() -> None:
    assert merge_short(["Curto.", "Também curto."], 50) == ["Curto. Também curto."]
