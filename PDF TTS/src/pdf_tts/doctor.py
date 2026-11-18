"""Verificação de ambiente e insumos."""

from __future__ import annotations

import asyncio
import hashlib
import importlib.metadata
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess

from pdf_tts.audio import run_hidden
from pdf_tts.config import ROOT, ProjectConfig, load_projects

EXPECTED_PDFS = {
    "mkt120": "EA08D740BCC68EC1317AD3CE8D1C6A5C07A706C9821F1E62C02062FDAAC242F1",
    "com150": "ACA653AC0049D373DF3ECCE00C24E026ECC4808FFF67F8DFD712D2BCF3C7DD42",
}

VOICE_PRIMARY = "pt-BR-FranciscaNeural"
MIN_FREE_BYTES = 3 * 1024**3  # 3 GB


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    critical: bool = True


def _run(command: list[str], timeout: int = 30) -> CompletedProcess[str]:
    return run_hidden(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def find_tool(name: str, env_var: str | None = None) -> str | None:
    if env_var and os.environ.get(env_var):
        candidate = Path(os.environ[env_var])
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def check_python() -> Check:
    version = sys.version_info
    ok = version.major == 3 and version.minor == 11
    return Check(
        "Python 3.11",
        ok,
        f"{version.major}.{version.minor}.{version.micro} em {sys.executable}",
    )


def check_ffmpeg() -> list[Check]:
    checks: list[Check] = []
    ffmpeg = find_tool("ffmpeg", "FFMPEG_BIN")
    ffprobe = find_tool("ffprobe", "FFPROBE_BIN")
    checks.append(Check("ffmpeg", bool(ffmpeg), ffmpeg or "não encontrado no PATH"))
    checks.append(Check("ffprobe", bool(ffprobe), ffprobe or "não encontrado no PATH"))

    if ffmpeg:
        result = _run([ffmpeg, "-version"])
        first_line = (result.stdout or result.stderr).splitlines()[0] if result.returncode == 0 else "falha"
        checks.append(Check("ffmpeg versão", result.returncode == 0, first_line, critical=False))
        encoders = _run([ffmpeg, "-hide_banner", "-encoders"])
        text = (encoders.stdout or "") + (encoders.stderr or "")
        checks.append(Check("codec libmp3lame", "libmp3lame" in text, "MP3"))
        checks.append(Check("codec AAC", " aac " in text or "\naac" in text, "M4B"))
    return checks


def check_python_packages() -> list[Check]:
    checks: list[Check] = []
    for package, label, critical in [
        ("edge-tts", "edge-tts", True),
        ("pdfplumber", "pdfplumber", True),
        ("pypdf", "pypdf", False),
        ("pypdfium2", "pypdfium2 (capa)", False),
        ("num2words", "num2words", True),
        ("PyYAML", "PyYAML", True),
    ]:
        try:
            version = importlib.metadata.version(package)
            checks.append(Check(label, True, version, critical=critical))
        except importlib.metadata.PackageNotFoundError:
            checks.append(Check(label, False, "não instalado", critical=critical))
    return checks


def check_edge_voices() -> list[Check]:
    checks: list[Check] = []
    try:
        import edge_tts

        voices = asyncio.run(edge_tts.list_voices())
    except Exception as exc:  # noqa: BLE001 - queremos mostrar qualquer falha de rede
        return [Check("Edge TTS catálogo", False, f"{type(exc).__name__}: {exc}")]

    pt_br = [v for v in voices if str(v.get("Locale", "")).lower() == "pt-br"]
    names = sorted(str(v.get("ShortName", "")) for v in pt_br)
    checks.append(Check("Edge TTS catálogo", True, f"{len(voices)} vozes, {len(pt_br)} pt-BR"))
    checks.append(
        Check(
            "Voz principal",
            VOICE_PRIMARY in names,
            f"{VOICE_PRIMARY} {'disponível' if VOICE_PRIMARY in names else 'AUSENTE'}; pt-BR: {', '.join(names)}",
        )
    )
    return checks


def check_pdfs(projects: dict[str, ProjectConfig]) -> list[Check]:
    checks: list[Check] = []
    for key, project in projects.items():
        path = project.pdf
        if not path.exists():
            checks.append(
                Check(
                    f"PDF {key}",
                    False,
                    f"não encontrado: {path.relative_to(ROOT)} (veja input/README.md)",
                )
            )
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        expected = EXPECTED_PDFS.get(key)
        ok = expected is None or digest == expected
        detail = f"{size:,} bytes; sha256={digest[:12]}…"
        if expected and not ok:
            detail += f"; ESPERADO {expected[:12]}…"
        checks.append(Check(f"PDF {key}", ok, detail))
    return checks


def check_dirs(projects: dict[str, ProjectConfig]) -> list[Check]:
    checks: list[Check] = []
    for name, path in [
        ("content/", ROOT / "content"),
        ("cache/", ROOT / "cache"),
        ("output/", ROOT / "output"),
        ("manifests/", ROOT / "manifests"),
    ]:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            checks.append(Check(f"Escrita {name}", True, str(path.relative_to(ROOT))))
        except OSError as exc:
            checks.append(Check(f"Escrita {name}", False, str(exc)))
    for project in projects.values():
        project.output_dir.mkdir(parents=True, exist_ok=True)
    return checks


def check_disk() -> Check:
    usage = shutil.disk_usage(ROOT)
    ok = usage.free >= MIN_FREE_BYTES
    return Check(
        "Espaço em disco",
        ok,
        f"{usage.free / 1024**3:.1f} GB livres (mínimo 3 GB)",
        critical=True,
    )


def run_doctor() -> int:
    _, projects = load_projects()
    checks: list[Check] = []
    checks.append(check_python())
    checks.extend(check_ffmpeg())
    checks.extend(check_python_packages())
    checks.extend(check_edge_voices())
    checks.extend(check_pdfs(projects))
    checks.extend(check_dirs(projects))
    checks.append(check_disk())

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="PDF TTS — doctor")
        table.add_column("OK", justify="center", width=3)
        table.add_column("Verificação", style="bold")
        table.add_column("Detalhe")
        for check in checks:
            mark = "[green]✓[/green]" if check.ok else ("[red]✗[/red]" if check.critical else "[yellow]![/yellow]")
            table.add_row(mark, check.name, check.detail)
        console.print(table)
    except Exception:  # noqa: BLE001 - fallback sem rich
        for check in checks:
            mark = "OK " if check.ok else ("ERRO" if check.critical else "AVISO")
            print(f"[{mark}] {check.name}: {check.detail}")

    failures = [check for check in checks if not check.ok and check.critical]
    warnings = [check for check in checks if not check.ok and not check.critical]
    if warnings:
        print(f"\n{len(warnings)} aviso(s) não crítico(s).")
    if failures:
        print(f"\n{len(failures)} verificação(ões) crítica(s) falharam:")
        for failure in failures:
            print(f"  - {failure.name}: {failure.detail}")
        return 1
    print("\nAmbiente OK.")
    return 0
