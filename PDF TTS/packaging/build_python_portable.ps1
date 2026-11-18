#requires -Version 5.1
<#
.SYNOPSIS
  Gera uma alternativa portátil usando o Python assinado da máquina.

  Serve para computadores com Smart App Control ativo, que bloqueiam o
  executável criado pelo PyInstaller por ele não ter assinatura digital.
#>
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Crie o ambiente primeiro: .\scripts\setup.ps1" }

$basePython = (& $python -c "import sys; print(sys.base_prefix)").Trim()
if (-not (Test-Path (Join-Path $basePython "pythonw.exe"))) {
    throw "Python base não encontrado em $basePython"
}

$dist = Join-Path $root "dist\Pathway PDF TTS"
if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
New-Item -ItemType Directory -Force -Path $dist | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist "Lib") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist "Lib\site-packages") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist "logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist "output") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist "PDFs") | Out-Null

Write-Host "Copiando runtime Python assinado..."
foreach ($name in @("pythonw.exe", "python311.dll", "python3.dll", "vcruntime140.dll", "vcruntime140_1.dll")) {
    Copy-Item (Join-Path $basePython $name) (Join-Path $dist $name) -Force
}
Move-Item (Join-Path $dist "pythonw.exe") (Join-Path $dist "Pathway PDF TTS.exe")

Write-Host "Copiando DLLs, biblioteca padrão e Tcl/Tk..."
& robocopy (Join-Path $basePython "DLLs") (Join-Path $dist "DLLs") /E /NFL /NDL /NJH /NJS /NP | Out-Null
& robocopy (Join-Path $basePython "tcl") (Join-Path $dist "tcl") /E /NFL /NDL /NJH /NJS /NP | Out-Null
& robocopy (Join-Path $basePython "Lib") (Join-Path $dist "Lib") /E /XD (Join-Path $basePython "Lib\site-packages") (Join-Path $basePython "Lib\test") (Join-Path $basePython "Lib\idlelib") /XF *.pyc /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy da biblioteca padrão falhou ($LASTEXITCODE)" }

Write-Host "Copiando dependências do .venv..."
& robocopy (Join-Path $root ".venv\Lib\site-packages") (Join-Path $dist "Lib\site-packages") /E /XD __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy do site-packages falhou ($LASTEXITCODE)" }
Get-ChildItem (Join-Path $dist "Lib\site-packages") -Filter "__editable__*" -File -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host "Copiando código, config e FFmpeg..."
Copy-Item (Join-Path $root "src") (Join-Path $dist "src") -Recurse -Force
Copy-Item (Join-Path $root "config") (Join-Path $dist "config") -Recurse -Force
foreach ($tool in @("ffmpeg.exe", "ffprobe.exe")) {
    $candidate = Join-Path $root "dist\Pathway PDF TTS (PyInstaller)\_internal\$tool"
    if (-not (Test-Path $candidate)) { $candidate = Join-Path $root "dist\PDF TTS\_internal\$tool" }
    if (-not (Test-Path $candidate)) { $candidate = (Get-Command $tool -ErrorAction SilentlyContinue).Source }
    if ($candidate) { Copy-Item $candidate (Join-Path $dist $tool) -Force }
}

$sitecustomize = @'
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
os.environ["PATH"] = str(_ROOT) + os.pathsep + os.environ.get("PATH", "")

def _is_double_click() -> bool:
    if len(sys.argv) != 1:
        return False
    if sys.argv[0] == "":
        return True
    try:
        return Path(sys.argv[0]).resolve() == Path(sys.executable).resolve()
    except OSError:
        return False


if _is_double_click():
    try:
        from pdf_tts.launcher import run_gui

        code = run_gui()
    except SystemExit:
        raise
    except Exception:
        log_dir = _ROOT / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "launcher-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        code = 1
    os._exit(code)
'@
Set-Content -Path (Join-Path $dist "Lib\site-packages\sitecustomize.py") -Encoding utf8 -Value $sitecustomize

Copy-Item "packaging\LEIA-ME.txt" (Join-Path $dist "LEIA-ME.txt") -Force
Set-Content -Path (Join-Path $dist "PDFs\COLOQUE-SEUS-PDFS-AQUI.txt") -Encoding utf8 -Value "Coloque seus PDFs nesta pasta ou arraste-os direto na interface do Pathway PDF TTS."

$zip = Join-Path $root "dist\Pathway-PDF-TTS-Windows.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $dist -DestinationPath $zip -Force

Write-Host ""
Write-Host "Pronto:"
Write-Host "  Pasta: $dist"
Write-Host "  ZIP:   $zip"
