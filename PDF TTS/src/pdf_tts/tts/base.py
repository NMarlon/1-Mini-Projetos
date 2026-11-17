"""Protocolo de backend TTS."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class TTSBackendError(RuntimeError):
    """Falha permanente ao sintetizar um chunk."""


@dataclass
class SynthesisResult:
    path: Path
    duration: float
    cached: bool
    attempts: int


class TTSBackend(Protocol):
    name: str

    def cache_key(self, text: str) -> str: ...

    async def synthesize(self, text: str, force: bool = False) -> SynthesisResult: ...
