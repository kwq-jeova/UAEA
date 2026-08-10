from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
PHASE1_BENCHMARK_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime" / "tests" / "runtime_benchmark"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PHASE1_BENCHMARK_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_BENCHMARK_ROOT))

from backend.config import BackendSettings, DEFAULT_BACKEND_URLS  # noqa: E402
from backend.factory import create_backend  # noqa: E402
from backend.model_client import ModelClient as BackendModelClient  # noqa: E402
import phase1_runtime_benchmark as phase1_benchmark  # noqa: E402


class VLLMBenchmarkRunner(phase1_benchmark.BenchmarkRunner):
    def __init__(self, project_root: Path, backend_settings: BackendSettings) -> None:
        super().__init__(project_root, mode="real-vllm")
        self.backend_settings = backend_settings

    def _build_model(self, fault_injection: phase1_benchmark.FaultInjectionSpec | None = None):
        backend = create_backend(self.backend_settings)
        model = BackendModelClient(backend)
        return phase1_benchmark.FaultInjectedBenchmarkModel(
            model,
            fault_injection or phase1_benchmark.FaultInjectionSpec(),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run UAEA Phase-1 Runtime benchmark on VLLMBackend.")
    parser.add_argument("--case", default="", help="Run a single case_id, e.g. case_03.")
    parser.add_argument(
        "--level",
        default="",
        help="Run a benchmark level such as L0, L1, L2, L5, or all. Default runs core regression cases.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BACKEND_URLS["vllm"])
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--api-key", default="uaea-local")
    parser.add_argument("--json", action="store_true", help="Write JSON report under data/benchmark_results.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    backend_settings = BackendSettings(
        name="vllm",
        base_url=args.base_url,
        model_name=args.model,
        timeout_seconds=args.timeout,
        api_key=args.api_key,
    )
    runner = VLLMBenchmarkRunner(PROJECT_ROOT, backend_settings)
    results = runner.run(phase1_benchmark.select_cases(args.case, args.level))
    for result in results:
        phase1_benchmark.print_result(result)

    payload = {
        "benchmark": "phase1_runtime_vllm_benchmark",
        "mode": runner.mode,
        "backend": {
            "name": backend_settings.name,
            "base_url": backend_settings.base_url,
            "model": backend_settings.model_name,
            "timeout_seconds": backend_settings.timeout_seconds,
        },
        "phase1_commit": "de0ecb0e8837c848f842a996fa2dad1c93666f2f",
        "summary": {
            "total": len(results),
            "passed": sum(1 for result in results if result.passed),
            "failed": sum(1 for result in results if not result.passed),
        },
        "results": [result.to_dict() for result in results],
    }
    if args.json or args.output is not None:
        output = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output + "\n", encoding="utf-8")
        else:
            default_path = runner.results_root / f"phase1_runtime_vllm_benchmark_{phase1_benchmark.utc_stamp()}.json"
            default_path.write_text(output + "\n", encoding="utf-8")
            print("=" * 72)
            print(f"JSON report: {default_path}")

    failed = sum(1 for result in results if not result.passed)
    print("=" * 72)
    print(f"Summary: passed={len(results) - failed}; failed={failed}; total={len(results)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
