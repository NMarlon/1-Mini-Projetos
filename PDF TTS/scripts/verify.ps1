#requires -Version 5.1
<#
.SYNOPSIS
  Verifica os arquivos finais (MP3/M4B/SRT/capítulos/loudness).
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
& $python -m pdf_tts verify --project all
