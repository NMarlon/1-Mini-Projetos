#requires -RunAsAdministrator
# Troca a impressora para uma porta TCP/IP RAW (padrao), mais estavel que LPR/WSD.
param(
    [string]$PrinterName = 'L3150 Series(Rede)',
    [string]$Ip = '192.168.0.227',
    [int]$PortNumber = 9100
)
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$reports = Join-Path $root 'reports'
New-Item -ItemType Directory -Force -Path $reports | Out-Null
$log = Join-Path $reports 'set-tcp-port.log'

Start-Transcript -Path $log -Append -Force | Out-Null
try {
    $portName = "IP_$Ip"
    Write-Output "=== TROCANDO PORTA PARA TCP/IP RAW ==="
    Write-Output "Impressora: $PrinterName"
    Write-Output "IP: $Ip : $PortNumber"
    Write-Output "Porta: $portName"

    $existing = Get-PrinterPort -Name $portName -ErrorAction SilentlyContinue
    if (-not $existing) {
        Write-Output "Criando porta $portName..."
        Add-PrinterPort -Name $portName -PrinterHostAddress $Ip -PortNumber $PortNumber
    } else {
        Write-Output "Porta $portName ja existe."
    }

    Write-Output "Apontando a impressora para a nova porta..."
    Set-Printer -Name $PrinterName -PortName $portName

    Start-Sleep -Seconds 2
    Write-Output "=== ESTADO FINAL ==="
    Get-Printer -Name $PrinterName | Select-Object Name, DriverName, PortName, PrinterStatus, JobCount | Format-List
    Get-PrinterPort -Name $portName | Select-Object Name, PrinterHostAddress, PortNumber, Protocol | Format-List
    Write-Output "FIM"
}
catch {
    Write-Output "ERRO: $($_.Exception.Message)"
    throw
}
finally {
    Stop-Transcript | Out-Null
}
