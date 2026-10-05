from __future__ import annotations

import argparse
import atexit
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "runtime" / "phase1-runtime"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Observe vLLM generation/Hermes without changing parser results.")
    parser.add_argument("--diagnostic-path", type=Path, required=True)
    args, cli_args = parser.parse_known_args()
    from harness.generation_diagnostics import install_generation_diagnostics
    from vllm.entrypoints.cli.main import main as vllm_main

    recorder = install_generation_diagnostics(args.diagnostic_path)
    atexit.register(recorder.close)
    sys.argv = ["vllm", *cli_args]
    vllm_main()


if __name__ == "__main__":
    main()
