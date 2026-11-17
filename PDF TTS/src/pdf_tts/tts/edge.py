"""Backend Edge TTS com cache, retry e validação."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
from datetime import UTC, datetime
from pathlib import Path

import edge_tts

from pdf_tts.audio import sanitize_component, validate_audio
from pdf_tts.tts.base import SynthesisResult, TTSBackendError

logger = logging.getLogger("pdf_tts.edge")


class EdgeBackend:
    name = "edge"

    def __init__(
        self,
        voice: str,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
        cache_root: Path | None = None,
        concurrency: int = 3,
        retries: int = 5,
        timeout: float = 120.0,
        proxy: str | None = None,
    ) -> None:
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        self.cache_root = cache_root or Path("cache/edge")
        self.cache_dir = self.cache_root / sanitize_component(voice) / sanitize_component(rate)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.concurrency = max(1, min(4, int(concurrency)))
        self.retries = max(1, int(retries))
        self.timeout = timeout
        self.proxy = proxy
        self._semaphore = asyncio.Semaphore(self.concurrency)
        self._failure_streak = 0
        self._abort = False

    def cache_key(self, text: str) -> str:
        payload = "\x1f".join(
            [self.name, self.voice, self.rate, self.volume, self.pitch, text]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.mp3"

    def metadata_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _cached_duration(self, key: str) -> float | None:
        path = self.cache_path(key)
        if not path.exists() or path.stat().st_size < 500:
            return None
        metadata_path = self.metadata_path(key)
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                duration = float(metadata.get("duration", 0))
                if duration >= 0.2:
                    return duration
            except (ValueError, OSError):
                pass
        valid, duration, _ = validate_audio(path)
        return duration if valid else None

    def cached_duration(self, text: str) -> float | None:
        return self._cached_duration(self.cache_key(text))

    def _write_metadata(self, key: str, text: str, duration: float) -> None:
        metadata = {
            "engine": self.name,
            "voice": self.voice,
            "rate": self.rate,
            "volume": self.volume,
            "pitch": self.pitch,
            "chars": len(text),
            "duration": round(duration, 3),
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        self.metadata_path(key).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    async def synthesize(self, text: str, force: bool = False) -> SynthesisResult:
        if not text.strip():
            raise TTSBackendError("texto vazio")
        key = self.cache_key(text)
        path = self.cache_path(key)
        if not force:
            duration = self._cached_duration(key)
            if duration is not None:
                return SynthesisResult(path=path, duration=duration, cached=True, attempts=0)

        if self._abort:
            raise TTSBackendError(
                "síntese abortada após falhas consecutivas; verifique a conexão e rode --resume"
            )

        async with self._semaphore:
            last_error: Exception | None = None
            for attempt in range(1, self.retries + 1):
                tmp = path.with_name(f"{path.stem}.{random.randint(100000, 999999)}.part")
                try:
                    communicate = edge_tts.Communicate(
                        text,
                        self.voice,
                        rate=self.rate,
                        volume=self.volume,
                        pitch=self.pitch,
                        proxy=self.proxy,
                    )
                    await asyncio.wait_for(communicate.save(str(tmp)), timeout=self.timeout)
                    valid, duration, reason = validate_audio(tmp)
                    if not valid:
                        raise TTSBackendError(f"áudio inválido: {reason}")
                    tmp.replace(path)
                    self._write_metadata(key, text, duration)
                    self._failure_streak = 0
                    return SynthesisResult(
                        path=path,
                        duration=duration,
                        cached=False,
                        attempts=attempt,
                    )
                except Exception as exc:  # noqa: BLE001 - serviço externo pode falhar de várias formas
                    last_error = exc
                    tmp.unlink(missing_ok=True)
                    self._failure_streak += 1
                    logger.warning(
                        "falha ao sintetizar (tentativa %d/%d): %s: %s",
                        attempt,
                        self.retries,
                        type(exc).__name__,
                        exc,
                    )
                    if self._failure_streak >= 6:
                        self._abort = True
                    if attempt < self.retries:
                        delay = min(30.0, 2.0**attempt + random.uniform(0.0, 1.0))
                        await asyncio.sleep(delay)
            raise TTSBackendError(
                f"falha após {self.retries} tentativas: {type(last_error).__name__}: {last_error}"
            )
