from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.scenario_fixture import evaluate_fixture, load_fixture


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a Phase-2B Memory architecture fixture.")
    parser.add_argument(
        "fixture",
        type=Path,
        nargs="?",
        default=Path("data/memory_test_fixtures/long_context_mixed_100.json"),
        help="Path to a Memory architecture fixture JSON file.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report.")
    args = parser.parse_args()

    report = evaluate_fixture(load_fixture(args.fixture))
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"fixture_id: {report.fixture_id}")
        print(f"valid: {report.valid}")
        for key, value in report.metrics.items():
            print(f"{key}: {value}")
        if report.issues:
            print("issues:")
            for issue in report.issues:
                print(f"- {issue}")
        if report.warnings:
            print("warnings:")
            for warning in report.warnings:
                print(f"- {warning}")
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
