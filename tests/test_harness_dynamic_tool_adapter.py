from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from harness.codex_dynamic_tools import (  # noqa: E402
    DynamicToolBinding,
    HarnessDynamicToolAdapter,
)
from runtime.capability import CapabilityMetadata, ToolResult  # noqa: E402
from runtime.ledger import LedgerStub  # noqa: E402
from runtime.sandbox import Sandbox  # noqa: E402
from runtime.tools import ToolRegistry  # noqa: E402


class HarnessDynamicToolAdapterTests(unittest.TestCase):
    def test_dynamic_tool_spec_uses_explicit_tool_schema(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            registry.register_capability(
                CapabilityMetadata(
                    name="mock.external_operation",
                    tool_name="mock_external_operation",
                    version="0.1",
                    permission="external",
                    produces_observation=True,
                    context_cost="low",
                    future_phase="test",
                ),
                lambda arguments, objective: ToolResult(True, "ok", dict(arguments)),
            )
            adapter = HarnessDynamicToolAdapter(
                registry,
                [
                    DynamicToolBinding.from_registry(
                        registry,
                        "mock.external_operation",
                        description="Run the deterministic external fixture.",
                        input_schema={
                            "type": "object",
                            "properties": {"target": {"type": "string"}},
                            "required": ["target"],
                        },
                    )
                ],
            )

            specs = adapter.dynamic_tools()

        self.assertEqual(specs[0]["type"], "function")
        self.assertEqual(specs[0]["name"], "mock_external_operation")
        self.assertEqual(specs[0]["inputSchema"]["required"], ["target"])

    def test_dispatch_reuses_registry_and_preserves_execution_identity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            registry.register_capability(
                CapabilityMetadata(
                    name="mock.external_operation",
                    tool_name="mock_external_operation",
                    version="0.1",
                    permission="external",
                    produces_observation=True,
                    context_cost="low",
                    future_phase="test",
                ),
                lambda arguments, objective: ToolResult(
                    True,
                    "mock completed",
                    {"received": dict(arguments), "objective": objective},
                ),
            )
            adapter = HarnessDynamicToolAdapter(
                registry,
                [
                    DynamicToolBinding.from_registry(
                        registry,
                        "mock.external_operation",
                        description="Run the deterministic external fixture.",
                        input_schema={"type": "object"},
                    )
                ],
            )

            dispatch = adapter.dispatch(
                {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "callId": "call-1",
                    "tool": "mock_external_operation",
                    "arguments": {"target": "fixture"},
                },
                objective="run fixture",
            )

        self.assertTrue(dispatch.ok)
        self.assertEqual(dispatch.action_request.request_id, "call-1")
        self.assertEqual(dispatch.action_request.capability, "mock.external_operation")
        self.assertEqual(dispatch.observation.capability, "mock.external_operation")
        self.assertEqual(dispatch.observation.tool_name, "mock_external_operation")
        trace = dispatch.to_trace_metadata()
        self.assertEqual(trace["harness"]["thread_id"], "thread-1")
        self.assertEqual(trace["harness"]["turn_id"], "turn-1")
        self.assertEqual(trace["harness"]["call_id"], "call-1")
        self.assertEqual(
            trace["action_request"]["capability"],
            trace["execution_observation"]["capability"],
        )

    def test_existing_document_capability_can_be_exposed_without_runtime_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sandbox_root = root / "sandbox"
            sandbox_root.mkdir()
            (sandbox_root / "README.md").write_text(
                "# Fixture\n\n## First\n\nsection body\n",
                encoding="utf-8",
            )
            registry = ToolRegistry(Sandbox(root, sandbox_root), LedgerStub(root / "traces"))
            adapter = HarnessDynamicToolAdapter(
                registry,
                [
                    DynamicToolBinding.from_registry(
                        registry,
                        "document.read_section",
                        description="Read one Markdown section.",
                        input_schema={
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "section_index": {"type": "integer"},
                            },
                            "required": ["path", "section_index"],
                        },
                    )
                ],
                max_output_chars=1000,
            )

            dispatch = adapter.dispatch(
                {
                    "threadId": "thread-file",
                    "turnId": "turn-file",
                    "callId": "call-file",
                    "tool": "read_section",
                    "arguments": {"path": "README.md", "section_index": 1},
                }
            )
            response = dispatch.to_app_server_response()

        self.assertTrue(dispatch.ok)
        self.assertEqual(dispatch.observation.capability, "document.read_section")
        self.assertTrue(response["success"])
        self.assertEqual(response["contentItems"][0]["type"], "inputText")
        self.assertIn("section body", response["contentItems"][0]["text"])

    def test_unknown_dynamic_tool_returns_failed_observation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            adapter = HarnessDynamicToolAdapter(registry, [])

            dispatch = adapter.dispatch(
                {
                    "threadId": "thread-unknown",
                    "turnId": "turn-unknown",
                    "callId": "call-unknown",
                    "tool": "missing",
                    "arguments": {},
                }
            )

        self.assertFalse(dispatch.ok)
        self.assertEqual(dispatch.observation.status, "failure")
        self.assertFalse(dispatch.to_app_server_response()["success"])
        self.assertEqual(dispatch.to_trace_metadata()["harness"]["call_id"], "call-unknown")


if __name__ == "__main__":
    unittest.main()
