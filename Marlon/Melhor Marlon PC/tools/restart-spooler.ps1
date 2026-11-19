#requires -RunAsAdministrator
# Reinicia o spooler e tenta limpar a fila travada com seguranca.
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
$reports = Join-Path $root 'reports'
New-Item -ItemType Directory -Force -Path $reports | Out-Null
$log = Join-Path $reports 'spool-restart.log'

Start-Transcript -Path $log -Append -Force | Out-Null
try {
    Write-Output "=== RESTART SPOOLER $(Get-Date -Format 'yyyyMMdd-HHmmss') ==="

    Write-Output "Garantindo spooler iniciado..."
    Start-Service -Name Spooler -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Output "Spooler: $((Get-Service Spooler).Status)"

    Write-Output "Parando helpers da Epson que podem segurar o spool..."
    foreach ($svc in 'EpsonCustomerResearchParticipation') {
        $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
        if ($s -and $s.Status -eq 'Running') {
            Write-Output "Parando servico $svc"
            Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
        }
    }
    foreach ($proc in 'EPCP','EEM','EEventManager','EpsonStatusMonitor3','EpsonStatusMonitor') {
        Get-Process -Name $proc -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Output "Parando processo $($_.ProcessName) ($($_.Id))"
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Output "Parando Spooler..."
    Stop-Service -Name Spooler -Force
    (Get-Service Spooler).WaitForStatus('Stopped', '00:00:30')
    Start-Sleep -Seconds 2

    $spool = Join-Path $env:SystemRoot 'System32\spool\PRINTERS'
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup = Join-Path $reports "spool-backup-$stamp"
    New-Item -ItemType Directory -Force -Path $backup | Out-Null

    $files = Get-ChildItem -Path $spool -File -ErrorAction SilentlyContinue
    if ($files) {
        foreach ($f in $files) {
            Write-Output "Removendo $($f.Name) ($($f.Length) bytes)"
            Remove-Item -LiteralPath $f.FullName -Force -ErrorAction SilentlyContinue
            if (Test-Path $f.FullName) {
                Write-Output "  ainda existe; tentando mover para backup"
                Move-Item -LiteralPath $f.FullName -Destination $backup -Force -ErrorAction SilentlyContinue
            }
        }
    } else {
        Write-Output "Spool vazio."
    }

    Write-Output "Iniciando Spooler..."
    Start-Service -Name Spooler
    (Get-Service Spooler).WaitForStatus('Running', '00:00:30')
    Start-Sleep -Seconds 3

    Write-Output "=== ESTADO FINAL ==="
    Get-Service Spooler | Select-Object Name, Status, StartType | Format-List
    Get-Printer | Select-Object Name, DriverName, PortName, PrinterStatus, JobCount | Format-Table -AutoSize
    Get-PrintJob -PrinterName 'L3150 Series(Rede)' -ErrorAction SilentlyContinue |
        Select-Object Id, DocumentName, JobStatus, Size | Format-Table -AutoSize
    Write-Output "FIM"
}
catch {
    Write-Output "ERRO: $($_.Exception.Message)"
}
finally {
    # Nunca deixar o spooler parado
    $svc = Get-Service Spooler -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -ne 'Running') {
        Write-Output "Garantindo spooler no finally..."
        Start-Service -Name Spooler -ErrorAction SilentlyContinue
    }
    Stop-Transcript | Out-Null
}
