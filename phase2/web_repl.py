from __future__ import annotations

import os
import time
from pathlib import Path

from .runtime_factory import build_agent
from .terminal_input import read_user_input
from .web_context import ProjectionLimits
from .web_shell import Phase2WebShell


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = PROJECT_ROOT / "data" / "memory" / "source_ingestion.sqlite"
DEFAULT_SNAPSHOT_ROOT = PROJECT_ROOT / "data" / "memory" / "web_snapshots"


def main() -> None:
    agent, ledger, config = build_agent()
    shell = Phase2WebShell(
        agent,
        db_path=Path(os.environ.get("UAEA_SOURCE_DB", str(DEFAULT_DB))),
        snapshot_root=Path(os.environ.get("UAEA_WEB_SNAPSHOT_ROOT", str(DEFAULT_SNAPSHOT_ROOT))),
        projection_limits=ProjectionLimits(
            max_sources=int(os.environ.get("UAEA_WEB_MAX_SOURCES", "3")),
            per_source_chars=int(os.environ.get("UAEA_WEB_PER_SOURCE_CHARS", "1200")),
            total_chars=int(os.environ.get("UAEA_WEB_TOTAL_CHARS", "2400")),
        ),
        intent_model=agent.model,
        enable_semantic_intent=os.environ.get("UAEA_WEB_SEMANTIC_INTENT", "1") != "0",
    )
    turn_index = 1
    print("=" * 72)
    print("UAEA Phase-2 Web Runtime Started")
    print(f"Backend    : {agent.model.backend.backend_name}")
    print(f"Session    : {ledger.session_id}")
    print(f"Sandbox    : {config.sandbox_root}")
    print(f"Trajectory : {ledger.path}")
    print(f"Source DB  : {shell.db_path}")
    print(f"Snapshots  : {shell.snapshot_root}")
    print("Commands   : /web fetch <url> | /web search <query>")
    print("Natural    : 请访问 <url> ... | 请联网搜索 <query> ...")
    print("Semantic   : enabled; set UAEA_WEB_SEMANTIC_INTENT=0 to disable")
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
        print(f"\n[Turn {turn_index} | PHASE-2 SHELL]\nProcessing...")
        started_at = time.monotonic()
        result = shell.handle(user_input)
        elapsed = time.monotonic() - started_at
        if result.used_web:
            print(f"[Turn {turn_index} | WEB]")
            if result.intent_source:
                print(f"  intent: {result.intent_source}")
            print(f"  access_events: {list(result.access_event_ids)}")
            print(f"  metrics: {result.metrics}")
            if result.error:
                print(f"  web_error: {result.error}")
        print(f"\n[Turn {turn_index} | ASSISTANT | {elapsed:.1f}s]")
        print("-" * 72)
        print(result.response)
        print("-" * 72)
        print(f"[Turn {turn_index} | TRACE] {ledger.path}")
        turn_index += 1


if __name__ == "__main__":
    main()
