"""Divisão do texto em chunks faláveis com pausas."""

from __future__ import annotations

import re

from pdf_tts.clean import has_letter
from pdf_tts.models import Block, Chunk
from pdf_tts.normalize import normalize_text, strip_list_marker

SPLIT_ABBREVIATIONS = [
    r"\bp\.ex\.",
    r"\bP\.ex\.",
    r"\betc\.",
    r"\bvs\.",
    r"\bi\.e\.",
    r"\bDra\.",
    r"\bDr\.",
    r"\bSra\.",
    r"\bSr\.",
    r"\bProfa\.",
    r"\bProf\.",
    r"\bfig\.",
    r"\bFig\.",
    r"\bpág\.",
    r"\bpp\.",
    r"\bp\.",
    r"\bart\.",
]

GAP_BY_KIND = {
    "section_heading": 1200,
    "heading": 700,
    "paragraph": 350,
    "list_item": 250,
    "option": 200,
    "caption": 300,
    "table": 500,
}


def split_sentences(text: str) -> list[str]:
    """Divide em frases protegendo abreviações, iniciais e números pontuados."""
    protected = text
    tokens: list[str] = []

    def protect(match: re.Match[str]) -> str:
        token = f"\x01{chr(0xE100 + len(tokens))}\x01"
        tokens.append(match.group(0))
        return token

    for pattern in SPLIT_ABBREVIATIONS:
        protected = re.sub(pattern, protect, protected, flags=re.IGNORECASE)
    protected = re.sub(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ]\.", protect, protected)
    protected = re.sub(r"(?<!\d)\d+\.\d+(?!\d)", protect, protected)
    protected = re.sub(r"\.{3,}", protect, protected)

    parts = re.findall(r".+?(?:[.!?](?:[\"'”’])?)(?=\s|$)|.+$", protected, flags=re.DOTALL)
    restored: list[str] = []
    for part in parts:
        for index, token_text in enumerate(tokens):
            part = part.replace(f"\x01{chr(0xE100 + index)}\x01", token_text)
        part = re.sub(r"\s+", " ", part).strip()
        if part:
            restored.append(part)
    return restored or [text.strip()]


def split_long(text: str, max_chars: int) -> list[str]:
    text = text.strip()
    parts: list[str] = []
    while len(text) > max_chars:
        window = text[:max_chars]
        cut = -1
        for separator in ("; ", ": ", ", "):
            index = window.rfind(separator)
            if index >= max_chars * 0.4:
                cut = index + len(separator)
                break
        if cut < 0:
            index = window.rfind(" ")
            cut = index if index >= max_chars * 0.4 else max_chars
        cut = max(1, cut)
        part = text[:cut].strip()
        if part:
            parts.append(part)
        text = text[cut:].strip()
    if text:
        parts.append(text)
    return parts


def merge_short(parts: list[str], min_chars: int) -> list[str]:
    merged: list[str] = []
    for part in parts:
        if merged and len(merged[-1]) < min_chars:
            merged[-1] = f"{merged[-1]} {part}".strip()
        else:
            merged.append(part)
    return merged


def chunk_block(
    block: Block,
    lexicon: dict,
    min_chars: int,
    max_chars: int,
    first_gap_ms: int,
) -> list[Chunk]:
    display = block.text.strip()
    if not display:
        return []
    if block.kind == "list_item":
        display = strip_list_marker(display)

    if block.kind in {"heading", "section_heading"}:
        parts = [display]
    elif block.kind == "caption" and len(display) <= max_chars:
        parts = [display]
    else:
        parts = split_sentences(display)
        parts = merge_short(parts, min_chars)
        expanded: list[str] = []
        for part in parts:
            expanded.extend(split_long(part, max_chars))
        parts = [part for part in expanded if part.strip()]

    chunks: list[Chunk] = []
    for index, part in enumerate(parts):
        spoken = normalize_text(part, lexicon, kind=block.kind)
        if not spoken or not has_letter(spoken):
            continue
        chunks.append(
            Chunk(
                id="",
                lesson_id="",
                section_id=block.section_id or "",
                block_id=block.id,
                kind=block.kind,
                text=part,
                spoken=spoken,
                gap_before_ms=first_gap_ms if index == 0 else 0,
            )
        )
    return chunks
