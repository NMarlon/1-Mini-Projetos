# ======================================================================
# Configurar-Webapp.ps1
#
# O QUE FAZ:
#   1. Copia o renderer do Desktop que ja vem na instalacao do Hermes
#      (app.asar.unpacked\dist) para uma pasta gravavel.
#   2. Aponta HERMES_WEBAPP_DIST para essa pasta no .env.
#   3. Liga o Webapp no gateway (127.0.0.1:9120) e define webapp.public_url.
#   4. Reinicia o gateway e publica :8444 no Tailscale Serve.
#
# POR QUE ISSO EXISTE:
#   A instalacao da Microsoft Store nao inclui apps/desktop/dist-webapp.
#   O renderer Electron que ja vem no app funciona no navegador; o gateway
#   injeta window.__HERMES_UI_SURFACE__="webapp". Ver DOCS/09-ERROS.
#
# QUANDO RODAR:
#   - Para habilitar o workspace completo (sessoes, projetos, arquivos,
#     Git, terminal) no navegador ou no Hermes-Android.
#   - Depois de atualizar o Hermes (recopia o renderer novo).
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Webapp.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\Configurar-Webapp.ps1 -Forcar
# ======================================================================

[CmdletBinding()]
param(
    [int]$PortaLocal = 9120,
    [int]$PortaPublica = 8444,
    [switch]$Forcar,
    [switch]$SemTailscale
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\common.ps1"

Write-Head "Configurar Webapp oficial"

# --- 1. Renderer ----------------------------------------------------
$payload = Get-HermesPayloadRoot
if (-not $payload) {
    Write-Err2 "Payload do Hermes nao encontrado."
    exit 1
}

# payload = ...\app\resources\agent-payload\hermes-agent
# resources = ...\app\resources
$resources = Split-Path -Parent (Split-Path -Parent $payload)
$sourceDist = Join-Path $resources 'app.asar.unpacked\dist'
if (-not (Test-Path -LiteralPath (Join-Path $sourceDist 'index.html'))) {
    Write-Err2 ("Renderer nao encontrado em: {0}" -f $sourceDist)
    Write-Host "Esta instalacao pode nao ser a MSIX/Store. Ajuste o caminho manualmente."
    exit 1
}

$pkg = Get-AppxPackage -Name '*HermesAgent*' -ErrorAction SilentlyContinue |
    Sort-Object Version -Descending | Select-Object -First 1
$pkgVersion = if ($pkg) { "$($pkg.Version)" } else { "desconhecida" }

$destRoot = Join-Path (Get-HermesMobileDir) 'webapp-dist'
$destIndex = Join-Path $destRoot 'index.html'
$manifestPath = Join-Path (Get-HermesMobileDir) 'webapp-dist.json'

$needCopy = $Forcar -or (-not (Test-Path -LiteralPath $destIndex))
if (-not $needCopy -and (Test-Path -LiteralPath $manifestPath)) {
    try {
        $prev = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($prev.source_version -ne $pkgVersion) { $needCopy = $true }
    } catch { $needCopy = $true }
}

if ($needCopy) {
    Write-Step ("Copiando renderer de {0}" -f $sourceDist)
    Ensure-Dir $destRoot | Out-Null

    # robocopy /MIR espelha; exit codes 0-7 sao sucesso
    # cmd /c com aspas evita o PowerShell quebrar caminhos com espacos
    $cmd = 'robocopy "' + $sourceDist + '" "' + $destRoot + '" /MIR /NFL /NDL /NJH /NJS /NP'
    & cmd.exe /c $cmd | Out-Null
    $rc = $LASTEXITCODE
    if ($rc -ge 8) {
        Write-Err2 ("robocopy falhou (exit {0})." -f $rc)
        exit 1
    }
    Write-Ok ("Renderer copiado para: {0}" -f $destRoot)
} else {
    Write-Ok ("Renderer ja atualizado em: {0}" -f $destRoot)
}

# Manifesto de integridade/versionamento
$indexHash = (Get-FileHash -LiteralPath $destIndex -Algorithm SHA256).Hash
$manifest = [ordered]@{
    source_path     = $sourceDist
    source_version  = $pkgVersion
    copied_at       = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    index_sha256    = $indexHash
    destination     = $destRoot
}
Write-TextNoBom -Path $manifestPath -Content (($manifest | ConvertTo-Json -Depth 3) + "`r`n")
Write-Ok ("Manifesto: {0}" -f $manifestPath)

# --- 2. .env ---------------------------------------------------------
$envPath = Join-Path (Get-HermesHome) '.env'
$values = [ordered]@{
    'HERMES_WEBAPP_DIST' = $destRoot
}
Set-EnvBlock -Path $envPath -Values $values -Marker 'Hermes-Mobile-Webapp'
Write-Ok "HERMES_WEBAPP_DIST gravado no .env."

# --- 3. Config -------------------------------------------------------
$self = Get-TailscaleSelf
if ($null -eq $self) {
    Write-Err2 "Tailscale sem status; nao consigo montar a URL publica."
    exit 1
}
$publicUrl = "https://$($self.DnsName):$PortaPublica"

Write-Step "Ligando webapp no gateway..."
$null = Invoke-Hermes -Arguments @('config', 'set', 'webapp.enabled', 'true')
$null = Invoke-Hermes -Arguments @('config', 'set', 'webapp.host', '127.0.0.1')
$null = Invoke-Hermes -Arguments @('config', 'set', 'webapp.port', "$PortaLocal")
$null = Invoke-Hermes -Arguments @('config', 'set', 'webapp.public_url', $publicUrl)

$conf = Invoke-Hermes -Arguments @('config', 'get', 'webapp')
Write-Ok "webapp configurado:"
Write-Host $conf

# --- 4. Reiniciar gateway -------------------------------------------
Write-Step "Reiniciando gateway para aplicar..."
$prev = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $null = & hermes.exe gateway stop 2>&1
    Start-Sleep -Seconds 3
    $null = & hermes.exe gateway restart 2>&1
} finally {
    $ErrorActionPreference = $prev
}

