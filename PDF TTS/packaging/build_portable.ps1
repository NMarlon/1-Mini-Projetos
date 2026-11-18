#requires -Version 5.1
<#
.SYNOPSIS
  Gera a pasta portátil dist/PDF TTS e o ZIP para distribuição.
#>
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Crie o ambiente primeiro: .\scripts\setup.ps1"
}

Write-Host "Gerando executável com PyInstaller..."
& $python -m PyInstaller "packaging\pdf_tts.spec" --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

$dist = Join-Path $root "dist\PDF TTS"
if (-not (Test-Path $dist)) { throw "Pasta dist\PDF TTS não foi criada" }

Copy-Item "packaging\LEIA-ME.txt" (Join-Path $dist "LEIA-ME.txt") -Force
New-Item -ItemType Directory -Force -Path (Join-Path $dist "PDFs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist "output") | Out-Null
Set-Content -Path (Join-Path $dist "PDFs\COLOQUE-SEUS-PDFS-AQUI.txt") -Encoding utf8 -Value "Coloque seus PDFs nesta pasta ou arraste-os direto na interface do PDF TTS."

$zip = Join-Path $root "dist\PDF-TTS-Windows.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $dist -DestinationPath $zip -Force

Write-Host ""
Write-Host "Pronto:"
Write-Host "  Pasta: $dist"
Write-Host "  ZIP:   $zip"
