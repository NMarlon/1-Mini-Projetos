#Requires -Version 5.1
<#
.SYNOPSIS
    Compacta o banco de sessoes do OpenCode com backup previo.

.DESCRIPTION
    Para o servico do OpenCode, cria um backup compacto via VACUUM INTO,
    executa VACUUM no banco principal, valida a integridade e reinicia o
    servico. Nenhuma sessao e apagada.

.NOTES
    Execute em um PowerShell separado, com o OpenCode fechado.
#>
[CmdletBinding()]
param(
    [string]$DbPath = (Join-Path $HOME ".local\share\opencode\opencode.db"),
    [string]$BackupDir = "",
    [switch]$DryRun,
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ([string]::IsNullOrWhiteSpace($BackupDir)) {
    $BackupDir = Join-Path $PSScriptRoot "backups"
}

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "OK  $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "!!  $Message" -ForegroundColor Yellow
}

function Get-SizeMB([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        return [math]::Round(((Get-Item -LiteralPath $Path).Length / 1MB), 1)
    }
    return 0
}

function Format-MB([double]$Value) {
    return ("{0:N1} MB" -f $Value)
}

function Invoke-Sqlite {
    param(
        [Parameter(Mandatory = $true)][string]$Sqlite,
        [Parameter(Mandatory = $true)][string]$Database,
        [Parameter(Mandatory = $true)][string]$Sql,
        [switch]$ReadOnly
    )
    $sqliteArgs = @()
    if ($ReadOnly) {
        $sqliteArgs += "-readonly"
    }
    $sqliteArgs += $Database
    $sqliteArgs += $Sql
    $output = & $Sqlite @sqliteArgs 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "sqlite3 falhou (codigo $LASTEXITCODE): $($output | Out-String)"
    }
    return ($output | Out-String).Trim()
}

$db = (Resolve-Path -LiteralPath $DbPath -ErrorAction Stop).Path
$dbSizeBytes = (Get-Item -LiteralPath $db).Length
$walPath = "$db-wal"
$shmPath = "$db-shm"

Write-Host "OpenCode - compactacao segura do banco de sessoes" -ForegroundColor White
Write-Host "Banco: $db"
Write-Host ("Tamanho atual: {0:N1} MB" -f ($dbSizeBytes / 1MB))
$walMB = Format-MB (Get-SizeMB $walPath)
$shmMB = Format-MB (Get-SizeMB $shmPath)
Write-Host ("WAL: {0} | SHM: {1}" -f $walMB, $shmMB)

$sqliteCmd = Get-Command sqlite3.exe -ErrorAction SilentlyContinue
if (-not $sqliteCmd) {
    throw "sqlite3.exe nao encontrado no PATH. Instale o SQLite ou ajuste o PATH."
}
$sqlite = $sqliteCmd.Source
Write-Host "sqlite3: $sqlite"

$driveName = (Get-Item -LiteralPath $db).PSDrive.Name
$freeBytes = (Get-PSDrive -Name $driveName).Free
Write-Host ("Espaco livre em {0}: {1:N1} GB" -f $driveName, ($freeBytes / 1GB))
if ($freeBytes -lt 2GB) {
    throw "Espaco livre insuficiente (minimo 2 GB para backup + compactacao)."
}

$pageSize = [int](Invoke-Sqlite -Sqlite $sqlite -Database $db -Sql "PRAGMA page_size;" -ReadOnly)
$pageCount = [int](Invoke-Sqlite -Sqlite $sqlite -Database $db -Sql "PRAGMA page_count;" -ReadOnly)
$freePages = [int](Invoke-Sqlite -Sqlite $sqlite -Database $db -Sql "PRAGMA freelist_count;" -ReadOnly)
$liveBytes = ($pageCount - $freePages) * $pageSize
$freePgBytes = $freePages * $pageSize
$freePgMB = Format-MB ($freePgBytes / 1MB)
$liveMB = Format-MB ($liveBytes / 1MB)
Write-Host ("Paginas: {0:N0} | livres: {1:N0} ({2})" -f $pageCount, $freePages, $freePgMB)
Write-Host ("Estimativa apos VACUUM: {0}" -f $liveMB)

$opencodeCmd = Get-Command opencode -ErrorAction SilentlyContinue
$serviceWasRunning = $false
if ($opencodeCmd) {
    $statusText = (& $opencodeCmd.Source service status 2>&1 | Out-String)
    if ($statusText -match "https?://") {
        $serviceWasRunning = $true
        Write-Host "Servico em execucao: $($statusText.Trim())"
    }
    else {
        Write-Host "Servico parado."
    }
}
else {
    Write-Warn "CLI 'opencode' nao encontrado; o servico nao sera reiniciado automaticamente."
}

