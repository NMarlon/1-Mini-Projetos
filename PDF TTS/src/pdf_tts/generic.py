"""Conversão genérica de um PDF em audiolivro, sem configuração manual."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pdf_tts.build import BuildOptions, run_build_project
from pdf_tts.config import (
    ROOT,
    ProjectConfig,
    WeekConfig,
    load_lexicon,
    load_projects,
    load_settings,
)
from pdf_tts.discover import Chapter, Discovery, discover_pdf
from pdf_tts.extract import extract_project
from pdf_tts.lessons import build_lesson, write_lesson
from pdf_tts.segment import segment_project, write_project_outputs
from pdf_tts.verify import run_verify_project

ProgressCallback = Callable[[str, int, int, str], None]


@dataclass
class ConvertOptions:
    chapter_mode: str = "auto"
    chapter_size: int = 10
    manual_chapters: list[dict[str, Any]] | None = None
    content_mode: str = "auto"
    profile: str = "auto"
    voice: str | None = None
    rate: str | None = None


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-").upper()
    return ascii_text[:60] or "LIVRO"


def _notify(callback: ProgressCallback | None, stage: str, current: int, total: int, message: str = "") -> None:
    if callback is not None:
        callback(stage, current, total, message)


def make_project(
    pdf_path: Path,
    discovery: Discovery,
    options: ConvertOptions,
) -> ProjectConfig:
    defaults, _ = load_projects()
    settings = copy.deepcopy(defaults)
    settings["voice"] = options.voice or settings.get("voice", "pt-BR-FranciscaNeural")
    settings["rate"] = options.rate or settings.get("rate", "-5%")
    settings["chapter_label"] = "Parte"
    settings["content_mode"] = options.content_mode
    settings["profile"] = options.profile
    settings["include"] = {
        **settings.get("include", {}),
        "references": options.content_mode in {"all", "raw"},
    }

    digest = hashlib.sha1(
        f"{pdf_path.resolve()}|{pdf_path.stat().st_size}|{pdf_path.stat().st_mtime}".encode()
    ).hexdigest()[:10]
    key = f"auto_{digest}"
    base_slug = slugify(discovery.title or pdf_path.stem)
    slug = f"AUTO-{base_slug}-{digest[:4]}"

    weeks = tuple(
        WeekConfig(
            week=chapter.number,
            start_page=chapter.start_page,
            end_page=chapter.end_page,
            title=chapter.title,
        )
        for chapter in discovery.chapters
    )
    return ProjectConfig(
        key=key,
        title=discovery.title,
        short_title=pdf_path.stem,
        slug=slug,
        pdf=pdf_path,
        output_dir=ROOT / "output" / slug,
        language="pt-BR",
        weeks=weeks,
        settings=settings,
    )


def coverage_report(
    discovery: Discovery,
    blocks: list,
    chunks: int,
    warnings: list[str],
) -> dict[str, Any]:
    kept_pages = {block.page for block in blocks if block.is_content}
    dropped = Counter(block.drop_reason for block in blocks if block.is_dropped)
    text_pages = set(discovery.text_page_numbers)
    missing = sorted(text_pages - kept_pages)
    only_dropped = sorted(
        page
        for page in text_pages
        if page not in kept_pages and any(block.page == page and block.is_dropped for block in blocks)
    )
    return {
        "pages_total": discovery.total_pages,
        "pages_with_text": discovery.text_pages,
        "pages_narrated": len(kept_pages & text_pages),
        "pages_without_audio": missing,
        "pages_only_dropped": only_dropped,
        "image_only_pages": discovery.image_only_pages,
        "dropped_blocks": dict(dropped),
        "chapters": [chapter.to_dict() for chapter in discovery.chapters],
        "chunks": chunks,
        "warnings": warnings,
    }


def convert_pdf(
    pdf_path: Path,
    options: ConvertOptions | None = None,
    progress_cb: ProgressCallback | None = None,
    discovery: Discovery | None = None,
) -> dict[str, Any]:
    options = options or ConvertOptions()
    pdf_path = Path(pdf_path)
    if options.content_mode not in {"auto", "all", "raw"}:
        raise ValueError("Modo de conteúdo inválido; use auto, all ou raw.")
    if options.profile not in {"auto", "pathway", "generic"}:
        raise ValueError("Perfil inválido; use auto, pathway ou generic.")
    if discovery is None:
        _notify(progress_cb, "analisando", 0, 1, "lendo PDF")
        discovery = discover_pdf(
            pdf_path,
            chapter_mode=options.chapter_mode,
            chapter_size=options.chapter_size,
            manual_chapters=options.manual_chapters,
            profile=options.profile,
        )
    if options.manual_chapters:
        discovery = copy.deepcopy(discovery)
        chapters = sorted(
            [
                Chapter(
                    number=index + 1,
                    title=str(item.get("title") or f"Parte {index + 1:02d}").strip(),
                    start_page=int(item["start_page"]),
                    end_page=int(item.get("end_page") or item["start_page"]),
                    confidence="manual",
                )
                for index, item in enumerate(options.manual_chapters)
            ],
            key=lambda chapter: chapter.start_page,
        )
        if not chapters or chapters[0].start_page != 1 or chapters[-1].end_page != discovery.total_pages:
            raise ValueError(
                "Os capítulos manuais devem começar na página 1 e terminar na última página do PDF."
            )
        for index, chapter in enumerate(chapters):
            if chapter.end_page < chapter.start_page:
                raise ValueError(f"Capítulo inválido: {chapter.title}")
            if index + 1 < len(chapters) and chapters[index + 1].start_page != chapter.end_page + 1:
                raise ValueError("Os capítulos manuais devem ser contínuos, sem lacunas ou sobreposições.")
            chapter.number = index + 1
        discovery.chapters = chapters
    _notify(progress_cb, "analisando", 1, 1, f"{len(discovery.chapters)} capítulos")
    if discovery.text_pages == 0:
        raise ValueError(
            "Este PDF não tem camada de texto. A v1 não consegue narrar PDFs escaneados; "
            "use um PDF com texto ou aguarde o OCR."
        )
    _notify(progress_cb, "analisando", 1, 1, f"{len(discovery.chapters)} capítulos")
    project = make_project(pdf_path, discovery, options)

    _notify(progress_cb, "extraindo", 0, 1, pdf_path.name)
    blocks, body_size = extract_project(project, content_mode=options.content_mode)
    settings = load_settings()
    lexicon = load_lexicon()
    weeks = segment_project(project, blocks, settings)
    write_project_outputs(project, weeks, blocks)
    _notify(progress_cb, "extraindo", 1, 1, f"{len(blocks)} blocos, corpo {body_size:.1f} pt")

    total_chunks = 0
    for week in weeks:
        lesson = build_lesson(project, week, settings, lexicon)
        write_lesson(project, lesson)
        total_chunks += int(lesson["stats"]["chunks"])
    _notify(progress_cb, "segmentando", 1, 1, f"{total_chunks} chunks")

    warnings = list(discovery.warnings)
    coverage = coverage_report(discovery, blocks, total_chunks, warnings)
    if coverage["pages_without_audio"]:
        warnings.append(
            "Páginas com texto sem áudio: "
            + ", ".join(str(page) for page in coverage["pages_without_audio"][:30])
            + ("…" if len(coverage["pages_without_audio"]) > 30 else "")
        )
        coverage["warnings"] = warnings

    report_dir = project.output_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "coverage.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    code = run_build_project(
        project,
        BuildOptions(
            project=project.key,
            voice=options.voice,
            rate=options.rate,
            no_assemble=False,
        ),
        progress_cb=progress_cb,
    )
    if code:
        raise RuntimeError("A síntese ou a montagem falhou; veja o log e use --resume.")

    code = run_verify_project(
        project,
        check_loudness=False,
        check_silence=False,
        progress_cb=progress_cb,
    )
    if code:
        raise RuntimeError("A verificação estrutural encontrou problemas; veja o relatório.")

    return {
        "project": project,
        "discovery": discovery,
        "coverage": coverage,
        "output_dir": project.output_dir,
        "manifest": project.manifest_path,
    }


def load_manual_chapters(path: str | Path | None) -> list[dict[str, Any]] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("chapters", [])
    if not isinstance(data, list):
        raise ValueError("O arquivo de capítulos deve conter uma lista JSON.")
    return data


def run_detect(
    pdf_path: str | Path,
    chapter_mode: str = "auto",
    chapter_size: int = 10,
    manual_chapters: list[dict[str, Any]] | None = None,
    profile: str = "auto",
    as_json: bool = False,
) -> int:
    discovery = discover_pdf(
        Path(pdf_path),
        chapter_mode=chapter_mode,
        chapter_size=chapter_size,
        manual_chapters=manual_chapters,
        profile=profile,
    )
    if as_json:
        print(json.dumps(discovery.to_dict(), ensure_ascii=False, indent=2))
        return 0
    print(f"PDF: {discovery.pdf}")
    print(f"Título: {discovery.title}")
    print(
        f"Páginas: {discovery.total_pages}; com texto: {discovery.text_pages}; "
        f"estrutura: {discovery.structure} ({discovery.confidence}); "
        f"perfil usado: {discovery.profile_used}"
    )
    for chapter in discovery.chapters:
        print(
            f"  {chapter.number:02d}. p.{chapter.start_page}-{chapter.end_page} "
            f"[{chapter.confidence}] {chapter.title}"
        )
    for warning in discovery.warnings:
        print(f"AVISO: {warning}")
    return 0


def run_convert_cli(
    pdf_path: str | Path,
    options: ConvertOptions,
) -> int:
    def progress(stage: str, current: int, total: int, message: str) -> None:
        print(f"[{stage}] {current}/{total} {message}")

    try:
        result = convert_pdf(Path(pdf_path), options, progress_cb=progress)
    except Exception as exc:  # noqa: BLE001 - CLI amigável
        print(f"ERRO: {type(exc).__name__}: {exc}")
        return 1
    print(f"\nPronto: {result['output_dir']}")
    for lesson in sorted(result["output_dir"].glob("S*.mp3")):
        print(f"  {lesson.name}")
    print(f"Manifest: {result['manifest']}")
    coverage = result["coverage"]
    print(
        f"Cobertura: {coverage['pages_narrated']}/{coverage['pages_with_text']} páginas com texto narradas; "
        f"{coverage['chunks']} chunks."
    )
    for warning in coverage["warnings"]:
        print(f"AVISO: {warning}")
    return 0
