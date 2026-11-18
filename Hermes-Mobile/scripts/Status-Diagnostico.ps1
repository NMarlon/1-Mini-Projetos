# ======================================================================
# Status-Diagnostico.ps1
#
# O QUE FAZ: panorama tecnico do projeto Hermes-Mobile.
#           Somente leitura: nao altera configuracao.
#
# QUANDO RODAR: antes de assumir qualquer coisa e apos qualquer mudanca.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Status-Diagnostico.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\Status-Diagnostico.ps1 -SalvarEmLog
# ======================================================================

[CmdletBinding()]
param(
    [switch]$SalvarEmLog,
    [int]$Porta = 80
)

. "$PSScriptRoot\lib\common.ps1"

$logLines = New-Object System.Collections.Generic.List[string]
function Report {
    param([string]$Msg = '')
    $logLines.Add($Msg) | Out-Null
    Write-Host $Msg
}

function Report-Ok { param([string]$Msg) Report ("[OK] " + $Msg) }
function Report-Warn { param([string]$Msg) Report ("[AVISO] " + $Msg) }
function Report-Err { param([string]$Msg) Report ("[ERRO] " + $Msg) }

Report ""
Report "=== Hermes-Mobile - diagnostico ==="
Report ("Data/Hora       : {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Report ("Usuario Windows : {0}" -f $env:USERNAME)
Report ("Administrador?  : {0}" -f (Test-IsAdmin))

# ---------------------------------------------------------------
# 1. Hermes
# ---------------------------------------------------------------
Report ""
Report "--- 1. Hermes ---"
$exe = Get-HermesExe
if (-not $exe) {
    Report-Err "hermes.exe nao encontrado no PATH."
} else {
    Report-Ok ("CLI: {0}" -f $exe)
    Report ("     Versao: {0}" -f (Get-HermesVersion))

    $verOut = ''
    try { $verOut = Invoke-Hermes -Arguments @('--version') } catch { }
    if ($verOut -match 'install out of sync') {
        Report-Warn "Aviso 'install out of sync' presente (pre-existente; nao impede o uso)."
    }
}

$hermesHome = Get-HermesHome
Report ("     Home  : {0}" -f $hermesHome)
if (Test-Path -LiteralPath $hermesHome) { Report-Ok "Home existe." } else { Report-Err "Home nao existe." }

$payload = Get-HermesPayloadRoot
if ($payload) { Report-Ok ("Payload: {0}" -f $payload) } else { Report-Warn "Payload do Hermes nao localizado." }

$py = Get-HermesPython
if ($py) { Report-Ok ("Python : {0}" -f $py) } else { Report-Warn "Python do Hermes nao localizado (hash scrypt pode falhar)." }

# ---------------------------------------------------------------
# 2. Configuracao
# ---------------------------------------------------------------
Report ""
Report "--- 2. Configuracao (dashboard) ---"
try {
    $pub = (Invoke-Hermes -Arguments @('config', 'get', 'dashboard.public_url')).Trim()
    if ($pub) { Report-Ok ("public_url: {0}" -f $pub) } else { Report-Warn "dashboard.public_url vazio (auth gate NAO liga em loopback)." }
} catch {
    Report-Warn "Nao consegui ler dashboard.public_url."
}

try {
    $auth = Invoke-Hermes -Arguments @('config', 'get', 'dashboard.basic_auth')
    $hasUser = ($auth -match "username:\s*'?[^'\s]")
    $hasHash = ($auth -match "password_hash:\s*'?[^'\s]")
    $hasPwd  = ($auth -match "password:\s*'?[^'\s]")
    $hasSec  = ($auth -match "secret:\s*'?[^'\s]")
    if ($hasUser -and ($hasHash -or $hasPwd) -and $hasSec) {
        Report-Ok "dashboard.basic_auth configurado no config.yaml."
    } else {
        Report "     config.yaml sem basic_auth (esperado; auth fica no .env)."
    }
} catch { }

# ---------------------------------------------------------------
# 3. .env (somente presenca, sem valores)
# ---------------------------------------------------------------
Report ""
Report "--- 3. Variaveis de auth no .env ---"
$envPath = Join-Path $hermesHome '.env'
if (-not (Test-Path -LiteralPath $envPath)) {
    Report-Err ".env nao existe em $envPath"
} else {
    $u  = Get-EnvValue -Path $envPath -Key 'HERMES_DASHBOARD_BASIC_AUTH_USERNAME'
    $h  = Get-EnvValue -Path $envPath -Key 'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH'
    $p  = Get-EnvValue -Path $envPath -Key 'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD'
    $s  = Get-EnvValue -Path $envPath -Key 'HERMES_DASHBOARD_BASIC_AUTH_SECRET'
    $ttl= Get-EnvValue -Path $envPath -Key 'HERMES_DASHBOARD_BASIC_AUTH_TTL_SECONDS'

    if ($u) { Report-Ok ("Usuario: {0}" -f $u) } else { Report-Err "Username ausente." }
    if ($h) {
        if ($h -match '^scrypt\$') { Report-Ok "Hash scrypt presente." } else { Report-Warn "PASSWORD_HASH presente, formato inesperado." }
    } elseif ($p) {
        Report-Warn "Senha em texto (PASSWORD) presente; prefira PASSWORD_HASH."
    } else {
        Report-Err "Nem PASSWORD_HASH nem PASSWORD presentes."
    }
    if ($s) { Report-Ok ("Secret presente (tamanho {0})." -f $s.Length) } else { Report-Err "Secret ausente." }
    if ($ttl) { Report-Ok ("TTL: {0} segundos" -f $ttl) } else { Report-Warn "TTL ausente (usa padrao)." }
}

# ---------------------------------------------------------------
# 4. Servidor local
# ---------------------------------------------------------------
Report ""
Report "--- 4. Servidor hermes serve ---"
try {
    $serveStatus = Invoke-Hermes -Arguments @('serve', '--status')
    Report ("     {0}" -f (($serveStatus -replace "`r", ' ') -replace "`n", ' | '))
} catch { }

$listeners = Get-PortListeners -Port $Porta
if (@($listeners).Count -gt 0) {
    $srv = Get-ServerProcessOnPort -Port $Porta
    Report-Ok ("Porta {0} escutando em {1} (PID {2}, {3})." -f $Porta, $srv.LocalAddress, $srv.Pid, $srv.Name)
} else {
    Report-Err ("Nada escutando em 127.0.0.1:{0}." -f $Porta)
}

$localStatus = '000'
$localBody = ''
if (@($listeners).Count -gt 0) {
    $localStatus = Test-HttpCode -Url "http://127.0.0.1:$Porta/api/status"
    $localBody = Get-HttpBody -Url "http://127.0.0.1:$Porta/api/status"
    if ($localStatus -eq '200') {
        Report-Ok ("GET http://127.0.0.1:{0}/api/status -> 200" -f $Porta)
        try {
            $j = $localBody | ConvertFrom-Json
            Report ("     version        : {0}" -f $j.version)
            Report ("     auth_required  : {0}" -f $j.auth_required)
            if ($null -ne $j.auth_providers) {
                Report ("     auth_providers : {0}" -f (($j.auth_providers) -join ', '))
            }
            if ($null -ne $j.profiles) {
                Report ("     profiles       : {0}" -f (($j.profiles).Count))
            }
        } catch {
            Report ("     Corpo (inicio): {0}" -f $localBody.Substring(0, [Math]::Min(160, $localBody.Length)))
        }
    } else {
        Report-Warn ("GET /api/status local -> HTTP {0}" -f $localStatus)
    }
}

# ---------------------------------------------------------------
# 5. Tailscale
# ---------------------------------------------------------------
Report ""
Report "--- 5. Tailscale ---"
if (-not (Test-TailscaleInstalled)) {
    Report-Err "Tailscale nao instalado."
} else {
    Report ("     Versao: {0}" -f ((& tailscale.exe version 2>$null | Select-Object -First 1)))
    $self = Get-TailscaleSelf
    if ($null -eq $self) {
        Report-Warn "Tailscale instalado mas sem status (daemon desligado?)."
    } else {
        Report-Ok ("Device : {0}" -f $self.HostName)
        Report ("     DNS    : {0}" -f $self.DnsName)
        Report ("     IP     : {0}" -f $self.TailscaleIP)
        Report ("     Conta  : {0}" -f $self.TailnetUser)
    }

    $e443 = Get-TailscaleServeEntry -Port 443
    if ($e443) {
        Report-Ok ("Serve 443 -> {0}" -f $e443.Proxy)
        if ($e443.Proxy -notmatch '28894') { Report-Warn "443 nao aponta para o OpenCode (28894)." }
    } else {
        Report-Warn "Serve 443 ausente (OpenCode pode estar fora do ar)."
    }

    $e8443 = Get-TailscaleServeEntry -Port 8443
    if ($e8443) {
        Report-Ok ("Serve 8443 -> {0}" -f $e8443.Proxy)
        if ($e8443.Proxy -notmatch '80') { Report-Warn "8443 nao aponta para o Hermes (80)." }
    } else {
        Report-Err "Serve 8443 ausente (celular nao alcanca o Hermes)."
    }

    $funnel = (& tailscale.exe funnel status 2>$null | Out-String).Trim()
    if (Test-TailscaleFunnelEnabled) {
        Report-Warn "Funnel ATIVO! Isso expoe o servico a internet. Revise."
    } else {
        Report-Ok "Funnel desativado."
    }
}

# ---------------------------------------------------------------
# 6. Saude pela URL publica
# ---------------------------------------------------------------
Report ""
Report "--- 6. Saude via HTTPS (a rota do celular) ---"
$pubUrl = ''
try { $pubUrl = (Invoke-Hermes -Arguments @('config', 'get', 'dashboard.public_url')).Trim() } catch { }
if (-not $pubUrl) {
    $self2 = Get-TailscaleSelf
    if ($self2) { $pubUrl = "https://$($self2.DnsName):8443" }
}

if ($pubUrl) {
    $healthUrl = "$($pubUrl.TrimEnd('/'))/api/status"
    $code = Test-HttpCode -Url $healthUrl -TimeoutSeconds 15
    if ($code -eq '200') {
        Report-Ok ("GET {0} -> 200" -f $healthUrl)
        $body = Get-HttpBody -Url $healthUrl
        try {
            $j = $body | ConvertFrom-Json
            Report ("     version        : {0}" -f $j.version)
            Report ("     auth_required  : {0}" -f $j.auth_required)
            if ($null -ne $j.auth_providers) {
                Report ("     auth_providers : {0}" -f (($j.auth_providers) -join ', '))
            }
        } catch { }
    } else {
        Report-Warn ("GET {0} -> HTTP {1}" -f $healthUrl, $code)
    }
} else {
    Report-Warn "URL publica nao definida; nao testado."
}

# ---------------------------------------------------------------
# 7. Autostart
# ---------------------------------------------------------------
Report ""
Report "--- 7. Autostart ---"
$task = Get-HermesMobileTask
if ($task) {
    Report-Ok ("Tarefa '{0}' existe (estado: {1})." -f $task.TaskName, $task.State)
    try {
        $info = Get-ScheduledTaskInfo -TaskName 'Hermes Mobile - Servidor' -ErrorAction SilentlyContinue
        if ($info) {
            Report ("     Ultima execucao: {0}" -f $info.LastRunTime)
            Report ("     Resultado      : {0}" -f $info.LastTaskResult)
        }
    } catch { }
} else {
    Report-Warn "Tarefa 'Hermes Mobile - Servidor' nao instalada."
}

# ---------------------------------------------------------------
# 8. Credenciais do projeto
# ---------------------------------------------------------------
Report ""
Report "--- 8. Credenciais locais ---"
$secretsPath = Get-SecretsPath
if (Test-Path -LiteralPath $secretsPath) {
    Report-Ok ("secrets.json existe: {0}" -f $secretsPath)
    $sec = Read-SecretFile
    if ($sec) {
        Report ("     Usuario: {0}" -f $sec.username)
        Report ("     URL    : {0}" -f $sec.url)
    }
} else {
    Report-Warn "secrets.json nao existe. Rode Configurar-Hermes.ps1."
}

# ---------------------------------------------------------------
# 9. Firewall (somente leitura)
# ---------------------------------------------------------------
Report ""
Report "--- 9. Firewall (regras Tailscale/Hermes) ---"
try {
    $rules = Get-NetFirewallRule -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -match 'Tailscale|Hermes' } |
        Select-Object -ExpandProperty DisplayName -Unique
    if ($rules) {
        foreach ($r in $rules) { Report ("     - {0}" -f $r) }
    } else {
        Report "     (nenhuma regra com esse nome)"
    }
} catch {
    Report-Warn "Falha ao consultar firewall."
}

