"""Orquestração de síntese, status e amostras."""

from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tqdm import tqdm

from pdf_tts.audio import validate_audio
from pdf_tts.config import ROOT, ProjectConfig, load_projects, resolve_projects
from pdf_tts.state import StateStore
from pdf_tts.tts.edge import EdgeBackend

SAMPLE_TEXT = (
    "Olá! Esta é uma amostra de voz do projeto PDF TTS. "
    "A narração é em português brasileiro e foi pensada para estudo. "
    "No dia 17 de novembro de 2026, às 9 horas e 30 minutos, o curso custa "
    "R$ 12,50, com 15% de desconto. "
    "As siglas SWOT, CRM e CLV aparecem no material, assim como WhatsApp e Canvas. "
    "Preencha a lacuna com atenção."
)

PRONUNCIATION_TEXT = (
    "Teste de pronúncia. S01, S02, MKT 120, COM 150. "
    "SWOT, CRM, CLV, KPI, PDF, IA, LGPD, WhatsApp, Canvas, OpenStax. "
    "Valores: R$ 1.200,00, US$ 18,000, 15%, 3,5. "
    "Datas: 17/11/2026. Horários: 9h30. "
    "Lacuna: ________. Fim do teste."
)


@dataclass
class BuildOptions:
    project: str = "all"
    lesson: str | None = None
    voice: str | None = None
    rate: str | None = None
    concurrency: int | None = None
    force: bool = False
    dry_run: bool = False
    no_assemble: bool = True


def _lesson_id(value: str) -> str:
    text = value.strip().upper()
    if text.startswith("S"):
        text = text[1:]
    return f"S{int(text):02d}"


def _load_lessons(project: ProjectConfig, lesson: str | None) -> list[tuple[Path, dict[str, Any]]]:
    lessons_dir = project.content_dir / "lessons"
    if not lessons_dir.exists():
        raise FileNotFoundError(
            f"{lessons_dir} não existe; rode `python -m pdf_tts segment --project {project.key}`."
        )
    if lesson:
        target = _lesson_id(lesson)
        paths = [lessons_dir / f"{target}.json"]
    else:
        paths = sorted(lessons_dir.glob("S*.json"))
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Aula não encontrada: {path}")
        loaded.append((path, json.loads(path.read_text(encoding="utf-8"))))
    if not loaded:
        raise FileNotFoundError(f"Nenhuma aula em {lessons_dir}; rode `segment`.")
    return loaded


