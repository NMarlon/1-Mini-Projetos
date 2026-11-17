# ======================================================================
# Manter-Acordado.ps1
#
# O QUE FAZ:
#   OPCAO MANUAL: evita suspensao/hibernacao quando o PC esta na tomada.
#   NAO e executado automaticamente (decisao do Marlon em 16/11/2026).
#
# QUANDO RODAR: somente se o Marlon pedir explicitamente.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Manter-Acordado.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\Manter-Acordado.ps1 -Ativar
#   powershell -ExecutionPolicy Bypass -File .\scripts\Manter-Acordado.ps1 -Reverter
# ======================================================================

[CmdletBinding()]
param(
    [switch]$Ativar,
    [switch]$Reverter,
    [switch]$Sim
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\common.ps1"

$backupPath = Join-Path (Get-HermesMobileDir) 'energia-backup.json'

function Get-AcValueMinutes {
    param([string]$SubSetting)
    try {
        $out = (& powercfg.exe /query SCHEME_CURRENT SUB_SLEEP $SubSetting 2>$null | Out-String)
        $m = [regex]::Match($out, 'Current AC Power Setting Index:\s*0x([0-9A-Fa-f]+)')
        if ($m.Success) {
            $seconds = [Convert]::ToInt32($m.Groups[1].Value, 16)
            return [int]($seconds / 60)
        }
    } catch { }
    return $null
}

function Set-AcTimeout {
    param([string]$Setting, [int]$Minutes)
    & powercfg.exe /change "$Setting" "$Minutes" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "powercfg falhou para $Setting=$Minutes (exit $LASTEXITCODE)."
    }
}

Write-Head "Energia (opcional)"

if ($Reverter) {
    if (-not (Test-Path -LiteralPath $backupPath)) {
        Write-Err2 "Backup nao encontrado: $backupPath"
        exit 1
    }
    $bk = Get-Content -LiteralPath $backupPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Step ("Restaurando standby={0} min, hibernate={1} min..." -f $bk.standby_min, $bk.hibernate_min)
    Set-AcTimeout -Setting 'standby-timeout-ac' -Minutes ([int]$bk.standby_min)
    Set-AcTimeout -Setting 'hibernate-timeout-ac' -Minutes ([int]$bk.hibernate_min)
    Write-Ok "Valores restaurados."
    exit 0
}

$standby = Get-AcValueMinutes -SubSetting 'STANDBYIDLE'
$hibernate = Get-AcValueMinutes -SubSetting 'HIBERNATEIDLE'

Write-Host ("Standby AC atual : {0} min" -f $standby)
Write-Host ("Hibernate AC atual: {0} min" -f $hibernate)

if (-not $Ativar) {
    Write-Host ""
    Write-Host "Nada alterado. Use -Ativar para desativar a suspensao na tomada."
    Write-Host "Ou -Reverter para restaurar um backup anterior."
    exit 0
}

if (-not $Sim) {
    $r = Read-Host "Desativar suspensao/hibernacao SOMENTE na tomada? (s/N)"
    if ($r -notmatch '^[sSyY]') {
        Write-Ok "Cancelado."
        exit 0
    }
}

# Backup
$data = [ordered]@{
    standby_min   = $standby
    hibernate_min = $hibernate
    created_at    = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    computer      = $env:COMPUTERNAME
}
Ensure-Dir (Get-HermesMobileDir) | Out-Null
Write-TextNoBom -Path $backupPath -Content (($data | ConvertTo-Json -Depth 3) + "`r`n")
Write-Ok ("Backup salvo em: {0}" -f $backupPath)

Set-AcTimeout -Setting 'standby-timeout-ac' -Minutes 0
Set-AcTimeout -Setting 'hibernate-timeout-ac' -Minutes 0

Write-Ok "Suspensao/hibernacao desativadas na tomada."
Write-Host "A bateria nao foi alterada."
Write-Host "Para reverter: -Reverter"
