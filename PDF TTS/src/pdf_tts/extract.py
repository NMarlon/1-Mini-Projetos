"""Extração de texto e tabelas dos PDFs com pdfplumber."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import pdfplumber

from pdf_tts.clean import (
    clean_cell,
    clean_text,
    has_letter,
    is_caption,
    is_page_number,
    is_section_heading,
    is_skip_line,
    is_small_print_drop,
    is_url_only,
    is_week_title,
    join_lines,
    looks_like_reference,
    strip_attribution,
    strip_urls,
)
from pdf_tts.config import ProjectConfig
from pdf_tts.models import Block


@dataclass
class Line:
    page: int
    text: str
    size: float
    fontname: str
    x0: float
    x1: float
    top: float
    bottom: float
    had_marker: bool = False


@dataclass
class RawBlock:
    page: int
    text: str
    size: float
    fontname: str
    top: float
    x0: float
    had_marker: bool = False
    lines: list[str] = field(default_factory=list)


def detect_body_size(pdf: pdfplumber.PDF) -> float:
    sizes: Counter[float] = Counter()
    for page in pdf.pages:
        for char in page.chars:
            size = round(float(char.get("size", 0)), 1)
            if size >= 6:
                sizes[size] += 1
    if not sizes:
        return 9.0
    return float(sizes.most_common(1)[0][0])


def _line_from_chars(page_number: int, chars: list[dict]) -> Line:
    chars = sorted(chars, key=lambda char: float(char["x0"]))
    size = Counter(round(float(char.get("size", 0)), 1) for char in chars).most_common(1)[0][0]
    fontname = Counter(str(char.get("fontname", "")) for char in chars).most_common(1)[0][0]
    parts: list[str] = []
    previous = None
    for char in chars:
        text = str(char.get("text", ""))
        if not text:
            continue
        if (
            previous is not None
            and not text.isspace()
            and not previous["text"].isspace()
            and float(char["x0"]) - float(previous["x1"]) > size * 0.45
        ):
            parts.append(" ")
        parts.append(text)
        previous = char
    text = "".join(parts)
    had_marker = bool(re.match(r"^[\uf584\uf0a7•\-–]\s*", text))
    return Line(
        page=page_number,
        text=text,
        size=size,
        fontname=fontname,
        x0=min(float(char["x0"]) for char in chars),
        x1=max(float(char["x1"]) for char in chars),
        top=min(float(char["top"]) for char in chars),
        bottom=max(float(char["bottom"]) for char in chars),
        had_marker=had_marker,
    )


def group_chars_into_lines(page_number: int, chars: list[dict], tolerance: float = 2.5) -> list[Line]:
    rows: list[list[dict]] = []
    for char in sorted(chars, key=lambda item: (float(item["top"]), float(item["x0"]))):
        placed = False
        for row in rows:
            if abs(float(row[0]["top"]) - float(char["top"])) <= tolerance:
                row.append(char)
                placed = True
                break
        if not placed:
            rows.append([char])
    lines = [_line_from_chars(page_number, row) for row in rows]
    return sorted(lines, key=lambda line: (line.top, line.x0))


def _is_header_footer(line: Line, page_height: float, body_size: float) -> str | None:
    if line.top < 40 and line.size <= body_size * 0.95:
        return "header"
    if line.top > page_height - 45:
        return "footer"
    if is_page_number(line.text) and line.top > page_height - 80:
        return "footer"
    return None


def _filter_lines(lines: list[Line], page_height: float, body_size: float) -> list[Line]:
    kept: list[Line] = []
    for line in lines:
        text = clean_text(line.text)
        if not text:
            continue
        if _is_header_footer(line, page_height, body_size):
            continue
        if is_skip_line(text) or is_url_only(text):
            continue
        if not has_letter(text) and not is_page_number(text) and len(text) < 4:
            continue
        line.text = text
        kept.append(line)
    return kept


def _bbox_contains_line(bbox: tuple[float, float, float, float], line: Line) -> bool:
    x0, top, x1, bottom = bbox
    center_y = (line.top + line.bottom) / 2
    center_x = (line.x0 + line.x1) / 2
    return (top - 2) <= center_y <= (bottom + 2) and (x0 - 2) <= center_x <= (x1 + 2)


def _find_caption(lines: list[Line], bbox: tuple[float, float, float, float]) -> Line | None:
    _, top, _, bottom = bbox
    candidates: list[tuple[float, Line]] = []
    for line in lines:
        if not is_caption(line.text):
            continue
        if (bottom - 5) <= line.top <= (bottom + 100) or (top - 100) <= line.top <= (top + 5):
            distance = min(abs(line.top - bottom), abs(line.top - top))
            candidates.append((distance, line))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def format_table(rows: list[list[str | None]]) -> str:
    cleaned: list[list[str]] = []
    for row in rows:
        cells = [clean_cell(cell, is_label=(index == 0)) for index, cell in enumerate(row)]
        if any(cells):
            cleaned.append(cells)
    if len(cleaned) < 2:
        return ""
    width = max(len(row) for row in cleaned)
    cleaned = [row + [""] * (width - len(row)) for row in cleaned]
    if max(sum(1 for cell in row if cell) for row in cleaned) < 2:
        return ""

    first = cleaned[0]
    first_nonempty = [cell for cell in first if cell]
    has_header = (
        len(first_nonempty) >= 2
        and max(len(cell) for cell in first_nonempty) <= 80
        and not any(re.match(r"^[\$\d]", cell) for cell in first_nonempty)
        and any(has_letter(cell) for cell in first_nonempty)
    )

    header = first if has_header else [""] * width
    data_rows = cleaned[1:] if has_header else cleaned

    sentences: list[str] = []
    for row in data_rows:
        if not any(row):
            continue
        cells = [cell for cell in row]
        label = cells[0].strip()
        pairs: list[str] = []
        for index in range(1, width):
            if not cells[index]:
                continue
            key = header[index].strip()
            pairs.append(f"{key}: {cells[index]}" if key else cells[index])
        if label and pairs:
            sentences.append(f"{label}. " + "; ".join(pairs))
        elif label:
            sentences.append(label)
        elif pairs:
            sentences.append("; ".join(pairs))
        else:
            sentences.append("; ".join(cell for cell in cells if cell))
    text = ". ".join(sentence.rstrip(" .") for sentence in sentences if sentence)
    return (text + ".") if text else ""


def extract_tables(
    page: pdfplumber.page.Page,
    lines: list[Line],
    body_size: float,
) -> tuple[list[RawBlock], list[Line]]:
    tables = page.find_tables()
    if not tables:
        return [], lines

    candidates = []
    for table in tables:
        data = table.extract()
        if not data:
            continue
        nonempty = max(sum(1 for cell in row if cell and str(cell).strip()) for row in data)
        if len(data) < 2 or nonempty < 2:
            continue
        x0, top, x1, bottom = table.bbox
        area = (x1 - x0) * (bottom - top)
        if area > page.width * page.height * 0.85:
            continue
        candidates.append((area, table, data))
    candidates.sort(key=lambda item: item[0], reverse=True)

    blocks: list[RawBlock] = []
    remaining = list(lines)
    occupied: list[tuple[float, float, float, float]] = []
    for _, table, data in candidates:
        bbox = tuple(float(value) for value in table.bbox)
        if any(
            not (bbox[2] < other[0] or bbox[0] > other[2] or bbox[3] < other[1] or bbox[1] > other[3])
            for other in occupied
        ):
            continue
        text = format_table(data)
        if not text:
            continue
        caption = _find_caption(remaining, bbox)
        if caption is not None:
            text = f"{clean_text(caption.text)} {text}"
            remaining = [line for line in remaining if line is not caption]
        blocks.append(
            RawBlock(
                page=page.page_number,
                text=text,
                size=body_size,
                fontname="table",
                top=bbox[1],
                x0=bbox[0],
                lines=[text],
            )
        )
        occupied.append(bbox)
        remaining = [line for line in remaining if not _bbox_contains_line(bbox, line)]

    return blocks, remaining


def _is_heading(line: Line, body_size: float) -> bool:
    if line.size >= body_size * 1.15:
        return True
    matched, _ = is_section_heading(line.text)
    return matched and line.size >= body_size * 1.05


def group_lines_into_blocks(lines: list[Line], body_size: float) -> list[RawBlock]:
    blocks: list[RawBlock] = []
    current: list[Line] = []
    current_heading = False
    previous: Line | None = None

    def flush() -> None:
        nonlocal current, current_heading
        if not current:
            return
        text = join_lines([line.text for line in current])
        if not text:
            current = []
            current_heading = False
            return
        blocks.append(
            RawBlock(
                page=current[0].page,
                text=text,
                size=current[0].size,
                fontname=current[0].fontname,
                top=min(line.top for line in current),
                x0=min(line.x0 for line in current),
                had_marker=any(line.had_marker for line in current),
                lines=[line.text for line in current],
            )
        )
        current = []
        current_heading = False

    for line in sorted(lines, key=lambda item: (item.top, item.x0)):
        heading = _is_heading(line, body_size)
        marker = line.had_marker or bool(re.match(r"^(\d+[.)]|[•\-–])\s+", line.text))
        new_block = False
        if not current:
            new_block = True
        elif heading or current_heading:
            new_block = True
        elif marker:
            new_block = True
        elif previous is not None:
            gap = line.top - previous.bottom
            if gap > body_size * 0.7:
                new_block = True
            elif abs(line.x0 - previous.x0) > body_size * 1.5:
                new_block = True
        if new_block:
            flush()
            current = [line]
            current_heading = heading
        else:
            current.append(line)
        previous = line
    flush()
    return _merge_heading_continuations(blocks)


def _merge_heading_continuations(blocks: list[RawBlock]) -> list[RawBlock]:
    merged: list[RawBlock] = []
    for block in blocks:
        if not merged:
            merged.append(block)
            continue
        previous = merged[-1]
        previous_heading = previous.lines and _looks_like_heading_block(previous)
        current_heading = _looks_like_heading_block(block)
        gap = block.top - previous.top
        matched_current, _ = is_section_heading(block.text)
        continuation = (
            previous_heading
            and current_heading
            and abs(previous.size - block.size) <= 0.3
            and gap < 45
            and not matched_current
            and not previous.text.rstrip().endswith((".", "!", "?", ":", ";"))
        )
        if continuation:
            previous.text = join_lines([previous.text, block.text])
            previous.lines.append(block.text)
        else:
            merged.append(block)
    return merged


def _looks_like_heading_block(block: RawBlock) -> bool:
    # Usado apenas na mesclagem; a classificação final recalcula com body_size.
    return block.fontname != "table" and (block.size >= 10.0 or bool(re.match(r"^S0\d\b", block.text)))


def classify_block(block: RawBlock, body_size: float, project_key: str) -> Block:
    text = strip_urls(clean_text(block.text))
    # Remove números de nota de rodapé colados ao fim de frases: "melhor.6",
    # 'isso." 12', "favor.11 Essas".
    text = re.sub(r'([.!?"”’])\s*\d{1,3}\b(?=\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ“"\'(\[]|$)', r"\1", text)
    kind = "paragraph"
    level = 3
    drop_reason: str | None = None

    if block.fontname == "table":
        return Block(
            id="pending",
            project=project_key,
            page=block.page,
            kind="table",
            text=text,
            size=block.size,
            fontname=block.fontname,
            top=block.top,
            x0=block.x0,
            level=2,
            original_kind="table",
            original_level=2,
        )

    if not text:
        drop_reason = "empty"
    elif is_skip_line(text):
        drop_reason = "boilerplate"
    elif is_url_only(text):
        drop_reason = "url"
    elif block.size <= body_size * 0.82 and re.search(r"\bCC BY\b|Wikimedia Commons", text, re.IGNORECASE):
        drop_reason = "license"
    elif is_small_print_drop(text):
        drop_reason = "source"
    elif len(text) <= 40 and re.match(
        r"^(\d{1,2}\s+)?(D&C|Éter|Mateus|Marcos|Lucas|João|Provérbios|Néfi|Gênesis|Êxodo|Isaías|Salmos)\s+\d+[:.]\d+",
        text,
        re.IGNORECASE,
    ):
        drop_reason = "scripture_ref"
    elif block.size <= body_size * 0.82:
        if is_small_print_drop(text):
            drop_reason = "small_print"
        elif is_caption(text):
            kind = "caption"
            level = 2
            text = strip_attribution(text)
        else:
            kind = "paragraph"
            level = 3
            text = strip_attribution(text)
    elif is_week_title(text) and block.size >= body_size * 2.0:
        kind = "week_title"
        level = 0
    else:
        matched_section, section_type = is_section_heading(text)
        if matched_section and block.size >= body_size * 1.05:
            kind = "section_heading"
            level = 1
        elif block.size >= body_size * 1.15:
            kind = "heading"
            level = 1 if block.size >= body_size * 1.9 else 2
        elif is_caption(text):
            kind = "caption"
            level = 2
        elif block.had_marker:
            kind = "option"
            text = f"Opção: {text}"
            level = 3
        elif looks_like_reference(text):
            kind = "reference"
            drop_reason = "reference"
        elif re.match(r"^(\d+[.)]|[•\-–])\s+", text):
            kind = "list_item"
            level = 3

    block_id = "pending"
    result = Block(
        id=block_id,
        project=project_key,
        page=block.page,
        kind=kind,
        text=text,
        size=block.size,
        fontname=block.fontname,
        top=block.top,
        x0=block.x0,
        level=level,
        original_kind=kind,
        original_level=level,
        drop_reason=drop_reason,
    )
    return result


def _is_reference_continuation(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if looks_like_reference(stripped):
        return True
    if re.match(r"^[A-Z]{3,}\.?$", stripped):
        return True
    if re.match(
        r"^(HEALTH|Oxford|Cambridge|Publications|Press|Journal|Erlbaum|In\s+[A-Z]|Omdahl|Behavior)"
        r"|^(Psychology|Performance|Communication|Studies|Quarterly|Review|Ethnicity|Outcomes|Social Issues)\b"
        r"|^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.",
        stripped,
        re.IGNORECASE,
    ):
        return True
    if any(
        term in stripped
        for term in ("Journal", "Ethnicity", "Outcomes", "Social Issues", "no. ", "pp. ")
    ):
        return True
    if re.search(r"\b(Eds?\.|ed\.|pág|pp?\.|Press|Journal|University|Publishing)\b", stripped, re.IGNORECASE):
        return True
    if len(stripped) <= 150 and (stripped[:1].islower() or re.match(r"^[\d(]", stripped)):
        return True
    if re.match(r"^[A-Z][a-z]+\.?$", stripped):
        return True
    return False


def _mark_reference_runs(blocks: list[Block]) -> None:
    """Após a primeira referência, descarta as linhas de continuação da bibliografia."""
    in_references = False
    for block in blocks:
        if block.kind == "reference":
            in_references = True
            continue
        if not in_references:
            continue
        if block.kind in {"section_heading", "week_title", "heading", "table"}:
            in_references = False
            continue
        if _is_reference_continuation(block.text):
            if block.drop_reason is None:
                block.kind = "reference"
                block.drop_reason = "reference_continuation"
        else:
            # Era uma citação isolada (ex.: quote espiritual); o texto seguinte
            # é conteúdo normal e deve continuar.
            in_references = False


def extract_page(
    page: pdfplumber.page.Page,
    page_number: int,
    body_size: float,
) -> list[Block]:
    chars = [char for char in page.chars if str(char.get("text", ""))]
    if not chars:
        return []
    lines = group_chars_into_lines(page_number, chars)
    lines = _filter_lines(lines, page.height, body_size)

    table_blocks, lines = extract_tables(page, lines, body_size)
    raw_blocks = group_lines_into_blocks(lines, body_size)
    raw_blocks.extend(table_blocks)
    raw_blocks.sort(key=lambda block: (block.top, block.x0))

    blocks: list[Block] = []
    for index, raw in enumerate(raw_blocks, start=1):
        block = classify_block(raw, body_size, "pending")
        block.id = f"pending-p{page_number:04d}-b{index:03d}"
        blocks.append(block)
    _mark_reference_runs(blocks)
    return blocks


def _merge_cross_page_continuations(blocks: list[Block]) -> None:
    """Junta fragmentos minúsculos que continuam uma frase da página anterior."""
    for index, current in enumerate(blocks):
        if current.is_dropped or current.kind != "paragraph":
            continue
        if not current.text[:1].islower() or len(current.text.split()) > 8:
            continue
        previous = None
        for candidate in reversed(blocks[:index]):
            if candidate.is_dropped:
                continue
            previous = candidate
            break
        if previous is None or previous.kind != "paragraph":
            continue
        if current.page > previous.page + 1:
            continue
        if previous.text.rstrip().endswith((".", "!", "?", ":", ";")):
            continue
        previous.text = f"{previous.text.rstrip()} {current.text.lstrip()}"
        current.drop_reason = "continuation"


def extract_project(project: ProjectConfig) -> tuple[list[Block], float]:
    if not project.pdf.exists():
        raise FileNotFoundError(
            f"PDF não encontrado: {project.pdf}. Veja input/README.md e copie o arquivo."
        )
    blocks: list[Block] = []
    with pdfplumber.open(project.pdf) as pdf:
        body_size = detect_body_size(pdf)
        for page in pdf.pages:
            blocks.extend(extract_page(page, page.page_number, body_size))
    for block in blocks:
        block.project = project.key
        block.id = block.id.replace("pending", project.key)
    _merge_cross_page_continuations(blocks)
    return blocks, body_size


def summarize_blocks(blocks: list[Block]) -> dict[str, int]:
    counter: Counter[str] = Counter(block.kind for block in blocks)
    counter["dropped"] = sum(1 for block in blocks if block.is_dropped)
    counter["total"] = len(blocks)
    return dict(counter)


def debug_page(project: ProjectConfig, page_number: int) -> list[Block]:
    with pdfplumber.open(project.pdf) as pdf:
        body_size = detect_body_size(pdf)
        page = pdf.pages[page_number - 1]
        return extract_page(page, page_number, body_size)
