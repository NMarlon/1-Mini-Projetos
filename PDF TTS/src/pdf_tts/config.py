"""Carregamento de configuração do projeto."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _data_root() -> Path:
    """Onde ficam input/content/output/cache/logs (ao lado do .exe quando empacotado)."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _resource_root() -> Path:
    """Onde ficam config/samples empacotados (o _internal no PyInstaller onedir)."""
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS", _data_root())).resolve()
    return _data_root()


ROOT = _data_root()
RESOURCE_ROOT = _resource_root()
CONFIG_DIR = RESOURCE_ROOT / "config"


@dataclass(frozen=True)
class WeekConfig:
    week: int
    start_page: int
    end_page: int
    title: str

    @property
    def lesson_id(self) -> str:
        return f"S{self.week:02d}"


@dataclass(frozen=True)
class ProjectConfig:
    key: str
    title: str
    short_title: str
    slug: str
    pdf: Path
    output_dir: Path
    language: str
    weeks: tuple[WeekConfig, ...]
    settings: dict[str, Any] = field(default_factory=dict)

    @property
    def content_dir(self) -> Path:
        return ROOT / "content" / self.key

    @property
    def cache_dir(self) -> Path:
        return ROOT / "cache" / self.key

    @property
    def manifest_path(self) -> Path:
        return ROOT / "manifests" / f"{self.slug}.json"

    def week(self, lesson_or_week: str | int) -> WeekConfig:
        if isinstance(lesson_or_week, int):
            number = lesson_or_week
        else:
            text = lesson_or_week.strip().upper()
            if text.startswith("S"):
                text = text[1:]
            number = int(text)
        for week in self.weeks:
            if week.week == number:
                return week
        raise KeyError(f"Semana {lesson_or_week!r} não existe em {self.key}")


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuração não encontrada: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML inválido (esperado mapa): {path}")
    return data


def load_settings() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "structure.yaml")


def load_projects() -> tuple[dict[str, Any], dict[str, ProjectConfig]]:
    data = load_yaml(CONFIG_DIR / "projects.yaml")
    defaults: dict[str, Any] = data.get("defaults", {})
    raw_projects: dict[str, Any] = data.get("projects", {})
    if not raw_projects:
        raise ValueError("config/projects.yaml não contém 'projects'")

    projects: dict[str, ProjectConfig] = {}
    for key, raw in raw_projects.items():
        weeks_raw = raw.get("weeks") or []
        weeks = tuple(
            WeekConfig(
                week=int(item["week"]),
                start_page=int(item["start_page"]),
                end_page=int(item["end_page"]),
                title=str(item["title"]).strip(),
            )
            for item in weeks_raw
        )
        _validate_weeks(key, weeks)

        settings = dict(defaults)
        for section, value in raw.items():
            if section in {"title", "short_title", "slug", "pdf", "output_dir", "language", "weeks"}:
                continue
            if isinstance(value, dict) and isinstance(settings.get(section), dict):
                settings[section] = {**settings[section], **value}
            else:
                settings[section] = value

        projects[key] = ProjectConfig(
            key=key,
            title=str(raw["title"]).strip(),
            short_title=str(raw.get("short_title", raw["title"])).strip(),
            slug=str(raw.get("slug", key.upper())).strip(),
            pdf=ROOT / str(raw["pdf"]),
            output_dir=ROOT / str(raw.get("output_dir", f"output/{key}")),
            language=str(raw.get("language", defaults.get("language", "pt-BR"))),
            weeks=weeks,
            settings=settings,
        )
    return defaults, projects


def load_lexicon() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "pronunciation.pt-BR.yaml")


def _validate_weeks(project_key: str, weeks: tuple[WeekConfig, ...]) -> None:
    if not weeks:
        raise ValueError(f"{project_key}: nenhuma semana configurada")
    numbers = [week.week for week in weeks]
    if numbers != list(range(1, len(weeks) + 1)):
        raise ValueError(f"{project_key}: semanas devem ser 1..N, veio {numbers}")
    previous_end = 0
    for week in weeks:
        if week.start_page <= previous_end:
            raise ValueError(f"{project_key}: semana {week.week} começa antes da anterior terminar")
        if week.end_page < week.start_page:
            raise ValueError(f"{project_key}: semana {week.week} tem fim antes do início")
        previous_end = week.end_page


def get_project(projects: dict[str, ProjectConfig], key: str) -> ProjectConfig:
    if key not in projects:
        raise KeyError(f"Projeto desconhecido: {key}. Opções: {', '.join(projects)}")
    return projects[key]


def resolve_projects(projects: dict[str, ProjectConfig], selector: str) -> list[ProjectConfig]:
    if selector == "all":
        return list(projects.values())
    return [get_project(projects, selector)]
