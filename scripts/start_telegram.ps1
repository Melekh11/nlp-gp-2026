param(
    [string]$TelegramToken = $env:TELEGRAM_TOKEN,
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$CloudflaredPath = "cloudflared",
    [string]$ModelPath = "",
    [switch]$KeepExisting
)

$ErrorActionPreference = "Stop"

function Stop-PortProcess {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        if ($connection.OwningProcess) {
            Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

function Wait-HttpJson {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 180
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            return Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 3
        }
        catch {
            Start-Sleep -Seconds 3
        }
    }
    throw "Timeout while waiting for $Url"
}

function Wait-TunnelUrl {
    param(
        [string]$LogPath,
        [int]$TimeoutSeconds = 90
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path $LogPath) {
            $content = Get-Content -Path $LogPath -Raw -ErrorAction SilentlyContinue
            $match = [regex]::Match($content, "https://[a-zA-Z0-9-]+\.trycloudflare\.com")
            if ($match.Success) {
                return $match.Value
            }
        }
        Start-Sleep -Seconds 2
    }
    throw "Cloudflared URL was not found in $LogPath"
}

Set-Location $ProjectRoot

if (-not $TelegramToken -or $TelegramToken -eq "TOKEN_FROM_BOTFATHER") {
    throw "Pass a real Telegram token: .\scripts\start_telegram.ps1 -TelegramToken '123456:ABC...'"
}

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python venv was not found: $python. Create .venv and install requirements first."
}

$cloudflaredCommand = Get-Command $CloudflaredPath -ErrorAction SilentlyContinue
if ($cloudflaredCommand) {
    $CloudflaredPath = $cloudflaredCommand.Source
}
elseif (-not (Test-Path $CloudflaredPath)) {
    throw "cloudflared was not found. Add it to PATH or pass -CloudflaredPath 'C:\tools\cloudflared\cloudflared.exe'."
}

if (-not $ModelPath) {
    $model = Get-ChildItem -Path (Join-Path $ProjectRoot "models") -Filter "*.tar.gz" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $model) {
        throw "No model found in models/. Run: .\.venv\Scripts\python.exe -m rasa train --force"
    }
    $ModelPath = $model.FullName
}

if (-not (Test-Path (Join-Path $ProjectRoot "credentials.yml"))) {
    throw "credentials.yml was not found. Create it using README section 10.3."
}

New-Item -ItemType Directory -Path (Join-Path $ProjectRoot ".runtime") -Force | Out-Null

$actionOut = Join-Path $ProjectRoot ".runtime\actions.out.log"
$actionErr = Join-Path $ProjectRoot ".runtime\actions.err.log"
$rasaOut = Join-Path $ProjectRoot ".runtime\rasa.out.log"
$rasaErr = Join-Path $ProjectRoot ".runtime\rasa.err.log"
$cloudOut = Join-Path $ProjectRoot ".runtime\cloudflared.out.log"
$cloudErr = Join-Path $ProjectRoot ".runtime\cloudflared.err.log"
$cloudLog = Join-Path $ProjectRoot ".runtime\cloudflared.log"

Remove-Item -LiteralPath $actionOut, $actionErr, $rasaOut, $rasaErr, $cloudOut, $cloudErr, $cloudLog -ErrorAction SilentlyContinue

if (-not $KeepExisting) {
    Stop-PortProcess -Port 5005
    Stop-PortProcess -Port 5055
    Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

$env:TEMP = "C:\rasa_tmp"
$env:TMP = "C:\rasa_tmp"
$env:PYTHONIOENCODING = "utf-8"
$env:SQLALCHEMY_SILENCE_UBER_WARNING = "1"
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null

Write-Host "Starting action server on http://127.0.0.1:5055 ..."
Start-Process -FilePath $python `
    -ArgumentList @("-m", "rasa", "run", "actions", "--actions", "actions") `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $actionOut `
    -RedirectStandardError $actionErr

Wait-HttpJson -Url "http://127.0.0.1:5055/health" -TimeoutSeconds 90 | Out-Null

Write-Host "Starting cloudflared tunnel to http://127.0.0.1:5005 ..."
Start-Process -FilePath $CloudflaredPath `
    -ArgumentList @("tunnel", "--url", "http://127.0.0.1:5005", "--no-autoupdate", "--logfile", $cloudLog) `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $cloudOut `
    -RedirectStandardError $cloudErr

$publicUrl = Wait-TunnelUrl -LogPath $cloudLog -TimeoutSeconds 120
$webhookUrl = "$publicUrl/webhooks/telegram/webhook"

$env:TELEGRAM_TOKEN = $TelegramToken
$env:TELEGRAM_WEBHOOK_URL = $webhookUrl

Write-Host "Starting Rasa server on http://127.0.0.1:5005 ..."
Write-Host "Tunnel: $publicUrl"
Start-Process -FilePath $python `
    -ArgumentList @("-m", "rasa", "run", "--enable-api", "--credentials", "credentials.yml", "--endpoints", "endpoints.yml", "--model", $ModelPath, "--cors", "*") `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $rasaOut `
    -RedirectStandardError $rasaErr

Wait-HttpJson -Url "http://127.0.0.1:5005/status" -TimeoutSeconds 360 | Out-Null

Write-Host "Setting Telegram webhook ..."
$setWebhook = Invoke-RestMethod -Uri "https://api.telegram.org/bot$TelegramToken/setWebhook" -Method Post -Body @{
    url = $webhookUrl
    drop_pending_updates = "true"
}
if (-not $setWebhook.ok) {
    throw "Telegram setWebhook failed: $($setWebhook.description)"
}

$webhookInfo = Invoke-RestMethod -Uri "https://api.telegram.org/bot$TelegramToken/getWebhookInfo" -Method Get

Write-Host ""
Write-Host "Telegram bot is running."
Write-Host "Public URL: $publicUrl"
Write-Host "Webhook URL: $($webhookInfo.result.url)"
Write-Host "Pending updates: $($webhookInfo.result.pending_update_count)"
Write-Host "Logs: .runtime\"
Write-Host "Send /start to the bot in Telegram."
