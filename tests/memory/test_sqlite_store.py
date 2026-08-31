from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator

from memory.candidate import EvidenceReference, MemoryCandidate, ScopeHypothesis
from memory.sqlite_store import (
    attachment_rows,
    connect,
    conversation_node_trace,
    counts,
    evidence_reference_for_attachment,
    evidence_reference_for_conversation_node,
    evidence_reference_for_web_access_event,
    get_candidate,
    get_web_access_event,
    get_web_source,
    ingest_chatgpt_export_directory,
    ingest_exported_conversation,
    ingest_fixture,
    ingest_web_fixture,
    initialize,
    insert_candidate,
    insert_web_access_event,
    trace_candidate,
    trace_evidence_reference,
    web_access_trace,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = PROJECT_ROOT / "data" / "memory_test_fixtures" / "long_context_mixed_100.json"
WEB_FIXTURE_PATH = PROJECT_ROOT / "data" / "memory_test_fixtures" / "web_source_w0_deterministic.json"
EXPORTED_CONVERSATION_PATH = PROJECT_ROOT / "tests" / "test_resources" / "UAEA_phase-1-benchmark-phase.json"
CHATGPT_CORPUS_PATH = PROJECT_ROOT / "tests" / "test_resources" / "chatgpt_personal_selected_2026-08-24"


class SQLitePrototypeTests(unittest.TestCase):
    def test_initializes_minimal_observation_schema_without_memory_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with closing(connect(Path(tmpdir) / "memory.db")) as connection:
                initialize(connection)
                table_names = {
                    row["name"]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }

        self.assertIn("source_records", table_names)
        self.assertIn("web_sources", table_names)
        self.assertIn("web_access_events", table_names)
        self.assertIn("evidence_references", table_names)
        self.assertIn("candidates", table_names)
        self.assertNotIn("memory", table_names)
        self.assertNotIn("memory_elements", table_names)

    def test_ingests_one_hundred_turn_fixture(self):
        with self.fixture_connection() as connection:
            actual_counts = ingest_fixture(connection, FIXTURE_PATH)

            self.assertEqual(actual_counts["source_records"], 100)
            self.assertEqual(actual_counts["candidates"], 11)
            self.assertEqual(actual_counts["retrieval_probes"], 5)
            self.assertGreaterEqual(actual_counts["evidence_references"], 11)
            self.assertGreater(actual_counts["candidate_evidence"], actual_counts["candidates"])

    def test_candidate_count_matches_fixture_expected_candidates(self):
        with self.fixture_connection() as connection:
            ingest_fixture(connection, FIXTURE_PATH)
            fixture_candidate_count = 11

            self.assertEqual(counts(connection)["candidates"], fixture_candidate_count)

    def test_candidate_retrieval_preserves_candidate_semantics(self):
        with self.fixture_connection() as connection:
            ingest_fixture(connection, FIXTURE_PATH)
            candidate = get_candidate(connection, "C005")

        assert candidate is not None
        self.assertIn("DS14B", candidate["claim"])
        self.assertEqual(candidate["source_provenance"], "derived")
        self.assertEqual(candidate["representation_facet_hint"], "failure lesson")
        self.assertEqual(candidate["scope_dimensions"]["backend"], "vLLM")
        self.assertEqual(candidate["candidate_state"], "closed")
        self.assertNotIn("memory_confidence", candidate)
        self.assertNotIn("truth_value", candidate)

    def test_evidence_trace_for_representative_candidates(self):
        with self.fixture_connection() as connection:
            ingest_fixture(connection, FIXTURE_PATH)
            for candidate_id in ("C001", "C005", "C006"):
                with self.subTest(candidate_id=candidate_id):
                    trace = trace_candidate(connection, candidate_id)

                    assert trace is not None
                    self.assertEqual(trace["candidate"]["candidate_id"], candidate_id)
                    self.assertTrue(trace["trace"])
                    for item in trace["trace"]:
                        self.assertIsNotNone(item["source_record"])
                        self.assertEqual(item["evidence"]["source_kind"], "conversation_turn")
                        self.assertEqual(item["source_record"]["source_kind"], "conversation_turn")

    def test_c006_scope_keeps_vllm_backend_dimension(self):
        with self.fixture_connection() as connection:
            ingest_fixture(connection, FIXTURE_PATH)
            candidate = get_candidate(connection, "C006")

        assert candidate is not None
        self.assertEqual(candidate["scope_dimensions"]["backend"], "vLLM")
        self.assertEqual(candidate["scope_dimensions"]["phase"], "Phase-2A")
        self.assertEqual(candidate["scope_dimensions"]["decision"], "production artifact")

    def test_candidate_states_remain_distinguishable_from_memory_lifecycle(self):
        with self.fixture_connection() as connection:
            initialize(connection)
            for state in ("open", "deferred", "closed"):
                insert_candidate(connection, self.build_candidate(f"C-{state}", state))
            rows = connection.execute(
                "SELECT candidate_state FROM candidates ORDER BY candidate_state"
            ).fetchall()

        self.assertEqual([row["candidate_state"] for row in rows], ["closed", "deferred", "open"])

    def test_fixture_deferred_candidate_is_not_promoted_by_sqlite(self):
        with self.fixture_connection() as connection:
            ingest_fixture(connection, FIXTURE_PATH)
            candidate = get_candidate(connection, "C007")

        assert candidate is not None
        self.assertEqual(candidate["candidate_state"], "deferred")
        self.assertNotIn("lifecycle_state", candidate)
        self.assertNotIn("final_validity", candidate)

    def test_candidate_can_survive_original_context_through_referenced_evidence(self):
        with self.fixture_connection() as connection:
            ingest_fixture(connection, FIXTURE_PATH)
            trace = trace_candidate(connection, "C006")

        assert trace is not None
        source_ids = {item["source_record"]["source_id"] for item in trace["trace"]}
        self.assertEqual(source_ids, {"T033", "T034"})
        self.assertIn("supersedes", trace["candidate"]["relation_hint"])

    def test_ingests_exported_conversation_as_raw_source_records(self):
        with self.fixture_connection() as connection:
            actual_counts = ingest_exported_conversation(connection, EXPORTED_CONVERSATION_PATH)
            roles = {
                row["role"]
                for row in connection.execute(
                    "SELECT DISTINCT role FROM source_records WHERE source_kind = 'exported_conversation_message'"
                ).fetchall()
            }

        self.assertEqual(actual_counts["source_records"], 340)
        self.assertEqual(roles, {"assistant", "user"})

    def test_exported_conversation_ingestion_does_not_create_candidates(self):
        with self.fixture_connection() as connection:
            ingest_exported_conversation(connection, EXPORTED_CONVERSATION_PATH)
            actual_counts = counts(connection)
            sample = connection.execute(
                """
                SELECT raw_json
                FROM source_records
                WHERE source_kind = 'exported_conversation_message'
                ORDER BY source_id
                LIMIT 1
                """
            ).fetchone()

        self.assertEqual(actual_counts["candidates"], 0)
        self.assertEqual(actual_counts["evidence_references"], 0)
        self.assertIsNotNone(sample)
        self.assertIn("chatGroupId", sample["raw_json"])

    def test_ingests_chatgpt_corpus_as_conversation_graph_source(self):
        with self.fixture_connection() as connection:
            actual_counts = ingest_chatgpt_export_directory(connection, CHATGPT_CORPUS_PATH)

        self.assertEqual(actual_counts["conversations"], 3)
        self.assertEqual(actual_counts["conversation_nodes"], 864)
        self.assertEqual(actual_counts["conversation_node_edges"], 861)
        self.assertEqual(actual_counts["source_files"], 19)
        self.assertEqual(actual_counts["candidates"], 0)

    def test_chatgpt_current_path_and_off_path_nodes_are_preserved(self):
        with self.fixture_connection() as connection:
            ingest_chatgpt_export_directory(connection, CHATGPT_CORPUS_PATH)
            total_current_path = connection.execute(
                "SELECT COUNT(*) FROM conversation_nodes WHERE is_current_path = 1"
            ).fetchone()[0]
            total_off_path = connection.execute(
                "SELECT COUNT(*) FROM conversation_nodes WHERE is_off_path = 1"
            ).fetchone()[0]
            phase1_off_path = connection.execute(
                """
                SELECT COUNT(*)
                FROM conversation_nodes n
                JOIN conversations c ON c.conversation_id = n.conversation_id
                WHERE c.title = 'UAEA_phase-1 benchmark phase'
                  AND n.is_off_path = 1
                """
            ).fetchone()[0]

        self.assertEqual(total_current_path, 862)
        self.assertEqual(total_off_path, 2)
        self.assertEqual(phase1_off_path, 2)

    def test_chatgpt_graph_parent_children_trace_is_recoverable(self):
        with self.fixture_connection() as connection:
            ingest_chatgpt_export_directory(connection, CHATGPT_CORPUS_PATH)
            edge = connection.execute(
                """
                SELECT conversation_id, parent_node_id, child_node_id
                FROM conversation_node_edges
                ORDER BY conversation_id, parent_node_id, child_node_id
                LIMIT 1
                """
            ).fetchone()
            trace = conversation_node_trace(connection, edge["conversation_id"], edge["parent_node_id"])

        assert trace is not None
        self.assertEqual(trace["node"]["node_id"], edge["parent_node_id"])
        self.assertIn(edge["child_node_id"], {child["node_id"] for child in trace["children"]})
        self.assertIsNotNone(trace["source_file"])

    def test_chatgpt_node_trace_keeps_source_file_and_raw_node(self):
        with self.fixture_connection() as connection:
            ingest_chatgpt_export_directory(connection, CHATGPT_CORPUS_PATH)
            node = connection.execute(
                """
                SELECT conversation_id, node_id
                FROM conversation_nodes
                WHERE role = 'user'
                  AND content_text <> ''
                ORDER BY current_path_index
                LIMIT 1
                """
            ).fetchone()
            trace = conversation_node_trace(connection, node["conversation_id"], node["node_id"])

        assert trace is not None
        self.assertIn(str(CHATGPT_CORPUS_PATH), trace["source_file"]["path"])
        self.assertEqual(trace["node"]["role"], "user")
        self.assertIn("message", trace["node"]["raw"])

    def test_chatgpt_attachment_availability_is_preserved(self):
        with self.fixture_connection() as connection:
            ingest_chatgpt_export_directory(connection, CHATGPT_CORPUS_PATH)
            attachments = attachment_rows(connection)

        states = [attachment["availability_state"] for attachment in attachments]
        self.assertEqual(len(attachments), 21)
        self.assertEqual(states.count("available"), 16)
        self.assertEqual(states.count("download_failed"), 5)
        available = next(attachment for attachment in attachments if attachment["availability_state"] == "available")
        failed = next(attachment for attachment in attachments if attachment["availability_state"] == "download_failed")
        self.assertTrue(Path(available["local_path"]).exists())
        self.assertEqual(failed["local_path"], "")

    def test_conversation_node_can_be_referenced_as_evidence_without_candidate_extraction(self):
        with self.fixture_connection() as connection:
            ingest_chatgpt_export_directory(connection, CHATGPT_CORPUS_PATH)
            node = connection.execute(
                """
                SELECT conversation_id, node_id
                FROM conversation_nodes
                WHERE role = 'user'
                  AND content_text <> ''
                ORDER BY conversation_id, current_path_index
                LIMIT 1
                """
            ).fetchone()
            reference = evidence_reference_for_conversation_node(
                connection,
                node["conversation_id"],
                node["node_id"],
            )
            trace = trace_evidence_reference(connection, reference)
            actual_counts = counts(connection)

        self.assertEqual(reference.source_kind, "conversation_node")
        self.assertEqual(reference.source_id, f"{node['conversation_id']}:{node['node_id']}")
        self.assertEqual(trace["source"]["node"]["node_id"], node["node_id"])
        self.assertEqual(actual_counts["candidates"], 0)
        self.assertEqual(actual_counts["evidence_references"], 0)

    def test_available_attachment_can_be_referenced_as_evidence(self):
        with self.fixture_connection() as connection:
            ingest_chatgpt_export_directory(connection, CHATGPT_CORPUS_PATH)
            attachment = connection.execute(
                """
                SELECT attachment_record_id
                FROM attachments
                WHERE availability_state = 'available'
                ORDER BY name
                LIMIT 1
                """
            ).fetchone()
            reference = evidence_reference_for_attachment(connection, attachment["attachment_record_id"])
            trace = trace_evidence_reference(connection, reference)

        self.assertEqual(reference.source_kind, "attachment")
        self.assertEqual(reference.source_id, attachment["attachment_record_id"])
        self.assertEqual(trace["source"]["attachment"]["availability_state"], "available")
        self.assertTrue(Path(trace["source"]["attachment"]["local_path"]).exists())
        self.assertIsNotNone(trace["source"]["node"])

    def test_failed_attachment_can_be_referenced_without_content_extraction(self):
        with self.fixture_connection() as connection:
            ingest_chatgpt_export_directory(connection, CHATGPT_CORPUS_PATH)
            attachment = connection.execute(
                """
                SELECT attachment_record_id
                FROM attachments
                WHERE availability_state = 'download_failed'
                ORDER BY name
                LIMIT 1
                """
            ).fetchone()
            reference = evidence_reference_for_attachment(connection, attachment["attachment_record_id"])
            trace = trace_evidence_reference(connection, reference)

        self.assertEqual(reference.source_kind, "attachment")
        self.assertIn("download_failed", reference.summary)
        self.assertEqual(trace["source"]["attachment"]["availability_state"], "download_failed")
        self.assertEqual(trace["source"]["attachment"]["local_path"], "")
        self.assertIsNotNone(trace["source"]["node"])

    def test_ingests_deterministic_web_fixture_without_candidates(self):
        with self.fixture_connection() as connection:
            actual_counts = ingest_web_fixture(connection, WEB_FIXTURE_PATH)

        self.assertEqual(actual_counts["web_access_events"], 5)
        self.assertEqual(actual_counts["web_sources"], 4)
        self.assertEqual(actual_counts["candidates"], 0)
        self.assertEqual(actual_counts["evidence_references"], 0)

    def test_web_repeated_access_shares_source_identity_and_keeps_events(self):
        with self.fixture_connection() as connection:
            ingest_web_fixture(connection, WEB_FIXTURE_PATH)
            first = get_web_access_event(connection, "WEB-E001")
            second = get_web_access_event(connection, "WEB-E002")
            assert first is not None
            assert second is not None
            source = get_web_source(connection, first["web_source_id"])

        assert source is not None
        self.assertEqual(first["web_source_id"], second["web_source_id"])
        self.assertNotEqual(first["access_event_id"], second["access_event_id"])
        self.assertNotEqual(first["accessed_at"], second["accessed_at"])
        self.assertEqual(source["first_accessed_at"], "2026-08-24T08:00:00Z")
        self.assertEqual(source["last_accessed_at"], "2026-08-24T08:20:00Z")

    def test_web_source_snapshot_is_referenced_not_duplicated(self):
        with self.fixture_connection() as connection:
            ingest_web_fixture(connection, WEB_FIXTURE_PATH)
            event = get_web_access_event(connection, "WEB-E003")
            trace = web_access_trace(connection, "WEB-E003")

        assert event is not None
        assert trace is not None
        self.assertGreater(event["content_bytes"], 0)
        self.assertGreater(event["content_chars"], 0)
        self.assertTrue(event["content_sha256"])
        self.assertEqual(event["content_ref"], "web_sources/large_context_source.html")
        self.assertLess(len(event["excerpt"]), event["content_chars"])
        self.assertEqual(trace["web_source"]["web_source_id"], event["web_source_id"])
        self.assertIn("content_ref_resolved", event["raw"])

    def test_failed_web_access_records_history_without_fabricated_content(self):
        with self.fixture_connection() as connection:
            ingest_web_fixture(connection, WEB_FIXTURE_PATH)
            event = get_web_access_event(connection, "WEB-E004")
            trace = web_access_trace(connection, "WEB-E004")

        assert event is not None
        assert trace is not None
        self.assertEqual(event["access_status"], "failed")
        self.assertEqual(event["http_status"], 503)
        self.assertEqual(event["content_ref"], "")
        self.assertEqual(event["content_sha256"], "")
        self.assertEqual(event["content_bytes"], 0)
        self.assertEqual(event["content_chars"], 0)
        self.assertEqual(event["excerpt"], "")
        self.assertEqual(trace["web_source"]["latest_access_status"], "failed")

    def test_web_metadata_incomplete_source_derives_domain_from_url(self):
        with self.fixture_connection() as connection:
            ingest_web_fixture(connection, WEB_FIXTURE_PATH)
            event = get_web_access_event(connection, "WEB-E005")

        assert event is not None
        self.assertEqual(event["domain"], "metadata-missing.example.test")
        self.assertEqual(event["title"], "")
        self.assertEqual(event["source_provenance"], "external")

    def test_web_access_event_can_be_referenced_as_evidence(self):
        with self.fixture_connection() as connection:
            ingest_web_fixture(connection, WEB_FIXTURE_PATH)
            reference = evidence_reference_for_web_access_event(connection, "WEB-E001")
            trace = trace_evidence_reference(connection, reference)

        self.assertEqual(reference.source_kind, "web_access_event")
        self.assertEqual(reference.source_id, "WEB-E001")
        self.assertEqual(trace["source"]["access_event"]["access_event_id"], "WEB-E001")
        self.assertEqual(trace["source"]["web_source"]["source_provenance"], "external")
        self.assertIn("DS14B", reference.summary)

    def test_insert_web_access_event_rejects_missing_url_as_adapter_issue(self):
        with self.fixture_connection() as connection:
            initialize(connection)
            with self.assertRaises(ValueError):
                insert_web_access_event(
                    connection,
                    {
                        "access_event_id": "WEB-BAD",
                        "access_status": "fetched",
                        "accessed_at": "2026-08-24T11:00:00Z",
                    },
                )

    @contextmanager
    def fixture_connection(self) -> Iterator[sqlite3.Connection]:
        with tempfile.TemporaryDirectory() as tmpdir:
            with closing(connect(Path(tmpdir) / "memory.db")) as connection:
                yield connection

    def build_candidate(self, candidate_id: str, state: str) -> MemoryCandidate:
        return MemoryCandidate(
            candidate_id=candidate_id,
            claim=f"Candidate processing state {state} can be persisted.",
            source_provenance="observed",
            evidence_references=(
                EvidenceReference(
                    source_kind="test_source",
                    source_id=f"source-{state}",
                    summary="Synthetic evidence for candidate status persistence.",
                ),
            ),
            scope_hypothesis=ScopeHypothesis.from_mapping(
                summary="Phase-2B SQLite prototype status test",
                dimensions={"project": "UAEA", "phase": "Phase-2B"},
            ),
            extraction_confidence=0.8,
            candidate_state=state,
        )


if __name__ == "__main__":
    unittest.main()
