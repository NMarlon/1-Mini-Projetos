# ======================================================================
# lib/common.ps1
# Biblioteca de funcoes compartilhadas do projeto "Hermes-Mobile".
#
# NAO execute este arquivo diretamente. Carregue com:
#   . "$PSScriptRoot\lib\common.ps1"
#
# Compativel com PowerShell 5.1. Codificacao: UTF-8 com BOM.
# ======================================================================

Set-StrictMode -Version 2

# ---------------------------------------------------------------
# Saida no console (sem emojis: consoles do PS 5.1 quebram)
# ---------------------------------------------------------------
function Write-Head {
    param([string]$Msg)
    Write-Host ""
    Write-Host "=== $Msg ===" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Msg)
    Write-Host "[..] $Msg" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Msg)
    Write-Host "[OK] $Msg" -ForegroundColor Green
}

function Write-Warn2 {
    param([string]$Msg)
    Write-Host "[AVISO] $Msg" -ForegroundColor Yellow
}

function Write-Err2 {
    param([string]$Msg)
    Write-Host "[ERRO] $Msg" -ForegroundColor Red
}

function Wait-UserKey {
    param([string]$Msg = "Aperte Enter para continuar.")
    Read-Host -Prompt $Msg | Out-Null
}

# ---------------------------------------------------------------
# Caminhos do projeto / Hermes
# ---------------------------------------------------------------
function Get-ProjectRoot {
    return (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
}

function Get-HermesHome {
    if ($env:HERMES_HOME -and $env:HERMES_HOME.Trim().Length -gt 0) {
        return $env:HERMES_HOME
    }
    return (Join-Path $env:LOCALAPPDATA 'hermes')
}

function Get-HermesMobileDir {
    return (Join-Path $env:LOCALAPPDATA 'HermesMobile')
}

function Ensure-Dir {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
    return $Path
}

function Get-HermesExe {
    $c = Get-Command hermes.exe -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    $c = Get-Command hermes -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    $alias = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\hermes.exe'
    if (Test-Path -LiteralPath $alias) { return $alias }
    return $null
}

function Invoke-Hermes {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    $exe = Get-HermesExe
    if (-not $exe) { throw "hermes.exe nao encontrado no PATH." }
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $exe @Arguments 2>$null | Out-String
    } finally {
        $ErrorActionPreference = $prev
    }
    return $out.Trim()
}

function Get-HermesVersion {
    try {
        $out = Invoke-Hermes -Arguments @('--version')
        if ($out -match '(\d+\.\d+\.\d+)') { return $Matches[1] }
        return $out
    } catch {
        return "indefinida"
    }
}

function Get-HermesPython {
    $hermesHome = Get-HermesHome

    # 1) Preferir o Python do venv staged (tem httpx, ruamel, plugins etc.)
    $venvCandidates = @()
    $installs = Join-Path $hermesHome 'installs'
    if (Test-Path -LiteralPath $installs) {
        $venvCandidates += Get-ChildItem -LiteralPath $installs -Filter 'python.exe' -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\venv\\Scripts\\python\.exe$' }
    }
    if ($venvCandidates.Count -gt 0) {
        return ($venvCandidates | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
    }

    # 2) Fallback: Python do store (pode nao ter todas as dependencias)
    $tools = Join-Path $hermesHome 'tools'
    if (Test-Path -LiteralPath $tools) {
        $toolCandidates = Get-ChildItem -LiteralPath $tools -Filter 'python.exe' -Recurse -Depth 2 -ErrorAction SilentlyContinue
        if ($toolCandidates.Count -gt 0) {
            return ($toolCandidates | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
        }
    }

    return $null
}

function Get-HermesPayloadRoot {
    try {
        $pkg = Get-AppxPackage -Name '*HermesAgent*' -ErrorAction SilentlyContinue |
            Sort-Object Version -Descending | Select-Object -First 1
        if ($pkg -and $pkg.InstallLocation) {
            $p = Join-Path $pkg.InstallLocation 'app\resources\agent-payload\hermes-agent'
            if (Test-Path -LiteralPath $p) { return $p }
        }
    } catch { }

    $base = 'C:\Program Files\WindowsApps'
    if (Test-Path -LiteralPath $base) {
        $dirs = Get-ChildItem -LiteralPath $base -Directory -Filter 'NousResearchInc.HermesAgent_*' -ErrorAction SilentlyContinue |
            Sort-Object Name -Descending
        foreach ($d in $dirs) {
            $p = Join-Path $d.FullName 'app\resources\agent-payload\hermes-agent'
            if (Test-Path -LiteralPath $p) { return $p }
        }
    }
    return $null
}

# ---------------------------------------------------------------
# .env (leitura/escrita sem BOM, com backup e bloco marcado)
# ---------------------------------------------------------------
function Read-TextNoBom {
    param([Parameter(Mandatory)][string]$Path)
    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
}

function Write-TextNoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $enc)
}

