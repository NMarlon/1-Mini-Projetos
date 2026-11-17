"""Construção das aulas faláveis (chunks por seção)."""

from __future__ import annotations

import json
import re
from typing import Any

from pdf_tts.chunking import GAP_BY_KIND, chunk_block
from pdf_tts.config import (
    ProjectConfig,
    load_lexicon,
    load_projects,
    load_settings,
    resolve_projects,
)
from pdf_tts.models import Block, Chunk, Week
from pdf_tts.normalize import normalize_text
from pdf_tts.segment import segment_project, write_project_outputs

CHARS_PER_SECOND_ESTIMATE = 15.5

PUBLISHER_RE = re.compile(
    r"^(Allyn|Bacon|McGraw|Hill|Pearson|SAGE|Routledge|Oxford|Cambridge|Erlbaum)\b",
    re.IGNORECASE,
)
FUNCTION_WORDS = {
    "a",
    "o",
    "as",
    "os",
    "de",
    "do",
    "da",
    "dos",
    "das",
    "que",
    "é",
    "uma",
    "um",
    "por",
    "em",
    "com",
    "para",
    "vai",
    "essa",
    "esse",
    "esta",
    "este",
    "seu",
    "sua",
    "no",
    "na",
    "e",
    "ou",
    "como",
    "quando",
    "onde",
    "porque",
    "mas",
    "se",
    "ao",
    "à",
}


def _clean_section_chunks(chunks: list[Chunk]) -> list[Chunk]:
    """Remove fragmentos inúteis e junta frases curtas quebradas pelo layout."""
    filtered: list[Chunk] = []
    for chunk in chunks:
        if chunk.kind in {"paragraph", "table", "caption"} and re.fullmatch(
            r"\d{1,3}[.)]?", chunk.text.strip()
        ):
            continue
        if chunk.kind == "paragraph" and len(chunk.text) < 60 and PUBLISHER_RE.match(chunk.text.strip()):
            continue
        filtered.append(chunk)

    merged: list[Chunk] = []
    index = 0
    while index < len(filtered):
        chunk = filtered[index]
        if (
            chunk.kind in {"paragraph", "table", "caption"}
            and len(chunk.spoken) < 30
            and index + 1 < len(filtered)
            and filtered[index + 1].kind in {"paragraph", "table", "caption"}
        ):
            following = filtered[index + 1].spoken.lstrip()
            prefix = chunk.spoken.rstrip()
            words = re.sub(r"[^\wÀ-ÿ]+$", "", prefix).split()
            last_word = words[-1].lower() if words else ""
            remove_period = (
                prefix.endswith(".")
                and not prefix.endswith("...")
                and (
                    last_word in FUNCTION_WORDS
                    or (len(words) <= 3 and following[:1].islower())
                )
            )
            if remove_period:
                prefix = prefix[:-1]
                if last_word in FUNCTION_WORDS and following[:1].isupper():
                    following = following[0].lower() + following[1:]
            chunk.spoken = f"{prefix} {following}".strip()
            chunk.text = f"{chunk.text.rstrip()} {filtered[index + 1].text.lstrip()}"
            merged.append(chunk)
            index += 2
            continue
        merged.append(chunk)
        index += 1
    return merged


