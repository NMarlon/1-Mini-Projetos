"""Montagem de MP3, M4B, SRT, capítulos e manifest."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import textwrap
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pdf_tts.audio import ffmpeg_path, validate_audio
from pdf_tts.config import ROOT, ProjectConfig, load_projects, load_settings, resolve_projects
from pdf_tts.tts.edge import EdgeBackend

logger = logging.getLogger("pdf_tts.assemble")
SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2


@dataclass
class TimelineEntry:
    chunk_id: str
    section_id: str
    section_title: str
    kind: str
    text: str
    mp3: Path
    wav: Path
    gap_ms: int
    duration: float
    start: float
    end: float


@dataclass
class LessonAudio:
    lesson_id: str
    title: str
    start_page: int
    end_page: int
    timeline: list[TimelineEntry]
    chapters: list[dict[str, Any]]
    duration: float
    mp3: Path
    m4b: Path
    srt: Path
    wav_norm: Path
    mp3_sha256: str
    m4b_sha256: str
    srt_sha256: str


def _load_lessons(project: ProjectConfig, lesson: str | None) -> list[tuple[Path, dict[str, Any]]]:
    lessons_dir = project.content_dir / "lessons"
    if lesson:
        text = lesson.strip().upper()
        target = f"S{int(text[1:] if text.startswith('S') else text):02d}"
        paths = [lessons_dir / f"{target}.json"]
    else:
        paths = sorted(lessons_dir.glob("S*.json"))
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Aula não encontrada: {path} (rode segment/build).")
        loaded.append((path, json.loads(path.read_text(encoding="utf-8"))))
    if not loaded:
        raise FileNotFoundError(f"Nenhuma aula em {lessons_dir}.")
    return loaded


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wav_info(path: Path) -> tuple[int, int, int, int]:
    with wave.open(str(path), "rb") as handle:
        return (
            handle.getnframes(),
            handle.getframerate(),
            handle.getnchannels(),
            handle.getsampwidth(),
        )


def _wav_duration(path: Path) -> float:
    frames, rate, _, _ = _wav_info(path)
    return frames / rate


def _ensure_wav(mp3: Path, wav: Path) -> Path:
    if wav.exists():
        try:
            frames, rate, channels, width = _wav_info(wav)
            if frames > 0 and rate == SAMPLE_RATE and channels == CHANNELS and width == SAMPLE_WIDTH:
                return wav
        except wave.Error:
            pass
    wav.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            ffmpeg_path(),
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(mp3),
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            str(CHANNELS),
            "-c:a",
            "pcm_s16le",
            str(wav),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"falha ao decodificar {mp3}: {result.stderr.strip()}")
    return wav


def _prepare_wavs(entries: list[TimelineEntry], wav_dir: Path) -> None:
    unique = {entry.mp3 for entry in entries}
    wav_dir.mkdir(parents=True, exist_ok=True)

    def convert(mp3: Path) -> None:
        _ensure_wav(mp3, wav_dir / f"{mp3.stem}.wav")

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(convert, unique))


def build_timeline(
    project: ProjectConfig,
    lesson: dict[str, Any],
    backend: EdgeBackend,
    wav_dir: Path,
) -> tuple[list[TimelineEntry], list[dict[str, Any]], float]:
    sections = {str(section["id"]): str(section["title"]) for section in lesson.get("sections", [])}
    entries: list[TimelineEntry] = []
    current_section = ""
    current_chapter_start = 0.0
    chapters: list[dict[str, Any]] = []
    clock = 0.0

    for chunk in lesson["chunks"]:
        key = chunk.get("cache_key") or backend.cache_key(chunk["spoken"])
        mp3 = backend.cache_path(key)
        if not mp3.exists():
            raise FileNotFoundError(
                f"Chunk sem áudio: {chunk['id']} ({mp3}). Rode `build --project {project.key} --lesson {lesson['lesson_id']}`."
            )
        wav = wav_dir / f"{mp3.stem}.wav"
        _ensure_wav(mp3, wav)
        duration = _wav_duration(wav)
        section_id = str(chunk["section_id"])
        if section_id != current_section:
            if current_section:
                chapters.append(
                    {
                        "title": sections.get(current_section, current_section),
                        "start": round(current_chapter_start, 3),
                        "end": round(clock, 3),
                    }
                )
            current_section = section_id
            current_chapter_start = clock
        gap = int(chunk.get("gap_before_ms", 0))
        clock += gap / 1000.0
        start = clock
        end = start + duration
        entries.append(
            TimelineEntry(
                chunk_id=str(chunk["id"]),
                section_id=section_id,
                section_title=sections.get(section_id, section_id),
                kind=str(chunk["kind"]),
                text=str(chunk["text"]),
                mp3=mp3,
                wav=wav,
                gap_ms=gap,
                duration=duration,
                start=start,
                end=end,
            )
        )
        clock = end

    if current_section:
        chapters.append(
            {
                "title": sections.get(current_section, current_section),
                "start": round(current_chapter_start, 3),
                "end": round(clock, 3),
            }
        )
    return entries, chapters, clock


def _silence_bytes(seconds: float) -> bytes:
    frames = max(0, int(round(seconds * SAMPLE_RATE)))
    return b"\x00\x00" * frames


def concat_timeline(entries: list[TimelineEntry], output_wav: Path) -> None:
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_wav), "wb") as out:
        out.setnchannels(CHANNELS)
        out.setsampwidth(SAMPLE_WIDTH)
        out.setframerate(SAMPLE_RATE)
        for entry in entries:
            if entry.gap_ms:
                out.writeframes(_silence_bytes(entry.gap_ms / 1000.0))
            with wave.open(str(entry.wav), "rb") as source:
                out.writeframes(source.readframes(source.getnframes()))


def concat_wavs(wavs: list[Path], output_wav: Path, gap_seconds: float = 2.0) -> None:
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_wav), "wb") as out:
        out.setnchannels(CHANNELS)
        out.setsampwidth(SAMPLE_WIDTH)
        out.setframerate(SAMPLE_RATE)
        for index, wav in enumerate(wavs):
            if index and gap_seconds:
                out.writeframes(_silence_bytes(gap_seconds))
            with wave.open(str(wav), "rb") as source:
                out.writeframes(source.readframes(source.getnframes()))


def measure_loudness(wav: Path, target_i: float, target_tp: float, target_lra: float) -> dict[str, str] | None:
    result = subprocess.run(
        [
            ffmpeg_path(),
            "-hide_banner",
            "-i",
            str(wav),
            "-af",
            f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        logger.warning("loudnorm medição falhou: %s", result.stderr.strip()[-500:])
        return None
    matches = re.findall(r"\{[\s\S]*?\}", result.stderr)
    for match in reversed(matches):
        try:
            data = json.loads(match)
        except json.JSONDecodeError:
            continue
        if "input_i" in data:
            return {key: str(value) for key, value in data.items()}
    return None


def apply_loudnorm(
    input_wav: Path,
    output_wav: Path,
    target_i: float,
    target_tp: float,
    target_lra: float,
) -> None:
    measured = measure_loudness(input_wav, target_i, target_tp, target_lra)
    if measured:
        audio_filter = (
            f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}"
            f":measured_I={measured.get('input_i')}"
            f":measured_TP={measured.get('input_tp')}"
            f":measured_LRA={measured.get('input_lra')}"
            f":measured_thresh={measured.get('input_thresh')}"
            f":offset={measured.get('target_offset')}:linear=true"
        )
    else:
        audio_filter = f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}"
    result = subprocess.run(
        [
            ffmpeg_path(),
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(input_wav),
            "-af",
            audio_filter,
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            str(CHANNELS),
            "-c:a",
            "pcm_s16le",
            str(output_wav),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"loudnorm falhou: {result.stderr.strip()}")


def _escape_ffmetadata(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("=", "\\=")
        .replace(";", "\\;")
        .replace("#", "\\#")
        .replace("\n", " ")
    )


def write_chapters(
    path: Path,
    chapters: list[dict[str, Any]],
    total_duration: float,
    metadata: dict[str, str],
) -> None:
    lines = [";FFMETADATA1"]
    for key, value in metadata.items():
        lines.append(f"{key}={_escape_ffmetadata(value)}")
    ordered = sorted(chapters, key=lambda item: float(item["start"]))
    for _index, chapter in enumerate(ordered):
        start = max(0, int(round(float(chapter["start"]) * 1000)))
        end = int(round(float(chapter["end"]) * 1000)) if chapter.get("end") is not None else int(total_duration * 1000)
        end = min(int(total_duration * 1000), max(start + 1, end))
        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={start}")
        lines.append(f"END={end}")
        lines.append(f"title={_escape_ffmetadata(str(chapter['title']))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _fmt_srt_time(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(path: Path, entries: list[TimelineEntry], offset: float = 0.0) -> None:
    cues = []
    for entry in entries:
        text = textwrap.fill(entry.text.strip(), width=80)
        if text:
            cues.append((entry.start + offset, entry.end + offset, text))
    lines: list[str] = []
    previous_end = -1.0
    for index, (start, end, text) in enumerate(cues, start=1):
        start = max(start, previous_end + 0.001)
        if end <= start:
            end = start + 0.1
        lines.append(str(index))
        lines.append(f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}")
        lines.append(text)
        lines.append("")
        previous_end = end
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def render_cover(project: ProjectConfig, output: Path) -> Path | None:
    try:
        import pypdfium2 as pdfium

        document = pdfium.PdfDocument(str(project.pdf))
        page = document[0]
        bitmap = page.render(scale=2)
        image = bitmap.to_pil()
        if image.height > 1400:
            ratio = 1400 / image.height
            image = image.resize((int(image.width * ratio), 1400))
        output.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(output, format="JPEG", quality=90)
        document.close()
        return output
    except Exception as exc:  # noqa: BLE001 - capa é opcional
        logger.warning("não foi possível renderizar a capa: %s", exc)
        return None


def encode_mp3(
    wav: Path,
    output: Path,
    metadata: dict[str, str],
) -> None:
    command = [
        ffmpeg_path(),
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(wav),
        "-c:a",
        "libmp3lame",
        "-b:a",
        "64k",
        "-ar",
        str(SAMPLE_RATE),
        "-ac",
        str(CHANNELS),
        "-id3v2_version",
        "3",
    ]
    for key, value in metadata.items():
        command += ["-metadata", f"{key}={value}"]
    command.append(str(output))
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if result.returncode != 0:
        raise RuntimeError(f"encode MP3 falhou: {result.stderr.strip()}")


def encode_m4b(
    wav: Path,
    output: Path,
    chapters_file: Path,
    cover: Path | None,
) -> None:
    command = [ffmpeg_path(), "-y", "-loglevel", "error", "-i", str(wav)]
    chapter_index = 1
    if cover and cover.exists():
        command += ["-i", str(cover)]
        chapter_index = 2
    command += ["-i", str(chapters_file)]
    command += ["-map", "0:a"]
    if cover and cover.exists():
        command += ["-map", "1:v", "-c:v", "mjpeg", "-disposition:v", "attached_pic"]
    command += [
        "-map_metadata",
        str(chapter_index),
        "-map_chapters",
        str(chapter_index),
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-ar",
        str(SAMPLE_RATE),
        "-ac",
        str(CHANNELS),
        "-movflags",
        "+faststart",
        "-f",
        "ipod",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if result.returncode != 0:
        raise RuntimeError(f"encode M4B falhou: {result.stderr.strip()}")


def _metadata(project: ProjectConfig, lesson: dict[str, Any], track: str | None = None) -> dict[str, str]:
    metadata = {
        "title": f"{lesson['lesson_id']} — {lesson['title']}",
        "artist": "PDF TTS (voz sintética)",
        "album": project.title,
        "album_artist": "PDF TTS",
        "genre": "Audiobook",
        "comment": f"Narrado por {lesson.get('voice', 'Edge TTS')}; gerado por PDF TTS.",
    }
    if track:
        metadata["track"] = track
    return metadata


def assemble_lesson(
    project: ProjectConfig,
    lesson: dict[str, Any],
    output_dir: Path,
    work_dir: Path,
    wav_cache: Path,
    audio_settings: dict[str, Any],
    cover: Path | None,
    track: str | None = None,
) -> LessonAudio:
    voice = str(lesson.get("voice") or project.settings.get("voice", "pt-BR-FranciscaNeural"))
    rate = str(lesson.get("rate") or project.settings.get("rate", "-5%"))
    backend = EdgeBackend(voice=voice, rate=rate, cache_root=ROOT / "cache" / "edge", concurrency=1)
    lesson_id = str(lesson["lesson_id"])
    entries, chapters, duration = build_timeline(project, lesson, backend, wav_cache)

    raw_wav = work_dir / f"{lesson_id}.wav"
    norm_wav = work_dir / f"{lesson_id}_norm.wav"
    concat_timeline(entries, raw_wav)
    apply_loudnorm(
        raw_wav,
        norm_wav,
        float(audio_settings.get("loudness_i", -16.0)),
        float(audio_settings.get("loudness_tp", -1.5)),
        float(audio_settings.get("loudness_lra", 11.0)),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    mp3 = output_dir / f"{lesson_id}.mp3"
    m4b = output_dir / f"{lesson_id}.m4b"
    srt = output_dir / f"{lesson_id}.srt"
    chapters_file = work_dir / f"{lesson_id}_chapters.txt"

    metadata = _metadata(project, lesson, track)
    write_chapters(chapters_file, chapters, duration, metadata)
    encode_mp3(norm_wav, mp3, metadata)
    encode_m4b(norm_wav, m4b, chapters_file, cover)
    write_srt(srt, entries)

    for path in (mp3, m4b):
        valid, _, reason = validate_audio(path)
        if not valid:
            raise RuntimeError(f"arquivo final inválido ({reason}): {path}")

    return LessonAudio(
        lesson_id=lesson_id,
        title=str(lesson["title"]),
        start_page=int(lesson["start_page"]),
        end_page=int(lesson["end_page"]),
        timeline=entries,
        chapters=chapters,
        duration=duration,
        mp3=mp3,
        m4b=m4b,
        srt=srt,
        wav_norm=norm_wav,
        mp3_sha256=_sha256(mp3),
        m4b_sha256=_sha256(m4b),
        srt_sha256=_sha256(srt),
    )


def _write_manifest(
    project: ProjectConfig,
    lessons: list[LessonAudio],
    total_duration: float,
    full_files: dict[str, Path] | None,
) -> Path:
    manifest = {
        "project": project.key,
        "title": project.title,
        "slug": project.slug,
        "source_pdf": project.pdf.relative_to(ROOT).as_posix(),
        "source_sha256": _sha256(project.pdf),
        "engine": "edge",
        "voice": str(project.settings.get("voice", "pt-BR-FranciscaNeural")),
        "rate": str(project.settings.get("rate", "-5%")),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "total_duration_s": round(total_duration, 2),
        "lessons": [
            {
                "id": lesson.lesson_id,
                "title": lesson.title,
                "start_page": lesson.start_page,
                "end_page": lesson.end_page,
                "duration_s": round(lesson.duration, 2),
                "chunks": len(lesson.timeline),
                "files": {
                    "mp3": lesson.mp3.relative_to(ROOT).as_posix(),
                    "m4b": lesson.m4b.relative_to(ROOT).as_posix(),
                    "srt": lesson.srt.relative_to(ROOT).as_posix(),
                    "sha256_mp3": lesson.mp3_sha256,
                    "sha256_m4b": lesson.m4b_sha256,
                    "sha256_srt": lesson.srt_sha256,
                },
                "chapters": lesson.chapters,
            }
            for lesson in lessons
        ],
    }
    if full_files:
        manifest["full"] = {
            name: {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(path),
                "size": path.stat().st_size,
            }
            for name, path in full_files.items()
        }
    project.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    project.manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    output_manifest = (ROOT / "output" / project.slug / "manifest.json")
    output_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return project.manifest_path


def _format_hms(seconds: float) -> str:
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _write_output_readme(project: ProjectConfig, lessons: list[LessonAudio], total_duration: float) -> None:
    lines = [
        f"# {project.title}",
        "",
        f"Narração sintética em pt-BR — {project.settings.get('voice', 'pt-BR-FranciscaNeural')} "
        f"({project.settings.get('rate', '-5%')}).",
        "",
        f"Duração total: {_format_hms(total_duration)}",
        "",
        "| Aula | Título | Duração | Arquivos |",
        "|---|---|---|---|",
    ]
    for lesson in lessons:
        duration = f"{int(lesson.duration // 60):02d}:{int(lesson.duration % 60):02d}"
        lines.append(
            f"| {lesson.lesson_id} | {lesson.title} | {duration} | "
            f"`{lesson.mp3.name}`, `{lesson.m4b.name}`, `{lesson.srt.name}` |"
        )
    lines += [
        "",
        "## Como ouvir",
        "",
        "- **MP3**: qualquer player; uma aula por arquivo.",
        "- **M4B**: players de audiolivro (Apple Books, VLC, Android); capítulos por seção.",
        "- **SRT**: legendas para VLC/players compatíveis.",
        "",
        "> Áudio gerado localmente. Não redistribua o conteúdo do curso.",
        "",
    ]
    (ROOT / "output" / project.slug / "README.md").write_text(
        "\n".join(lines), encoding="utf-8", newline="\n"
    )


def _assemble_full_book(
    project: ProjectConfig,
    lessons: list[LessonAudio],
    output_dir: Path,
    work_dir: Path,
    cover: Path | None,
) -> tuple[float, dict[str, Path]]:
    full_wav = work_dir / f"{project.slug}-completo.wav"
    concat_wavs([lesson.wav_norm for lesson in lessons], full_wav, gap_seconds=2.0)
    total_duration = _wav_duration(full_wav)

    chapters: list[dict[str, Any]] = []
    timeline: list[TimelineEntry] = []
    offset = 0.0
    for index, lesson in enumerate(lessons):
        if index:
            offset += 2.0
        for chapter in lesson.chapters:
            chapters.append(
                {
                    "title": f"{lesson.lesson_id} — {chapter['title']}",
                    "start": float(chapter["start"]) + offset,
                    "end": float(chapter["end"]) + offset,
                }
            )
        timeline.extend(lesson.timeline)
        offset += lesson.duration

    metadata = {
        "title": project.title,
        "artist": "PDF TTS (voz sintética)",
        "album": project.title,
        "album_artist": "PDF TTS",
        "genre": "Audiobook",
        "comment": f"Narrado por {project.settings.get('voice', 'Edge TTS')}; gerado por PDF TTS.",
    }
    chapters_file = work_dir / f"{project.slug}-completo_chapters.txt"
    write_chapters(chapters_file, chapters, total_duration, metadata)

    full_mp3 = output_dir / f"{project.slug}-completo.mp3"
    full_m4b = output_dir / f"{project.slug}-completo.m4b"
    full_srt = output_dir / f"{project.slug}-completo.srt"
    encode_mp3(full_wav, full_mp3, metadata)
    encode_m4b(full_wav, full_m4b, chapters_file, cover)

    # SRT completo: reconstrói a partir das timelines com offsets.
    offset = 0.0
    combined: list[TimelineEntry] = []
    for index, lesson in enumerate(lessons):
        if index:
            offset += 2.0
        for entry in lesson.timeline:
            combined.append(
                TimelineEntry(
                    chunk_id=entry.chunk_id,
                    section_id=entry.section_id,
                    section_title=entry.section_title,
                    kind=entry.kind,
                    text=entry.text,
                    mp3=entry.mp3,
                    wav=entry.wav,
                    gap_ms=entry.gap_ms,
                    duration=entry.duration,
                    start=entry.start + offset,
                    end=entry.end + offset,
                )
            )
        offset += lesson.duration
    write_srt(full_srt, combined)

    for path in (full_mp3, full_m4b):
        valid, _, reason = validate_audio(path)
        if not valid:
            raise RuntimeError(f"arquivo final inválido ({reason}): {path}")
    return total_duration, {"mp3": full_mp3, "m4b": full_m4b, "srt": full_srt}


def run_assemble(selector: str, lesson: str | None = None) -> int:
    _, projects = load_projects()
    settings = load_settings()
    audio_settings = settings.get("audio", {})
    for project in resolve_projects(projects, selector):
        output_dir = ROOT / "output" / project.slug
        work_dir = project.cache_dir / "work"
        wav_cache = project.cache_dir / "wav"
        work_dir.mkdir(parents=True, exist_ok=True)
        cover = render_cover(project, output_dir / "cover.jpg")
        loaded = _load_lessons(project, lesson)
        results: list[LessonAudio] = []
        for index, (_, data) in enumerate(loaded, start=1):
            print(f"[assemble] {project.key} {data['lesson_id']}…")
            track = f"{index}/{len(loaded)}" if not lesson else None
            result = assemble_lesson(
                project,
                data,
                output_dir,
                work_dir,
                wav_cache,
                audio_settings,
                cover,
                track=track,
            )
            print(
                f"  {result.lesson_id}: {result.duration / 60:.1f} min, "
                f"{result.mp3.name}, {result.m4b.name}, {result.srt.name}"
            )
            results.append(result)

        full_files = None
        total_duration = sum(result.duration for result in results)
        if not lesson:
            print("[assemble] livro completo…")
            total_duration, full_files = _assemble_full_book(project, results, output_dir, work_dir, cover)
        manifest = _write_manifest(project, results, total_duration, full_files)
        _write_output_readme(project, results, total_duration)
        print(f"  manifesto: {manifest.relative_to(ROOT)}")
    return 0
