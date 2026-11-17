# ======================================================================
# Instalar-Tudo.ps1
#
# O QUE FAZ:
#   1. Configura autenticacao + dashboard.public_url.
#   2. Sobe o hermes serve e o Tailscale Serve :8443.
#   3. Roda o diagnostico.
#   4. Instala o autostart (se confirmado).
#
# QUANDO RODAR: primeira instalacao ou PC novo.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Instalar-Tudo.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\Instalar-Tudo.ps1 -Sim
#   powershell -ExecutionPolicy Bypass -File .\scripts\Instalar-Tudo.ps1 -Sim -SemAutostart
# ======================================================================

[CmdletBinding()]
param(
    [switch]$Sim,
    [switch]$SemAutostart,
    [int]$Porta = 9119,
    [int]$PortaPublica = 8443,
    [string]$UrlPublica = ''
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\common.ps1"

Write-Head "Instalar Hermes Mobile"

# --- 1. Configuracao -------------------------------------------------
$cfgArgs = @()
if ($UrlPublica) { $cfgArgs += @('-UrlPublica', $UrlPublica) }

$global:LASTEXITCODE = 0
& "$PSScriptRoot\Configurar-Hermes.ps1" @cfgArgs
if ($LASTEXITCODE -ne 0) {
    Write-Err2 "Configurar-Hermes.ps1 falhou."
    exit $LASTEXITCODE
}

# --- 2. Servidor + Tailscale ----------------------------------------
$global:LASTEXITCODE = 0
& "$PSScriptRoot\Iniciar-Mobile.ps1" -Porta $Porta -PortaPublica $PortaPublica
if ($LASTEXITCODE -ne 0) {
    Write-Err2 "Iniciar-Mobile.ps1 falhou."
    exit $LASTEXITCODE
}

# --- 3. Diagnostico --------------------------------------------------
& "$PSScriptRoot\Status-Diagnostico.ps1" -SalvarEmLog

# --- 4. Autostart ----------------------------------------------------
if ($SemAutostart) {
    Write-Warn2 "Autostart ignorado (-SemAutostart)."
} else {
    $install = $false
    if ($Sim) {
        $install = $true
    } else {
        $r = Read-Host "Instalar autostart no login? (S/n)"
        if ($r -notmatch '^[nN]') { $install = $true }
    }
    if ($install) {
        & "$PSScriptRoot\Instalar-Autostart.ps1" -Porta $Porta
    } else {
        Write-Warn2 "Autostart nao instalado."
    }
}

# --- 5. Resumo -------------------------------------------------------
$self = Get-TailscaleSelf
$url = ''
if ($self) { $url = "https://$($self.DnsName):$PortaPublica" }

Write-Head "Instalacao concluida"
if ($url) { Write-Host ("URL     : {0}" -f $url) }
Write-Host "Usuario : hermes"
Write-Host "Senha   : powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1 -Revelar"
Write-Host ""
Write-Host "No celular:"
Write-Host "  1. Instale o Pomelu (Play Store: se.royan.pomelu)."
Write-Host "  2. Settings -> adicione a URL acima."
Write-Host "  3. Informe usuario/senha -> Test connection -> Save and connect."
