# ======================================================================
# Ver-Credenciais.ps1
#
# O QUE FAZ:
#   Mostra a URL e o usuario do gateway. Com -Revelar, mostra a senha.
#   Com -Copiar, copia a senha para a area de transferencia.
#
# QUANDO RODAR: ao configurar o Pomelu no celular.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1 -Revelar
#   powershell -ExecutionPolicy Bypass -File .\scripts\Ver-Credenciais.ps1 -Revelar -Copiar
# ======================================================================

[CmdletBinding()]
param(
    [switch]$Revelar,
    [switch]$Copiar
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\common.ps1"

Write-Head "Credenciais do Hermes Mobile"

$sec = Read-SecretFile
if ($null -eq $sec) {
    Write-Err2 ("secrets.json nao encontrado em {0}." -f (Get-SecretsPath))
    Write-Host "Rode Configurar-Hermes.ps1 primeiro."
    exit 1
}

Write-Host ("URL     : {0}" -f $sec.url)
Write-Host ("Usuario : {0}" -f $sec.username)
Write-Host ("Criado  : {0}" -f $sec.created_at)
Write-Host ("TTL     : {0} dias" -f $sec.ttl_days)

if ($Revelar) {
    Write-Host ("Senha   : {0}" -f $sec.password) -ForegroundColor Yellow
    if ($Copiar) {
        try {
            Set-Clipboard -Value "$($sec.password)"
            Write-Ok "Senha copiada para a area de transferencia."
        } catch {
            Write-Warn2 "Nao foi possivel copiar para a area de transferencia."
        }
    }
} else {
    Write-Host "Senha   : (oculta) use -Revelar"
}

Write-Host ""
Write-Host "No Pomelu: Settings -> URL acima -> usuario/senha -> Test connection."
