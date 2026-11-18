#requires -Version 5.1
<#
.SYNOPSIS
  Cria o .venv com Python 3.11, instala as dependências e roda o doctor.
#>
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv")) {
    Write-Host "Criando .venv com Python 3.11..."
    py -3.11 -m venv .venv
}

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python do .venv nao encontrado em $python"
}

& $python -m pip install --upgrade pip
$lock = Join-Path $root "requirements.lock.txt"
if (Test-Path $lock) {
    Write-Host "Instalando versões exatas do requirements.lock.txt..."
    & $python -m pip install -r $lock
    & $python -m pip install -e ".[dev]" --no-deps
} else {
    & $python -m pip install -e ".[dev]"
}

Write-Host ""
Write-Host "Ambiente pronto. Rodando doctor..."
& $python -m pdf_tts doctor
