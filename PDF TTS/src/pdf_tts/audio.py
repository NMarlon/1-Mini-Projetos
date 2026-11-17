"""Utilitários de áudio (ffprobe, validação, caminhos)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path


def find_tool(name: str, env_var: str | None = None) -> str | None:
    if env_var and os.environ.get(env_var):
        candidate = Path(os.environ[env_var])
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def ffprobe_path() -> str:
    tool = find_tool("ffprobe", "FFPROBE_BIN")
    if not tool:
        raise RuntimeError("ffprobe não encontrado no PATH (defina FFPROBE_BIN).")
    return tool


def ffmpeg_path() -> str:
    tool = find_tool("ffmpeg", "FFMPEG_BIN")
    if not tool:
        raise RuntimeError("ffmpeg não encontrado no PATH (defina FFMPEG_BIN).")
    return tool


def ffprobe_duration(path: Path, timeout: int = 30) -> float:
    command = [
        ffprobe_path(),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe falhou para {path}: {result.stderr.strip()}")
    data = json.loads(result.stdout or "{}")
    duration = data.get("format", {}).get("duration")
    if duration is None:
        raise RuntimeError(f"ffprobe não retornou duração para {path}")
    return float(duration)


def validate_audio(path: Path, min_duration: float = 0.2) -> tuple[bool, float, str]:
    if not path.exists():
        return False, 0.0, "arquivo não existe"
    size = path.stat().st_size
    if size < 500:
        return False, 0.0, f"arquivo pequeno ({size} bytes)"
    try:
        duration = ffprobe_duration(path)
    except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha do ffprobe
        return False, 0.0, f"ffprobe: {exc}"
    if duration < min_duration:
        return False, duration, f"duração curta ({duration:.2f}s)"
    return True, duration, "ok"


def sanitize_component(value: str) -> str:
    value = value.strip()
    if value.startswith("-"):
        value = "neg" + value[1:]
    value = value.replace("%", "pct").replace("+", "p")
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value.strip("._") or "default"
