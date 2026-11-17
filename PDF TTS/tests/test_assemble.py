"""Testes de montagem: SRT, capítulos e concatenação WAV."""

from __future__ import annotations

import wave
from pathlib import Path

from pdf_tts.assemble import (
    TimelineEntry,
    _fmt_srt_time,
    concat_wavs,
    write_chapters,
    write_srt,
)


def _silence_wav(path: Path, seconds: float) -> Path:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(b"\x00\x00" * int(seconds * 24000))
    return path


def _entry(start: float, end: float, text: str) -> TimelineEntry:
    return TimelineEntry(
        chunk_id="c1",
        section_id="S01-00",
        section_title="Semana 1",
        kind="paragraph",
        text=text,
        mp3=Path("a.mp3"),
        wav=Path("a.wav"),
        gap_ms=0,
        duration=end - start,
        start=start,
        end=end,
    )


def test_fmt_srt_time() -> None:
    assert _fmt_srt_time(0) == "00:00:00,000"
    assert _fmt_srt_time(3661.5) == "01:01:01,500"


def test_write_srt(tmp_path: Path) -> None:
    path = tmp_path / "a.srt"
    write_srt(path, [_entry(1.0, 2.5, "Olá mundo."), _entry(2.5, 4.0, "Segunda frase.")])
    text = path.read_text(encoding="utf-8")
    assert "1\n00:00:01,000 --> 00:00:02,500\nOlá mundo." in text
    assert "2\n00:00:02,501 --> 00:00:04,000\nSegunda frase." in text


def test_write_chapters(tmp_path: Path) -> None:
    path = tmp_path / "chapters.txt"
    write_chapters(
        path,
        [
            {"title": "Semana 1", "start": 0, "end": 10},
            {"title": "Introdução", "start": 10, "end": 20},
        ],
        20,
        {"title": "Livro", "artist": "PDF TTS"},
    )
    text = path.read_text(encoding="utf-8")
    assert text.startswith(";FFMETADATA1")
    assert "title=Livro" in text
    assert text.count("[CHAPTER]") == 2
    assert "START=0" in text
    assert "END=20000" in text


def test_concat_wavs_with_gap(tmp_path: Path) -> None:
    first = _silence_wav(tmp_path / "a.wav", 0.5)
    second = _silence_wav(tmp_path / "b.wav", 0.5)
    output = tmp_path / "out.wav"
    concat_wavs([first, second], output, gap_seconds=1.0)
    with wave.open(str(output), "rb") as handle:
        assert handle.getnframes() == 2 * 24000
        assert handle.getframerate() == 24000
