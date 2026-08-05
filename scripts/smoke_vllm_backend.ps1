param(
    [string]$BaseUrl = "http://127.0.0.1:8001/v1",
    [Parameter(Mandatory = $true)]
    [string]$Model,
    [int]$TimeoutSeconds = 300,
    [string]$ApiKey = "uaea-local"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

Invoke-RestMethod -Uri "$($BaseUrl.TrimEnd('/'))/models" -Method Get -TimeoutSec 10 | Out-Null

$env:UAEA_BACKEND = "vllm"
$env:UAEA_BACKEND_BASE_URL = $BaseUrl.TrimEnd("/")
$env:UAEA_BACKEND_MODEL = $Model
$env:UAEA_BACKEND_TIMEOUT = $TimeoutSeconds.ToString()
$env:UAEA_BACKEND_API_KEY = $ApiKey

Push-Location $projectRoot
try {
    python main.py
}
finally {
    Pop-Location
}