def build_lesson(
    project: ProjectConfig,
    week: Week,
    settings: dict[str, Any],
    lexicon: dict[str, Any],
) -> dict[str, Any]:
    chunk_settings = settings.get("chunking", {})
    min_chars = int(chunk_settings.get("min_chars", 80))
    max_chars = int(chunk_settings.get("max_chars", 1200))

    chunks: list[Chunk] = []
    sections_out: list[dict[str, Any]] = []

    for section in week.sections:
        title_spoken = normalize_text(section.title, lexicon, kind="section_heading")
        title_gap = 1800 if section.type == "week" else 1200
        chunks.append(
            Chunk(
                id="",
                lesson_id=week.id,
                section_id=section.id,
                block_id=f"{section.id}-title",
                kind="section_heading",
                text=section.title,
                spoken=title_spoken,
                gap_before_ms=title_gap,
            )
        )
        section_chunks: list[Chunk] = []
        for block in section.blocks:
            if block.kind == "section_heading":
                continue
            gap = GAP_BY_KIND.get(block.kind, 350)
            block_chunks = chunk_block(
                block,
                lexicon,
                min_chars=min_chars,
                max_chars=max_chars,
                first_gap_ms=gap,
            )
            section_chunks.extend(block_chunks)

        # O título da seção é o primeiro chunk; não deve ser fundido com o corpo.
        body_chunks = _clean_section_chunks(section_chunks)
        chunks.extend(body_chunks)

        sections_out.append(
            {
                "id": section.id,
                "title": section.title,
                "type": section.type,
                "start_page": section.start_page,
                "end_page": section.end_page,
                "chunks": 1 + len(body_chunks),
            }
        )

    for index, chunk in enumerate(chunks, start=1):
        chunk.id = f"{week.id}-c{index:04d}"
        chunk.lesson_id = week.id

    total_chars = sum(len(chunk.spoken) for chunk in chunks)
    estimated_duration = sum(
        len(chunk.spoken) / CHARS_PER_SECOND_ESTIMATE + chunk.gap_before_ms / 1000.0 for chunk in chunks
    )
    return {
        "project": project.key,
        "lesson_id": week.id,
        "week": week.week,
        "title": week.title,
        "start_page": week.start_page,
        "end_page": week.end_page,
        "sections": sections_out,
        "chunks": [chunk.to_dict() for chunk in chunks],
        "stats": {
            "chunks": len(chunks),
            "chars": total_chars,
            "estimated_duration_s": round(estimated_duration, 1),
            "estimated_duration_hms": _hms(estimated_duration),
        },
    }


def _hms(seconds: float) -> str:
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def write_lesson(project: ProjectConfig, lesson: dict[str, Any]) -> None:
    lessons_dir = project.content_dir / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    lesson_id = str(lesson["lesson_id"])
    path = lessons_dir / f"{lesson_id}.json"
    path.write_text(json.dumps(lesson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    lines: list[str] = [f"# {project.title} — {lesson_id}", ""]
    for section in lesson["sections"]:
        if section["type"] == "week":
            lines.append(f"## {section['title']}")
        else:
            lines.append(f"### {section['title']}")
        lines.append("")
        for chunk in lesson["chunks"]:
            if chunk["section_id"] != section["id"]:
                continue
            if chunk["block_id"].endswith("-title"):
                continue
            if chunk["kind"] == "heading":
                lines.append(f"#### {chunk['text']}")
            else:
                lines.append(chunk["text"])
            lines.append("")
    (lessons_dir / f"{lesson_id}.txt").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run_segment(selector: str) -> int:
    _, projects = load_projects()
    settings = load_settings()
    lexicon = load_lexicon()
    for project in resolve_projects(projects, selector):
        blocks_path = project.content_dir / "blocks.jsonl"
        if not blocks_path.exists():
            raise FileNotFoundError(f"{blocks_path} não existe; rode `extract` primeiro.")
        blocks = [
            Block.from_dict(json.loads(line))
            for line in blocks_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        weeks = segment_project(project, blocks, settings)
        write_project_outputs(project, weeks, blocks)

        total_chunks = 0
        total_chars = 0
        total_duration = 0.0
        for week in weeks:
            lesson = build_lesson(project, week, settings, lexicon)
            write_lesson(project, lesson)
            total_chunks += lesson["stats"]["chunks"]
            total_chars += lesson["stats"]["chars"]
            total_duration += lesson["stats"]["estimated_duration_s"]
            print(
                f"  {week.id}: {lesson['stats']['chunks']} chunks, "
                f"{lesson['stats']['chars']:,} chars, ~{lesson['stats']['estimated_duration_hms']}"
            )
        print(
            f"[segment] {project.key}: {total_chunks} chunks, {total_chars:,} chars, "
            f"~{_hms(total_duration)} estimados"
        )
    return 0