def _prepare_project(
    project: ProjectConfig,
    options: BuildOptions,
) -> tuple[EdgeBackend, list[tuple[Path, dict[str, Any]]], dict[str, dict[str, Any]]]:
    voice = options.voice or str(project.settings.get("voice", "pt-BR-FranciscaNeural"))
    rate = options.rate or str(project.settings.get("rate", "-5%"))
    concurrency = options.concurrency or int(project.settings.get("concurrency", 3))
    backend = EdgeBackend(
        voice=voice,
        rate=rate,
        cache_root=ROOT / "cache" / "edge",
        concurrency=concurrency,
    )
    lessons = _load_lessons(project, options.lesson)
    unique: dict[str, dict[str, Any]] = {}
    for path, lesson in lessons:
        lesson["engine"] = backend.name
        lesson["voice"] = voice
        lesson["rate"] = rate
        for chunk in lesson["chunks"]:
            key = backend.cache_key(chunk["spoken"])
            chunk["cache_key"] = key
            if key not in unique:
                unique[key] = {
                    "text": chunk["spoken"],
                    "lesson_id": lesson["lesson_id"],
                    "chunk_id": chunk["id"],
                }
        path.write_text(
            json.dumps(lesson, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return backend, lessons, unique


async def _synthesize_unique(
    backend: EdgeBackend,
    state: StateStore,
    unique: dict[str, dict[str, Any]],
    force: bool,
) -> list[tuple[str, str | None, bool, str | None]]:
    total = len(unique)
    progress = tqdm(total=total, desc=f"sintetizando {backend.voice}", unit="chunk")
    results: list[tuple[str, str | None, bool, str | None]] = []

    async def worker(key: str, item: dict[str, Any]) -> None:
        state.mark_running(key, item["lesson_id"], item["chunk_id"])
        try:
            result = await backend.synthesize(item["text"], force=force)
            state.mark_done(
                key,
                item["lesson_id"],
                item["chunk_id"],
                result.path,
                result.duration,
                result.attempts,
            )
            results.append((key, str(result.path), result.cached, None))
        except Exception as exc:  # noqa: BLE001 - reportamos e continuamos
            state.mark_failed(key, item["lesson_id"], item["chunk_id"], str(exc), 0)
            results.append((key, None, False, f"{type(exc).__name__}: {exc}"))
        finally:
            progress.update(1)
            progress.set_postfix(
                ok=sum(1 for item in results if item[3] is None),
                fail=sum(1 for item in results if item[3] is not None),
            )

    try:
        await asyncio.gather(*(worker(key, item) for key, item in unique.items()))
    finally:
        progress.close()
    return results


def run_build(options: BuildOptions) -> int:
    _, projects = load_projects()
    selected = resolve_projects(projects, options.project)
    for project in selected:
        backend, lessons, unique = _prepare_project(project, options)
        total_chunks = sum(len(lesson["chunks"]) for _, lesson in lessons)
        estimated = sum(
            len(chunk["spoken"]) / 15.5 + chunk.get("gap_before_ms", 0) / 1000.0
            for _, lesson in lessons
            for chunk in lesson["chunks"]
        )
        hits = sum(1 for text in (item["text"] for item in unique.values()) if backend.cached_duration(text) is not None)
        print(
            f"[build] {project.key}: {len(lessons)} aula(s), {total_chunks} chunks, "
            f"{len(unique)} textos únicos, {hits} em cache, ~{estimated / 3600:.2f} h"
        )
        if options.dry_run:
            print("  dry-run: nada foi sintetizado.")
            continue

        state_path = project.cache_dir / "state.db"
        with StateStore(state_path) as state:
            results = asyncio.run(_synthesize_unique(backend, state, unique, options.force))
            counts = state.counts()
        failures = [result for result in results if result[3] is not None]
        cached = sum(1 for result in results if result[2])
        generated = len(results) - cached - len(failures)
        print(
            f"  cache={cached} gerados={generated} falhas={len(failures)} "
            f"status={counts}"
        )
        if failures:
            print("  Falhas (primeiras 10):")
            for key, _, _, error in failures[:10]:
                print(f"    {key[:12]}… {error}")
            print("  Rode novamente com `--resume` (padrão) para tentar só o que faltou.")
            return 1
        if not options.no_assemble:
            print("  Montagem (MP3/M4B/SRT) entra na T06; chunks prontos.")
    return 0


def run_status(selector: str) -> int:
    _, projects = load_projects()
    for project in resolve_projects(projects, selector):
        voice = str(project.settings.get("voice", "pt-BR-FranciscaNeural"))
        rate = str(project.settings.get("rate", "-5%"))
        backend = EdgeBackend(voice=voice, rate=rate, cache_root=ROOT / "cache" / "edge", concurrency=1)
        state_path = project.cache_dir / "state.db"
        state_counts: dict[str, int] = {}
        if state_path.exists():
            with StateStore(state_path) as state:
                state_counts = state.counts()
        print(f"[status] {project.key} ({voice}, {rate}) estado={state_counts or 'sem state.db'}")
        for _path, lesson in _load_lessons(project, None):
            chunks = lesson["chunks"]
            unique_texts = {chunk["spoken"] for chunk in chunks}
            cached = sum(1 for text in unique_texts if backend.cached_duration(text) is not None)
            estimated = sum(
                len(chunk["spoken"]) / 15.5 + chunk.get("gap_before_ms", 0) / 1000.0
                for chunk in chunks
            )
            print(
                f"  {lesson['lesson_id']}: {len(chunks)} chunks, {len(unique_texts)} únicos, "
                f"{cached} em cache, {len(unique_texts) - cached} faltando, "
                f"~{int(estimated // 3600):02d}:{int((estimated % 3600) // 60):02d}"
            )
    return 0


def run_samples() -> int:
    samples_dir = ROOT / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    voices = [
        ("francisca", "pt-BR-FranciscaNeural"),
        ("antonio", "pt-BR-AntonioNeural"),
        ("thalita", "pt-BR-ThalitaMultilingualNeural"),
    ]
    for label, voice in voices:
        backend = EdgeBackend(
            voice=voice,
            rate="-5%",
            cache_root=ROOT / "cache" / "samples",
            concurrency=1,
            retries=3,
        )
        result = asyncio.run(backend.synthesize(SAMPLE_TEXT, force=True))
        target = samples_dir / f"{label}.mp3"
        shutil.copy2(result.path, target)
        valid, duration, reason = validate_audio(target)
        print(f"  {label}: {duration:.1f}s ({'ok' if valid else reason}) -> {target.name}")

    backend = EdgeBackend(
        voice="pt-BR-FranciscaNeural",
        rate="-5%",
        cache_root=ROOT / "cache" / "samples",
        concurrency=1,
        retries=3,
    )
    result = asyncio.run(backend.synthesize(PRONUNCIATION_TEXT, force=True))
    target = samples_dir / "pronunciation-test.mp3"
    shutil.copy2(result.path, target)
    valid, duration, reason = validate_audio(target)
    print(f"  pronunciation-test: {duration:.1f}s ({'ok' if valid else reason}) -> {target.name}")
    return 0
