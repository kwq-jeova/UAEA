from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.trajectory_reader import (
    TrajectoryReadError,
    read_trajectory_jsonl,
    validate_trajectory_records,
)
from harness.trajectory_writer import HarnessTrajectoryWriter


class HarnessTrajectoryReaderTests(unittest.TestCase):
    def test_reader_reconstructs_per_turn_timeline_from_canonical_trajectory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HarnessTrajectoryWriter(Path(tmpdir), run_id="reader-run", split_by_thread=True)
            writer.write_raw_event(
                {
                    "message": {
                        "method": "item/completed",
                        "params": {
                            "threadId": "thread-1",
                            "turnId": "turn-1",
                            "item": {
                                "type": "userMessage",
                                "id": "user-1",
                                "content": [{"type": "text", "text": "hello"}],
                            },
                        },
                    }
                }
            )
            writer.write_raw_event(
                {
                    "message": {
                        "method": "item/completed",
                        "params": {
                            "threadId": "thread-1",
                            "turnId": "turn-1",
                            "item": {
                                "type": "agentMessage",
                                "id": "agent-1",
                                "text": "hi",
                            },
                        },
                    }
                }
            )
            writer.write_raw_event(
                {
                    "message": {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "thread-1",
                            "turn": {"id": "turn-1", "status": "completed"},
                        },
                    }
                }
            )
            writer.close()

            result = read_trajectory_jsonl(Path(tmpdir) / "reader-run.trajectory.jsonl")
            validation = validate_trajectory_records(result.records)
            timelines = result.reconstruct_turns()

        self.assertTrue(validation.ok, validation.issues)
        self.assertEqual([record.sequence for record in result.records], [1, 2, 3])
        self.assertEqual(set(result.project_by_thread()), {"thread-1"})
        self.assertIn(("thread-1", "turn-1"), timelines)
        self.assertEqual(timelines[("thread-1", "turn-1")].terminal_state, "TURN_COMPLETED")
        self.assertIn("message", result.records[0].raw_event)
        self.assertEqual(result.records[0].event_id, "user-1")

    def test_reader_rejects_malformed_line_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.trajectory.jsonl"
            path.write_text('{"sequence": 1}\n{"sequence":', encoding="utf-8")

            with self.assertRaises(TrajectoryReadError):
                read_trajectory_jsonl(path)

    def test_reader_can_ignore_truncated_final_line(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "truncated.trajectory.jsonl"
            path.write_text(
                '{"sequence": 1, "event_type": "RAW_EVENT", '
                '"identity": {"thread_id": "", "turn_id": "", "item_id": "", "event_id": "e1"}, '
                '"payload": {}, "provenance": {}, "raw_event_reference": {}, "raw_event": {}}\n'
                '{"sequence":',
                encoding="utf-8",
            )

            result = read_trajectory_jsonl(path, allow_truncated_final_line=True)

        self.assertEqual(len(result.records), 1)
        self.assertEqual(len(result.issues), 1)
        self.assertIn("ignored malformed final line", result.issues[0])

    def test_validator_reports_non_monotonic_sequence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HarnessTrajectoryWriter(Path(tmpdir), run_id="reader-run")
            writer.write_raw_event(
                {
                    "message": {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "thread-1",
                            "turn": {"id": "turn-1", "status": "completed"},
                        },
                    }
                }
            )
            writer.close()
            path = Path(tmpdir) / "reader-run.trajectory.jsonl"
            text = path.read_text(encoding="utf-8").replace('"sequence": 1', '"sequence": 0')
            path.write_text(text + text, encoding="utf-8")

            result = read_trajectory_jsonl(path)
            validation = validate_trajectory_records(result.records)

        self.assertFalse(validation.ok)
        self.assertTrue(any("sequence" in issue for issue in validation.issues))

    def test_turn_only_records_are_backfilled_from_later_thread_identity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "backfill.trajectory.jsonl"
            path.write_text(
                '{"sequence": 1, "event_type": "RAW_EVENT", '
                '"identity": {"thread_id": "", "turn_id": "turn-1", "item_id": "", "event_id": "e1"}, '
                '"payload": {}, "provenance": {}, "raw_event_reference": {}, "raw_event": {}}\n'
                '{"sequence": 2, "event_type": "TURN_COMPLETED", '
                '"identity": {"thread_id": "thread-1", "turn_id": "turn-1", "item_id": "", "event_id": "e2"}, '
                '"payload": {}, "provenance": {}, "raw_event_reference": {}, "raw_event": {}}\n',
                encoding="utf-8",
            )

            result = read_trajectory_jsonl(path)
            threads = result.project_by_thread()
            timelines = result.reconstruct_turns()

        self.assertEqual(set(threads), {"thread-1"})
        self.assertIn(("thread-1", "turn-1"), timelines)
        self.assertNotIn(("unknown-thread", "turn-1"), timelines)


if __name__ == "__main__":
    unittest.main()
