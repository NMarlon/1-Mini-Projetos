"""Testes básicos da API local."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate

import pdf_tts.api as api_module
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
    health = client.get("/api/health").json()
    assert health["ok"] is True
    assert health["app"] == "pathway-pdf-tts"
    defaults = client.get("/api/defaults").json()
    assert defaults["voice"].startswith("pt-BR-")
    assert defaults["rate"] == "-5%"
    assert defaults["profile"] == "auto"


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
            data={"chapter_mode": "auto", "chapter_size": "10", "profile": "auto"},
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    discovery = payload["discovery"]
    assert discovery["total_pages"] == 1
    assert discovery["chapters"]
    assert discovery["text_pages"] == 1
    assert discovery["profile"] == "auto"

    reanalysis = client.post(
        "/api/reanalyze",
        json={"upload_id": payload["upload_id"], "profile": "generic"},
    )
    assert reanalysis.status_code == 200, reanalysis.text
    updated = reanalysis.json()["discovery"]
    assert updated["profile"] == "generic"
    assert updated["chapters"]


def test_rejects_invalid_content_mode(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "modo.pdf")
    client = TestClient(app)
    with pdf.open("rb") as handle:
        response = client.post(
            "/api/analyze",
            files={"file": ("Modo.pdf", handle, "application/pdf")},
        )
    upload_id = response.json()["upload_id"]
    job = client.post(
        "/api/jobs",
        json={
            "upload_id": upload_id,
            "chapter_mode": "auto",
            "content_mode": "invalido",
        },
    )
    assert job.status_code == 400


def test_logs_are_limited_to_known_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(api_module, "LOG_DIR", tmp_path)
    (tmp_path / "app.log").write_text("linha de teste\n", encoding="utf-8")
    client = TestClient(app)
    response = client.get("/api/logs/app.log")
    assert response.status_code == 200
    assert "linha de teste" in response.text
    download = client.get("/api/logs/app.log?download=1")
    assert download.status_code == 200
    assert "attachment" in download.headers["content-disposition"]
    assert client.get("/api/logs/segredo.txt").status_code == 404
