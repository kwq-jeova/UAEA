#!/usr/bin/env bash
set -euo pipefail

PORT="${VLLM_DS14B_PORT:-8001}"
PID_FILE="${VLLM_DS14B_PID_FILE:-/opt/uaea-runtime/vllm/pid/ds14b_smoke.pid}"

stop_pid() {
    local pid="$1"
    if [[ -z "${pid}" ]]; then
        return 1
    fi
    if ! kill -0 "${pid}" 2>/dev/null; then
        return 1
    fi
    kill "${pid}" 2>/dev/null || true
    for _ in $(seq 1 30); do
        if ! kill -0 "${pid}" 2>/dev/null; then
            return 0
        fi
        sleep 1
    done
    kill -9 "${pid}" 2>/dev/null || true
}

if [[ -f "${PID_FILE}" ]]; then
    pid="$(tr -d '[:space:]' < "${PID_FILE}")"
    if stop_pid "${pid}"; then
        exit 0
    fi
fi

listener_pid="$(
    ss -ltnp 2>/dev/null | grep ":${PORT}" | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | head -n 1
)"

if stop_pid "${listener_pid}"; then
    exit 0
fi

printf 'No running vLLM process found for port %s\n' "${PORT}" >&2
exit 1
