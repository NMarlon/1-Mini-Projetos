#requires -Version 5.1
<#
.SYNOPSIS
  Executa o pipeline completo, retomando de onde parou.
#>
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Crie o ambiente primeiro: .\scripts\setup.ps1"
}

Set-Location $root

& $python -m pdf_tts doctor
if ($LASTEXITCODE -ne 0) { throw "doctor falhou" }

& $python -m pdf_tts extract --project all
if ($LASTEXITCODE -ne 0) { throw "extract falhou" }

& $python -m pdf_tts segment --project all
if ($LASTEXITCODE -ne 0) { throw "segment falhou" }

& $python -m pdf_tts samples
if ($LASTEXITCODE -ne 0) { throw "samples falhou" }

& $python -m pdf_tts build --project mkt120 --lesson S01
if ($LASTEXITCODE -ne 0) { throw "build S01 falhou" }

& $python -m pdf_tts all --project all --resume
if ($LASTEXITCODE -ne 0) { throw "build completo falhou" }

Write-Host "Pipeline concluido. Veja output\ e manifests\."