function Backup-File {
    param(
        [Parameter(Mandatory)][string]$Path,
        [string]$Tag = 'backup'
    )
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $dir = Ensure-Dir (Join-Path (Get-HermesMobileDir) 'backups')
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $dest = Join-Path $dir ("{0}-{1}{2}" -f $Tag, $stamp, [System.IO.Path]::GetExtension($Path))
    Copy-Item -LiteralPath $Path -Destination $dest -Force
    return $dest
}

function Set-EnvBlock {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][System.Collections.IDictionary]$Values,
        [string]$Marker = 'Hermes-Mobile'
    )

    if (Test-Path -LiteralPath $Path) {
        $null = Backup-File -Path $Path -Tag '.env'
        $text = Read-TextNoBom -Path $Path
    } else {
        $text = ''
    }

    $lines = $text -split "`r?`n"
    $out = New-Object System.Collections.Generic.List[string]
    $skip = $false
    $startMarker = "# >>> $Marker >>>"
    $endMarker = "# <<< $Marker <<<"

    foreach ($line in $lines) {
        if ($line -eq $startMarker) { $skip = $true; continue }
        if ($line -eq $endMarker) { $skip = $false; continue }
        if ($skip) { continue }

        $parts = $line -split '=', 2
        $key = $parts[0].Trim()
        if ($Values.Contains($key)) { continue }
        $out.Add($line)
    }

    $out.Add($startMarker)
    foreach ($k in $Values.Keys) {
        $out.Add(("{0}={1}" -f $k, $Values[$k]))
    }
    $out.Add($endMarker)

    $new = ($out -join "`r`n")
    if (-not $new.EndsWith("`r`n")) { $new += "`r`n" }
    Write-TextNoBom -Path $Path -Content $new
}

function Get-EnvValue {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Key
    )
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $line = Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue |
        Where-Object { $_ -match ('^\s*' + [regex]::Escape($Key) + '=') } |
        Select-Object -Last 1
    if (-not $line) { return $null }
    return (($line -split '=', 2)[1]).Trim()
}

# ---------------------------------------------------------------
# Segredos do projeto
# ---------------------------------------------------------------
function Get-SecretsPath {
    return (Join-Path (Get-HermesMobileDir) 'secrets.json')
}

function Write-SecretFile {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][System.Collections.IDictionary]$Data
    )
    $dir = Ensure-Dir (Split-Path -Parent $Path)
    $json = ($Data | ConvertTo-Json -Depth 5)
    Write-TextNoBom -Path $Path -Content ($json + "`r`n")

    try {
        $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        # Usar cmd /c: o PowerShell 5.1 mangleia /grant:r quando chamado direto.
        $cmd = 'icacls "' + $Path + '" /inheritance:r /grant:r "' + $me + ':F"'
        & cmd.exe /c $cmd 2>&1 | Out-Null
    } catch {
        Write-Warn2 "Nao foi possivel ajustar a ACL de $Path."
    }
}

