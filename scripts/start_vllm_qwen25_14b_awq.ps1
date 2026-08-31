param(
    [string]$VllmVenvRoot = "/opt/uaea/vllm_env",
    [string]$ModelRoot = "/opt/uaea-models/models/Qwen2.5-14B-Instruct-AWQ",
    [string]$ServedModelName = "qwen25-14b-awq",
    [string]$HostName = "0.0.0.0",
    [int]$Port = 8001,
    [int]$MaxModelLen = 8192,
    [double]$GpuMemoryUtilization = 0.7,
    [string]$CudaRoot = "/opt/uaea/vllm_env/lib/python3.12/site-packages/nvidia/cu13",
    [string]$HfHome = "/opt/uaea-models/cache"
)

$ErrorActionPreference = "Stop"

$bash = @"
set -euo pipefail

VENV_ROOT="$VllmVenvRoot"
MODEL_ROOT="$ModelRoot"
SERVED_MODEL_NAME="$ServedModelName"
HOST="$HostName"
PORT="$Port"
CUDA_ROOT="$CudaRoot"
HF_HOME_VALUE="$HfHome"

if [[ ! -x "`${VENV_ROOT}/bin/vllm" ]]; then
    printf 'vLLM executable not found: %s\n' "`${VENV_ROOT}/bin/vllm" >&2
    exit 1
fi

if [[ ! -f "`${MODEL_ROOT}/config.json" ]]; then
    printf 'Qwen2.5-14B-AWQ model config not found: %s\n' "`${MODEL_ROOT}" >&2
    exit 1
fi

if [[ ! -f "`${MODEL_ROOT}/model.safetensors.index.json" && ! -f "`${MODEL_ROOT}/model.safetensors" ]]; then
    printf 'Qwen2.5-14B-AWQ model weights not found: %s\n' "`${MODEL_ROOT}" >&2
    exit 1
fi

export HF_HOME="`${HF_HOME_VALUE}"
export CUDA_HOME="`${CUDA_ROOT}"
export PATH="`${VENV_ROOT}/bin:`${CUDA_HOME}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export VLLM_USE_V2_MODEL_RUNNER=0
export VLLM_USE_FLASHINFER_SAMPLER=0

printf 'Starting vLLM: model=%s served=%s endpoint=http://127.0.0.1:%s/v1\n' "`${MODEL_ROOT}" "`${SERVED_MODEL_NAME}" "`${PORT}"

exec "`${VENV_ROOT}/bin/vllm" serve "`${MODEL_ROOT}" \
    --served-model-name "`${SERVED_MODEL_NAME}" \
    --dtype half \
    --max-model-len "$MaxModelLen" \
    --gpu-memory-utilization "$GpuMemoryUtilization" \
    --host "`${HOST}" \
    --port "`${PORT}"
"@

$bash | wsl -e bash -s
exit $LASTEXITCODE
