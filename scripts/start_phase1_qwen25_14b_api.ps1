param(
    [string]$ModelPath = "D:\LM_Studio_Models\Qwen\Qwen2.5-14B-Instruct",
    [string]$Template = "qwen",
    [int]$QuantizationBit = 4,
    [string]$CudaVisibleDevices = "0",
    [string]$UaeaRoot = "D:\AI_Agent_FW"
)

$ErrorActionPreference = "Stop"

$venvRoot = Join-Path $UaeaRoot ".venv_lmf_api"
$python = Join-Path $venvRoot "Scripts\python.exe"
$lmfCli = Join-Path $venvRoot "Scripts\llamafactory-cli.exe"

function Assert-PathExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Name not found: $Path"
    }
}

Assert-PathExists -Path $python -Name "LLaMA-Factory API python"
Assert-PathExists -Path $lmfCli -Name "LLaMA-Factory API CLI"
Assert-PathExists -Path $ModelPath -Name "Qwen2.5-14B-Instruct model"
Assert-PathExists -Path (Join-Path $ModelPath "config.json") -Name "Qwen2.5 config"
Assert-PathExists -Path (Join-Path $ModelPath "model.safetensors.index.json") -Name "Qwen2.5 safetensors index"

if ($QuantizationBit -ne 4) {
    throw "Qwen2.5-14B benchmark must use 4-bit HuggingFace/bitsandbytes loading on 24GB VRAM. Current QuantizationBit=$QuantizationBit."
}

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:CUDA_VISIBLE_DEVICES = $CudaVisibleDevices
$env:BITSANDBYTES_NOWELCOME = "1"

$cudaStatus = & $python -c "import torch; print('1' if torch.cuda.is_available() else '0')"
if ($cudaStatus.Trim() -ne "1") {
    throw "CUDA is not available in $venvRoot. Do not start Qwen2.5 endpoint from this environment."
}

$bnbStatus = & $python -c "import importlib.util; print('1' if importlib.util.find_spec('bitsandbytes') else '0')"
if ($bnbStatus.Trim() -ne "1") {
    throw "bitsandbytes is missing in $venvRoot. 4-bit Qwen2.5-14B loading requires it on 24GB VRAM."
}

Write-Host "Starting LLaMA-Factory OpenAI-compatible API for Qwen2.5-14B-Instruct"
Write-Host "ModelPath       : $ModelPath"
Write-Host "Template        : $Template"
Write-Host "QuantizationBit : $QuantizationBit"
Write-Host "Endpoint        : http://127.0.0.1:8000/v1"

& $lmfCli api `
    --model_name_or_path $ModelPath `
    --template $Template `
    --infer_backend huggingface `
    --quantization_bit $QuantizationBit
