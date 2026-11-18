"""Testes básicos da API local."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate

from pdf_tts.api import app


def _pdf(path: Path) -> Path:
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("H", parent=styles["Heading1"], fontSize=24, leading=30)
    body = ParagraphStyle("B", parent=styles["BodyText"], fontSize=11, leading=15)
    document = SimpleDocTemplate(str(path), pagesize=A4)
    document.build(
        [
            Paragraph("Capítulo 1 — Abertura", heading),
            Paragraph("Este é um texto de teste com conteúdo suficiente para extração.", body),
        ]
    )
    return path


def test_health_and_defaults() -> None:
    client = TestClient(app)
    assert client.get("/api/health").json()["ok"] is True
    defaults = client.get("/api/defaults").json()
    assert defaults["voice"].startswith("pt-BR-")
    assert defaults["rate"] == "-5%"


def test_index_and_assets() -> None:
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_analyze_pdf(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "teste.pdf")
    client = TestClient(app)
    with pdf.open("rb") as handle:
        response = client.post(
            "/api/analyze",
            files={"file": ("Teste.pdf", handle, "application/pdf")},
            data={"chapter_mode": "auto", "chapter_size": "10"},
        )
    assert response.status_code == 200, response.text
    discovery = response.json()["discovery"]
    assert discovery["total_pages"] == 1
    assert discovery["chapters"]
    assert discovery["text_pages"] == 1
