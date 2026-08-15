#!/usr/bin/env bash
set -euo pipefail

PROFILE_NAME="${1:?usage: run_vllm_kernel_profile_diagnostic.sh <profile-name> [extra-vllm-args...]}"
shift || true

VENV_ROOT="${VLLM_VENV_ROOT:-/opt/uaea/vllm_env}"
MODEL_ROOT="${VLLM_DS14B_MODEL_ROOT:-/opt/uaea-models/models/DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4}"
SERVED_MODEL_NAME="${VLLM_DS14B_MODEL_NAME:-ds14b-awq}"
HOST="${VLLM_DS14B_HOST:-0.0.0.0}"
PORT="${VLLM_DS14B_PORT:-8001}"
CUDA_ROOT="${VLLM_CUDA_ROOT:-${VENV_ROOT}/lib/python3.12/site-packages/nvidia/cu13}"
RUN_ROOT="${VLLM_DIAG_RUN_ROOT:-/opt/uaea-runtime/vllm/kernel-diagnostics}"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="${RUN_ROOT}/${STAMP}_${PROFILE_NAME}"
mkdir -p "${RUN_DIR}"

LOG_FILE="${RUN_DIR}/vllm.log"
PID_FILE="${RUN_DIR}/vllm.pid"
RESULT_FILE="/mnt/d/UAEA/data/diagnostics/vllm_kernel_profile_${PROFILE_NAME}_${STAMP}.json"

export HF_HOME="${HF_HOME:-/opt/uaea-models/cache}"
export CUDA_HOME="${CUDA_HOME:-${CUDA_ROOT}}"
export PATH="${VENV_ROOT}/bin:${CUDA_HOME}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export VLLM_USE_V2_MODEL_RUNNER="${VLLM_USE_V2_MODEL_RUNNER:-0}"
export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"

stop_pid() {
    local pid="${1:-}"
    if [[ -z "${pid}" ]]; then
        return 0
    fi
    if kill -0 "${pid}" 2>/dev/null; then
        kill "${pid}" 2>/dev/null || true
        for _ in $(seq 1 45); do
            if ! kill -0 "${pid}" 2>/dev/null; then
                return 0
            fi
            sleep 1
        done
        kill -9 "${pid}" 2>/dev/null || true
    fi
}

if ss -ltnp 2>/dev/null | grep -q ":${PORT}"; then
    echo "Port ${PORT} is already in use. Stop the existing service before running this diagnostic." | tee "${RUN_DIR}/error.txt" >&2
    exit 2
fi

echo "profile=${PROFILE_NAME}" > "${RUN_DIR}/metadata.txt"
echo "extra_args=$*" >> "${RUN_DIR}/metadata.txt"
echo "result_file=${RESULT_FILE}" >> "${RUN_DIR}/metadata.txt"

(
    exec "${VENV_ROOT}/bin/vllm" serve "${MODEL_ROOT}" \
        --served-model-name "${SERVED_MODEL_NAME}" \
        --dtype half \
        --max-model-len 16384 \
        --gpu-memory-utilization 0.7 \
        --host "${HOST}" \
        --port "${PORT}" \
        "$@"
) > "${LOG_FILE}" 2>&1 &

VLLM_PID="$!"
echo "${VLLM_PID}" > "${PID_FILE}"

cleanup() {
    stop_pid "${VLLM_PID}"
}
trap cleanup EXIT

READY=0
for _ in $(seq 1 240); do
    if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
        READY=1
        break
    fi
    if ! kill -0 "${VLLM_PID}" 2>/dev/null; then
        break
    fi
    sleep 2
done

if [[ "${READY}" != "1" ]]; then
    echo "vLLM profile ${PROFILE_NAME} did not become healthy." | tee "${RUN_DIR}/error.txt" >&2
    tail -200 "${LOG_FILE}" || true
    exit 3
fi

python /mnt/d/UAEA/scripts/diagnose_awq_hf_vs_vllm_isolation.py \
    --skip-hf \
    --vllm-url "http://127.0.0.1:${PORT}/v1" \
    --vllm-model "${SERVED_MODEL_NAME}" \
    --output "${RESULT_FILE}"

echo "result_file=${RESULT_FILE}"
echo "log_file=${LOG_FILE}"
