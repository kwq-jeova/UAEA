from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_ROOT.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run frozen UAEA Phase-1 benchmark against a Qwen2.5-14B OpenAI-compatible API."
    )
    parser.add_argument("--phase1-root", type=Path, default=Path(r"D:\UAEA-phase1-runtime-v1.0"))
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model-name", default="Qwen2.5-14B-Instruct")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--level", default="all")
    parser.add_argument("--case", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase1_qwen25_14b_benchmark",
        help="External output root for reports and trajectories. Keeps the frozen Phase-1 tree unchanged.",
    )
    args = parser.parse_args()

    phase1_root = args.phase1_root.resolve()
    benchmark_root = phase1_root / "tests" / "runtime_benchmark"
    if not benchmark_root.exists():
        raise SystemExit(f"Frozen Phase-1 benchmark root not found: {benchmark_root}")

    sys.path.insert(0, str(phase1_root))
    sys.path.insert(0, str(benchmark_root))

    import phase1_runtime_benchmark as benchmark  # noqa: PLC0415

    def qwen_default(cls):
        return cls(
            project_root=phase1_root,
            sandbox_root=phase1_root / "sandbox_workspace",
            trajectory_root=phase1_root / "data" / "trajectories",
            api_base_url=args.api_base_url,
            model_name=args.model_name,
            request_timeout_seconds=args.timeout,
        )

    benchmark.RuntimeConfig.default = classmethod(qwen_default)

    artifact_root = args.artifact_root.resolve()
    runner = benchmark.BenchmarkRunner.__new__(benchmark.BenchmarkRunner)
    runner.project_root = phase1_root
    runner.mode = "real"
    runner.results_root = artifact_root / "benchmark_results"
    runner.trajectory_root = artifact_root / "benchmark_trajectories"
    runner.results_root.mkdir(parents=True, exist_ok=True)
    runner.trajectory_root.mkdir(parents=True, exist_ok=True)

    results = runner.run(benchmark.select_cases(args.case, args.level))
    for result in results:
        benchmark.print_result(result)

    if args.json:
        report_path = runner.write_json_report(results)
        print("=" * 72)
        print(f"JSON report: {report_path}")

    failed = sum(1 for result in results if not result.passed)
    print("=" * 72)
    print(f"Summary: passed={len(results) - failed}; failed={failed}; total={len(results)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
