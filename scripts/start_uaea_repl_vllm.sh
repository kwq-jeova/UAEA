#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${UAEA_PROJECT_ROOT:-/mnt/d/UAEA}"
BASE_URL="${UAEA_BACKEND_BASE_URL:-http://127.0.0.1:8001/v1}"
MODEL="${UAEA_BACKEND_MODEL:-qwen25-14b-awq}"
TIMEOUT_SECONDS="${UAEA_BACKEND_TIMEOUT:-300}"
API_KEY="${UAEA_BACKEND_API_KEY:-uaea-local}"
PYTHON_EXE="${UAEA_PYTHON_EXE:-$(command -v python3 || true)}"
SKIP_HEALTH_CHECK="${UAEA_SKIP_VLLM_HEALTH_CHECK:-0}"

export LANG="${UAEA_LANG:-C.UTF-8}"
export LC_ALL="${UAEA_LC_ALL:-C.UTF-8}"
export PYTHONUTF8="${PYTHONUTF8:-1}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

if [[ ! -f "${PROJECT_ROOT}/main.py" ]]; then
    printf 'UAEA project root not found or missing main.py: %s\n' "${PROJECT_ROOT}" >&2
    exit 1
fi

if [[ -z "${PYTHON_EXE}" ]]; then
    printf 'Python executable not found. Set UAEA_PYTHON_EXE explicitly.\n' >&2
    exit 1
fi

if [[ "${SKIP_HEALTH_CHECK}" != "1" ]]; then
    "${PYTHON_EXE}" - "${BASE_URL%/}/models" <<'PY'
import json
import sys
import urllib.request

request = urllib.request.Request(sys.argv[1], headers={"Authorization": "Bearer uaea-local"})
with urllib.request.urlopen(request, timeout=10) as response:
    json.loads(response.read().decode("utf-8"))
PY
fi

printf 'Starting UAEA REPL with backend=vllm model=%s endpoint=%s python=%s\n' "${MODEL}" "${BASE_URL%/}" "${PYTHON_EXE}"
printf 'Input      : native terminal input with UTF-8 env; set UAEA_REPL_INPUT_MODE=raw only for diagnostics\n'
printf 'Web capability is disabled in this REPL. Use ./scripts/start_uaea_web_repl_vllm.sh for web access.\n'

cd "${PROJECT_ROOT}"
env \
    LANG="${LANG}" \
    LC_ALL="${LC_ALL}" \
    PYTHONUTF8="${PYTHONUTF8}" \
    PYTHONIOENCODING="${PYTHONIOENCODING}" \
    UAEA_BACKEND="vllm" \
    UAEA_BACKEND_BASE_URL="${BASE_URL%/}" \
    UAEA_BACKEND_MODEL="${MODEL}" \
    UAEA_BACKEND_TIMEOUT="${TIMEOUT_SECONDS}" \
    UAEA_BACKEND_API_KEY="${API_KEY}" \
    "${PYTHON_EXE}" - <<'PY'
from backend.config import BackendSettings
settings = BackendSettings.from_environment(
    default_base_url="http://127.0.0.1:8000/v1",
    default_model_name="DeepSeek-R1-Distill-Qwen-14B",
    default_timeout_seconds=300,
)
print(f"Resolved backend settings: backend={settings.name} model={settings.model_name} base_url={settings.base_url}")
if settings.name != "vllm":
    raise SystemExit("Resolved backend is not vllm; refusing to start REPL.")
PY

exec env \
    LANG="${LANG}" \
    LC_ALL="${LC_ALL}" \
    PYTHONUTF8="${PYTHONUTF8}" \
    PYTHONIOENCODING="${PYTHONIOENCODING}" \
    UAEA_BACKEND="vllm" \
    UAEA_BACKEND_BASE_URL="${BASE_URL%/}" \
    UAEA_BACKEND_MODEL="${MODEL}" \
    UAEA_BACKEND_TIMEOUT="${TIMEOUT_SECONDS}" \
    UAEA_BACKEND_API_KEY="${API_KEY}" \
    "${PYTHON_EXE}" main.py
