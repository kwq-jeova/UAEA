param(
    [string]$BaseUrl = "http://127.0.0.1:8001/v1",
    [string]$Model = "qwen25-14b-awq",
    [int]$TimeoutSeconds = 300,
    [string]$ApiKey = "uaea-local",
    [string]$PythonExe = ".\.venv_memory\Scripts\python.exe",
    [switch]$SkipHealthCheck
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$baseUrl = $BaseUrl.TrimEnd("/")
$pythonPath = Join-Path $projectRoot $PythonExe

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python executable not found: $pythonPath"
}

if (-not $SkipHealthCheck) {
    Invoke-RestMethod -Uri "$baseUrl/models" -Method Get -TimeoutSec 10 | Out-Null
}

$env:UAEA_BACKEND = "vllm"
$env:UAEA_BACKEND_BASE_URL = $baseUrl
$env:UAEA_BACKEND_MODEL = $Model
$env:UAEA_BACKEND_TIMEOUT = $TimeoutSeconds.ToString()
$env:UAEA_BACKEND_API_KEY = $ApiKey

Write-Host "Starting UAEA Web REPL with backend=vllm model=$Model endpoint=$baseUrl"

Push-Location $projectRoot
try {
    & $pythonPath -m phase2.web_repl
}
finally {
    Pop-Location
}
