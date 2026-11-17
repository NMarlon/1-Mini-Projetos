"""Testes de configuração (sem depender dos PDFs)."""

from __future__ import annotations

from pdf_tts.config import load_lexicon, load_projects, load_settings, resolve_projects


def test_projects_load() -> None:
    _, projects = load_projects()
    assert set(projects) == {"mkt120", "com150"}
    for project in projects.values():
        assert len(project.weeks) == 7
        assert [week.week for week in project.weeks] == list(range(1, 8))
        assert project.weeks[0].start_page < project.weeks[-1].end_page
        assert project.title
        assert project.slug


def test_week_lookup() -> None:
    _, projects = load_projects()
    project = projects["mkt120"]
    assert project.week("S01").week == 1
    assert project.week(7).title == "Estratégia de Vendas"


def test_resolve_projects() -> None:
    _, projects = load_projects()
    assert len(resolve_projects(projects, "all")) == 2
    assert resolve_projects(projects, "mkt120")[0].key == "mkt120"


def test_settings_and_lexicon() -> None:
    settings = load_settings()
    assert settings["chunking"]["max_chars"] >= settings["chunking"]["min_chars"]
    lexicon = load_lexicon()
    assert lexicon["replacements"]
    patterns = [item["pattern"] for item in lexicon["replacements"]]
    assert any("SWOT" in pattern for pattern in patterns)
