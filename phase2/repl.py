from __future__ import annotations

import time

from .runtime_factory import build_agent
from .terminal_input import read_user_input


def main() -> None:
    agent, ledger, config = build_agent()
    turn_index = 1
    print("=" * 72)
    print("UAEA Phase-2A Runtime Started")
    print(f"Backend    : {agent.model.backend.backend_name}")
    print(f"Session    : {ledger.session_id}")
    print(f"Sandbox    : {config.sandbox_root}")
    print(f"Trajectory : {ledger.path}")
    print("Web        : disabled in this REPL; use scripts/start_uaea_web_repl_vllm.sh")
    print("Type 'exit' or 'quit' to stop.")
    print("=" * 72)
    while True:
        try:
            user_input = read_user_input(f"\n[Turn {turn_index} | USER]\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break
        print(f"\n[Turn {turn_index} | RUNTIME]\nProcessing...")
        started_at = time.monotonic()
        response = agent.handle(user_input)
        elapsed = time.monotonic() - started_at
        print(f"\n[Turn {turn_index} | ASSISTANT | {elapsed:.1f}s]")
        print("-" * 72)
        print(response)
        print("-" * 72)
        print(f"[Turn {turn_index} | TRACE] {ledger.path}")
        turn_index += 1