$procNames = @("OpenCode", "opencode-cli", "opencode")
$running = @(Get-Process -Name $procNames -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    Write-Warn "Processos do OpenCode em execucao:"
    $running | Select-Object Id, ProcessName | Format-Table -AutoSize | Out-Host
    if (-not $opencodeCmd) {
        throw "Ha processos do OpenCode abertos e a CLI 'opencode' nao foi encontrada. Feche tudo e tente novamente."
    }
    Write-Warn "Feche a TUI/app. O script vai parar o servico de fundo e exigir zero processos antes do VACUUM."
}
else {
    Write-Ok "Nenhum processo do OpenCode em execucao."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = Join-Path $BackupDir "opencode-$stamp.db"

if ($DryRun) {
    Write-Step "Simulacao (-DryRun)"
    Write-Host "Backup seria criado em: $backupPath"
    Write-Host "Comandos que seriam executados:"
    Write-Host "  opencode service stop"
    $backupSqlPreview = $backupPath.Replace("\", "/")
    Write-Host "  sqlite3 `"$db`" `"VACUUM INTO '$backupSqlPreview';`""
    Write-Host "  sqlite3 `"$db`" `"VACUUM;`""
    Write-Host "  sqlite3 `"$db`" `"PRAGMA wal_checkpoint(TRUNCATE);`""
    Write-Host "  opencode service start"
    Write-Host ""
    Write-Host "Nada foi alterado."
    return
}

if (-not $Yes) {
    Write-Host ""
    Write-Host "ATENCAO: o OpenCode deve estar fechado. O script vai parar o servico," -ForegroundColor Yellow
    Write-Host "criar um backup e compactar o banco. Nenhuma sessao sera apagada." -ForegroundColor Yellow
    $answer = Read-Host "Digite VACUUM para continuar"
    if ($answer -ne "VACUUM") {
        Write-Host "Cancelado."
        return
    }
}

$serviceStopped = $false
try {
    if ($serviceWasRunning) {
        Write-Step "Parando o servico do OpenCode"
        & $opencodeCmd.Source service stop | Out-Host
        $serviceStopped = $true
        Start-Sleep -Seconds 2
    }

    for ($i = 0; $i -lt 20; $i++) {
        $still = @(Get-Process -Name $procNames -ErrorAction SilentlyContinue)
        if ($still.Count -eq 0) {
            break
        }
        Start-Sleep -Seconds 1
    }
    $still = @(Get-Process -Name $procNames -ErrorAction SilentlyContinue)
    if ($still.Count -gt 0) {
        throw "Ainda ha processos do OpenCode em execucao. Feche-os e tente novamente."
    }
    Write-Ok "Nenhum processo usando o banco."

    Write-Step "Criando backup compacto"
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    $backupSqlPath = $backupPath.Replace("\", "/").Replace("'", "''")
    Invoke-Sqlite -Sqlite $sqlite -Database $db -Sql "VACUUM INTO '$backupSqlPath';" | Out-Null
    if (-not (Test-Path -LiteralPath $backupPath)) {
        throw "O backup nao foi criado em $backupPath"
    }
    $backupSize = Get-SizeMB $backupPath
    Write-Ok ("Backup criado: {0} ({1:N1} MB)" -f $backupPath, $backupSize)

    Write-Step "Validando o backup"
    $backupCheck = Invoke-Sqlite -Sqlite $sqlite -Database $backupPath -Sql "PRAGMA integrity_check;" -ReadOnly
    if ($backupCheck -ne "ok") {
        throw "Falha na validacao do backup: $backupCheck"
    }
    Write-Ok "Backup integro."

    Write-Step "Compactando o banco principal"
    Invoke-Sqlite -Sqlite $sqlite -Database $db -Sql "PRAGMA wal_checkpoint(TRUNCATE);" | Out-Null
    Invoke-Sqlite -Sqlite $sqlite -Database $db -Sql "VACUUM;" | Out-Null
    Invoke-Sqlite -Sqlite $sqlite -Database $db -Sql "PRAGMA wal_checkpoint(TRUNCATE);" | Out-Null
    $check = Invoke-Sqlite -Sqlite $sqlite -Database $db -Sql "PRAGMA integrity_check;" -ReadOnly
    if ($check -ne "ok") {
        throw "Falha na validacao do banco principal: $check"
    }
    Write-Ok "Banco principal integro."

    $newSizeBytes = (Get-Item -LiteralPath $db).Length
    $newFreePages = [int](Invoke-Sqlite -Sqlite $sqlite -Database $db -Sql "PRAGMA freelist_count;" -ReadOnly)
    $savedMB = ($dbSizeBytes - $newSizeBytes) / 1MB
    Write-Step "Resultado"
    Write-Host ("Antes:  {0:N1} MB" -f ($dbSizeBytes / 1MB))
    Write-Host ("Depois: {0:N1} MB" -f ($newSizeBytes / 1MB))
    Write-Host ("Economia: {0:N1} MB" -f $savedMB) -ForegroundColor Green
    Write-Host ("Paginas livres restantes: {0:N0}" -f $newFreePages)
    $walAfterMB = Format-MB (Get-SizeMB $walPath)
    Write-Host ("WAL depois: {0}" -f $walAfterMB)
    Write-Host ""
    Write-Host "Backup guardado em: $backupPath" -ForegroundColor Yellow
    Write-Host "Nao apague o backup antes de abrir o OpenCode e conferir o historico." -ForegroundColor Yellow
}
catch {
    Write-Host ""
    Write-Host "ERRO: $_" -ForegroundColor Red
    if ($backupPath -and (Test-Path -LiteralPath $backupPath)) {
        Write-Host "Backup disponivel em: $backupPath" -ForegroundColor Yellow
    }
    exit 1
}
finally {
    if ($serviceStopped -and $opencodeCmd) {
        Write-Step "Reiniciando o servico do OpenCode"
        try {
            & $opencodeCmd.Source service start | Out-Host
            Write-Ok "Servico reiniciado."
        }
        catch {
            Write-Warn "Nao foi possivel reiniciar o servico. Rode: opencode service start"
        }
    }
}
