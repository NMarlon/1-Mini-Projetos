# ======================================================================
# Parar-Mobile.ps1
#
# O QUE FAZ:
#   Para APENAS o `hermes serve` deste projeto (pela porta).
#   Nunca roda `hermes serve --stop` (que pararia o Desktop tambem).
#   Opcionalmente remove o handler :8443 do Tailscale.
#
# QUANDO RODAR: manutencao / rollback.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Parar-Mobile.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\Parar-Mobile.ps1 -RemoverServe
# ======================================================================

[CmdletBinding()]
param(
    [int]$Porta = 80,
    [switch]$RemoverServe,
    [switch]$Force,
    [switch]$PararGateway
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\common.ps1"

Write-Head "Parar Hermes Mobile"

$existing = Get-ServerProcessOnPort -Port $Porta
if (-not $existing) {
    Write-Ok ("Nada escutando na porta {0}." -f $Porta)
} else {
    $isHermes = ($existing.CommandLine -match 'hermes') -and ($existing.CommandLine -match 'serve')
    if (-not $isHermes -and -not $Force) {
        Write-Err2 ("A porta {0} e do PID {1} ({2}), que nao parece ser o hermes serve." -f $Porta, $existing.Pid, $existing.Name)
        Write-Host "Use -Force somente se tiver certeza."
        exit 1
    }

    Write-Step ("Parando PID {0}..." -f $existing.Pid)
    Stop-Process -Id $existing.Pid -Force -ErrorAction Stop
    Start-Sleep -Seconds 2

    $after = Get-ServerProcessOnPort -Port $Porta
    if ($after) {
        Write-Warn2 ("A porta {0} ainda esta ocupada (PID {1})." -f $Porta, $after.Pid)
    } else {
        Write-Ok ("Servidor parado; porta {0} livre." -f $Porta)
    }
}

if ($RemoverServe) {
    & "$PSScriptRoot\Configurar-Tailscale.ps1" -Porta $Porta -Remover
} else {
    Write-Host "Handler :8443 mantido (use -RemoverServe para remover)."
}

if ($PararGateway) {
    Write-Step "Parando o gateway (webapp em :9120)..."
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $null = & hermes.exe gateway stop 2>&1
    } finally {
        $ErrorActionPreference = $prev
    }
    Write-Ok "Gateway parado."
} else {
    Write-Host "Gateway/webapp em :9120 continua rodando (use -PararGateway para parar)."
}

Write-Ok "O OpenCode em :443 nao foi tocado."
