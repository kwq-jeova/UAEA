param(
    [string]$Phase1Root = "D:\UAEA-phase1-runtime-v1.0",
    [string]$ApiBaseUrl = "http://127.0.0.1:8000/v1",
    [string]$ModelName = "Qwen2.5-14B-Instruct",
    [int]$TimeoutSeconds = 300,
    [string]$Level = "all",
    [string]$Case = "",
    [string]$ArtifactRoot = "D:\UAEA\data\phase1_qwen25_14b_benchmark",
    [switch]$NoJson
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$runner = Join-Path $scriptRoot "run_phase1_qwen25_14b_benchmark.py"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Benchmark wrapper not found: $runner"
}

if (-not (Test-Path -LiteralPath $Phase1Root)) {
    throw "Frozen Phase-1 root not found: $Phase1Root"
}

$argsList = @(
    $runner,
    "--phase1-root", $Phase1Root,
    "--api-base-url", $ApiBaseUrl,
    "--model-name", $ModelName,
    "--timeout", $TimeoutSeconds.ToString(),
    "--level", $Level,
    "--artifact-root", $ArtifactRoot
)

if ($Case) {
    $argsList += @("--case", $Case)
}

if (-not $NoJson) {
    $argsList += "--json"
}

python @argsList
