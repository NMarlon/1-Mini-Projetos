# ======================================================================
# Remover-Autostart.ps1
#
# O QUE FAZ:
#   Remove a Tarefa Agendada "Hermes Mobile - Servidor", o atalho da
#   area de trabalho e o fallback da pasta Startup.
#   NAO para o servidor em execucao.
#
# QUANDO RODAR: rollback / desinstalacao.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Remover-Autostart.ps1
# ======================================================================

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\common.ps1"

Write-Head "Remover autostart"

$taskName = 'Hermes Mobile - Servidor'
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop
    Write-Ok ("Tarefa removida: {0}" -f $taskName)
} else {
    Write-Ok "Tarefa nao existia."
}

$desktop = [Environment]::GetFolderPath('Desktop')
$desktopLnk = Join-Path $desktop 'Hermes Mobile.lnk'
if (Test-Path -LiteralPath $desktopLnk) {
    Remove-Item -LiteralPath $desktopLnk -Force
    Write-Ok "Atalho da area de trabalho removido."
}

$startup = [Environment]::GetFolderPath('Startup')
$startupLnk = Join-Path $startup 'Hermes Mobile.lnk'
if (Test-Path -LiteralPath $startupLnk) {
    Remove-Item -LiteralPath $startupLnk -Force
    Write-Ok "Atalho da pasta Startup removido."
}

$vbs = Join-Path (Get-HermesMobileDir) 'Iniciar-HermesMobile.vbs'
if (Test-Path -LiteralPath $vbs) {
    Remove-Item -LiteralPath $vbs -Force
    Write-Ok "VBS de fallback removido."
}

Write-Ok "Autostart removido. O servidor atual continua rodando."
