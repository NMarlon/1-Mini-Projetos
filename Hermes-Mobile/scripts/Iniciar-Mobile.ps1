# ======================================================================
# Iniciar-Mobile.ps1
#
# O QUE FAZ:
#   1. Garante o `hermes serve` em 127.0.0.1:<Porta>.
#   2. Garante o Tailscale Serve em :<PortaPublica>.
#   3. Mostra a URL e como obter as credenciais.
#
# QUANDO RODAR: dia a dia, apos ligar/reiniciar o PC.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Mobile.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Mobile.ps1 -AbrirNavegador
# ======================================================================

[CmdletBinding()]
param(
    [int]$Porta = 9119,
    [int]$PortaPublica = 8443,
    [switch]$SemTailscale,
    [switch]$AbrirNavegador
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\common.ps1"

Write-Head "Hermes Mobile"

& "$PSScriptRoot\Iniciar-Servidor.ps1" -Porta $Porta

if (-not $SemTailscale) {
    & "$PSScriptRoot\Configurar-Tailscale.ps1" -Porta $Porta -PortaPublica $PortaPublica
} else {
    Write-Warn2 "Tailscale Serve ignorado (-SemTailscale)."
}

$self = Get-TailscaleSelf
$url = ''
if ($self) {
    $url = "https://$($self.DnsName):$PortaPublica"
}

# Confirmar que o servidor responde localmente
$localCode = Test-HttpCode -Url "http://127.0.0.1:$Porta/api/status"
if ($localCode -eq '200') {
    Write-Ok ("Servidor local OK (HTTP {0})." -f $localCode)
} else {
    Write-Warn2 ("Servidor local respondeu HTTP {0}." -f $localCode)
}

# Confirmar a URL publica (se Tailscale ativo)
if ($url -and -not $SemTailscale) {
    $pubCode = Test-HttpCode -Url "$url/api/status" -TimeoutSeconds 20
    if ($pubCode -eq '200') {
        Write-Ok ("URL publica OK: {0}" -f $url)
    } else {
        Write-Warn2 ("URL publica respondeu HTTP {0}. Veja DOCS/06-TROUBLESHOOTING.md." -f $pubCode)
    }
}

Write-Head "Pronto"
if ($url) { Write-Host ("URL     : {0}" -f $url) }
Write-Host ("Usuario : hermes (ou o configurado)")
Write-Host "Senha   : use Ver-Credenciais.ps1 -Revelar"
Write-Host ""
Write-Host "No celular: Pomelu -> Settings -> adicionar a URL acima."

if ($AbrirNavegador -and $url) {
    Start-Process $url | Out-Null
}
