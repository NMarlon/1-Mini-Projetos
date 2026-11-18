"""API local da interface one-click."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Annotated, Any

import edge_tts
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from pdf_tts.config import ROOT, load_projects
from pdf_tts.discover import Discovery, discover_pdf
from pdf_tts.generic import ConvertOptions
from pdf_tts.jobs import JobManager

WEB_DIR = Path(__file__).parent / "web"
UPLOAD_DIR = ROOT / "input" / "uploads"
ANALYSIS_DIR = ROOT / "cache" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="PDF TTS", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
manager = JobManager(ROOT / "cache" / "jobs.db")


class ChapterIn(BaseModel):
    title: str = ""
    start_page: int = Field(ge=1)
    end_page: int = Field(ge=1)


class JobIn(BaseModel):
    upload_id: str
    chapter_mode: str = "auto"
    chapter_size: int = 10
    chapters: list[ChapterIn] | None = None
    content_mode: str = "auto"
    voice: str | None = None
    rate: str | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "version": "0.2.0"}


@app.get("/api/defaults")
def defaults() -> dict[str, Any]:
    project_defaults, _ = load_projects()
    return {
        "voice": project_defaults.get("voice", "pt-BR-FranciscaNeural"),
        "rate": project_defaults.get("rate", "-5%"),
        "chapter_size": 10,
    }


@app.post("/api/analyze")
async def analyze(
    file: Annotated[UploadFile, File()],
    chapter_mode: Annotated[str, Form()] = "auto",
    chapter_size: Annotated[int, Form()] = 10,
) -> dict[str, Any]:
    original = Path(file.filename or "documento.pdf").name
    if not original.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF.")
    upload_id = uuid.uuid4().hex[:12]
    target = UPLOAD_DIR / f"{upload_id}.pdf"
    content = await file.read()
    if len(content) < 1000:
        raise HTTPException(status_code=400, detail="O arquivo parece vazio ou inválido.")
    target.write_bytes(content)
    try:
        discovery = await run_in_threadpool(
            discover_pdf,
            target,
            chapter_mode,
            chapter_size,
            None,
        )
    except Exception as exc:  # noqa: BLE001 - devolvemos mensagem amigável
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Não foi possível ler o PDF: {exc}") from exc
    if (
        not discovery.title
        or len(discovery.title.strip()) < 3
        or discovery.title.strip().isdigit()
        or re.fullmatch(r"[0-9a-f-]{8,}", discovery.title.strip(), re.IGNORECASE)
    ):
        discovery.title = Path(original).stem
    analysis_path = ANALYSIS_DIR / f"{upload_id}.json"
    analysis_path.write_text(
        json.dumps(discovery.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "upload_id": upload_id,
        "filename": original,
        "analysis_path": str(analysis_path),
        "discovery": discovery.to_dict(),
    }


@app.post("/api/jobs")
def create_job(request: JobIn) -> dict[str, Any]:
    pdf_path = UPLOAD_DIR / f"{request.upload_id}.pdf"
    analysis_path = ANALYSIS_DIR / f"{request.upload_id}.json"
    if not pdf_path.exists() or not analysis_path.exists():
        raise HTTPException(status_code=404, detail="Upload não encontrado; envie o PDF novamente.")
    discovery = Discovery.from_dict(json.loads(analysis_path.read_text(encoding="utf-8")))
    manual = None
    chapter_mode = request.chapter_mode
    if chapter_mode == "manual":
        if not request.chapters:
            raise HTTPException(status_code=400, detail="Informe os capítulos manuais.")
        manual = [chapter.model_dump() for chapter in request.chapters]
    options = ConvertOptions(
        chapter_mode=chapter_mode,
        chapter_size=request.chapter_size,
        manual_chapters=manual,
        content_mode=request.content_mode,
        voice=request.voice,
        rate=request.rate,
    )
    job_id = manager.create(pdf_path, analysis_path, discovery, options)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    result = dict(job)
    result.pop("options_json", None)
    result.pop("coverage_json", None)
    options = json.loads(job.get("options_json") or "{}")
    result["options"] = options
    try:
        result["coverage"] = json.loads(job.get("coverage_json") or "null")
    except json.JSONDecodeError:
        result["coverage"] = None
    output_dir = job.get("output_dir")
    if output_dir and Path(output_dir).exists():
        result["files"] = sorted(path.name for path in Path(output_dir).glob("*.mp3"))
        result["files"] += sorted(path.name for path in Path(output_dir).glob("*.m4b"))
        result["files"] += sorted(path.name for path in Path(output_dir).glob("*.srt"))
    else:
        result["files"] = []
    return result


@app.get("/api/jobs")
def list_jobs() -> dict[str, Any]:
    jobs = []
    for job in manager.list():
        jobs.append(
            {
                "id": job["id"],
                "pdf_name": job["pdf_name"],
                "title": job["title"],
                "status": job["status"],
                "stage": job["stage"],
                "current": job["current"],
                "total": job["total"],
                "created_at": job["created_at"],
                "output_dir": job["output_dir"],
            }
        )
    return {"jobs": jobs}


@app.post("/api/open-folder")
def open_folder(payload: dict[str, str]) -> dict[str, Any]:
    job_id = payload.get("job_id", "")
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    output_dir = job.get("output_dir")
    if not output_dir or not Path(output_dir).exists():
        raise HTTPException(status_code=404, detail="A pasta de saída ainda não existe.")
    path = Path(output_dir).resolve()
    output_root = (ROOT / "output").resolve()
    if output_root not in path.parents and path != output_root:
        raise HTTPException(status_code=400, detail="Pasta fora da área permitida.")
    if os.name == "nt":
        os.startfile(str(path))  # noqa: S606 - caminho validado e local
    else:
        raise HTTPException(status_code=400, detail="Abrir pasta é suportado apenas no Windows.")
    return {"ok": True, "path": str(path)}


@app.get("/api/voices")
async def voices() -> dict[str, Any]:
    try:
        catalog = await edge_tts.list_voices()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Edge TTS indisponível: {exc}") from exc
    pt_br = [
        {
            "name": voice.get("ShortName"),
            "gender": voice.get("Gender"),
            "locale": voice.get("Locale"),
        }
        for voice in catalog
        if str(voice.get("Locale", "")).lower() == "pt-br"
    ]
    return {"voices": sorted(pt_br, key=lambda item: str(item["name"]))}
