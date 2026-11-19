#requires -RunAsAdministrator
# Corrige a fila e troca a impressora para TCP/IP RAW 9100, depois imprime um ponto.
$ErrorActionPreference = 'Stop'

$printerName = 'L3150 Series(Rede)'
$ip = '192.168.0.227'
$portName = "IP_$ip"
$root = Split-Path -Parent $PSScriptRoot
$reports = Join-Path $root 'reports'
New-Item -ItemType Directory -Force -Path $reports | Out-Null
$log = Join-Path $reports 'fix-print.log'

Start-Transcript -Path $log -Append -Force | Out-Null
try {
    Write-Output "=== FIX PRINT $(Get-Date -Format 'yyyyMMdd-HHmmss') ==="

    Write-Output "Parando Epson Event Manager (segura o spool)..."
    Get-Process -Name 'EEventManager' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1

    Write-Output "Parando Spooler e limpando fila..."
    Stop-Service -Name Spooler -Force
    (Get-Service Spooler).WaitForStatus('Stopped', '00:00:30')
    $spool = Join-Path $env:SystemRoot 'System32\spool\PRINTERS'
    $backup = Join-Path $reports ("spool-backup-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Force -Path $backup | Out-Null
    Get-ChildItem -Path $spool -File -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Output "Removendo $($_.Name) ($($_.Length) bytes)"
        Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
        if (Test-Path $_.FullName) {
            Move-Item -LiteralPath $_.FullName -Destination $backup -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Service -Name Spooler
    (Get-Service Spooler).WaitForStatus('Running', '00:00:30')
    Start-Sleep -Seconds 2

    Write-Output "Garantindo porta TCP/IP RAW $portName..."
    if (-not (Get-PrinterPort -Name $portName -ErrorAction SilentlyContinue)) {
        Add-PrinterPort -Name $portName -PrinterHostAddress $ip -PortNumber 9100
    }
    Write-Output "Apontando $printerName para $portName..."
    Set-Printer -Name $printerName -PortName $portName
    Start-Sleep -Seconds 2
    Get-Printer -Name $printerName | Select-Object Name, DriverName, PortName, PrinterStatus, JobCount | Format-List

    Write-Output "Imprimindo ponto de teste..."
    Add-Type -AssemblyName System.Drawing
    $doc = New-Object System.Drawing.Printing.PrintDocument
    $doc.PrinterSettings.PrinterName = $printerName
    if (-not $doc.PrinterSettings.IsValid) { throw "PrinterSettings invalido." }
    $a4 = $doc.PrinterSettings.PaperSizes | Where-Object { $_.PaperKind -eq [System.Drawing.Printing.PaperKind]::A4 } | Select-Object -First 1
    if ($a4) { $doc.DefaultPageSettings.PaperSize = $a4 }
    $doc.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0, 0, 0, 0)
    $doc.PrintController = New-Object System.Drawing.Printing.StandardPrintController
    $doc.add_PrintPage({ param($s, $e) $e.Graphics.FillEllipse([System.Drawing.Brushes]::Black, 20, 20, 15, 15) })
    $doc.Print()
    Write-Output "Ponto enviado."

    Start-Sleep -Seconds 8
    Write-Output "=== FILA (8s) ==="
    Get-PrintJob -PrinterName $printerName -ErrorAction SilentlyContinue |
        Select-Object Id, DocumentName, JobStatus, Size | Format-Table -AutoSize
    Start-Sleep -Seconds 10
    Write-Output "=== FILA (18s) ==="
    Get-PrintJob -PrinterName $printerName -ErrorAction SilentlyContinue |
        Select-Object Id, DocumentName, JobStatus, Size | Format-Table -AutoSize
    Get-Printer -Name $printerName | Select-Object Name, PrinterStatus, JobCount | Format-List
    Write-Output "FIM"
}
catch {
    Write-Output "ERRO: $($_.Exception.Message)"
}
finally {
    $svc = Get-Service Spooler -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -ne 'Running') {
        Write-Output "Religando spooler no finally..."
        Start-Service -Name Spooler -ErrorAction SilentlyContinue
    }
    Stop-Transcript | Out-Null
}
