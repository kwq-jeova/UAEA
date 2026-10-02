from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from harness.codex_dynamic_tools import (  # noqa: E402
    DynamicToolBinding,
    HarnessDynamicToolAdapter,
)
from harness.semantic_state_adapter import HarnessSemanticStateAdapter  # noqa: E402
from runtime.capability import CapabilityMetadata, ToolResult  # noqa: E402
from runtime.ledger import LedgerStub  # noqa: E402
from runtime.sandbox import Sandbox  # noqa: E402
from runtime.tools import ToolRegistry  # noqa: E402
from phase2.web_adapter import WebAdapter  # noqa: E402
from phase2.web_capability import WebSearchCapability, web_search_metadata  # noqa: E402


class HarnessDynamicToolAdapterTests(unittest.TestCase):
    def test_failure_projection_does_not_expose_stale_relevance_or_raw_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_data = {
                "execution_status": "timeout", "execution_succeeded": False,
                "reason": "request_timeout", "failure_explanation": "The HTTP request timed out.",
                "requested_provider": "bing", "actual_provider": "bing", "fallback_occurred": False,
                "http_attempted": True, "evidence_status": None,
                "evidence_evaluation": {"performed": False, "reason": "execution_not_successful"},
                "raw_search_results": [{"url": "https://stale.example/result"}],
                "search_contract": {"candidate_status": "low_relevance"},
                "recommended_next_action": "revise_query",
            }
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            registry.register_capability(web_search_metadata(), lambda arguments, objective: ToolResult(False, "timeout", raw_data))
            adapter = HarnessDynamicToolAdapter(registry, [DynamicToolBinding.from_registry(
                registry, "web.search", description="Search", input_schema={"type": "object"},
            )])
            dispatch = adapter.dispatch({"threadId": "thread", "turnId": "turn", "callId": "failed",
                                         "tool": "web_search", "arguments": {"provider": "bing", "allow_fallback": False}})
            text = dispatch.to_app_server_response()["contentItems"][0]["text"]
        payload = json.loads(text)
        self.assertEqual(payload["status"], "timeout")
        self.assertEqual(payload["data"]["actual_provider"], "bing")
        self.assertFalse(payload["data"]["execution_succeeded"])
        self.assertNotIn("low_relevance", text)
        self.assertNotIn("revise_query", text)
        self.assertNotIn("https://stale.example/result", text)
        self.assertEqual(dispatch.tool_result.data["raw_search_results"], raw_data["raw_search_results"])
        self.assertEqual(dispatch.tool_result.data["search_contract"]["candidate_status"], "low_relevance")

    @patch.dict("os.environ", {"SERPAPI_KEY": ""})
    def test_real_strict_google_missing_credential_projects_failure_not_low_relevance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            web_adapter = WebAdapter(snapshot_root=root / "snapshots")
            registry.register_capability(web_search_metadata(), WebSearchCapability(
                db_path=root / "source.sqlite", adapter=web_adapter,
            ))
            binding = DynamicToolBinding.from_registry(registry, "web.search", description="Search", input_schema={"type": "object"})
            for budget in (4000, 1000):
                with self.subTest(budget=budget), patch.object(web_adapter, "_http_get") as request:
                    adapter = HarnessDynamicToolAdapter(registry, [binding], max_output_chars=budget)
                    dispatch = adapter.dispatch({"threadId": "thread", "turnId": "turn", "callId": f"call-{budget}",
                                                 "tool": "web_search", "arguments": {
                        "query": "AGI research", "provider": "google", "allow_fallback": False,
                    }})
                    response = dispatch.to_app_server_response()
                request.assert_not_called()
                text = response["contentItems"][0]["text"]
                payload = json.loads(text)
                self.assertFalse(response["success"])
                self.assertLessEqual(len(text), budget)
                self.assertEqual(payload["status"], "configuration_error")
                self.assertEqual(payload["data"]["reason"], "credential_missing")
                self.assertEqual(payload["data"]["requested_provider"], "google")
                self.assertIsNone(payload["data"]["actual_provider"])
                self.assertFalse(payload["data"]["fallback_occurred"])
                self.assertFalse(payload["data"]["execution_succeeded"])
                self.assertNotIn("low_relevance", text)
                self.assertNotIn("revise_query", text)
                self.assertIn("Google search requires SERPAPI_KEY", payload["message"])
                self.assertEqual(dispatch.observation.status, "failure")
                self.assertEqual(dispatch.to_trace_metadata()["execution_observation"]["data"]["reason"], "credential_missing")

    def test_semantic_authority_rejects_conflict_before_registry_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            calls: list[dict] = []
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            registry.register_capability(
                CapabilityMetadata(
                    name="web.search",
                    tool_name="web_search",
                    version="0.1",
                    permission="network",
                    produces_observation=True,
                    context_cost="bounded",
                    future_phase="test",
                ),
                lambda arguments, objective: (
                    calls.append(dict(arguments))
                    or ToolResult(True, "executed", {"actual_provider": "bing"})
                ),
            )
            semantic_state = HarnessSemanticStateAdapter()
            semantic_state.prepare_turn(
                "thread-authority",
                "仅使用 Google 搜索，不要 Bing，不允许 fallback",
                turn_id="turn-policy",
            )
            semantic_state.consume_raw_event({"message": {
                "method": "turn/completed",
                "params": {"threadId": "thread-authority", "turn": {"id": "turn-policy", "status": "completed"}},
            }})
            projection = semantic_state.prepare_turn(
                "thread-authority", "AI agent 最近研究，最好是开发论坛的", turn_id="turn-authority",
            )
            adapter = HarnessDynamicToolAdapter(
                registry,
                [
                    DynamicToolBinding.from_registry(
                        registry,
                        "web.search",
                        description="Search the web.",
                        input_schema={"type": "object"},
                    )
                ],
            )
            adapter.bind_semantic_state_adapter(semantic_state)

            rejected = adapter.dispatch(
                {
                    "threadId": "thread-authority",
                    "turnId": "turn-authority",
                    "callId": "call-conflict",
                    "tool": "web_search",
                    "arguments": {
                        "query": "LoRA training",
                        "provider": "google",
                        "allow_fallback": True,
                    },
                }
            )
            rejected_payload = json.loads(
                rejected.to_app_server_response()["contentItems"][0]["text"]
            )
            accepted = adapter.dispatch(
                {
                    "threadId": "thread-authority",
                    "turnId": "turn-authority",
                    "callId": "call-corrected",
                    "tool": "web_search",
                    "arguments": {
                        "query": "LoRA training",
                        "provider": "google",
                        "allow_fallback": False,
                    },
                }
            )
            trace = rejected.to_trace_metadata()

        self.assertFalse(rejected.ok)
        self.assertEqual(rejected_payload["data"]["error_kind"], "semantic_validation")
        self.assertEqual(rejected_payload["data"]["semantic_status"], "constraint_conflict")
        self.assertEqual(calls, [{"query": "LoRA training", "provider": "google", "allow_fallback": False}])
        self.assertFalse(trace["semantic_validation"]["valid"])
        self.assertEqual(trace["semantic_validation"]["effective_state_id"], projection.payload["effective_state_id"])
        self.assertTrue(any(item["provenance"]["turn_id"] == "turn-policy"
                            for item in rejected_payload["data"]["semantic_items"]))
        self.assertTrue(all(item["owner"] and item["scope"]
                            for item in rejected_payload["data"]["semantic_items"]))
        self.assertEqual(rejected.action_request.parameters["allow_fallback"], True)
        self.assertTrue(accepted.ok)

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
                max_output_chars=1500,
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
        self.assertLessEqual(len(json.dumps(payload, ensure_ascii=False)), 1500)

    def test_low_relevance_model_projection_hides_raw_urls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            registry.register_capability(
                CapabilityMetadata(
                    name="web.search",
                    tool_name="web_search",
                    version="0.1",
                    permission="network",
                    produces_observation=True,
                    context_cost="bounded",
                    future_phase="test",
                ),
                lambda arguments, objective: ToolResult(
                    True,
                    "low relevance",
                    {
                        "raw_search_results": [
                            {"title": "raw", "url": "https://raw.example/result"}
                        ],
                        "raw_results_before_filtering": [
                            {"title": "raw", "url": "https://raw.example/result"}
                        ],
                        "raw_search_result_domains": ["raw.example"],
                        "search_results": [],
                        "candidate_evidence_results": [],
                        "citable_results": [],
                        "evidence_eligibility": {
                            "candidate_status": "low_relevance",
                            "citable_result_count": 0,
                        },
                        "search_contract": {
                            "candidate_status": "low_relevance",
                            "recommended_next_action": "revise_query",
                        },
                        "bounded_evidence_block": (
                            "[WEB EVIDENCE BLOCK]\n"
                            "url: https://raw.example/result"
                        ),
                    },
                ),
            )
            adapter = HarnessDynamicToolAdapter(
                registry,
                [
                    DynamicToolBinding.from_registry(
                        registry,
                        "web.search",
                        description="Search the web.",
                        input_schema={"type": "object"},
                    )
                ],
            )

            dispatch = adapter.dispatch(
                {
                    "threadId": "thread-low",
                    "turnId": "turn-low",
                    "callId": "call-low",
                    "tool": "web_search",
                    "arguments": {"query": "unrelated"},
                }
            )
            payload = json.loads(
                dispatch.to_app_server_response()["contentItems"][0]["text"]
            )

        model_data = payload["data"]
        self.assertNotIn("https://raw.example/result", json.dumps(model_data))
        self.assertNotIn("https://raw.example/result", model_data["bounded_evidence_block"])
        self.assertEqual(model_data["model_visible_evidence"]["citable_results"], [])
        self.assertEqual(
            model_data["model_visible_evidence"]["recommended_next_action"],
            "revise_query",
        )

    def test_semantic_validation_failure_is_structured_and_retryable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            registry = ToolRegistry(Sandbox(root, root / "sandbox"), LedgerStub(root / "traces"))
            registry.register_capability(
                CapabilityMetadata(
                    name="web.search",
                    tool_name="web_search",
                    version="0.1",
                    permission="network",
                    produces_observation=True,
                    context_cost="bounded",
                    future_phase="test",
                ),
                lambda arguments, objective: ToolResult(
                    False,
                    "provider was explicitly specified, but fallback policy is missing.",
                    {
                        "semantic_status": "ambiguous_provider_fallback_policy",
                        "requested_provider": "google",
                        "actual_provider": None,
                        "fallback_occurred": False,
                        "retry_instruction": (
                            "Retry web.search with allow_fallback=true or allow_fallback=false."
                        ),
                        "error_kind": "semantic_validation",
                        "retryable": True,
                    },
                ),
            )
            adapter = HarnessDynamicToolAdapter(
                registry,
                [
                    DynamicToolBinding.from_registry(
                        registry,
                        "web.search",
                        description="Search the web.",
                        input_schema={"type": "object"},
                    )
                ],
            )

            dispatch = adapter.dispatch(
                {
                    "threadId": "thread-retry",
                    "turnId": "turn-retry",
                    "callId": "call-retry",
                    "tool": "web_search",
                    "arguments": {"query": "AI", "provider": "google"},
                }
            )
            payload = json.loads(
                dispatch.to_app_server_response()["contentItems"][0]["text"]
            )

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["data"]["error_kind"], "semantic_validation")
        self.assertTrue(payload["data"]["retryable"])
        self.assertIn("allow_fallback=true", payload["data"]["retry_instruction"])


if __name__ == "__main__":
    unittest.main()
