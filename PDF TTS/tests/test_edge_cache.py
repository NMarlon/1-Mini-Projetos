"""Testes do cache do Edge TTS e utilitários de áudio (sem rede)."""

from __future__ import annotations

from pathlib import Path

from pdf_tts.audio import sanitize_component
from pdf_tts.tts.edge import EdgeBackend


def test_cache_key_is_deterministic_and_sensitive() -> None:
    backend = EdgeBackend("pt-BR-FranciscaNeural", "-5%", cache_root=Path("cache/test"))
    first = backend.cache_key("Olá mundo.")
    second = backend.cache_key("Olá mundo.")
    assert first == second
    assert len(first) == 64
    other = EdgeBackend("pt-BR-AntonioNeural", "-5%", cache_root=Path("cache/test"))
    assert other.cache_key("Olá mundo.") != first
    assert backend.cache_key("Olá mundo!") != first


def test_cache_paths() -> None:
    backend = EdgeBackend("pt-BR-FranciscaNeural", "-5%", cache_root=Path("cache/test"))
    key = backend.cache_key("texto")
    assert backend.cache_path(key).name == f"{key}.mp3"
    assert backend.metadata_path(key).name == f"{key}.json"
    assert "neg5pct" in str(backend.cache_dir)


def test_sanitize_component() -> None:
    assert sanitize_component("-5%") == "neg5pct"
    assert sanitize_component("+5%") == "p5pct"
    assert sanitize_component("pt-BR-FranciscaNeural") == "pt-BR-FranciscaNeural"
    assert sanitize_component("a/b c") == "a_b_c"
