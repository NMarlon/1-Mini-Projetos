# ======================================================================
# Instalar-Autostart.ps1
#
# O QUE FAZ:
#   1. Cria a Tarefa Agendada "Hermes Mobile - Servidor" no logon.
#      (Se o Task Scheduler recusar, usa a pasta Startup como fallback.)
#   2. Cria o atalho "Hermes Mobile" na area de trabalho (URL do tailnet).
#
# QUANDO RODAR: depois de validar o acesso manualmente.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File .\scripts\Instalar-Autostart.ps1
# ======================================================================

[CmdletBinding()]
param(
    [int]$Porta = 9119,
    [switch]$SemAtalho
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lib\common.ps1"

Write-Head "Instalar autostart"

$root = Get-ProjectRoot
$script = Join-Path $root 'scripts\Iniciar-Servidor.ps1'
$taskName = 'Hermes Mobile - Servidor'
$me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

if (-not (Test-Path -LiteralPath $script)) {
    Write-Err2 ("Script nao encontrado: {0}" -f $script)
    exit 1
}

$taskInstalled = $false
try {
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' `
        -Argument ("-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"{0}`" -Porta {1} -Foreground" -f $script, $Porta)

    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

    $principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero)

    $task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings

    Register-ScheduledTask -TaskName $taskName -InputObject $task -Force -ErrorAction Stop | Out-Null
    $taskInstalled = $true
    Write-Ok ("Tarefa Agendada '{0}' criada." -f $taskName)

    # Limpar fallback antigo, se existir
    $oldStartupLnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'Hermes Mobile.lnk'
    if (Test-Path -LiteralPath $oldStartupLnk) { Remove-Item -LiteralPath $oldStartupLnk -Force }
    $oldVbs = Join-Path (Get-HermesMobileDir) 'Iniciar-HermesMobile.vbs'
    if (Test-Path -LiteralPath $oldVbs) { Remove-Item -LiteralPath $oldVbs -Force }
} catch {
    Write-Warn2 ("Nao foi possivel criar a Tarefa Agendada: {0}" -f $_.Exception.Message)
    Write-Step "Usando fallback: pasta Startup + VBS."
}

if (-not $taskInstalled) {
    $mobileDir = Ensure-Dir (Get-HermesMobileDir)
    $vbs = Join-Path $mobileDir 'Iniciar-HermesMobile.vbs'
    $vbsContent = @"
Set sh = CreateObject("WScript.Shell")
sh.Run "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""$script"" -Porta $Porta -Foreground", 0, False
"@
    [System.IO.File]::WriteAllText($vbs, $vbsContent, (New-Object System.Text.UTF8Encoding($false)))

    $startup = [Environment]::GetFolderPath('Startup')
    $startupLnk = Join-Path $startup 'Hermes Mobile.lnk'
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut($startupLnk)
    $sc.TargetPath = 'wscript.exe'
    $sc.Arguments = '"' + $vbs + '"'
    $sc.WindowStyle = 7
    $sc.Save()
    Write-Ok ("Fallback criado: {0}" -f $startupLnk)
}

# --- Atalho na area de trabalho -------------------------------------
if (-not $SemAtalho) {
    $self = Get-TailscaleSelf
    if ($self) {
        $url = "https://$($self.DnsName):8443"
        try {
            $desktop = [Environment]::GetFolderPath('Desktop')
            $urlFile = Join-Path $desktop 'Hermes Mobile.url'
            $content = "[InternetShortcut]`r`nURL=$url`r`nIconFile=$env:SystemRoot\System32\SHELL32.dll`r`nIconIndex=13`r`n"
            Write-TextNoBom -Path $urlFile -Content $content

            # Remover .lnk antigo/vazio, se existir
            $oldLnk = Join-Path $desktop 'Hermes Mobile.lnk'
            if (Test-Path -LiteralPath $oldLnk) { Remove-Item -LiteralPath $oldLnk -Force }

            Write-Ok ("Atalho criado: {0}" -f $urlFile)
        } catch {
            Write-Warn2 "Nao foi possivel criar o atalho na area de trabalho."
        }
    } else {
        Write-Warn2 "Tailscale sem status; atalho nao criado."
    }
}

# --- Verificacao -----------------------------------------------------
$task = Get-HermesMobileTask
if ($task) {
    Write-Ok ("Tarefa '{0}' presente (estado: {1})." -f $task.TaskName, $task.State)
} elseif (-not $taskInstalled) {
    Write-Ok "Fallback na pasta Startup presente."
}

Write-Host ""
Write-Host "O servidor sera iniciado no proximo logon."
Write-Host "Para testar agora:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\Iniciar-Mobile.ps1"
