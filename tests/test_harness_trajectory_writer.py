from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.event_normalizer import PRE_TURN_CONTEXT, TURN_COMPLETED, USER_INPUT
from harness.trajectory_writer import HarnessTrajectoryWriter


class HarnessTrajectoryWriterTests(unittest.TestCase):
    def test_run_file_preserves_receive_order_and_raw_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HarnessTrajectoryWriter(Path(tmpdir), run_id="run-1")
            writer.write_raw_event(
                {
                    "observed_at": "2026-09-16T00:00:00+00:00",
                    "message": {
                        "method": "turn/start",
                        "params": {
                            "threadId": "thread-1",
                            "input": [{"type": "text", "text": "hello"}],
                            "additionalContext": {"uaea": {"kind": "application", "value": "ctx"}},
                        },
                    },
                },
                raw_event_reference={"stream": "stdin"},
            )
            writer.write_raw_event(
                {
                    "observed_at": "2026-09-16T00:00:01+00:00",
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
                    },
                },
                raw_event_reference={"stream": "stdout"},
            )
            writer.close()

            path = Path(tmpdir) / "run-1.trajectory.jsonl"
            rows = _read_jsonl(path)

        self.assertEqual([row["event_type"] for row in rows], [PRE_TURN_CONTEXT, USER_INPUT])
        self.assertEqual([row["sequence"] for row in rows], [1, 2])
        self.assertEqual(rows[0]["identity"]["thread_id"], "thread-1")
        self.assertEqual(rows[1]["identity"]["item_id"], "user-1")
        self.assertEqual(rows[0]["raw_event_reference"]["stream"], "stdin")
        self.assertIn("raw_event", rows[0])

    def test_thread_split_writes_independent_trajectory_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HarnessTrajectoryWriter(Path(tmpdir), run_id="run-thread", split_by_thread=True)
            writer.write_raw_event(
                {
                    "message": {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "thread/A",
                            "turn": {"id": "turn-a", "status": "completed"},
                        },
                    }
                }
            )
            writer.write_raw_event(
                {
                    "message": {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "thread/B",
                            "turn": {"id": "turn-b", "status": "completed"},
                        },
                    }
                }
            )
            stats = writer.stats.to_dict()
            writer.close()

            paths = sorted(Path(tmpdir).glob("*.trajectory.jsonl"))
            rows_by_path = {path.name: _read_jsonl(path) for path in paths}

        self.assertEqual(len(paths), 3)
        self.assertEqual(stats["event_count"], 2)
        self.assertEqual(stats["event_types"], {TURN_COMPLETED: 2})
        self.assertIn("run-thread.trajectory.jsonl", rows_by_path)
        self.assertEqual(len(rows_by_path["run-thread.trajectory.jsonl"]), 2)
        self.assertEqual(
            sorted(
                row[0]["identity"]["thread_id"]
                for name, row in rows_by_path.items()
                if name != "run-thread.trajectory.jsonl"
            ),
            ["thread/A", "thread/B"],
        )

    def test_filename_segments_are_safe_bounded_and_collision_resistant(self):
        long_id = "thread/" + ("x" * 180)
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HarnessTrajectoryWriter(
                Path(tmpdir),
                run_id="run:/with illegal chars and an extremely long suffix " + ("r" * 180),
                split_by_thread=True,
            )
            writer.write_raw_event(
                {
                    "message": {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "thread/A",
                            "turn": {"id": "turn-a", "status": "completed"},
                        },
                    }
                }
            )
            writer.write_raw_event(
                {
                    "message": {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "thread:A",
                            "turn": {"id": "turn-b", "status": "completed"},
                        },
                    }
                }
            )
            writer.write_raw_event(
                {
                    "message": {
                        "method": "turn/completed",
                        "params": {
                            "threadId": long_id,
                            "turn": {"id": "turn-long", "status": "completed"},
                        },
                    }
                }
            )
            writer.close()
            names = [path.name for path in Path(tmpdir).glob("*.trajectory.jsonl")]

        self.assertEqual(len(names), 4)
        self.assertEqual(len(set(names)), 4)
        for name in names:
            self.assertNotIn("/", name)
            self.assertNotIn(":", name)
            self.assertLessEqual(max(len(part) for part in name.split(".")), 96)

    def test_terminal_event_is_flushed_before_close(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HarnessTrajectoryWriter(Path(tmpdir), run_id="flush-run")
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
            rows = _read_jsonl(Path(tmpdir) / "flush-run.trajectory.jsonl")
            writer.close()

        self.assertEqual(rows[0]["event_type"], TURN_COMPLETED)

    def test_turn_start_response_uses_request_thread_for_projection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HarnessTrajectoryWriter(Path(tmpdir), run_id="projection-run", split_by_thread=True)
            writer.write_raw_event(
                {
                    "message": {
                        "id": 10,
                        "method": "turn/start",
                        "params": {
                            "threadId": "thread-1",
                            "input": [{"type": "text", "text": "hello"}],
                        },
                    }
                }
            )
            writer.write_raw_event(
                {
                    "message": {
                        "id": 10,
                        "result": {
                            "turn": {
                                "id": "turn-1",
                                "status": "inProgress",
                            }
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

            canonical = _read_jsonl(Path(tmpdir) / "projection-run.trajectory.jsonl")
            projection = _read_jsonl(Path(tmpdir) / "projection-run.thread-1.trajectory.jsonl")
            unknown = Path(tmpdir) / "projection-run.unknown-thread.trajectory.jsonl"

        self.assertFalse(unknown.exists())
        self.assertEqual([row["sequence"] for row in projection], [1, 2, 3])
        self.assertEqual([row["sequence"] for row in canonical], [1, 2, 3])
        self.assertEqual(projection[1]["identity"]["thread_id"], "thread-1")
        self.assertEqual(
            projection[1]["raw_event_reference"]["identity_backfill"],
            "writer_request_or_turn_mapping",
        )

    def test_writer_returns_written_events_and_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = HarnessTrajectoryWriter(Path(tmpdir), run_id="run-result")
            result = writer.write_raw_event(
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

        self.assertEqual(len(result.events), 1)
        self.assertEqual(result.events[0].event_type, TURN_COMPLETED)
        self.assertEqual(len(result.paths), 1)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    unittest.main()