# ---------------------------------------------------------------
# 10. OpenCode
# ---------------------------------------------------------------
Report ""
Report "--- 10. OpenCode (nao deve ser afetado) ---"
$self3 = Get-TailscaleSelf
if ($self3) {
    $ocUrl = "https://$($self3.DnsName)/api/info"
    $ocCode = Test-HttpCode -Url $ocUrl -TimeoutSeconds 15
    if ($ocCode -eq '200' -or $ocCode -eq '401') {
        Report-Ok ("GET {0} -> HTTP {1} (servico de pe)." -f $ocUrl, $ocCode)
    } else {
        Report-Warn ("GET {0} -> HTTP {1}" -f $ocUrl, $ocCode)
    }
}

# ---------------------------------------------------------------
# 11. Webapp oficial (opcional)
# ---------------------------------------------------------------
Report ""
Report "--- 11. Webapp oficial (opcional) ---"
$webappRaw = ''
$webappEnabled = $false
$webappPort = 9120
$webappPublic = ''

try {
    $webappRaw = Invoke-Hermes -Arguments @('config', 'get', 'webapp')
    Report ("     {0}" -f (($webappRaw -replace "`r", ' ') -replace "`n", ' | '))
    if ($webappRaw -match 'enabled:\s*true') { $webappEnabled = $true }
    if ($webappRaw -match 'port:\s*(\d+)') { $webappPort = [int]$Matches[1] }
    if ($webappRaw -match 'public_url:\s*(\S+)') { $webappPublic = $Matches[1] }
} catch {
    Report-Warn "Nao consegui ler a configuracao do webapp."
}

