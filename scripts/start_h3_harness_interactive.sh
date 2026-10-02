#!/usr/bin/env bash
set +x
set -euo pipefail

PROJECT_ROOT="${UAEA_PROJECT_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
PYTHON_EXE="${UAEA_PYTHON_EXE:-python3}"
cd -- "${PROJECT_ROOT}"

if [[ "${1:-}" == "--web-env-check" ]]; then
    shift
    exec "${PYTHON_EXE}" -m phase2.web_environment --check "$@"
fi
if [[ "${1:-}" == "--web-env-smoke" ]]; then
    shift
    exec "${PYTHON_EXE}" -m phase2.web_environment --serpapi-smoke "$@"
fi
exec "${PYTHON_EXE}" scripts/h3_harness_interactive_repl.py "$@"
