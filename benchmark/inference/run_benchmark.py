from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
for path in (PROJECT_ROOT, PHASE1_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backend.transformers_backend import TransformersBackend  # noqa: E402
from benchmark.inference.metrics import NvidiaSmiMetricsCollector  # noqa: E402
from benchmark.inference.runner import InferenceBenchmarkRunner  # noqa: E402
from benchmark.inference.workloads import uaea_phase2a_workloads  # noqa: E402
from runtime.model_client import ModelClient  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run UAEA Phase-2A inference workloads.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default="DeepSeek-R1-Distill-Qwen-14B")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    client = ModelClient(args.base_url, args.model, args.timeout)
    backend = TransformersBackend(client, model_name=args.model)
    runner = InferenceBenchmarkRunner(NvidiaSmiMetricsCollector(args.device))
    report = {
        "backend": backend.backend_name,
        "model": backend.model_name,
        "phase1_commit": "de0ecb0e8837c848f842a996fa2dad1c93666f2f",
        "samples": [sample.to_dict() for sample in runner.run(backend, uaea_phase2a_workloads())],
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
