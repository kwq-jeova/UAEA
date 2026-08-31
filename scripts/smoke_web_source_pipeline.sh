#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${UAEA_PROJECT_ROOT:-/mnt/d/UAEA}"
PYTHON_EXE="${UAEA_PYTHON_EXE:-$(command -v python3 || true)}"

if [[ ! -f "${PROJECT_ROOT}/scripts/smoke_web_source_pipeline.py" ]]; then
    printf 'UAEA web smoke script not found under project root: %s\n' "${PROJECT_ROOT}" >&2
    exit 1
fi

if [[ -z "${PYTHON_EXE}" ]]; then
    printf 'Python executable not found. Set UAEA_PYTHON_EXE explicitly.\n' >&2
    exit 1
fi

cd "${PROJECT_ROOT}"
exec "${PYTHON_EXE}" scripts/smoke_web_source_pipeline.py "$@"
