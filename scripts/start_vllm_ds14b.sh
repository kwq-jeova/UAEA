#!/usr/bin/env bash
set -euo pipefail

VENV_ROOT="${VLLM_VENV_ROOT:-/opt/uaea/vllm_env}"
MODEL_ROOT="${VLLM_DS14B_MODEL_ROOT:-/opt/uaea-models/models/DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4}"
SERVED_MODEL_NAME="${VLLM_DS14B_MODEL_NAME:-ds14b-awq}"
HOST="${VLLM_DS14B_HOST:-0.0.0.0}"
PORT="${VLLM_DS14B_PORT:-8001}"
CUDA_ROOT="${VLLM_CUDA_ROOT:-${VENV_ROOT}/lib/python3.12/site-packages/nvidia/cu13}"

if [[ ! -x "${VENV_ROOT}/bin/vllm" ]]; then
    printf 'vLLM executable not found: %s\n' "${VENV_ROOT}/bin/vllm" >&2
    exit 1
fi

if [[ ! -f "${MODEL_ROOT}/config.json" ]]; then
    printf 'Complete DS14B model not found: %s\n' "${MODEL_ROOT}" >&2
    exit 1
fi

if [[ ! -f "${MODEL_ROOT}/model.safetensors.index.json" && ! -f "${MODEL_ROOT}/model.safetensors" ]]; then
    printf 'Complete DS14B model weights not found: %s\n' "${MODEL_ROOT}" >&2
    exit 1
fi

export HF_HOME="${HF_HOME:-/opt/uaea-models/cache}"
export CUDA_HOME="${CUDA_HOME:-${CUDA_ROOT}}"
export PATH="${VENV_ROOT}/bin:${CUDA_HOME}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export VLLM_USE_V2_MODEL_RUNNER="${VLLM_USE_V2_MODEL_RUNNER:-0}"
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"

exec "${VENV_ROOT}/bin/vllm" serve "${MODEL_ROOT}" \
    --served-model-name "${SERVED_MODEL_NAME}" \
    --dtype half \
    --max-model-len 16384 \
    --gpu-memory-utilization 0.7 \
    --host "${HOST}" \
    --port "${PORT}"
