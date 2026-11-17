"""Verificação técnica dos arquivos finais."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pdf_tts.assemble import measure_loudness
from pdf_tts.audio import ffmpeg_path, ffprobe_duration, ffprobe_path, validate_audio
from pdf_tts.config import ROOT, ProjectConfig, load_projects, resolve_projects


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    text = path.read_text(encoding="utf-8").strip()
    cues: list[tuple[float, float, str]] = []
    for block in re.split(r"\n\s*\n", text):
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        match = re.match(
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
            lines[1].strip(),
        )
        if not match:
            continue
        values = [int(value) for value in match.groups()]
        start = values[0] * 3600 + values[1] * 60 + values[2] + values[3] / 1000
        end = values[4] * 3600 + values[5] * 60 + values[6] + values[7] / 1000
        cues.append((start, end, "\n".join(lines[2:])))
    return cues


def ffprobe_chapters(path: Path) -> list[dict]:
    result = subprocess.run(
        [ffprobe_path(), "-v", "error", "-show_chapters", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return []
    return json.loads(result.stdout or "{}").get("chapters", [])


def ffprobe_streams(path: Path) -> list[dict]:
    result = subprocess.run(
        [ffprobe_path(), "-v", "error", "-show_streams", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return []
    return json.loads(result.stdout or "{}").get("streams", [])


def silence_gaps(path: Path, threshold_db: int = -35, min_seconds: float = 5.0) -> list[float]:
    result = subprocess.run(
        [
            ffmpeg_path(),
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            f"silencedetect=noise={threshold_db}dB:d={min_seconds}",
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
    gaps: list[float] = []
    for match in re.finditer(r"silence_duration:\s*([\d.]+)", result.stderr or ""):
        gaps.append(float(match.group(1)))
    return gaps


def _check_audio_file(path: Path, label: str) -> list[CheckResult]:
    if not path.exists():
        return [CheckResult(label, False, "arquivo não existe")]
    valid, duration, reason = validate_audio(path)
    return [CheckResult(label, valid, f"{duration:.1f}s ({reason})" if valid else reason)]


def verify_lesson(
    project: ProjectConfig,
    lesson_id: str,
    check_loudness: bool = True,
    check_silence: bool = True,
) -> list[CheckResult]:
    output = ROOT / "output" / project.slug
    mp3 = output / f"{lesson_id}.mp3"
    m4b = output / f"{lesson_id}.m4b"
    srt = output / f"{lesson_id}.srt"
    checks: list[CheckResult] = []
    checks.extend(_check_audio_file(mp3, f"{lesson_id} MP3"))
    checks.extend(_check_audio_file(m4b, f"{lesson_id} M4B"))
    if not mp3.exists():
        return checks

    duration = ffprobe_duration(mp3)

    if srt.exists():
        cues = parse_srt(srt)
        last = cues[-1][1] if cues else 0.0
        checks.append(
            CheckResult(
                f"{lesson_id} SRT",
                bool(cues) and last <= duration + 1.0,
                f"{len(cues)} cues; última em {last:.1f}s / áudio {duration:.1f}s",
            )
        )
    else:
        checks.append(CheckResult(f"{lesson_id} SRT", False, "arquivo não existe"))

    chapters = ffprobe_chapters(m4b) if m4b.exists() else []
    if chapters:
        first_start = float(chapters[0]["start_time"])
        last_end = float(chapters[-1]["end_time"])
        monotonic = all(
            float(chapters[index]["start_time"]) <= float(chapters[index + 1]["start_time"])
            for index in range(len(chapters) - 1)
        )
        checks.append(
            CheckResult(
                f"{lesson_id} capítulos",
                first_start <= 0.1 and last_end <= duration + 1.0 and monotonic,
                f"{len(chapters)} capítulos; {first_start:.1f}s–{last_end:.1f}s",
            )
        )
    else:
        checks.append(CheckResult(f"{lesson_id} capítulos", False, "nenhum capítulo"))

    streams = ffprobe_streams(m4b) if m4b.exists() else []
    has_cover = any(
        stream.get("codec_type") == "video"
        and stream.get("disposition", {}).get("attached_pic") in (1, True)
        for stream in streams
    )
    checks.append(CheckResult(f"{lesson_id} capa", has_cover, "attached_pic" if has_cover else "sem capa"))

    if check_loudness:
        measured = measure_loudness(mp3, -16.0, -1.5, 11.0)
        if measured:
            loudness = float(measured.get("input_i", 0))
            true_peak = float(measured.get("input_tp", 0))
            ok = -17.5 <= loudness <= -14.5 and true_peak <= -0.5
            checks.append(
                CheckResult(f"{lesson_id} loudness", ok, f"{loudness:.2f} LUFS; TP {true_peak:.2f} dB")
            )
        else:
            checks.append(CheckResult(f"{lesson_id} loudness", False, "medição falhou"))

    if check_silence:
        gaps = silence_gaps(mp3)
        checks.append(
            CheckResult(
                f"{lesson_id} silêncios >5s",
                not gaps,
                "nenhum" if not gaps else ", ".join(f"{gap:.1f}s" for gap in gaps),
            )
        )
    return checks


def verify_full_book(project: ProjectConfig, check_loudness: bool = True) -> list[CheckResult]:
    output = ROOT / "output" / project.slug
    mp3 = output / f"{project.slug}-completo.mp3"
    m4b = output / f"{project.slug}-completo.m4b"
    checks: list[CheckResult] = []
    if not mp3.exists() or not m4b.exists():
        return checks
    checks.extend(_check_audio_file(mp3, "livro MP3"))
    checks.extend(_check_audio_file(m4b, "livro M4B"))
    duration = ffprobe_duration(mp3)
    chapters = ffprobe_chapters(m4b)
    checks.append(
        CheckResult(
            "livro capítulos",
            bool(chapters) and float(chapters[-1]["end_time"]) <= duration + 1.0,
            f"{len(chapters)} capítulos; fim {float(chapters[-1]['end_time']):.1f}s" if chapters else "nenhum",
        )
    )
    if check_loudness:
        measured = measure_loudness(mp3, -16.0, -1.5, 11.0)
        if measured:
            loudness = float(measured.get("input_i", 0))
            true_peak = float(measured.get("input_tp", 0))
            checks.append(
                CheckResult(
                    "livro loudness",
                    -17.5 <= loudness <= -14.5 and true_peak <= -0.5,
                    f"{loudness:.2f} LUFS; TP {true_peak:.2f} dB",
                )
            )
    return checks


def run_verify(
    selector: str,
    lesson: str | None = None,
    check_loudness: bool = True,
    check_silence: bool = True,
) -> int:
    _, projects = load_projects()
    failures = 0
    for project in resolve_projects(projects, selector):
        output = ROOT / "output" / project.slug
        if not output.exists():
            print(f"[verify] {project.key}: output/ ausente")
            failures += 1
            continue
        if lesson:
            text = lesson.strip().upper()
            lesson_ids = [f"S{int(text[1:] if text.startswith('S') else text):02d}"]
        else:
            lesson_ids = [f"S{index:02d}" for index in range(1, 8)]
        checks: list[CheckResult] = []
        for lesson_id in lesson_ids:
            checks.extend(
                verify_lesson(project, lesson_id, check_loudness=check_loudness, check_silence=check_silence)
            )
        if not lesson:
            checks.extend(verify_full_book(project, check_loudness=check_loudness))
        print(f"[verify] {project.key}")
        for check in checks:
            mark = "OK  " if check.ok else "FAIL"
            print(f"  [{mark}] {check.name}: {check.detail}")
            if not check.ok:
                failures += 1
    return 1 if failures else 0
