# Adobe MCP Server — Installation Script
# Installs deps + configures Claude Code CLI + Claude Desktop App
# Run: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Auto-detect Python executable
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    $PythonExe = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}
if (-not $PythonExe) {
    Write-Host "ERROR: Python not found in PATH. Install Python 3.10+ from https://python.org" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Adobe MCP Server Installer ===" -ForegroundColor Cyan

# 1. Install Python dependencies
Write-Host "`n[1/3] Installing Python dependencies..." -ForegroundColor Yellow
& $PythonExe -m pip install "mcp[cli]" pydantic httpx --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: pip install failed" -ForegroundColor Red; exit 1 }
Write-Host "  Dependencies installed." -ForegroundColor Green

# 2. Configure Claude Code CLI (~/.claude/settings.json)
Write-Host "`n[2/3] Configuring Claude Code CLI..." -ForegroundColor Yellow
$claudeCodeSettings = "$env:USERPROFILE\.claude\settings.json"
if (Test-Path $claudeCodeSettings) {
    $settings = Get-Content $claudeCodeSettings -Raw | ConvertFrom-Json
    if (-not $settings.mcpServers) {
        $settings | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue @{} -Force
    }
    $adobeMcp = @{ command = $PythonExe; args = @("$ScriptDir\adobe_mcp.py") }
    $settings.mcpServers | Add-Member -NotePropertyName "adobe_mcp" -NotePropertyValue $adobeMcp -Force
    $settings | ConvertTo-Json -Depth 10 | Set-Content $claudeCodeSettings -Encoding UTF8
    Write-Host "  Claude Code CLI configured." -ForegroundColor Green
} else {
    Write-Host "  WARNING: Settings not found, creating..." -ForegroundColor Yellow
    $s = @{ mcpServers = @{ adobe_mcp = @{ command = $PythonExe; args = @("$ScriptDir\adobe_mcp.py") } } }
    New-Item -ItemType Directory -Path (Split-Path $claudeCodeSettings) -Force | Out-Null
    $s | ConvertTo-Json -Depth 10 | Set-Content $claudeCodeSettings -Encoding UTF8
}

# 3. Configure Claude Desktop App (%APPDATA%\Claude\claude_desktop_config.json)
Write-Host "`n[3/3] Configuring Claude Desktop App..." -ForegroundColor Yellow
$claudeDesktopConfig = "$env:APPDATA\Claude\claude_desktop_config.json"
if (Test-Path $claudeDesktopConfig) {
    $config = Get-Content $claudeDesktopConfig -Raw | ConvertFrom-Json
    if (-not $config.mcpServers) {
        $config | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue @{} -Force
    }
    $adobeMcp = @{ command = $PythonExe; args = @("$ScriptDir\adobe_mcp.py") }
    $config.mcpServers | Add-Member -NotePropertyName "adobe_mcp" -NotePropertyValue $adobeMcp -Force
    $config | ConvertTo-Json -Depth 10 | Set-Content $claudeDesktopConfig -Encoding UTF8
    Write-Host "  Claude Desktop App configured." -ForegroundColor Green
} else {
    Write-Host "  Creating config..." -ForegroundColor Yellow
    $c = @{ mcpServers = @{ adobe_mcp = @{ command = $PythonExe; args = @("$ScriptDir\adobe_mcp.py") } } }
    New-Item -ItemType Directory -Path (Split-Path $claudeDesktopConfig) -Force | Out-Null
    $c | ConvertTo-Json -Depth 10 | Set-Content $claudeDesktopConfig -Encoding UTF8
}

Write-Host "`n=== Installation Complete ===" -ForegroundColor Cyan
Write-Host "Server: $ScriptDir\adobe_mcp.py"
Write-Host "Python: $PythonExe"
Write-Host "`nRestart both apps to activate:" -ForegroundColor Yellow
Write-Host "  1. Claude Code CLI: close terminal, reopen, run 'claude'"
Write-Host "  2. Claude Desktop: right-click tray > Quit, then relaunch"
Write-Host ""
