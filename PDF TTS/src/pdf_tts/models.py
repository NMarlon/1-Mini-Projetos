"""Modelos de dados do pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CONTENT_KINDS = {
    "section_heading",
    "heading",
    "paragraph",
    "list_item",
    "option",
    "caption",
    "table",
}


@dataclass
class Block:
    id: str
    project: str
    page: int
    kind: str
    text: str
    size: float
    fontname: str
    top: float
    x0: float
    level: int = 3
    original_kind: str | None = None
    original_level: int | None = None
    section_id: str | None = None
    drop_reason: str | None = None

    @property
    def is_dropped(self) -> bool:
        return self.drop_reason is not None

    @property
    def is_content(self) -> bool:
        return not self.is_dropped and self.kind in CONTENT_KINDS

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "project": self.project,
            "page": self.page,
            "kind": self.kind,
            "text": self.text,
            "size": round(self.size, 2),
            "fontname": self.fontname,
            "top": round(self.top, 2),
            "x0": round(self.x0, 2),
            "level": self.level,
            "original_kind": self.original_kind,
            "original_level": self.original_level,
            "section_id": self.section_id,
            "drop_reason": self.drop_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Block:
        return cls(
            id=str(data["id"]),
            project=str(data["project"]),
            page=int(data["page"]),
            kind=str(data["kind"]),
            text=str(data["text"]),
            size=float(data.get("size", 0)),
            fontname=str(data.get("fontname", "")),
            top=float(data.get("top", 0)),
            x0=float(data.get("x0", 0)),
            level=int(data.get("level", 3)),
            original_kind=data.get("original_kind"),
            original_level=data.get("original_level"),
            section_id=data.get("section_id"),
            drop_reason=data.get("drop_reason"),
        )


@dataclass
class Section:
    id: str
    title: str
    type: str
    blocks: list[Block] = field(default_factory=list)
    start_page: int = 0
    end_page: int = 0

    @property
    def chars(self) -> int:
        return sum(len(block.text) for block in self.blocks)

    @property
    def has_content(self) -> bool:
        return any(block.kind != "heading" and block.kind != "section_heading" for block in self.blocks)

    def content_blocks(self) -> list[Block]:
        return [block for block in self.blocks if block.kind != "section_heading"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "chars": self.chars,
            "blocks": len(self.blocks),
            "content_blocks": len(self.content_blocks()),
        }


@dataclass
class Week:
    week: int
    id: str
    title: str
    start_page: int
    end_page: int
    sections: list[Section] = field(default_factory=list)

    @property
    def chars(self) -> int:
        return sum(section.chars for section in self.sections)

    def to_dict(self) -> dict[str, Any]:
        return {
            "week": self.week,
            "id": self.id,
            "title": self.title,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "chars": self.chars,
            "sections": [section.to_dict() for section in self.sections],
        }
