from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.models import InferenceRequest
from backend.vllm_backend import VLLMBackend
from phase2.runtime_factory import build_agent


def request_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Authorization": "Bearer uaea-local"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def gpu_snapshot() -> dict[str, str] | None:
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.used,memory.total,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    values = [value.strip() for value in output.splitlines()[0].split(",")]
    return {
        "name": values[0],
        "memory_used_mib": values[1],
        "memory_total_mib": values[2],
        "utilization_percent": values[3],
    }


def event_counts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    counts: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        counts[str(event.get("event_type", "unknown"))] += 1
    return dict(sorted(counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Phase-2A vLLM small-model path.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="Qwen2.5-0.5B-Instruct")
    parser.add_argument("--runtime", action="store_true")
    parser.add_argument(
        "--runtime-prompt",
        default="Read README section 1 and evaluate it.",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    report: dict[str, Any] = {
        "models": request_json(f"{base_url}/models"),
        "gpu_before": gpu_snapshot(),
    }

    backend = VLLMBackend(base_url, args.model, timeout_seconds=300)
    response = backend.generate(
        InferenceRequest(
            task_type="vllm_small_model_smoke",
            messages=[
                {"role": "system", "content": "Answer directly and concisely."},
                {"role": "user", "content": "Explain what a firmware bootloader does."},
            ],
            max_tokens=96,
            temperature=0.0,
        )
    )
    report["backend_generation"] = {
        "ok": response.ok,
        "text": response.text,
        "finish_reason": response.finish_reason,
        "latency_ms": round(response.latency_ms, 3),
        "usage": response.usage.to_dict(),
        "tokens_per_second": response.tokens_per_second,
        "error": response.error.to_dict() if response.error else None,
    }

    if args.runtime:
        os.environ.update(
            {
                "UAEA_BACKEND": "vllm",
                "UAEA_BACKEND_BASE_URL": base_url,
                "UAEA_BACKEND_MODEL": args.model,
                "UAEA_BACKEND_TIMEOUT": "300",
            }
        )
        agent, ledger, _ = build_agent()
        started_at = time.monotonic()
        runtime_response = agent.handle(args.runtime_prompt)
        report["runtime"] = {
            "response": runtime_response,
            "latency_ms": round((time.monotonic() - started_at) * 1000, 3),
            "trajectory": str(ledger.path),
            "event_counts": event_counts(ledger.path),
        }

    report["gpu_after"] = gpu_snapshot()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
