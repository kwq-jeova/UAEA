"""Print configured Harness provenance without starting inference or changing defaults."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.version_manifest import codex_process_environment, selected_harness, verify_binary_digest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Query one pinned tag without changing the default")
    parser.add_argument("--verify-binary", action="store_true")
    args = parser.parse_args()
    record = selected_harness(args.version)
    if args.verify_binary:
        verify_binary_digest(Path(record["binary"]), record)
        record["binary_reported_version"] = subprocess.check_output(
            [record["binary"], "--version"], text=True, timeout=30,
            env=codex_process_environment()).strip()
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
