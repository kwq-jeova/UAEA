from __future__ import annotations

import unittest

from harness.event_normalizer import (
    AGENT_OUTPUT,
    COMMAND_EXECUTION,
    CONTEXT_COMPACTION,
    ERROR,
    OBSERVATION,
    PRE_TURN_CONTEXT,
    TOKEN_USAGE,
    TOOL_CALL,
    TOOL_RESULT,
    TURN_COMPLETED,
    USER_INPUT,
    HarnessEventNormalizer,
)


class HarnessEventNormalizerTests(unittest.TestCase):
    def test_user_and_agent_messages_preserve_identity_order_and_raw_event(self):
        normalizer = HarnessEventNormalizer()
        events = normalizer.normalize_many(
            [
                {
                    "observed_at": "2026-09-15T00:00:00+00:00",
                    "message": {
                        "method": "item/completed",
                        "params": {
                            "threadId": "thread-1",
                            "turnId": "turn-1",
                            "item": {
                                "type": "userMessage",
                                "id": "user-item",
                                "content": [{"type": "text", "text": "hello"}],
                            },
                        },
                    },
                },
                {
                    "observed_at": "2026-09-15T00:00:01+00:00",
                    "message": {
                        "method": "item/agentMessage/delta",
                        "params": {
                            "threadId": "thread-1",
                            "turnId": "turn-1",
                            "itemId": "agent-item",
                            "delta": "hi",
                        },
                    },
                },
                {
                    "observed_at": "2026-09-15T00:00:02+00:00",
                    "message": {
                        "method": "item/completed",
                        "params": {
                            "threadId": "thread-1",
                            "turnId": "turn-1",
                            "item": {
                                "type": "agentMessage",
                                "id": "agent-item",
                                "text": "hi",
                            },
                        },
                    },
                },
            ],
            raw_event_reference_prefix={"path": "fixture.jsonl"},
        )

        self.assertEqual([event.event_type for event in events], [USER_INPUT, AGENT_OUTPUT, AGENT_OUTPUT])
        self.assertEqual([event.sequence for event in events], [1, 2, 3])
        self.assertEqual(events[0].thread_id, "thread-1")
        self.assertEqual(events[0].turn_id, "turn-1")
        self.assertEqual(events[0].item_id, "user-item")
        self.assertEqual(events[1].item_id, "agent-item")
        self.assertEqual(events[0].raw_event_reference["path"], "fixture.jsonl")
        self.assertEqual(events[0].raw_event_reference["raw_index"], 0)
        self.assertIn("message", events[0].to_dict()["raw_event"])

    def test_pre_turn_additional_context_becomes_lifecycle_event(self):
        normalizer = HarnessEventNormalizer()

        events = normalizer.normalize(
            {
                "message": {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "turn/start",
                    "params": {
                        "threadId": "thread-pre",
                        "input": [{"type": "text", "text": "answer"}],
                        "additionalContext": {
                            "uaea.lifecycle.goal_state": {
                                "kind": "application",
                                "value": "Goal state marker",
                            }
                        },
                        "model": "qwen25-14b-awq",
                    },
                }
            }
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, PRE_TURN_CONTEXT)
        self.assertEqual(events[0].thread_id, "thread-pre")
        self.assertEqual(
            events[0].payload["additional_context"]["uaea.lifecycle.goal_state"]["value"],
            "Goal state marker",
        )

    def test_dynamic_tool_call_and_result_emit_observation_without_semantic_judgment(self):
        normalizer = HarnessEventNormalizer()
        events = normalizer.normalize_many(
            [
                {
                    "message": {
                        "method": "item/tool/call",
                        "id": 1,
                        "params": {
                            "threadId": "thread-tool",
                            "turnId": "turn-tool",
                            "callId": "call-1",
                            "tool": "read_section",
                            "arguments": {"path": "README.md", "section_index": 1},
                        },
                    }
                },
                {
                    "message": {
                        "method": "item/completed",
                        "params": {
                            "threadId": "thread-tool",
                            "turnId": "turn-tool",
                            "item": {
                                "type": "dynamicToolCall",
                                "id": "call-1",
                                "tool": "read_section",
                                "arguments": {"path": "README.md", "section_index": 1},
                                "status": "completed",
                                "success": True,
                                "contentItems": [{"type": "inputText", "text": '{"ok": true}'}],
                                "durationMs": 41,
                            },
                        },
                    }
                },
            ]
        )

        self.assertEqual(
            [event.event_type for event in events],
            [TOOL_CALL, TOOL_RESULT, OBSERVATION],
        )
        self.assertEqual(events[0].item_id, "call-1")
        self.assertEqual(events[1].item_id, "call-1")
        self.assertTrue(events[2].payload["item"]["success"])
        self.assertEqual(events[2].payload["item"]["tool"], "read_section")

    def test_command_execution_failure_and_turn_error_are_normalized(self):
        normalizer = HarnessEventNormalizer()
        events = normalizer.normalize_many(
            [
                {
                    "message": {
                        "method": "item/completed",
                        "params": {
                            "threadId": "thread-command",
                            "turnId": "turn-command",
                            "item": {
                                "type": "commandExecution",
                                "id": "call-command",
                                "command": "/bin/bash -lc 'cat README.md'",
                                "cwd": "/mnt/d/UAEA",
                                "status": "failed",
                                "aggregatedOutput": "bubblewrap is unavailable",
                                "exitCode": 101,
                                "durationMs": 28,
                            },
                        },
                    }
                },
                {
                    "message": {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "thread-command",
                            "turn": {
                                "id": "turn-command",
                                "status": "failed",
                                "error": {"message": "failed"},
                            },
                        },
                    }
                },
            ]
        )

        self.assertEqual(
            [event.event_type for event in events],
            [COMMAND_EXECUTION, OBSERVATION, ERROR, TURN_COMPLETED, ERROR],
        )
        self.assertEqual(events[0].payload["item"]["exitCode"], 101)
        self.assertEqual(events[3].turn_id, "turn-command")

    def test_app_server_error_notification_is_normalized(self):
        normalizer = HarnessEventNormalizer()

        events = normalizer.normalize(
            {
                "message": {
                    "method": "error",
                    "params": {
                        "threadId": "thread-error",
                        "turnId": "turn-error",
                        "error": {"message": "bad request"},
                        "willRetry": False,
                    },
                }
            }
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, ERROR)
        self.assertEqual(events[0].thread_id, "thread-error")
        self.assertEqual(events[0].turn_id, "turn-error")
        self.assertEqual(events[0].payload["error"]["message"], "bad request")

    def test_token_usage_turn_completion_and_compaction_are_supported(self):
        normalizer = HarnessEventNormalizer()
        events = normalizer.normalize_many(
            [
                {
                    "message": {
                        "method": "thread/tokenUsage/updated",
                        "params": {
                            "threadId": "thread-ctx",
                            "turnId": "turn-ctx",
                            "tokenUsage": {
                                "total": {"totalTokens": 8191},
                                "modelContextWindow": 31129,
                            },
                        },
                    }
                },
                {
                    "message": {
                        "method": "item/completed",
                        "params": {
                            "threadId": "thread-ctx",
                            "turnId": "turn-ctx",
                            "item": {
                                "type": "contextCompaction",
                                "id": "compact-1",
                                "status": "completed",
                            },
                        },
                    }
                },
                {
                    "message": {
                        "method": "turn/completed",
                        "params": {
                            "threadId": "thread-ctx",
                            "turn": {
                                "id": "turn-ctx",
                                "status": "completed",
                                "durationMs": 100,
                            },
                        },
                    }
                },
            ]
        )

        self.assertEqual(
            [event.event_type for event in events],
            [TOKEN_USAGE, CONTEXT_COMPACTION, TURN_COMPLETED],
        )
        self.assertEqual(
            events[0].payload["params"]["tokenUsage"]["modelContextWindow"],
            31129,
        )
        self.assertEqual(events[1].item_id, "compact-1")
        self.assertEqual(events[2].turn_id, "turn-ctx")


if __name__ == "__main__":
    unittest.main()
