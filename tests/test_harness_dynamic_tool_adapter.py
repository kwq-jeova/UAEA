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

    def test_bounded_app_server_response_remains_valid_json(self):
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
                    "large result",
                    {
                        "search_query": "recursive self improvement",
                        "search_results": [
                            {"title": "Returned source", "url": "https://example.test/source", "snippet": "ok"}
                        ],
                        "search_contract": {
                            "citation_policy": "Only cite URLs present in search_results.",
                            "page_evidence_requires_fetch": True,
                        },
                        "bounded_evidence_block": "x" * 5000,
                    },
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
                max_output_chars=700,
            )

            dispatch = adapter.dispatch(
                {
                    "threadId": "thread-large",
                    "turnId": "turn-large",
                    "callId": "call-large",
                    "tool": "mock_external_operation",
                    "arguments": {},
                }
            )
            text = dispatch.to_app_server_response()["contentItems"][0]["text"]
            payload = json.loads(text)

        self.assertLessEqual(len(text), 700)
        self.assertTrue(payload["data"]["_tool_output_truncated"])
        self.assertEqual(payload["data"]["search_results"][0]["url"], "https://example.test/source")
        self.assertIn("citation_policy", payload["data"]["search_contract"])

    def test_extreme_bounded_response_preserves_evidence_contract(self):
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
                    "Actual provider www.bing.com returned uncertain candidate evidence; citable_results is empty.",
                    {
                        "search_query": "recursive self-improvement AI papers",
                        "search_provider": "www.bing.com",
                        "candidate_evidence_results": [
                            {"title": "x" * 500, "url": f"https://example.test/{idx}", "snippet": "y" * 500}
                            for idx in range(10)
                        ],
                        "citable_results": [],
                        "evidence_eligibility": {"candidate_status": "uncertain", "citable_result_count": 0},
                        "search_contract": {
                            "candidate_status": "uncertain",
                            "actual_search_provider": "www.bing.com",
                            "citation_policy": "Only cite URLs present in citable_results or later web.fetch results.",
                        },
                    },
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
                max_output_chars=350,
            )

            dispatch = adapter.dispatch(
                {
                    "threadId": "thread-small",
                    "turnId": "turn-small",
                    "callId": "call-small",
                    "tool": "mock_external_operation",
                    "arguments": {},
                }
            )
            payload = json.loads(dispatch.to_app_server_response()["contentItems"][0]["text"])

        self.assertEqual(payload["data"]["search_provider"], "www.bing.com")
        self.assertEqual(payload["data"]["evidence_eligibility"]["candidate_status"], "uncertain")
        self.assertEqual(payload["data"]["search_contract"]["candidate_status"], "uncertain")


if __name__ == "__main__":
    unittest.main()
