"""Testes do helper de subprocessos sem console."""

from __future__ import annotations

import os
import subprocess

from pdf_tts.audio import run_hidden


def test_run_hidden_sets_windows_flags(monkeypatch) -> None:
    captured: dict = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("pdf_tts.audio.subprocess.run", fake_run)
    run_hidden(["ffmpeg", "-version"], capture_output=True)
    assert captured["command"] == ["ffmpeg", "-version"]
    if os.name == "nt":
        assert captured["creationflags"] == subprocess.CREATE_NO_WINDOW
        assert captured["startupinfo"].dwFlags & subprocess.STARTF_USESHOWWINDOW