Write-Step "Aguardando webapp em http://127.0.0.1:$PortaLocal/api/status..."
$code = Wait-Http -Url "http://127.0.0.1:$PortaLocal/api/status" -TimeoutSeconds 90
if (-not $code) {
    Write-Err2 "O webapp nao respondeu. Veja os logs:"
    Write-Host ("  {0}\logs\gateway.log" -f (Get-HermesHome))
    Get-Content (Join-Path (Get-HermesHome) 'logs\gateway.log') -Tail 40 -ErrorAction SilentlyContinue
    exit 1
}
Write-Ok ("Webapp local respondeu HTTP {0}." -f $code)

# --- 5. Tailscale Serve :8444 ---------------------------------------
if (-not $SemTailscale) {
    Write-Step ("Publicando :{0} -> 127.0.0.1:{1}..." -f $PortaPublica, $PortaLocal)
    $target = "http://127.0.0.1:$PortaLocal"
    $existing = Get-TailscaleServeEntry -Port $PortaPublica
    if (-not ($existing -and $existing.Proxy -eq $target)) {
        $null = & tailscale.exe serve --bg --yes --https=$PortaPublica $target 2>&1
        Start-Sleep -Seconds 3
    }
    $entry = Get-TailscaleServeEntry -Port $PortaPublica
    if ($entry -and $entry.Proxy -eq $target) {
        Write-Ok ("Tailscale :{0} ativo -> {1}" -f $PortaPublica, $entry.Proxy)
    } else {
        Write-Warn2 ("Tailscale :{0} nao confirmado." -f $PortaPublica)
    }
    $e443 = Get-TailscaleServeEntry -Port 443
    $e8443 = Get-TailscaleServeEntry -Port 8443
    if ($e443) { Write-Ok ("Serve 443 preservado -> {0}" -f $e443.Proxy) }
    if ($e8443) { Write-Ok ("Serve 8443 preservado -> {0}" -f $e8443.Proxy) }
}

# --- 6. Testes -------------------------------------------------------
Write-Head "Webapp pronto"
$localRoot = "http://127.0.0.1:$PortaLocal/"
$publicRoot = "$publicUrl/"
$rootCode = Test-HttpCode -Url $localRoot -TimeoutSeconds 20
Write-Host ("Local  : {0} (HTTP {1})" -f $localRoot, $rootCode)
if (-not $SemTailscale) {
    $pubCode = Test-HttpCode -Url $publicRoot -TimeoutSeconds 30
    Write-Host ("Publico: {0} (HTTP {1})" -f $publicRoot, $pubCode)
    $body = Get-HttpBody -Url $publicUrl -TimeoutSeconds 20
    if ($body -match 'assets/|Hermes') { Write-Ok "HTML do webapp servido." } else { Write-Warn2 "HTML inesperado; confira no navegador." }
}
Write-Host ""
Write-Host "Abra no Chrome (celular ou PC) e faca login com o usuario/senha do Pomelu:"
Write-Host ("  {0}" -f $publicUrl)
Write-Host "O Pomelu continua em :8443; o webapp usa :8444."
