from __future__ import annotations

import argparse
import json
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from memory.sqlite_store import connect, counts, initialize, web_access_trace
from phase2.web_adapter import WebAdapter
from phase2.web_context import ProjectionLimits, project_web_access_events


DEFAULT_DB = PROJECT_ROOT / "data" / "memory" / "source_ingestion.sqlite"
DEFAULT_SNAPSHOT_ROOT = PROJECT_ROOT / "data" / "memory" / "web_snapshots"


def run_smoke(
    *,
    db_path: Path,
    snapshot_root: Path,
    fetch_urls: list[str],
    search_queries: list[str],
    repeat: int,
    project: bool,
    max_sources: int,
    per_source_chars: int,
    total_chars: int,
    timeout_seconds: int,
    search_url_template: str | None,
) -> dict[str, Any]:
    if repeat < 1:
        raise ValueError("--repeat must be >= 1")
    if not fetch_urls and not search_queries:
        raise ValueError("provide at least one --fetch or --search")

    adapter = WebAdapter(
        snapshot_root=snapshot_root,
        timeout_seconds=timeout_seconds,
        search_url_template=search_url_template,
    )
    trace_event_ids: list[str] = []
    projection_event_ids: list[str] = []
    operations: list[dict[str, Any]] = []
    warnings: list[str] = []

    with closing(connect(db_path)) as connection:
        initialize(connection)
        before_counts = counts(connection)
        for iteration in range(1, repeat + 1):
            for url in fetch_urls:
                result = adapter.fetch_url(connection, url)
                trace_event_ids.extend(result.related_access_event_ids or (result.access_event_id,))
                projection_event_ids.append(result.access_event_id)
                operations.append(_operation_payload("fetch", iteration, result))
            for query in search_queries:
                result = adapter.search(connection, query)
                trace_event_ids.extend(result.related_access_event_ids or (result.access_event_id,))
                projection_event_ids.append(result.access_event_id)
                operations.append(_operation_payload("search", iteration, result))
                if len(result.related_access_event_ids) > 1:
                    warnings.append(
                        f"search used fallback attempts: query={query!r} "
                        f"attempts={len(result.related_access_event_ids)} selected={result.access_event_id}"
                    )
                if result.status == "fetched" and not result.search_results:
                    warnings.append(
                        f"search returned no parsed results: query={query!r} "
                        f"url={result.url} http_status={result.http_status}"
                    )
        after_counts = counts(connection)
        traces = [web_access_trace(connection, event_id) for event_id in trace_event_ids]
        projection_payload: dict[str, Any] | None = None
        if project:
            projection = project_web_access_events(
                connection,
                projection_event_ids,
                limits=ProjectionLimits(
                    max_sources=max_sources,
                    per_source_chars=per_source_chars,
                    total_chars=total_chars,
                ),
            )
            projection_payload = {
                "metrics": projection.metrics(),
                "evidence_block": projection.evidence_block(),
            }

    return {
        "db": str(db_path),
        "snapshot_root": str(snapshot_root),
        "before_counts": before_counts,
        "after_counts": after_counts,
        "operations": operations,
        "traces": traces,
        "warnings": warnings,
        "projection": projection_payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a live Phase-2 Web source pipeline smoke test without starting Runtime or vLLM."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite source history database path.")
    parser.add_argument("--snapshot-root", type=Path, default=DEFAULT_SNAPSHOT_ROOT, help="Web snapshot directory.")
    parser.add_argument("--fetch", action="append", default=[], help="URL to fetch. Can be repeated.")
    parser.add_argument("--search", action="append", default=[], help="Search query to run. Can be repeated.")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat each fetch/search operation this many times.")
    parser.add_argument("--no-project", action="store_true", help="Skip bounded evidence projection.")
    parser.add_argument("--max-sources", type=int, default=3, help="Maximum projected web sources.")
    parser.add_argument("--per-source-chars", type=int, default=800, help="Maximum projected chars per source.")
    parser.add_argument("--total-chars", type=int, default=2000, help="Maximum total projected chars.")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds.")
    parser.add_argument(
        "--search-url-template",
        default=None,
        help="Optional search URL template. Must contain {query}. Overrides default fallback providers.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    result = run_smoke(
        db_path=args.db,
        snapshot_root=args.snapshot_root,
        fetch_urls=list(args.fetch),
        search_queries=list(args.search),
        repeat=args.repeat,
        project=not args.no_project,
        max_sources=args.max_sources,
        per_source_chars=args.per_source_chars,
        total_chars=args.total_chars,
        timeout_seconds=args.timeout,
        search_url_template=args.search_url_template,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_text(result)
    return 0


def _operation_payload(kind: str, iteration: int, result: Any) -> dict[str, Any]:
    return {
        "kind": kind,
        "iteration": iteration,
        "access_event_id": result.access_event_id,
        "url": result.url,
        "status": result.status,
        "http_status": result.http_status,
        "title": result.title,
        "content_ref": result.content_ref,
        "error": result.error,
        "search_result_count": len(result.search_results),
        "related_access_event_ids": list(result.related_access_event_ids),
    }


def _print_text(result: dict[str, Any]) -> None:
    print(f"db: {result['db']}")
    print(f"snapshot_root: {result['snapshot_root']}")
    print("counts:")
    _print_count_delta(result["before_counts"], result["after_counts"])
    print("operations:")
    for operation in result["operations"]:
        print(
            f"  {operation['kind']}#{operation['iteration']} "
            f"{operation['access_event_id']} [{operation['status']}] "
            f"http={operation['http_status']} {operation['url']}"
        )
        if operation["error"]:
            print(f"    error: {operation['error']}")
        if operation["search_result_count"]:
            print(f"    search_results: {operation['search_result_count']}")
        if operation["related_access_event_ids"]:
            print(f"    related_access_events: {operation['related_access_event_ids']}")
    if result["warnings"]:
        print("warnings:")
        for warning in result["warnings"]:
            print(f"  {warning}")
    print("traces:")
    for trace in result["traces"]:
        if trace is None:
            print("  <missing>")
            continue
        event = trace["access_event"]
        source = trace["web_source"]
        print(
            f"  event={event['access_event_id']} source={source['web_source_id'] if source else '<missing>'} "
            f"status={event['access_status']} chars={event['content_chars']} hash={event['content_sha256']}"
        )
        print(f"    content_ref: {event['content_ref'] or '<none>'}")
    if result["projection"] is not None:
        print("projection_metrics:")
        for key, value in result["projection"]["metrics"].items():
            print(f"  {key}: {value}")
        print("evidence_block:")
        print(result["projection"]["evidence_block"])


def _print_count_delta(before: dict[str, int], after: dict[str, int]) -> None:
    for key in sorted(after):
        delta = after[key] - before.get(key, 0)
        if delta:
            print(f"  {key}: {after[key]} ({delta:+d})")
        else:
            print(f"  {key}: {after[key]}")


if __name__ == "__main__":
    raise SystemExit(main())
