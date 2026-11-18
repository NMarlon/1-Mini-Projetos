# ======================================================================
# Iniciar-Servidor.ps1
#
# O QUE FAZ:
#   Garante que o `hermes serve` esteja rodando em 127.0.0.1:<Porta>.
#   - Modo normal: sobe em background e volta.
#   - Modo -Foreground: bloqueia (usado pela Tarefa Agendada, para o
#     Task Scheduler poder reiniciar se cair).
#
# QUANDO RODAR:
#   - Dia a dia: Iniciar-Mobile.ps1 (que chama este).
#   - Autostart: Tarefa Agendada chama com -Foreground.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Servidor.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Servidor.ps1 -Porta 9121
#   powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Servidor.ps1 -Foreground
# ======================================================================

[CmdletBinding()]
param(
    [int]$Porta = 80,
    [switch]$Foreground
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\common.ps1"

Write-Head "Servidor Hermes (porta $Porta)"

$existing = Get-ServerProcessOnPort -Port $Porta
if ($existing) {
    $isHermes = ($existing.CommandLine -match 'hermes') -and ($existing.CommandLine -match 'serve')
    if ($isHermes) {
        Write-Ok ("Ja esta rodando na porta {0} (PID {1})." -f $Porta, $existing.Pid)
        exit 0
    }
    Write-Err2 ("A porta {0} esta ocupada pelo PID {1} ({2}), que nao parece ser o hermes serve." -f $Porta, $existing.Pid, $existing.Name)
    Write-Host "Nao vou parar esse processo. Use outra porta com -Porta."
    exit 1
}

$exe = Get-HermesExe
if (-not $exe) {
    Write-Err2 "hermes.exe nao encontrado."
    exit 1
}

$logsDir = Ensure-Dir (Join-Path (Get-ProjectRoot) 'logs')
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

if ($Foreground) {
    Write-Step "Rodando em foreground (a Tarefa Agendada mantem este processo)."
    $taskLog = Join-Path $logsDir ("task-servidor-{0}.log" -f $stamp)
    $header = "=== Hermes Mobile task ===`r`nData: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`r`nExe: $exe`r`nPorta: $Porta`r`n"
    Write-TextNoBom -Path $taskLog -Content $header
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $exe serve --host 127.0.0.1 --port $Porta --skip-build *> $taskLog
    } finally {
        $ErrorActionPreference = $prev
    }
    exit $LASTEXITCODE
}

Write-Step "Subindo em background (processo destacado)..."
$started = Start-HermesServeDetached -Port $Porta
Write-Step ("VBS: {0}" -f $started.Vbs)

Write-Step "Aguardando /api/status..."
$code = Wait-Http -Url "http://127.0.0.1:$Porta/api/status" -TimeoutSeconds 60

if (-not $code) {
    Write-Err2 "O servidor nao respondeu em 60s."
    Write-Host "Veja os logs do Hermes:"
    Write-Host ("  {0}\logs" -f (Get-HermesHome))
    try {
        $tail = Invoke-Hermes -Arguments @('logs', '--since', '5m')
        if ($tail) { Write-Host $tail }
    } catch { }
    exit 1
}

$srv = Get-ServerProcessOnPort -Port $Porta
if ($srv) {
    Write-Ok ("Servidor ativo: http://127.0.0.1:{0} (PID {1})." -f $Porta, $srv.Pid)
}
