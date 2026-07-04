<#
Starts a dedicated Ollama instance for YEYO-HACK (uncensored models like dolphin-llama3).

Why:
- Keep the "normal" assistant model separate from red-team testing.
- Run on a different port (default 11435) and with a separate models directory.

Usage:
  powershell -ExecutionPolicy Bypass -File .\scripts\start-ollama-hack.ps1

Optional:
  powershell -ExecutionPolicy Bypass -File .\scripts\start-ollama-hack.ps1 -Pull
  powershell -ExecutionPolicy Bypass -File .\scripts\start-ollama-hack.ps1 -Host 0.0.0.0:11435
#>

param(
    [string]$Host = "127.0.0.1:11435",
    [string]$Model = "dolphin-llama3",
    [string]$ModelsDir = "$env:USERPROFILE\.ollama-hack\models",
    [switch]$Pull
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "[YEYO-HACK] Ollama CLI not found. Install Ollama first (https://ollama.com)." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null

# Ollama uses host:port (no scheme) for serve binding.
$env:OLLAMA_HOST = $Host
$env:OLLAMA_MODELS = $ModelsDir

Write-Host "[YEYO-HACK] OLLAMA_HOST=$($env:OLLAMA_HOST)"
Write-Host "[YEYO-HACK] OLLAMA_MODELS=$($env:OLLAMA_MODELS)"
Write-Host "[YEYO-HACK] Model (recommended): $Model"

if ($Pull) {
    Write-Host "[YEYO-HACK] Pulling model: $Model ..."
    ollama pull $Model
}

Write-Host "[YEYO-HACK] Starting ollama serve (Ctrl+C to stop)..."
ollama serve
