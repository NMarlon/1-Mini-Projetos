"""Detecção genérica de capítulos e camada de texto de um PDF."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber
from pypdf import PdfReader

from pdf_tts.clean import clean_text, has_letter, is_page_number
from pdf_tts.extract import detect_body_size, group_chars_into_lines

CHAPTER_PATTERN = re.compile(
    r"^(Capítulo|Capitulo|Chapter|Parte|Part|Unidade|Unit|Aula|Semana|Lição|Licao|Lesson|Módulo|Modulo|Module)\b",
    re.IGNORECASE,
)
SUBSECTION_PATTERN = re.compile(r"^S\d{2}\b", re.IGNORECASE)


@dataclass
class Chapter:
    number: int
    title: str
    start_page: int
    end_page: int
    confidence: str = "auto"

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "confidence": self.confidence,
        }


@dataclass
class Discovery:
    pdf: Path
    title: str
    total_pages: int
    text_pages: int
    text_page_numbers: list[int]
    image_only_pages: list[int]
    body_size: float
    chapters: list[Chapter]
    structure: str
    confidence: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pdf": str(self.pdf),
            "title": self.title,
            "total_pages": self.total_pages,
            "text_pages": self.text_pages,
            "text_page_numbers": self.text_page_numbers,
            "image_only_pages": self.image_only_pages,
            "body_size": self.body_size,
            "chapters": [chapter.to_dict() for chapter in self.chapters],
            "structure": self.structure,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Discovery:
        chapters = [
            Chapter(
                number=int(item.get("number", index + 1)),
                title=str(item.get("title", f"Parte {index + 1}")),
                start_page=int(item["start_page"]),
                end_page=int(item["end_page"]),
                confidence=str(item.get("confidence", "manual")),
            )
            for index, item in enumerate(data.get("chapters", []))
        ]
        return cls(
            pdf=Path(data["pdf"]),
            title=str(data.get("title", "Livro")),
            total_pages=int(data["total_pages"]),
            text_pages=int(data.get("text_pages", 0)),
            text_page_numbers=[int(page) for page in data.get("text_page_numbers", [])],
            image_only_pages=[int(page) for page in data.get("image_only_pages", [])],
            body_size=float(data.get("body_size", 9.0)),
            chapters=chapters,
            structure=str(data.get("structure", "manual")),
            confidence=str(data.get("confidence", "manual")),
            warnings=[str(item) for item in data.get("warnings", [])],
        )


@dataclass
class _Candidate:
    page: int
    top: float
    size: float
    text: str


def _pdf_title(pdf_path: Path, reader: PdfReader) -> str:
    metadata = reader.metadata or {}
    title = str(metadata.get("/Title") or "").strip()
    normalized = title.strip("() ").lower()
    invalid = {"", "anonymous", "untitled", "document", "sem título", "sem titulo"}
    if (
        title
        and normalized not in invalid
        and not re.fullmatch(r"[0-9a-f-]{8,}", title.strip(), re.IGNORECASE)
        and len(title) > 1
        and not title.lower().endswith(".pdf")
        and not title.lower().startswith("microsoft word")
    ):
        return title
    return pdf_path.stem.replace("_", " ").strip() or "Livro"


def _outline_chapters(reader: PdfReader) -> list[Chapter]:
    items: list[tuple[int, str]] = []

    def walk(nodes: Any, depth: int = 0) -> None:
        if not isinstance(nodes, list):
            return
        for node in nodes:
            if isinstance(node, list):
                if depth == 0:
                    walk(node, depth + 1)
                continue
            try:
                page = reader.get_destination_page_number(node) + 1
            except Exception:  # noqa: BLE001 - outline pode ser inconsistente
                continue
            title = clean_text(str(getattr(node, "title", "") or "")).strip()
            if 1 <= page and title:
                items.append((page, title))
            if depth == 0 and isinstance(node, list):
                walk(node, depth + 1)

    walk(reader.outline)
    items.sort(key=lambda item: item[0])
    deduped: list[tuple[int, str]] = []
    seen_pages: set[int] = set()
    for page, title in items:
        if page in seen_pages:
            continue
        seen_pages.add(page)
        deduped.append((page, title))
    if len(deduped) < 2:
        return []
    return [
        Chapter(number=index + 1, title=title, start_page=page, end_page=page, confidence="outline")
        for index, (page, title) in enumerate(deduped)
    ]


def _heading_candidates(pdf: pdfplumber.PDF, body_size: float) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    frequencies: Counter[str] = Counter()
    page_lines: list[list[Any]] = []
    for page in pdf.pages:
        chars = [char for char in page.chars if str(char.get("text", ""))]
        if not chars:
            page_lines.append([])
            continue
        lines = group_chars_into_lines(page.page_number, chars)
        filtered = [
            line
            for line in lines
            if line.top > 48 and line.top < page.height - 45 and line.size >= body_size * 1.15
        ]
        # Páginas iniciais com muitos títulos costumam ser sumário; não são capítulos.
        if page.page_number <= 5 and len(filtered) >= 4:
            filtered = []
        page_lines.append(filtered)
        for line in filtered:
            text = clean_text(line.text)
            if 3 <= len(text) <= 140 and has_letter(text) and not is_page_number(text):
                frequencies[text] += 1

    frequent = {text for text, count in frequencies.items() if count >= max(4, len(pdf.pages) * 0.25)}
    max_size = max((line.size for lines in page_lines for line in lines), default=body_size * 1.5)
    for lines in page_lines:
        if not lines:
            continue
        for line in lines:
            text = clean_text(line.text)
            if not (3 <= len(text) <= 140) or not has_letter(text) or is_page_number(text):
                continue
            if text in frequent and line.size < body_size * 1.8:
                continue
            candidates.append(_Candidate(page=line.page, top=line.top, size=line.size, text=text))
    if not candidates:
        return []
    # Mantém o maior título de cada página, mas permite continuação de título.
    by_page: dict[int, list[_Candidate]] = {}
    for candidate in candidates:
        by_page.setdefault(candidate.page, []).append(candidate)
    selected: list[_Candidate] = []
    for page, items in sorted(by_page.items()):
        items.sort(key=lambda item: (-item.size, item.top))
        patterned = [item for item in items if CHAPTER_PATTERN.match(item.text)]
        first = patterned[0] if patterned else items[0]
        if first.size < max_size - 0.25 and not CHAPTER_PATTERN.match(first.text):
            continue
        title_parts = [first.text]
        for candidate in items[1:]:
            if abs(candidate.size - first.size) <= 0.2 and candidate.top - first.top < 45:
                title_parts.append(candidate.text)
            else:
                break
        selected.append(
            _Candidate(
                page=page,
                top=first.top,
                size=first.size,
                text=clean_text(" ".join(title_parts)),
            )
        )
    return selected


def _candidate_chapters(candidates: list[_Candidate], total_pages: int) -> list[Chapter]:
    if not candidates:
        return []
    candidates.sort(key=lambda item: (item.page, item.top))
    pattern_matches = [candidate for candidate in candidates if CHAPTER_PATTERN.match(candidate.text)]
    if pattern_matches:
        chosen = pattern_matches
    else:
        subsection_matches = [candidate for candidate in candidates if SUBSECTION_PATTERN.match(candidate.text)]
        chosen = subsection_matches if len(subsection_matches) >= 2 else candidates
    # Evita uma explosão de capítulos: no máximo um a cada 2 páginas e 120 no total.
    filtered: list[_Candidate] = []
    last_page = 0
    for candidate in chosen:
        if candidate.page <= last_page:
            continue
        filtered.append(candidate)
        last_page = candidate.page
        if len(filtered) >= 120:
            break
    if len(filtered) < 2:
        return []
    chapters = [
        Chapter(number=index + 1, title=candidate.text, start_page=candidate.page, end_page=candidate.page)
        for index, candidate in enumerate(filtered)
    ]
    return _finalize_chapters(chapters, total_pages)


def _finalize_chapters(chapters: list[Chapter], total_pages: int) -> list[Chapter]:
    chapters.sort(key=lambda chapter: chapter.start_page)
    cleaned: list[Chapter] = []
    for chapter in chapters:
        chapter.start_page = max(1, min(total_pages, int(chapter.start_page)))
        chapter.end_page = max(chapter.start_page, min(total_pages, int(chapter.end_page)))
        if cleaned and chapter.start_page <= cleaned[-1].start_page:
            continue
        cleaned.append(chapter)
    if not cleaned:
        return []
    if cleaned[0].start_page > 1:
        cleaned.insert(
            0,
            Chapter(
                number=1,
                title="Abertura",
                start_page=1,
                end_page=cleaned[0].start_page - 1,
                confidence="auto",
            ),
        )
    for index, chapter in enumerate(cleaned):
        next_start = cleaned[index + 1].start_page if index + 1 < len(cleaned) else total_pages + 1
        chapter.end_page = min(total_pages, next_start - 1)
        chapter.number = index + 1
    if cleaned[-1].end_page < total_pages:
        cleaned[-1].end_page = total_pages
    return cleaned


def _fallback_chapters(total_pages: int, chapter_size: int) -> list[Chapter]:
    size = max(1, int(chapter_size))
    chapters: list[Chapter] = []
    start = 1
    while start <= total_pages:
        end = min(total_pages, start + size - 1)
        chapters.append(
            Chapter(
                number=len(chapters) + 1,
                title=f"Parte {len(chapters) + 1:02d} — páginas {start}–{end}",
                start_page=start,
                end_page=end,
                confidence="fallback",
            )
        )
        start = end + 1
    return chapters


def _manual_chapters(raw: list[dict[str, Any]], total_pages: int) -> list[Chapter]:
    chapters = [
        Chapter(
            number=index + 1,
            title=str(item.get("title") or f"Parte {index + 1:02d}").strip(),
            start_page=int(item["start_page"]),
            end_page=int(item.get("end_page") or item["start_page"]),
            confidence="manual",
        )
        for index, item in enumerate(raw)
    ]
    if not chapters:
        raise ValueError("A lista manual de capítulos está vazia.")
    chapters = _finalize_chapters(chapters, total_pages)
    if not chapters:
        raise ValueError("Nenhum capítulo manual válido.")
    return chapters


def discover_pdf(
    pdf_path: Path,
    chapter_mode: str = "auto",
    chapter_size: int = 10,
    manual_chapters: list[dict[str, Any]] | None = None,
) -> Discovery:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise ValueError("PDF protegido por senha; desbloqueie antes de converter.") from exc
    title = _pdf_title(pdf_path, reader)
    total_pages = len(reader.pages)
    warnings: list[str] = []
    image_only_pages: list[int] = []
    text_page_numbers: list[int] = []
    text_pages = 0
    body_size = 9.0
    outline: list[Chapter] = []
    try:
        outline = _outline_chapters(reader)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Não foi possível ler o índice do PDF: {exc}")

    with pdfplumber.open(pdf_path) as pdf:
        body_size = detect_body_size(pdf)
        for page in pdf.pages:
            text = clean_text(page.extract_text() or "")
            if len(text) >= 20:
                text_pages += 1
                text_page_numbers.append(page.page_number)
            elif page.images:
                image_only_pages.append(page.page_number)

    if text_pages == 0:
        warnings.append("Este PDF não tem camada de texto; a v1 não consegue narrar PDFs escaneados.")
    elif text_pages < total_pages * 0.5:
        warnings.append(
            f"Apenas {text_pages} de {total_pages} páginas têm texto; páginas de imagem não serão narradas."
        )
    if image_only_pages:
        warnings.append(
            "Páginas sem texto: " + ", ".join(str(page) for page in image_only_pages[:30])
            + ("…" if len(image_only_pages) > 30 else "")
        )

    if chapter_mode == "manual":
        chapters = _manual_chapters(manual_chapters or [], total_pages)
        structure = "manual"
        confidence = "manual"
    elif chapter_mode == "none":
        chapters = [
            Chapter(number=1, title="Livro completo", start_page=1, end_page=total_pages, confidence="manual")
        ]
        structure = "none"
        confidence = "manual"
    else:
        chapters = outline
        structure = "outline"
        confidence = "high" if chapters else "low"
        if not chapters:
            with pdfplumber.open(pdf_path) as pdf:
                candidates = _heading_candidates(pdf, body_size)
            chapters = _candidate_chapters(candidates, total_pages)
            structure = "headings"
            confidence = "medium" if chapters else "low"
        if not chapters:
            chapters = _fallback_chapters(total_pages, chapter_size)
            structure = "fallback"
            confidence = "low"
            warnings.append(
                f"Não identifiquei capítulos; o PDF será dividido em blocos de {chapter_size} páginas."
            )
        else:
            chapters = _finalize_chapters(chapters, total_pages)

    if not chapters:
        raise ValueError("Não foi possível criar nenhum capítulo para este PDF.")
    chapters = _finalize_chapters(chapters, total_pages)

    return Discovery(
        pdf=pdf_path,
        title=title,
        total_pages=total_pages,
        text_pages=text_pages,
        text_page_numbers=text_page_numbers,
        image_only_pages=image_only_pages,
        body_size=body_size,
        chapters=chapters,
        structure=structure,
        confidence=confidence,
        warnings=warnings,
    )
