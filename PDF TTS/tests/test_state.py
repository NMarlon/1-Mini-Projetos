"""Testes do estado SQLite."""

from __future__ import annotations

from pathlib import Path

from pdf_tts.state import StateStore


def test_state_lifecycle(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    with StateStore(path) as state:
        state.mark_running("abc", "S01", "S01-c0001")
        assert state.get("abc")["status"] == "running"
        state.mark_done("abc", "S01", "S01-c0001", tmp_path / "a.mp3", 1.5, 1)
        assert state.get("abc")["status"] == "done"
        assert state.counts() == {"done": 1}

        state.mark_failed("def", "S02", "S02-c0001", "erro", 3)
        assert state.get("def")["status"] == "failed"
        assert state.counts("S02") == {"failed": 1}
        assert state.failed()[0]["key"] == "def"
