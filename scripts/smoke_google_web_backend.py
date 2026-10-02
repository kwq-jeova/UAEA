from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from h3_harness_interactive_repl import build_interactive_adapter  # noqa: E402
from phase2.web_environment import WebEnvironmentError, load_web_environment  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-1 Google backend smoke through the existing UAEA dynamic adapter; no inference.")
    parser.add_argument("--result-root", type=Path, default=Path("/mnt/d/UAEA-runtime/h3-results"))
    args = parser.parse_args()
    try:
        load_web_environment(require_key=True, require_proxy=True)
    except WebEnvironmentError as exc:
        print(f"[GOOGLE SMOKE] {exc}", file=sys.stderr)
        return 2
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    root = args.result_root / f"google-backend-{stamp}-{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=False)
    adapter = build_interactive_adapter(root / "adapter")
    dispatch = adapter.dispatch({
        "threadId": "google-backend-smoke", "turnId": "turn-1", "callId": "google-call-1",
        "tool": "web_search", "arguments": {
            "query": "LoRA training", "provider": "google", "allow_fallback": False,
            "language": "en", "max_results": 3,
        },
    })
    data = dispatch.tool_result.data
    serialized = json.dumps(dispatch.to_trace_metadata(), ensure_ascii=False)
    secret = os.environ["SERPAPI_KEY"].encode()
    secret_clean = secret not in serialized.encode()
    for path in (root / "adapter").rglob("*"):
        if path.is_file() and secret in path.read_bytes():
            secret_clean = False
    if secret_clean:
        (root / "dispatch.json").write_text(serialized, encoding="utf-8")
    passed = (
        dispatch.tool_result.ok and data.get("execution_succeeded") is True
        and data.get("requested_provider") == "google" and data.get("actual_provider") == "google"
        and data.get("acquisition_backend") == "serpapi" and data.get("fallback_occurred") is False
        and data.get("raw_search_result_count", 0) > 0 and secret_clean
    )
    report = {
        "phase": "Phase 1 Google backend integration", "status": "PASS" if passed else "FAIL",
        "requested_provider": data.get("requested_provider"), "actual_provider": data.get("actual_provider"),
        "acquisition_backend": data.get("acquisition_backend"), "execution_status": data.get("execution_status"),
        "reason": data.get("reason"), "fallback_occurred": data.get("fallback_occurred"),
        "raw_search_result_count": data.get("raw_search_result_count", 0),
        "citable_result_count": len(data.get("citable_results", [])), "evidence_status": data.get("evidence_status"),
        "secret_leakage_check": "PASS" if secret_clean else "FAIL", "artifact": str(root),
        "model_turn_executed": False,
    }
    (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
