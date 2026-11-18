# ======================================================================
# Configurar-Tailscale.ps1
#
# O QUE FAZ:
#   Cria/garante o handler HTTPS do Tailscale Serve para o Hermes:
#       https://<pc>.<tailnet>.ts.net:8443  ->  http://127.0.0.1:80
#
#   NUNCA altera o handler :443 (OpenCode).
#
# QUANDO RODAR:
#   - Primeira instalacao.
#   - Depois de mudar a porta local do hermes serve.
#   - Para remover apenas o handler 8443.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Tailscale.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Tailscale.ps1 -Remover
#   powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Tailscale.ps1 -Porta 9121
# ======================================================================

[CmdletBinding()]
param(
    [int]$Porta = 80,
    [int]$PortaPublica = 8443,
    [switch]$Remover,
    [switch]$HttpFallback
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\common.ps1"

Write-Head "Configurar Tailscale Serve"

if (-not (Test-TailscaleInstalled)) {
    Write-Err2 "Tailscale nao instalado."
    exit 1
}

$self = Get-TailscaleSelf
if ($null -eq $self) {
    Write-Err2 "Tailscale sem status. Verifique se esta logado e o daemon esta rodando."
    exit 1
}

$target = "http://127.0.0.1:$Porta"
$url = "https://$($self.DnsName):$PortaPublica"

Write-Ok ("PC      : {0}" -f $self.HostName)
Write-Ok ("DNS     : {0}" -f $self.DnsName)
Write-Ok ("Alvo    : {0}" -f $target)

# --- Remover somente o handler do Hermes ----------------------------
if ($Remover) {
    Write-Step ("Removendo handler :{0} (o :443 do OpenCode nao sera tocado)..." -f $PortaPublica)
    $out = (& tailscale.exe serve --https=$PortaPublica off 2>&1 | Out-String).Trim()
    if ($out) { Write-Host $out }

    $e443 = Get-TailscaleServeEntry -Port 443
    if ($e443) {
        Write-Ok ("Serve 443 preservado -> {0}" -f $e443.Proxy)
    } else {
        Write-Warn2 "Serve 443 nao encontrado. Verifique o OpenCode."
    }

    $e = Get-TailscaleServeEntry -Port $PortaPublica
    if ($e) {
        Write-Warn2 ("Handler :{0} ainda aparece no status." -f $PortaPublica)
    } else {
        Write-Ok ("Handler :{0} removido." -f $PortaPublica)
    }
    exit 0
}

# --- Verificar se ja esta configurado -------------------------------
$existing = Get-TailscaleServeEntry -Port $PortaPublica
if ($existing -and $existing.Proxy -eq $target) {
    Write-Ok ("Ja configurado: :{0} -> {1}" -f $PortaPublica, $target)
} else {
    Write-Step ("Criando handler HTTPS :{0} -> {1}..." -f $PortaPublica, $target)
    $out = (& tailscale.exe serve --bg --yes --https=$PortaPublica $target 2>&1 | Out-String).Trim()
    if ($out) { Write-Host $out }
    Start-Sleep -Seconds 3
}

$entry = Get-TailscaleServeEntry -Port $PortaPublica
if ($entry -and $entry.Proxy -eq $target) {
    Write-Ok ("Handler :{0} ativo -> {1}" -f $PortaPublica, $entry.Proxy)
} else {
    Write-Warn2 ("Handler HTTPS :{0} nao confirmado." -f $PortaPublica)
    Write-Host "Saida do 'tailscale serve status':"
    Write-Host (& tailscale.exe serve status 2>&1 | Out-String)

    if ($HttpFallback) {
        Write-Step "Tentando fallback HTTP privado (sem TLS)..."
        $out2 = (& tailscale.exe serve --bg --yes --http=$PortaPublica $target 2>&1 | Out-String).Trim()
        if ($out2) { Write-Host $out2 }
        Start-Sleep -Seconds 3
        $entry2 = Get-TailscaleServeEntry -Port $PortaPublica
        if ($entry2 -and $entry2.Proxy -eq $target) {
            Write-Warn2 ("Fallback HTTP ativo: http://{0}:{1}" -f $self.DnsName, $PortaPublica)
            Write-Warn2 "Atualize dashboard.public_url para http://... se usar este fallback."
            exit 0
        }
    }

    Write-Err2 "Nao foi possivel ativar o Tailscale Serve. Veja DOCS/06-TROUBLESHOOTING.md."
    exit 1
}

# --- Garantir que o OpenCode (443) continua -------------------------
$e443 = Get-TailscaleServeEntry -Port 443
if ($e443) {
    Write-Ok ("Serve 443 preservado -> {0}" -f $e443.Proxy)
} else {
    Write-Warn2 "Serve 443 nao encontrado. O OpenCode pode estar fora do ar."
}

Write-Head "Pronto"
Write-Host ("URL do Hermes: {0}" -f $url)
Write-Host ""
Write-Host "Teste:"
Write-Host ("  curl.exe -s {0}/api/status" -f $url)
