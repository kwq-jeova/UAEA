#!/usr/bin/env bash
set +x
set -euo pipefail

# Shared Harness entry: Linux/aarch64 selects n1x (external 32K/8000).
# The h3 profile retains 5090D managed 32K/8002 behavior.
# start_vllm_n1x.sh manages the N1X model service separately.

PROJECT_ROOT="${UAEA_PROJECT_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
PYTHON_EXE="${UAEA_PYTHON_EXE:-python3}"

# Inherit the user's existing WSL proxy setup for non-interactive launches too.
# The helper discovers the gateway and honors its own disabled flag.
if [[ -z "${HTTP_PROXY:-${http_proxy:-}}" && -z "${HTTPS_PROXY:-${https_proxy:-}}" \
      && -f "$HOME/.config/wsl-proxy/proxy.sh" ]]; then
    . "$HOME/.config/wsl-proxy/proxy.sh"
fi
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