function Read-SecretFile {
    $path = Get-SecretsPath
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try {
        return (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        return $null
    }
}

# ---------------------------------------------------------------
# Tokens aleatorios / hash scrypt
# ---------------------------------------------------------------
function New-RandomToken {
    param([int]$Bytes = 24)

    $py = Get-HermesPython
    if ($py) {
        try {
            $out = & $py -c "import secrets; print(secrets.token_urlsafe($Bytes))" 2>$null | Out-String
            $token = $out.Trim()
            if ($token.Length -ge 16) { return $token }
        } catch { }
    }

    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $buf = New-Object byte[] $Bytes
    $rng.GetBytes($buf)
    $b64 = [Convert]::ToBase64String($buf)
    return ($b64 -replace '[^A-Za-z0-9]', '')
}

function Get-PasswordHash {
    param([Parameter(Mandatory)][string]$Password)

    $py = Get-HermesPython
    $root = Get-HermesPayloadRoot
    if (-not $py) { throw "Python do Hermes nao encontrado." }
    if (-not $root) { throw "Payload do Hermes nao encontrado." }

    $env:HERMES_MOBILE_PW = $Password
    $code = "import os,sys; sys.path.insert(0, r'$root'); from plugins.dashboard_auth.basic import hash_password; print(hash_password(os.environ['HERMES_MOBILE_PW']))"
    try {
        $out = & $py -c $code 2>&1 | Out-String
    } finally {
        Remove-Item Env:\HERMES_MOBILE_PW -ErrorAction SilentlyContinue
    }

    $hash = ($out -split "`r?`n" | Where-Object { $_ -match '^scrypt\$' } | Select-Object -First 1)
    if (-not $hash) { throw "Falha ao gerar hash scrypt: $out" }
    return $hash.Trim()
}

# ---------------------------------------------------------------
# Tailscale
# ---------------------------------------------------------------
function Test-TailscaleInstalled {
    return ($null -ne (Get-Command tailscale.exe -ErrorAction SilentlyContinue))
}

function Get-TailscaleSelf {
    if (-not (Test-TailscaleInstalled)) { return $null }
    try {
        $raw = (& tailscale.exe status --json 2>$null | Out-String)
        if (-not $raw -or -not $raw.Trim()) { return $null }
        $json = $raw | ConvertFrom-Json
        if (-not $json) { return $null }

        $selfProp = $json.PSObject.Properties.Match('Self')
        if ($selfProp.Count -eq 0 -or $null -eq $selfProp.Value) { return $null }
        $self = $selfProp.Value

        $tailnetUser = ''
        $tnProp = $json.PSObject.Properties.Match('CurrentTailnet')
        if ($tnProp.Count -gt 0 -and $null -ne $tnProp.Value) {
            $tailnetUser = "$($tnProp.Value.Name)"
        }

        $ip = $null
        $ipProp = $self.PSObject.Properties.Match('TailscaleIPs')
        if ($ipProp.Count -gt 0 -and $null -ne $ipProp.Value) {
            $ip = ($ipProp.Value | Select-Object -First 1)
        }

        return [pscustomobject]@{
            DnsName     = ("$($self.DNSName)" -replace '\.$', '')
            TailscaleIP = $ip
            HostName    = "$($self.HostName)"
            TailnetUser = $tailnetUser
        }
    } catch {
        return $null
    }
}

function Get-TailscaleServeJson {
    if (-not (Test-TailscaleInstalled)) { return $null }
    $raw = (& tailscale.exe serve status --json 2>$null | Out-String)
    if (-not $raw -or -not $raw.Trim() -or $raw.Trim() -eq '{}') { return $null }
    return $raw
}

function Get-TailscaleServeEntry {
    param([Parameter(Mandatory)][int]$Port)

    $raw = Get-TailscaleServeJson
    if (-not $raw) { return $null }
    try { $json = $raw | ConvertFrom-Json } catch { return $null }
    if (-not $json) { return $null }

    $webProp = $json.PSObject.Properties.Match('Web')
    if ($webProp.Count -eq 0 -or $null -eq $webProp.Value) { return $null }

    $entry = $webProp.Value.PSObject.Properties |
        Where-Object { $_.Name -match (':' + $Port + '$') } |
        Select-Object -First 1
    if (-not $entry) { return $null }

    $proxy = $null
    $handlers = $entry.Value.PSObject.Properties.Match('Handlers')
    if ($handlers.Count -gt 0 -and $null -ne $handlers.Value) {
        $root = $handlers.Value.PSObject.Properties.Match('/')
        if ($root.Count -gt 0 -and $null -ne $root.Value) {
            $proxy = "$($root.Value.Proxy)"
        }
    }

    return [pscustomobject]@{
        Host   = $entry.Name
        Port   = $Port
        Proxy  = $proxy
        Raw    = $entry.Value
    }
}

function Test-TailscaleFunnelEnabled {
    $raw = Get-TailscaleServeJson
    if (-not $raw) { return $false }
    try { $json = $raw | ConvertFrom-Json } catch { return $false }
    if (-not $json) { return $false }

    $prop = $json.PSObject.Properties.Match('AllowFunnel')
    if ($prop.Count -eq 0 -or $null -eq $prop.Value) { return $false }

    foreach ($p in $prop.Value.PSObject.Properties) {
        if ($p.Value -eq $true) { return $true }
    }
    return $false
}

function Test-TailscaleServeTarget {
    param(
        [Parameter(Mandatory)][int]$Port,
        [Parameter(Mandatory)][string]$Proxy
    )
    $entry = Get-TailscaleServeEntry -Port $Port
    if (-not $entry) { return $false }
    return ($entry.Proxy -eq $Proxy)
}

# ---------------------------------------------------------------
# Portas / processos / HTTP
# ---------------------------------------------------------------
function Get-PortListeners {
    param([Parameter(Mandatory)][int]$Port)
    return (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Get-ServerProcessOnPort {
    param([Parameter(Mandatory)][int]$Port)

    $conn = Get-PortListeners -Port $Port | Select-Object -First 1
    if (-not $conn) { return $null }

    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($conn.OwningProcess)" -ErrorAction SilentlyContinue
    $name = ''
    $cmd = ''
    if ($proc) {
        $name = "$($proc.Name)"
        $cmd = "$($proc.CommandLine)"
    }

    return [pscustomobject]@{
        Pid         = $conn.OwningProcess
        Name        = $name
        CommandLine = $cmd
        LocalAddress= $conn.LocalAddress
        LocalPort   = $conn.LocalPort
    }
}

function Stop-ServerOnPort {
    param([Parameter(Mandatory)][int]$Port)

    $p = Get-ServerProcessOnPort -Port $Port
    if (-not $p) { return $false }

    if ($p.CommandLine -notmatch 'hermes' -or $p.CommandLine -notmatch 'serve') {
        throw "A porta $Port esta em uso pelo PID $($p.Pid) ($($p.Name)), que nao parece ser o 'hermes serve'. Nao vou parar."
    }

    Stop-Process -Id $p.Pid -Force -ErrorAction Stop
    return $true
}

function Start-HermesServeDetached {
    param([Parameter(Mandatory)][int]$Port)

    $exe = Get-HermesExe
    if (-not $exe) { throw "hermes.exe nao encontrado." }

    $hermesHome = Get-HermesHome
    $mobileDir = Ensure-Dir (Get-HermesMobileDir)
    $vbs = Join-Path $mobileDir ("Iniciar-HermesServe-{0}.vbs" -f $Port)

    $content = @"
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "$hermesHome"
sh.Run """$exe"" serve --host 127.0.0.1 --port $Port --skip-build", 0, False
"@

    Write-TextNoBom -Path $vbs -Content ($content -replace "`r?`n", "`r`n")
    $p = Start-Process -FilePath 'wscript.exe' -ArgumentList @("`"$vbs`"") -WindowStyle Hidden -PassThru
    return [pscustomobject]@{ Vbs = $vbs; WscriptPid = $p.Id }
}

function Test-HttpCode {
    param(
        [Parameter(Mandatory)][string]$Url,
        [int]$TimeoutSeconds = 10
    )
    try {
        $code = (& curl.exe -s -m $TimeoutSeconds -o NUL -w "%{http_code}" $Url 2>$null | Out-String).Trim()
        if ($code -match '^\d{3}$') { return $code }
        return '000'
    } catch {
        return '000'
    }
}

function Get-HttpBody {
    param(
        [Parameter(Mandatory)][string]$Url,
        [int]$TimeoutSeconds = 10
    )
    try {
        return ((& curl.exe -s -m $TimeoutSeconds $Url 2>$null | Out-String).Trim())
    } catch {
        return ''
    }
}

function Wait-Http {
    param(
        [Parameter(Mandatory)][string]$Url,
        [int]$TimeoutSeconds = 60,
        [int[]]$Accept = @(200, 301, 302, 303, 307, 308, 401, 403)
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $code = Test-HttpCode -Url $Url
        if ($code -match '^\d{3}$' -and ($Accept -contains [int]$code)) { return $code }
        Start-Sleep -Milliseconds 500
    }
    return $null
}

# ---------------------------------------------------------------
# Admin / tarefas
# ---------------------------------------------------------------
function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-HermesMobileTask {
    return (Get-ScheduledTask -TaskName 'Hermes Mobile - Servidor' -ErrorAction SilentlyContinue)
}
