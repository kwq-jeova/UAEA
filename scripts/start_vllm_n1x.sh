#!/usr/bin/env bash
# N1X's only maintained vLLM profile; 8K bring-up assets are historical.
set +x
set -euo pipefail
PROJECT_ROOT="${UAEA_PROJECT_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
ROOT="${UAEA_N1X_ROOT:-$HOME/uaea-n1x}"
if (( $# )); then
    echo "Configure harness/n1x_profile.json; this launcher accepts no overrides." >&2
    exit 2
fi
exec "${UAEA_PYTHON_EXE:-python3}" -B - "$ROOT" "$PROJECT_ROOT/harness/n1x_profile.json" <<'PY_PROFILE'
from pathlib import Path
import hashlib
import json
import os
import sys
from urllib.parse import urlsplit

root, profile_path = Path(sys.argv[1]), Path(sys.argv[2])
profile = json.loads(profile_path.read_text())
if (profile["profile"] != "n1x" or profile["context_window"] != 32768
        or profile["vllm_mode"] != "external"
        or not profile["enable_auto_tool_choice"]
        or profile["tool_call_parser"] != "hermes"):
    raise SystemExit("The formal N1X profile requires 32768 context and Hermes.")
patch = root / profile["uma_patch"]["path"]
if hashlib.sha256(patch.read_bytes()).hexdigest() != profile["uma_patch"]["sha256"]:
    raise SystemExit("N1X UMA patch checksum mismatch; no service started.")
endpoint = urlsplit(profile["base_url"])
if (endpoint.scheme != "http" or endpoint.hostname != "127.0.0.1"
        or endpoint.port != 8000 or endpoint.path or endpoint.username
        or endpoint.password or endpoint.query or endpoint.fragment):
    raise SystemExit("The formal N1X endpoint is http://127.0.0.1:8000.")
os.environ.update(profile["environment"])
os.environ.pop("SERPAPI_KEY", None)
binary = str(root / profile["venv"] / "bin/vllm")
argv = [binary, "serve", str(root / profile["model_path"]),
        "--served-model-name", profile["model"],
        "--host", endpoint.hostname, "--port", str(endpoint.port),
        "--dtype", profile["dtype"], "--max-model-len", str(profile["context_window"]),
        "--gpu-memory-utilization", str(profile["gpu_memory_utilization"]),
        "--max-num-seqs", str(profile["max_num_seqs"])]
if profile["enforce_eager"]:
    argv.append("--enforce-eager")
argv += ["--enable-auto-tool-choice", "--tool-call-parser", profile["tool_call_parser"]]
print("N1X formal profile: 32768 / Hermes / port 8000; UMA checksum verified.", flush=True)
os.execv(binary, argv)
PY_PROFILE