$webappDist = Get-EnvValue -Path $envPath -Key 'HERMES_WEBAPP_DIST'
if ($webappDist) {
    if (Test-Path -LiteralPath (Join-Path $webappDist 'index.html')) {
        Report-Ok ("HERMES_WEBAPP_DIST: {0}" -f $webappDist)
    } else {
        Report-Err ("HERMES_WEBAPP_DIST sem index.html: {0}" -f $webappDist)
    }
} elseif ($webappEnabled) {
    Report-Warn "Webapp habilitado, mas HERMES_WEBAPP_DIST esta ausente."
} else {
    Report "     Webapp desabilitado."
}

if ($webappEnabled) {
    $wlisteners = Get-PortListeners -Port $webappPort
    if (@($wlisteners).Count -gt 0) {
        $wsrv = Get-ServerProcessOnPort -Port $webappPort
        Report-Ok ("Porta {0} escutando (PID {1}, {2})." -f $webappPort, $wsrv.Pid, $wsrv.Name)
        $wcode = Test-HttpCode -Url "http://127.0.0.1:$webappPort/api/status"
        if ($wcode -eq '200') {
            Report-Ok ("GET http://127.0.0.1:{0}/api/status -> 200" -f $webappPort)
        } else {
            Report-Warn ("Webapp local -> HTTP {0}" -f $wcode)
        }
    } else {
        Report-Err ("Nada escutando em 127.0.0.1:{0} (webapp)." -f $webappPort)
    }

    if ($webappPublic) {
        $wpub = $webappPublic.TrimEnd('/')
        $wcode2 = Test-HttpCode -Url "$wpub/api/status" -TimeoutSeconds 20
        if ($wcode2 -eq '200') {
            Report-Ok ("Webapp publico -> 200 ({0})" -f $webappPublic)
        } else {
            Report-Warn ("Webapp publico -> HTTP {0}" -f $wcode2)
        }
        $wlogin = Test-HttpCode -Url "$wpub/login" -TimeoutSeconds 20
        if ($wlogin -eq '200') {
            Report-Ok "Pagina de login do webapp -> 200"
        } else {
            Report-Warn ("Login do webapp -> HTTP {0}" -f $wlogin)
        }
    }

    $e8444 = Get-TailscaleServeEntry -Port 8444
    if ($e8444) {
        Report-Ok ("Serve 8444 -> {0}" -f $e8444.Proxy)
    } else {
        Report-Warn "Serve 8444 ausente (webapp nao chega no celular)."
    }
}

# ---------------------------------------------------------------
# Log
# ---------------------------------------------------------------
if ($SalvarEmLog) {
    $logsDir = Ensure-Dir (Join-Path (Get-ProjectRoot) 'logs')
    $file = Join-Path $logsDir ("diagnostico-{0}.txt" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
    $logLines | Set-Content -LiteralPath $file -Encoding UTF8
    Report ""
    Report ("[OK] Log salvo em: {0}" -f $file)
}

Report ""
Report "Fim do diagnostico."
