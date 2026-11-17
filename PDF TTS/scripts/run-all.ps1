#requires -Version 5.1
<#
.SYNOPSIS
  Executa o pipeline completo (extract, segment, build, assemble, verify).
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

& $python -m pdf_tts all --project all
if ($LASTEXITCODE -ne 0) { throw "pipeline falhou" }

Write-Host "Pipeline concluido. Veja output\ e manifests\."
