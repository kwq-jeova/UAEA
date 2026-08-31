#!/usr/bin/env bash
set -euo pipefail

VENV_ROOT="${VLLM_VENV_ROOT:-/opt/uaea/vllm_env}"
MODEL_ROOT="${VLLM_QWEN25_AWQ_MODEL_ROOT:-/opt/uaea-models/models/Qwen2.5-14B-Instruct-AWQ}"
SERVED_MODEL_NAME="${VLLM_QWEN25_AWQ_MODEL_NAME:-qwen25-14b-awq}"
HOST="${VLLM_QWEN25_AWQ_HOST:-0.0.0.0}"
PORT="${VLLM_QWEN25_AWQ_PORT:-8001}"
MAX_MODEL_LEN="${VLLM_QWEN25_AWQ_MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTILIZATION="${VLLM_QWEN25_AWQ_GPU_MEMORY_UTILIZATION:-0.7}"
CUDA_ROOT="${VLLM_CUDA_ROOT:-${VENV_ROOT}/lib/python3.12/site-packages/nvidia/cu13}"

if [[ ! -x "${VENV_ROOT}/bin/vllm" ]]; then
    printf 'vLLM executable not found: %s\n' "${VENV_ROOT}/bin/vllm" >&2
    exit 1
fi

if [[ ! -f "${MODEL_ROOT}/config.json" ]]; then
    printf 'Qwen2.5-14B-AWQ model config not found: %s\n' "${MODEL_ROOT}" >&2
    exit 1
fi

if [[ ! -f "${MODEL_ROOT}/model.safetensors.index.json" && ! -f "${MODEL_ROOT}/model.safetensors" ]]; then
    printf 'Qwen2.5-14B-AWQ model weights not found: %s\n' "${MODEL_ROOT}" >&2
    exit 1
fi

export HF_HOME="${HF_HOME:-/opt/uaea-models/cache}"
export CUDA_HOME="${CUDA_HOME:-${CUDA_ROOT}}"
export PATH="${VENV_ROOT}/bin:${CUDA_HOME}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export VLLM_USE_V2_MODEL_RUNNER="${VLLM_USE_V2_MODEL_RUNNER:-0}"
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"

printf 'Starting vLLM: model=%s served=%s endpoint=http://127.0.0.1:%s/v1\n' \
    "${MODEL_ROOT}" "${SERVED_MODEL_NAME}" "${PORT}"

exec "${VENV_ROOT}/bin/vllm" serve "${MODEL_ROOT}" \
    --served-model-name "${SERVED_MODEL_NAME}" \
    --dtype half \
    --max-model-len "${MAX_MODEL_LEN}" \
    --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
    --host "${HOST}" \
    --port "${PORT}"
