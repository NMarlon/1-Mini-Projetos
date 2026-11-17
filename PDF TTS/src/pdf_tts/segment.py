"""Estruturação do texto em semanas, seções e manuscript."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from pdf_tts.clean import is_section_heading, normalize_heading_key
from pdf_tts.config import ProjectConfig, load_projects, load_settings, resolve_projects
from pdf_tts.extract import extract_project, summarize_blocks
from pdf_tts.models import Block, Section, Week

GENERIC_SECTION_TYPES = {
    "introduction",
    "conclusion",
    "summary",
    "study_tips",
    "exercises",
    "quiz",
    "vocabulary",
    "spiritual",
}
DEEP_SECTION_TYPES = {"sxx", "task", "discussion", "case_study", "project"}


def _synthetic_week_title(project: ProjectConfig, week_number: int, title: str, page: int) -> Block:
    return Block(
        id=f"{project.key}-S{week_number:02d}-title",
        project=project.key,
        page=page,
        kind="section_heading",
        text=f"Semana {week_number} — {title}",
        size=0.0,
        fontname="synthetic",
        top=0.0,
        x0=0.0,
        level=1,
    )


def _blocks_in_page_range(blocks: list[Block], start: int, end: int) -> list[Block]:
    return [block for block in blocks if start <= block.page <= end]


def segment_project(
    project: ProjectConfig,
    blocks: list[Block],
    settings: dict[str, Any],
) -> list[Week]:
    # `segment` pode transformar um título de seção em subseção. Restaura a
    # classificação original antes de reestruturar, para que `resegment` seja
    # idempotente.
    for block in blocks:
        if block.original_kind:
            block.kind = block.original_kind
            block.level = block.original_level if block.original_level is not None else block.level

    weeks: list[Week] = []
    for week_config in project.weeks:
        week_number = week_config.week
        week_blocks = _blocks_in_page_range(blocks, week_config.start_page, week_config.end_page)
        week_blocks.sort(key=lambda block: (block.page, block.top, block.x0))

        title_block = _synthetic_week_title(project, week_number, week_config.title, week_config.start_page)
        week_section = Section(
            id=f"S{week_number:02d}-00",
            title=title_block.text,
            type="week",
            blocks=[title_block],
            start_page=week_config.start_page,
            end_page=week_config.end_page,
        )
        sections: list[Section] = [week_section]
        current = week_section

        for block in week_blocks:
            if block.kind == "week_title" or block.is_dropped:
                continue
            if block.kind == "section_heading":
                matched, section_type = is_section_heading(block.text)
                if not matched:
                    section_type = "section"
                # "Introdução", "Conclusão" etc. dentro de um estudo de caso,
                # tarefa ou discussão são subseções, não capítulos novos.
                if (
                    matched
                    and section_type in GENERIC_SECTION_TYPES
                    and current.type in DEEP_SECTION_TYPES
                    and block.page == current.start_page
                ):
                    block.kind = "heading"
                    block.level = 2
                    current.blocks.append(block)
                    current.end_page = max(current.end_page, block.page)
                    continue
                # Evita duplicar o mesmo título quando a página anterior só tinha o cabeçalho.
                if normalize_heading_key(block.text) == normalize_heading_key(current.title) and not current.has_content:
                    current.start_page = block.page
                    current.end_page = max(current.end_page, block.page)
                    continue
                current = Section(
                    id=f"S{week_number:02d}-{len(sections):02d}",
                    title=block.text,
                    type=section_type,
                    blocks=[],
                    start_page=block.page,
                    end_page=block.page,
                )
                sections.append(current)
            elif (
                block.kind == "heading"
                and block.level == 1
                and current.has_content
                and (current.type in {"quiz", "exercises"} or current.chars >= 6000)
            ):
                # Um quiz/exercício não deve engolir o capítulo seguinte; seções
                # muito longas também ganham um novo capítulo em títulos nível 1.
                current = Section(
                    id=f"S{week_number:02d}-{len(sections):02d}",
                    title=block.text,
                    type="heading",
                    blocks=[],
                    start_page=block.page,
                    end_page=block.page,
                )
                sections.append(current)
            else:
                current.blocks.append(block)
                current.start_page = min(current.start_page, block.page)
                current.end_page = max(current.end_page, block.page)

        cleaned = _clean_sections(sections)
        weeks.append(
            Week(
                week=week_number,
                id=f"S{week_number:02d}",
                title=week_config.title,
                start_page=week_config.start_page,
                end_page=week_config.end_page,
                sections=cleaned,
            )
        )
    return weeks


def _clean_sections(sections: list[Section]) -> list[Section]:
    # Remove seções vazias (só cabeçalho), exceto a seção-síntese da semana.
    # Não deduplica títulos: "Introdução" pode existir na semana e dentro de
    # uma tarefa, e são seções diferentes.
    filtered: list[Section] = []
    for section in sections:
        if section.type == "week":
            filtered.append(section)
            continue
        if not section.has_content:
            continue
        filtered.append(section)

    # Reatribui IDs sequenciais e section_id dos blocos.
    for index, section in enumerate(filtered):
        week_prefix = section.id.split("-", 1)[0]
        section.id = f"{week_prefix}-{index:02d}"
        for block in section.blocks:
            block.section_id = section.id
    return filtered


def write_project_outputs(project: ProjectConfig, weeks: list[Week], blocks: list[Block]) -> None:
    content_dir = project.content_dir
    content_dir.mkdir(parents=True, exist_ok=True)
    lessons_dir = content_dir / "lessons"
    lessons_dir.mkdir(exist_ok=True)

    with (content_dir / "blocks.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for block in blocks:
            handle.write(json.dumps(block.to_dict(), ensure_ascii=False) + "\n")

    with (content_dir / "skipped.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for block in blocks:
            if block.is_dropped:
                handle.write(
                    json.dumps(
                        {
                            "id": block.id,
                            "page": block.page,
                            "kind": block.kind,
                            "reason": block.drop_reason,
                            "preview": block.text[:160],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    structure = {
        "project": project.key,
        "title": project.title,
        "short_title": project.short_title,
        "source_pdf": str(project.pdf.relative_to(project.pdf.parents[2])),
        "weeks": [week.to_dict() for week in weeks],
        "totals": {
            "weeks": len(weeks),
            "chars": sum(week.chars for week in weeks),
            "blocks": len(blocks),
            "dropped": sum(1 for block in blocks if block.is_dropped),
            "kinds": dict(Counter(block.kind for block in blocks)),
        },
    }
    with (content_dir / "structure.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(structure, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    _write_manuscript(project, weeks, blocks, content_dir / "manuscript.md")


def _write_manuscript(project: ProjectConfig, weeks: list[Week], blocks: list[Block], path: Path) -> None:
    lines: list[str] = [f"# {project.title}", ""]
    last_page = 0
    for week in weeks:
        lines.append(f"## Semana {week.week} — {week.title}")
        lines.append("")
        for section in week.sections:
            if section.type != "week":
                lines.append(f"### {section.title}")
                lines.append("")
            for block in section.blocks:
                if block.kind == "section_heading" and section.type == "week":
                    continue
                if block.page != last_page:
                    lines.append(f"<!-- p{block.page} -->")
                    last_page = block.page
                if block.kind == "heading":
                    lines.append(f"#### {block.text}")
                elif block.kind == "caption":
                    lines.append(f"*{block.text}*")
                else:
                    lines.append(block.text)
                lines.append("")

    skipped = [block for block in blocks if block.is_dropped]
    lines.append("---")
    lines.append("")
    lines.append("## Apêndice — blocos descartados")
    lines.append("")
    for block in skipped:
        preview = block.text.replace("\n", " ")[:140]
        lines.append(f"- p. {block.page} · `{block.kind}` · `{block.drop_reason}` · {preview}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run_resegment(selector: str) -> int:
    """Reestrutura a partir de blocks.jsonl, sem reabrir os PDFs (iteração rápida)."""
    _, projects = load_projects()
    settings = load_settings()
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
        print(f"[resegment] {project.key}: {sum(week.chars for week in weeks):,} chars")
        for week in weeks:
            print(f"  S{week.week:02d} seções={len(week.sections)} chars={week.chars:,}")
    return 0


def run_extract(selector: str) -> int:
    _, projects = load_projects()
    settings = load_settings()
    selected = resolve_projects(projects, selector)
    for project in selected:
        print(f"[extract] {project.key}: {project.pdf.name}")
        blocks, body_size = extract_project(project)
        weeks = segment_project(project, blocks, settings)
        write_project_outputs(project, weeks, blocks)
        summary = summarize_blocks(blocks)
        total_chars = sum(week.chars for week in weeks)
        print(
            f"  body_size={body_size:.1f} blocks={len(blocks)} "
            f"chars={total_chars:,} dropped={summary.get('dropped', 0)}"
        )
        for week in weeks:
            print(
                f"  S{week.week:02d} p{week.start_page}-{week.end_page} "
                f"chars={week.chars:,} seções={len(week.sections)}"
            )
        print(f"  -> {project.content_dir.relative_to(project.content_dir.parents[1])}")
    return 0
