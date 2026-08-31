from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from memory.sqlite_store import (
    candidate_rows,
    attachment_rows,
    connect,
    conversation_node_trace,
    conversation_rows,
    counts,
    ingest_chatgpt_export_directory,
    ingest_exported_conversation,
    ingest_fixture,
    ingest_web_fixture,
    initialize,
    trace_candidate,
    web_access_event_rows,
    web_access_trace,
    web_source_rows,
)
from phase2.web_context import ProjectionLimits, project_web_access_events


DEFAULT_FIXTURE = PROJECT_ROOT / "data" / "memory_test_fixtures" / "long_context_mixed_100.json"
DEFAULT_WEB_FIXTURE = PROJECT_ROOT / "data" / "memory_test_fixtures" / "web_source_w0_deterministic.json"
DEFAULT_DB = PROJECT_ROOT / "data" / "memory" / "source_ingestion.sqlite"


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the experimental Phase-2B SQLite prototype.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE, help="Fixture JSON to ingest.")
    parser.add_argument("--web-fixture", type=Path, default=DEFAULT_WEB_FIXTURE, help="Deterministic web fixture JSON to ingest.")
    parser.add_argument("--export", type=Path, help="Exported conversation JSON to ingest as source records.")
    parser.add_argument("--chatgpt-corpus", type=Path, help="Directory containing ChatGPT conversation export JSON files.")
    parser.add_argument("--init", action="store_true", help="Initialize the SQLite prototype schema.")
    parser.add_argument("--ingest-fixture", action="store_true", help="Ingest the fixture into SQLite.")
    parser.add_argument("--ingest-web-fixture", action="store_true", help="Ingest the deterministic web source fixture into SQLite.")
    parser.add_argument("--ingest-export", action="store_true", help="Ingest an exported conversation JSON into source records.")
    parser.add_argument("--ingest-chatgpt-corpus", action="store_true", help="Ingest ChatGPT export JSON files as normalized source records.")
    parser.add_argument("--counts", action="store_true", help="Show table counts.")
    parser.add_argument("--conversations", action="store_true", help="Show normalized conversations.")
    parser.add_argument("--candidates", action="store_true", help="Show candidate rows.")
    parser.add_argument("--attachments", action="store_true", help="Show attachment rows.")
    parser.add_argument("--web-sources", action="store_true", help="Show normalized web source rows.")
    parser.add_argument("--web-access-events", action="store_true", help="Show web access event rows.")
    parser.add_argument("--trace", metavar="CANDIDATE_ID", help="Trace candidate -> evidence -> source.")
    parser.add_argument("--trace-node", nargs=2, metavar=("CONVERSATION_ID", "NODE_ID"), help="Trace conversation node -> parent / children / source file.")
    parser.add_argument("--trace-web", metavar="ACCESS_EVENT_ID", help="Trace web access event -> web source.")
    parser.add_argument("--project-web", nargs="+", metavar="ACCESS_EVENT_ID", help="Project web access events into a bounded evidence block.")
    parser.add_argument("--project-web-max-sources", type=int, default=3, help="Maximum web sources to include in projection.")
    parser.add_argument("--project-web-per-source-chars", type=int, default=800, help="Maximum characters per projected web source.")
    parser.add_argument("--project-web-total-chars", type=int, default=2000, help="Maximum total projected web characters.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    with connect(args.db) as connection:
        if args.init:
            initialize(connection)
        if args.ingest_fixture:
            ingest_fixture(connection, args.fixture)
        if args.ingest_web_fixture:
            ingest_web_fixture(connection, args.web_fixture)
        if args.ingest_export:
            if args.export is None:
                parser.error("--ingest-export requires --export")
            ingest_exported_conversation(connection, args.export)
        if args.ingest_chatgpt_corpus:
            if args.chatgpt_corpus is None:
                parser.error("--ingest-chatgpt-corpus requires --chatgpt-corpus")
            ingest_chatgpt_export_directory(connection, args.chatgpt_corpus)

        output: dict[str, object] = {"db": str(args.db)}
        if args.counts:
            output["counts"] = counts(connection)
        if args.conversations:
            output["conversations"] = conversation_rows(connection)
        if args.candidates:
            output["candidates"] = candidate_rows(connection)
        if args.attachments:
            output["attachments"] = attachment_rows(connection)
        if args.web_sources:
            output["web_sources"] = web_source_rows(connection)
        if args.web_access_events:
            output["web_access_events"] = web_access_event_rows(connection)
        if args.trace:
            output["trace"] = trace_candidate(connection, args.trace)
        if args.trace_node:
            output["node_trace"] = conversation_node_trace(connection, args.trace_node[0], args.trace_node[1])
        if args.trace_web:
            output["web_trace"] = web_access_trace(connection, args.trace_web)
        if args.project_web:
            projection = project_web_access_events(
                connection,
                args.project_web,
                limits=ProjectionLimits(
                    max_sources=args.project_web_max_sources,
                    per_source_chars=args.project_web_per_source_chars,
                    total_chars=args.project_web_total_chars,
                ),
            )
            output["web_projection"] = {
                "metrics": projection.metrics(),
                "evidence_block": projection.evidence_block(),
            }

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        _print_text(output)
    return 0


def _print_text(output: dict[str, object]) -> None:
    print(f"db: {output['db']}")
    if "counts" in output:
        print("counts:")
        for key, value in dict(output["counts"]).items():
            print(f"  {key}: {value}")
    if "candidates" in output:
        print("candidates:")
        for row in output["candidates"]:
            candidate = dict(row)
            print(
                f"  {candidate['candidate_id']} "
                f"[{candidate['candidate_state']}, {candidate['source_provenance']}]: "
                f"{candidate['claim']}"
            )
    if "conversations" in output:
        print("conversations:")
        for row in output["conversations"]:
            conversation = dict(row)
            print(
                f"  {conversation['conversation_id']} "
                f"{conversation['title']} nodes={conversation['node_count']} "
                f"current={conversation['current_node_id']}"
            )
    if "attachments" in output:
        print("attachments:")
        for row in output["attachments"]:
            attachment = dict(row)
            print(
                f"  {attachment['availability_state']} "
                f"{attachment['conversation_id']}:{attachment['node_id']} "
                f"{attachment['name']} -> {attachment['local_path']}"
            )
    if "web_sources" in output:
        print("web_sources:")
        for row in output["web_sources"]:
            source = dict(row)
            print(
                f"  {source['web_source_id']} {source['domain']} "
                f"[{source['latest_access_status']}] {source['url']}"
            )
    if "web_access_events" in output:
        print("web_access_events:")
        for row in output["web_access_events"]:
            event = dict(row)
            print(
                f"  {event['access_event_id']} {event['accessed_at']} "
                f"[{event['access_status']}] {event['url']} "
                f"bytes={event['content_bytes']} chars={event['content_chars']}"
            )
    if "trace" in output:
        print("trace:")
        trace = output["trace"]
        if trace is None:
            print("  <missing>")
            return
        candidate = trace["candidate"]
        print(f"  candidate: {candidate['candidate_id']} [{candidate['candidate_state']}]")
        print(f"  claim: {candidate['claim']}")
        print(f"  scope: {candidate['scope']}")
        for item in trace["trace"]:
            evidence = item["evidence"]
            source = item["source_record"]
            print(f"  evidence: {evidence['evidence_id']} -> {evidence['source_kind']}:{evidence['source_id']}")
            if source:
                print(f"    source: {source['role']} / {source['category']} / {source['content']}")
            else:
                print("    source: <missing>")
    if "node_trace" in output:
        print("node_trace:")
        trace = output["node_trace"]
        if trace is None:
            print("  <missing>")
            return
        node = trace["node"]
        print(f"  node: {node['conversation_id']}:{node['node_id']}")
        print(f"  role/content: {node['role']} / {node['content_type']}")
        print(f"  parent: {trace['parent']['node_id'] if trace['parent'] else '<none>'}")
        print(f"  children: {[child['node_id'] for child in trace['children']]}")
        print(f"  source_file: {trace['source_file']['path'] if trace['source_file'] else '<missing>'}")
    if "web_trace" in output:
        print("web_trace:")
        trace = output["web_trace"]
        if trace is None:
            print("  <missing>")
            return
        event = trace["access_event"]
        source = trace["web_source"]
        print(f"  event: {event['access_event_id']} [{event['access_status']}] {event['accessed_at']}")
        print(f"  url: {event['url']}")
        print(f"  source: {source['web_source_id'] if source else '<missing>'}")
        print(f"  content_ref: {event['content_ref']}")
        print(f"  content_sha256: {event['content_sha256']}")
    if "web_projection" in output:
        print("web_projection:")
        projection = output["web_projection"]
        print("  metrics:")
        for key, value in projection["metrics"].items():
            print(f"    {key}: {value}")
        print("  evidence_block:")
        print(projection["evidence_block"])


if __name__ == "__main__":
    raise SystemExit(main())
