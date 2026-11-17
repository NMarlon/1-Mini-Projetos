# ======================================================================
# Configurar-Hermes.ps1
#
# O QUE FAZ:
#   1. Gera usuario, senha forte, hash scrypt e secret de assinatura.
#   2. Grava HERMES_DASHBOARD_BASIC_AUTH_* no .env do Hermes (com backup).
#   3. Salva a senha em %LOCALAPPDATA%\HermesMobile\secrets.json (ACL).
#   4. Define dashboard.public_url no config.yaml.
#
# QUANDO RODAR:
#   - Primeira instalacao.
#   - Troca de senha / rotacao de credenciais.
#   - Mudanca do nome do PC no Tailscale.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Hermes.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Hermes.ps1 -Revelar
# ======================================================================

[CmdletBinding()]
param(
    [string]$Usuario = 'hermes',
    [string]$Senha = '',
    [int]$TtlDias = 7,
    [string]$UrlPublica = '',
    [switch]$Rotacionar,
    [switch]$Revelar
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\common.ps1"

Write-Head "Configurar Hermes para acesso mobile"

# --- 1. Verificacoes -------------------------------------------------
$exe = Get-HermesExe
if (-not $exe) {
    Write-Err2 "hermes.exe nao encontrado. Instale o Hermes Agent primeiro."
    exit 1
}

$hermesHome = Get-HermesHome
$envPath = Join-Path $hermesHome '.env'
if (-not (Test-Path -LiteralPath $hermesHome)) {
    Write-Err2 "Home do Hermes nao encontrada: $hermesHome"
    exit 1
}
if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Warn2 ".env nao existe; sera criado em $envPath"
}

Write-Ok ("Hermes: {0}" -f (Get-HermesVersion))
Write-Ok ("Home:   {0}" -f $hermesHome)

# --- 2. URL publica --------------------------------------------------
if (-not $UrlPublica) {
    $self = Get-TailscaleSelf
    if ($null -eq $self) {
        Write-Err2 "Nao consegui ler o Tailscale. Rode 'tailscale status' e tente de novo."
        Write-Host "Ou informe a URL manualmente: -UrlPublica https://seu-pc.tailnet.ts.net:8443"
        exit 1
    }
    $UrlPublica = "https://$($self.DnsName):8443"
    Write-Ok ("Tailscale: {0} ({1})" -f $self.HostName, $self.TailscaleIP)
}
$UrlPublica = $UrlPublica.TrimEnd('/')
Write-Ok ("URL publica: {0}" -f $UrlPublica)

# --- 3. Credenciais --------------------------------------------------
$existing = Read-SecretFile
$existingHash = Get-EnvValue -Path $envPath -Key 'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH'
$existingSecret = Get-EnvValue -Path $envPath -Key 'HERMES_DASHBOARD_BASIC_AUTH_SECRET'
$reused = $false

if (-not $Senha -and -not $Rotacionar -and $existing -and $existing.password -and $existingHash -and $existingSecret) {
    $Senha = "$($existing.password)"
    $hash = $existingHash
    $secret = $existingSecret
    $reused = $true
    Write-Ok "Credenciais existentes reutilizadas (use -Rotacionar para trocar)."
} else {
    if (-not $Senha) {
        $Senha = New-RandomToken -Bytes 24
        Write-Ok "Senha forte gerada."
    }
    $secret = New-RandomToken -Bytes 32

    Write-Step "Calculando hash scrypt (pode levar alguns segundos)..."
    $hash = Get-PasswordHash -Password $Senha
    Write-Ok "Hash scrypt gerado."
}

$ttlSeconds = $TtlDias * 86400

# --- 4. .env ---------------------------------------------------------
$values = [ordered]@{
    'HERMES_DASHBOARD_BASIC_AUTH_USERNAME'      = $Usuario
    'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH' = $hash
    'HERMES_DASHBOARD_BASIC_AUTH_SECRET'        = $secret
    'HERMES_DASHBOARD_BASIC_AUTH_TTL_SECONDS'   = "$ttlSeconds"
}

Write-Step "Gravando variaveis no .env (com backup)..."
Set-EnvBlock -Path $envPath -Values $values -Marker 'Hermes-Mobile'
Write-Ok "Variaveis HERMES_DASHBOARD_BASIC_AUTH_* gravadas."

# --- 5. secrets.json -------------------------------------------------
$secretsPath = Get-SecretsPath
$data = [ordered]@{
    url        = $UrlPublica
    username   = $Usuario
    password   = $Senha
    created_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    ttl_days   = $TtlDias
}
Write-SecretFile -Path $secretsPath -Data $data
Write-Ok ("Senha salva em: {0}" -f $secretsPath)

# --- 6. dashboard.public_url ----------------------------------------
Write-Step "Definindo dashboard.public_url..."
$null = Invoke-Hermes -Arguments @('config', 'set', 'dashboard.public_url', $UrlPublica)
$configured = Invoke-Hermes -Arguments @('config', 'get', 'dashboard.public_url')

if ($configured.Trim() -ne $UrlPublica) {
    Write-Warn2 ("Valor configurado difere do esperado: {0}" -f $configured)
} else {
    Write-Ok ("dashboard.public_url = {0}" -f $configured)
}

# --- 7. Resumo -------------------------------------------------------
Write-Head "Configuracao concluida"
Write-Host ("Usuario : {0}" -f $Usuario)
Write-Host ("URL     : {0}" -f $UrlPublica)
Write-Host ("TTL     : {0} dias" -f $TtlDias)
if ($reused) { Write-Host "Modo    : credenciais existentes reutilizadas" } else { Write-Host "Modo    : credenciais novas" }
if ($Revelar) {
    Write-Host ("Senha   : {0}" -f $Senha) -ForegroundColor Yellow
} else {
    Write-Host "Senha   : (oculta) use Ver-Credenciais.ps1 -Revelar"
}
Write-Host ""
Write-Host "Proximo passo: subir o servidor e o Tailscale."
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Mobile.ps1"
