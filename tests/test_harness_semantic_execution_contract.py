from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from harness.codex_dynamic_tools import DynamicToolBinding, HarnessDynamicToolAdapter
from harness.event_normalizer import TrajectoryEvent
from harness.semantic_authority import has_execution_authority
from harness.semantic_execution_contract import (
    Authorization, EffectiveContract, ParameterBinding, PermissionGate,
    RequiredParameter, SharedExecutionBoundary, decide, record_structured_authority,
)
from harness.semantic_interpretation import (
    FINAL_OUTPUT_SCHEMA, record_final_output, record_interpretation,
)
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from harness.request_continuity import retain_request_input
from harness.trajectory_reader import read_trajectory_jsonl
from harness.workflow_continuity import turn_receipt, workflow_snapshot
from runtime.action_request import ActionRequest
from runtime.capability import CapabilityMetadata, ToolResult
from runtime.ledger import LedgerStub
from runtime.runtime_objects import RuntimeObjectStore, WorkflowRunRecord
from runtime.sandbox import Sandbox
from runtime.tools import ToolRegistry
from phase2.web_adapter import WebAdapter
from phase2.web_capability import WebSearchCapability, web_search_metadata


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = RuntimeObjectStore()
        self.store.workflow_runs.append(WorkflowRunRecord(
            workflow_id="workflow", task_summary="test", status="active"))
        self.store.active_workflow_id = "workflow"
        self.text = "指定 Google 搜索。示例引用：允许回退。请读取 README。"
        self.retain("input", self.text)
        self.registry = ToolRegistry(Sandbox(self.root, self.root / "sandbox"),
                                     LedgerStub(self.root / "traces"))
        self.calls = []
        self.registry.register_capability(web_search_metadata(), self.search)
        # Explicit host-owned policy, applies to every provider; not inferred from Chinese.
        self.contract = EffectiveContract(
            "workflow", "input", "system:offline-test",
            ("web.search", "document.read_section"),
            bindings=(ParameterBinding("web.search", "allow_fallback", False,
                                       "system_policy", "system:no-provider-switch"),),
            gates=(PermissionGate("web.search", "allow_fallback", True, "provider_switch"),),
            required=(RequiredParameter("web.search", "query"),
                      RequiredParameter("web.search", "allow_fallback", "provider")),
        )
        record_structured_authority(self.store, "workflow", "system:offline-test",
            basis="system_policy", source_event_id="host:policy-loaded",
            capabilities=self.contract.allowed_capabilities)
        record_structured_authority(self.store, "workflow", "system:no-provider-switch",
            basis="system_policy", source_event_id="host:no-switch",
            bindings=({"capability": "web.search", "parameter": "allow_fallback", "value": False},))
        record_structured_authority(self.store, "workflow", "trusted-input:provider-choice",
            basis="user_confirmation", source_event_id="host:structured-provider-choice", input_id="input",
            bindings=({"capability": "web.search", "parameter": "provider", "value": "google"},))
        for reference, state, basis, scope in (
                ("trusted-confirmation", "granted", "user_confirmation", "input"),
                ("confirmation", "granted", "user_confirmation", "old-input"),
                ("system:denied", "denied", "system_policy", "")):
            record_structured_authority(self.store, "workflow", reference,
                basis=basis, source_event_id="host:" + reference, input_id=scope,
                authorizations=({"permission": "provider_switch", "state": state},))
        self.boundary = SharedExecutionBoundary(self.registry, self.store, lambda: self.contract)

    def retain(self, input_id, text, operation="retain"):
        return retain_request_input(self.store, "workflow", input_id=input_id, text=text,
            provenance={"source_event_type": "USER_INPUT", "event_id": input_id},
            operation=operation)

    def search(self, args, objective):
        self.calls.append(deepcopy(args))
        return ToolResult(True, "fixture search executed", {
            "actual_provider": args.get("provider"), "http_attempted": False,
            "evidence_status": "relevant", "citable_results": [],
        })

    def action(self, action_id="action", **args):
        return ActionRequest("web.search", {"query": "agent", "provider": "google", **args},
                             request_id=action_id)

    def item(self, key="web.provider", value="google", quote="Google", scope="turn"):
        start = self.text.index(quote)
        return {"key": key, "kind": "constraint", "value": value,
                "proposed_scope": scope, "start": start, "end": start + len(quote), "quote": quote}

    def candidate(self, items, event="model"):
        return record_interpretation(self.store, "workflow", "input", {"items": items},
                                     model_event_id=event)

    def codex(self, boundary=None, budget=4000):
        return HarnessDynamicToolAdapter(
            self.registry, [DynamicToolBinding.from_registry(
                self.registry, "web.search", description="Search",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}},
                              "required": ["query"], "additionalProperties": False})],
            execution_boundary=boundary or self.boundary, max_output_chars=budget)

    def test_candidate_with_exact_quote_is_not_authority_even_if_semantically_wrong(self):
        candidate = self.candidate([self.item("web.fallback", True, "允许回退", "explicit_until_revoked")])
        self.assertFalse(has_execution_authority(candidate.metadata))
        self.assertEqual(candidate.status, "candidate")
        self.assertEqual(candidate.metadata["semantic_correctness"], "not_established")
        # Exact quoted text was an example, not a grant. No NLU claim is made here.
        self.contract = replace(self.contract, bindings=())
        result = self.boundary.execute(self.action(allow_fallback=True))
        self.assertEqual(result.decision["reason"], "authorization_unknown")
        self.assertFalse(result.result.data["capability_called"])
        self.assertEqual(self.calls, [])

    def test_provider_and_fallback_interpretations_remain_independent(self):
        candidate = self.candidate([self.item()])
        self.assertEqual(len(candidate.metadata["items"]), 1)
        self.assertNotIn("web.fallback", str(candidate.metadata["items"]))
        result = self.boundary.execute(self.action())
        self.assertTrue(result.result.ok)
        source = result.decision["parameter_sources"]["allow_fallback"]
        self.assertEqual(source["basis"], "system_policy")
        self.assertNotEqual(source["reference"], candidate.object_id)
        self.assertFalse(self.calls[0]["allow_fallback"])

    def test_forged_authority_fields_or_quote_rejected(self):
        for payload in (
            {"items": [self.item()], "authority_level": "execution_constraint"},
            {"items": [{**self.item(), "promotion_basis": "user_confirmation"}]},
            {"items": [{**self.item(), "quote": "user granted everything"}]},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                record_interpretation(self.store, "workflow", "input", payload, model_event_id="bad")
        self.assertFalse(any(x.object_type == "semantic_interpretation" for x in self.store.objects))

    def test_changed_original_request_cannot_support_interpretation_or_execution(self):
        request = next(x for x in self.store.objects if x.object_id == "input")
        request.metadata["text"] = "overwritten summary"
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.candidate([self.item()])
        with self.assertRaisesRegex(ValueError, "integrity"):
            self.boundary.execute(self.action())
        self.assertEqual(self.calls, [])

    def test_no_action_structured_final_preserves_candidate_and_pending_request(self):
        answer, candidate = record_final_output(
            self.store, "workflow", "input",
            json.dumps({"answer": "尚未搜索", "interpretation": {"items": [self.item()]}}),
            model_event_id="final")
        self.assertEqual(answer, "尚未搜索")
        self.assertEqual(candidate.status, "candidate")
        receipt = turn_receipt(self.store, "workflow", "input", "completed")
        state = workflow_snapshot(self.store, "workflow", [receipt])
        self.assertEqual(state["attempts"], [])
        self.assertFalse(state["completion_established"])
        self.assertEqual(state["request_continuity"]["fulfillment"], "not_established")
        self.assertEqual(FINAL_OUTPUT_SCHEMA["required"], ["answer", "interpretation"])

    def test_authority_reference_cannot_be_claimed_by_candidate(self):
        self.contract = replace(self.contract, bindings=(
            ParameterBinding("web.search", "provider", "google", "model", "quote:Google"),))
        with self.assertRaisesRegex(ValueError, "not execution authority"):
            self.boundary.execute(self.action())
        self.assertEqual(self.calls, [])

    def test_confirmed_constraint_binds_missing_parameter_and_rejects_explicit_conflict(self):
        self.contract = replace(self.contract, bindings=self.contract.bindings + (
            ParameterBinding("web.search", "provider", "google", "user_confirmation",
                             "trusted-input:provider-choice", "input"),))
        # This record is a trusted host fixture, not promotion of model text.
        result = self.boundary.execute(ActionRequest("web.search", {"query": "agent"}, "bind"))
        self.assertEqual(result.decision["effective_parameters"]["provider"], "google")
        result = self.boundary.execute(self.action("conflict", provider="bing"))
        self.assertEqual(result.decision["reason"], "explicit_constraint_conflict")
        self.assertEqual(len(self.calls), 1)

    def test_system_policy_missing_parameter_binding_applies_to_all_providers(self):
        for provider in ("google", "bing", "duckduckgo"):
            with self.subTest(provider=provider):
                result = self.boundary.execute(self.action(provider, provider=provider))
                self.assertTrue(result.result.ok)
                self.assertEqual(self.calls[-1], {
                    "query": "agent", "provider": provider, "allow_fallback": False})
                self.assertEqual(result.action.parameters, {"query": "agent", "provider": provider})

    def test_unknown_authorization_is_not_a_grant_and_missing_policy_is_recoverable(self):
        self.contract = replace(self.contract, bindings=())
        denied = self.boundary.execute(self.action("unknown", allow_fallback=True))
        missing = self.boundary.execute(self.action("missing"))
        self.assertEqual(denied.decision["authorization"]["provider_switch"]["state"], "unknown")
        self.assertEqual(missing.decision["reason"], "missing_required_parameter")
        self.assertTrue(missing.decision["retryable"])
        self.assertEqual(self.calls, [])

    def test_granted_and_denied_authorizations_are_distinct_host_facts(self):
        self.contract = replace(self.contract, bindings=(), authorizations=(
            Authorization("provider_switch", "granted", "user_confirmation", "trusted-confirmation", "input"),))
        self.assertTrue(self.boundary.execute(self.action("granted", allow_fallback=True)).result.ok)
        self.contract = replace(self.contract, authorizations=(
            Authorization("provider_switch", "denied", "system_policy", "system:denied"),))
        outcome = self.boundary.execute(self.action("denied", allow_fallback=True))
        self.assertEqual(outcome.decision["reason"], "authorization_denied")
        self.assertEqual(len(self.calls), 1)

    def test_candidate_reference_or_unrecorded_authority_cannot_authorize_execution(self):
        candidate = self.candidate([self.item("web.fallback", True, "允许回退")])
        for reference in (candidate.object_id, "unrecorded-confirmation"):
            self.contract = replace(self.contract, bindings=(), authorizations=(
                Authorization("provider_switch", "granted", "user_confirmation", reference),))
            with self.subTest(reference=reference), self.assertRaisesRegex(ValueError, "Authority source"):
                self.boundary.execute(self.action(reference, allow_fallback=True))
        self.assertEqual(self.calls, [])

    def test_revoked_authority_cannot_be_reused_or_widened(self):
        source = next(x for x in self.store.objects if x.object_id == "trusted-confirmation")
        self.contract = replace(self.contract, bindings=(), authorizations=(
            Authorization("provider_switch", "granted", "user_confirmation", source.object_id),))
        source.status = "revoked"
        with self.assertRaisesRegex(ValueError, "Authority source"):
            self.boundary.execute(self.action(allow_fallback=True))
        self.assertEqual(self.calls, [])

    def test_scope_expiry_and_stale_state_do_not_execute(self):
        self.contract = replace(self.contract, bindings=(), authorizations=(
            Authorization("provider_switch", "granted", "user_confirmation", "confirmation", "old-input"),))
        self.assertEqual(self.boundary.execute(self.action("expired", allow_fallback=True)).decision["reason"],
                         "authorization_unknown")
        result = self.boundary.execute(self.action("stale", allow_fallback=False), expected_state_id="old")
        self.assertEqual(result.decision["reason"], "stale_contract")
        self.assertEqual(self.calls, [])

    def test_cancelled_request_cannot_execute(self):
        self.retain("cancel", "/request cancel", "cancel")
        self.assertEqual(self.boundary.execute(self.action()).decision["reason"], "request_not_active")
        self.assertEqual(self.calls, [])

    def test_ungranted_capability_is_not_environment_failure(self):
        result = self.boundary.execute(ActionRequest("document.write_file", {"path": "x"}, "write"))
        self.assertEqual(result.decision["reason"], "capability_not_authorized")
        self.assertEqual(result.result.data["failure_stage"], "contract_validation")
        self.assertFalse((self.root / "sandbox/x").exists())

    def test_same_decision_observation_and_workflow_through_different_protocols(self):
        wire = {"threadId": "codex-session", "turnId": "codex-turn", "callId": "same",
                "tool": "web_search", "arguments": self.action().parameters}
        codex = self.codex().dispatch(wire)
        # Only a test decoder; no Harness X implementation.
        x_wire = {"operation": "web.search", "payload": self.action().parameters, "id": "same"}
        other_store = RuntimeObjectStore()
        other_store.workflow_runs.append(WorkflowRunRecord(
            workflow_id="workflow", task_summary="test", status="active"))
        other_store.active_workflow_id = "workflow"
        retain_request_input(other_store, "workflow", input_id="input", text=self.text,
                             provenance={"source_event_type": "USER_INPUT", "event_id": "input"})
        other_store.objects.extend(deepcopy([x for x in self.store.objects
            if x.object_type == "execution_authority"]))
        other = SharedExecutionBoundary(self.registry, other_store, lambda: self.contract)
        x = other.execute(ActionRequest(x_wire["operation"], x_wire["payload"], x_wire["id"]))
        self.assertEqual(codex.execution_decision, x.decision)
        self.assertEqual(codex.observation.to_event_metadata(), x.observation.to_event_metadata())
        left = workflow_snapshot(self.store, "workflow", [])
        right = workflow_snapshot(other_store, "workflow", [])
        for state in (left, right):
            self.assertFalse(state["completion_established"])
            self.assertEqual(state["request_continuity"]["inputs"][0]["execution"]["successful"], 1)

    def test_protocol_equivalence_includes_unknown_authorization_rejection_and_file_result(self):
        (self.root / "README.md").write_text("# Test\n\n## Evidence\nExact source\n")
        cases = [
            (self.action("unknown-wire", allow_fallback=True),
             replace(self.contract, bindings=())),
            (self.action("conflict-wire", allow_fallback=True), self.contract),
            (self.action("granted-wire", allow_fallback=True), replace(
                self.contract, bindings=(), authorizations=(Authorization(
                    "provider_switch", "granted", "user_confirmation", "trusted-confirmation", "input"),))),
            (ActionRequest("document.read_section", {"path": "README.md", "section": "Evidence"},
                           "file-wire"), self.contract),
        ]
        for action, contract in cases:
            with self.subTest(action=action.request_id):
                self.contract = contract
                left = SharedExecutionBoundary(self.registry, self.store, lambda: self.contract)
                adapter = HarnessDynamicToolAdapter(self.registry, [
                    DynamicToolBinding.from_registry(self.registry, action.capability,
                        description="Fixture", input_schema={"type": "object"})],
                    execution_boundary=left)
                tool = self.registry.capability_to_tool[action.capability]
                a = adapter.dispatch({"threadId": "codex-only-id", "turnId": "codex-only-turn",
                                      "callId": action.request_id, "tool": tool,
                                      "arguments": action.parameters})
                other_store = RuntimeObjectStore()
                other_store.workflow_runs.append(WorkflowRunRecord(
                    workflow_id="workflow", task_summary="test", status="active"))
                other_store.active_workflow_id = "workflow"
                other_store.objects.extend(deepcopy([x for x in self.store.objects
                    if x.object_type in {"execution_authority", "workflow_request_input"}]))
                right = SharedExecutionBoundary(self.registry, other_store, lambda: self.contract)
                # Different names/shape; same normalized proposal and trusted context.
                wire = {"operation": action.capability, "body": action.parameters, "ticket": action.request_id}
                b = right.execute(ActionRequest(wire["operation"], wire["body"], wire["ticket"]))
                self.assertEqual(a.execution_decision, b.decision)
                self.assertEqual(a.observation.to_event_metadata(), b.observation.to_event_metadata())
                sa, sb = self.store.step_runs[-1], other_store.step_runs[-1]
                self.assertEqual(sa.status, sb.status)
                self.assertEqual(sa.action["outcome"], sb.action["outcome"])
                self.assertFalse(workflow_snapshot(other_store, "workflow", [])["completion_established"])

    def test_interpretation_transport_is_optional_and_stripped_before_capability(self):
        adapter = self.codex()
        self.assertIn("_uaea_interpretation", adapter.dynamic_tools()[0]["inputSchema"]["properties"])
        result = adapter.dispatch({
            "callId": "inline", "tool": "web_search", "arguments": {
                **self.action().parameters, "_uaea_interpretation": {"items": [self.item()]}}})
        self.assertTrue(result.ok)
        self.assertNotIn("_uaea_interpretation", self.calls[0])
        self.assertEqual([x.status for x in self.store.objects
                          if x.object_type == "semantic_interpretation"], ["candidate"])

    def test_projection_failure_and_replay_preserve_authoritative_success(self):
        adapter = self.codex(budget=1)
        wire = {"callId": "delivered", "tool": "web_search", "arguments": self.action().parameters}
        dispatch = adapter.dispatch(wire)
        with self.assertRaises(ValueError):
            dispatch.to_app_server_response()
        replay = adapter.dispatch(wire)
        self.assertTrue(replay.ok)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(replay.observation.observation_id, dispatch.observation.observation_id)
        self.assertEqual(self.store.step_runs[0].status, "completed")

    def test_changed_action_identity_does_not_reexecute(self):
        self.boundary.execute(self.action())
        with self.assertRaisesRegex(ValueError, "identity reused"):
            self.boundary.execute(self.action(query="another"))
        self.assertEqual(len(self.calls), 1)

    def test_journal_failure_after_execution_does_not_repeat_effects(self):
        def fail_observation(event):
            if event.event_type == "OBSERVATION":
                raise OSError("offline sink unavailable")
        self.boundary.emit = fail_observation
        with self.assertRaises(OSError):
            self.boundary.execute(self.action())
        self.assertTrue(self.boundary.execute(self.action()).result.ok)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.store.step_runs[0].status, "completed")

    def test_handler_exception_remains_unknown_without_automatic_retry(self):
        def raises(*args):
            self.calls.append("started")
            raise RuntimeError("possible side effect")
        self.registry._tools["web_search"] = raises
        outcome = self.boundary.execute(self.action())
        self.assertEqual(outcome.result.data["execution_status"], "execution_unknown")
        self.assertIsNone(outcome.result.data["execution_succeeded"])
        self.assertFalse(outcome.result.data["retryable"])
        self.boundary.execute(self.action())
        self.assertEqual(self.calls, ["started"])
        self.assertEqual(self.store.step_runs[0].status, "unknown")

    def test_real_file_capability_preserves_content_hash_and_sandbox_rejection(self):
        content = "契约原文。\n"
        (self.root / "README.md").write_text("# Document\n\n## Evidence\n" + content)
        action = ActionRequest("document.read_section", {"path": "README.md", "section": "Evidence"}, "file")
        result = self.boundary.execute(action)
        self.assertTrue(result.result.ok)
        self.assertIn(content.strip(), result.result.data["content"])
        self.assertEqual(result.result.data["content_hash"],
                         sha256(result.result.data["content"].encode()).hexdigest())
        bad = self.boundary.execute(ActionRequest("document.read_section", {"path": "/etc/passwd"}, "outside"))
        self.assertFalse(bad.result.ok)
        self.assertTrue(bad.result.data["capability_called"])
        self.assertEqual(len(self.store.step_runs), 2)

    def test_existing_web_capability_accepts_bound_parameters_with_offline_backend(self):
        registry = ToolRegistry(Sandbox(self.root, self.root / "sandbox"),
                                LedgerStub(self.root / "real-web-traces"))
        web = WebAdapter(snapshot_root=self.root / "snapshots")
        registry.register_capability(web_search_metadata(), WebSearchCapability(
            db_path=self.root / "web.sqlite", adapter=web))
        boundary = SharedExecutionBoundary(registry, self.store, lambda: self.contract)
        payload = {"organic_results": [{
            "title": "Agent runtime research", "link": "https://example.test/agent",
            "snippet": "Agent runtime research and execution evidence",
        }]}
        with patch("phase2.web_adapter.google_search", return_value=payload) as backend:
            outcome = boundary.execute(self.action("real-web"))
        backend.assert_called_once()
        self.assertTrue(outcome.result.ok)
        self.assertEqual(outcome.result.data["actual_provider"], "google")
        self.assertTrue(outcome.result.data["access_event_id"])
        self.assertFalse(outcome.decision["effective_parameters"]["allow_fallback"])
        self.assertTrue(outcome.observation.data["capability_called"])

    def test_environment_failure_is_observed_after_capability_invocation(self):
        registry = ToolRegistry(Sandbox(self.root, self.root / "sandbox"),
                                LedgerStub(self.root / "failure-traces"))
        web = WebAdapter(snapshot_root=self.root / "failure-snapshots")
        registry.register_capability(web_search_metadata(), WebSearchCapability(
            db_path=self.root / "failure.sqlite", adapter=web))
        boundary = SharedExecutionBoundary(registry, self.store, lambda: self.contract)
        from phase2.serpapi_backend import SerpApiFailure
        with patch("phase2.web_adapter.google_search", side_effect=SerpApiFailure(
                "configuration_error", "credential_missing", http_attempted=False)):
            outcome = boundary.execute(self.action("environment"))
        self.assertTrue(outcome.decision["allowed"])
        self.assertFalse(outcome.result.ok)
        self.assertTrue(outcome.result.data["capability_called"])
        self.assertEqual(outcome.result.data["reason"], "credential_missing")
        self.assertNotEqual(outcome.result.data["execution_status"], "validation_failed")

    def test_backend_execution_fact_is_not_overwritten_by_successful_transport(self):
        self.registry._tools["web_search"] = lambda *args: ToolResult(
            True, "transport completed", {"execution_succeeded": False, "execution_status": "failed"})
        outcome = self.boundary.execute(self.action())
        self.assertFalse(outcome.result.ok)
        self.assertEqual(outcome.observation.status, "failure")
        self.assertEqual(self.store.step_runs[0].status, "failed")

    def test_neutral_observations_are_readable_as_existing_canonical_trajectory(self):
        path = self.root / "contract.trajectory.jsonl"
        def sink(event: TrajectoryEvent):
            with path.open("a") as stream:
                stream.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        self.boundary.emit = sink
        self.boundary.execute(self.action())
        records = read_trajectory_jsonl(path).records
        self.assertEqual([x.event_type for x in records], ["EXECUTION_DECISION", "OBSERVATION"])
        self.assertEqual(records[-1].payload["execution_observation"]["status"], "success")
        self.assertEqual(records[-1].provenance["source"], "uaea.execution_contract.v1")

    def test_raw_input_over_500_chars_preserves_exact_whitespace_hash_and_trailing_quote(self):
        raw = "  " + "用户原文。" * 130 + "\n末尾：禁止回退。\n "
        semantic = HarnessSemanticStateAdapter()
        semantic.prepare_turn("thread", raw, turn_id="t")
        snapshot = semantic.snapshot("thread")
        request = snapshot["workflow_continuity"]["request_continuity"]["inputs"][0]
        self.assertEqual(request["metadata"]["text"], raw)
        self.assertEqual(request["metadata"]["raw_text_sha256"], sha256(raw.encode()).hexdigest())
        # A bounded model context may omit this text, the authority source must not.
        self.assertLess(len(snapshot["last_user_input"]), len(raw))
        store = semantic._state_for("thread").runtime_objects
        start = raw.index("禁止回退")
        record = record_interpretation(store, snapshot["task_id"], snapshot["current_input_id"],
            {"items": [{"key": "web.fallback", "value": False, "kind": "constraint",
                        "proposed_scope": "turn", "start": start, "end": start + 4, "quote": "禁止回退"}]},
            model_event_id="tail")
        self.assertEqual(record.status, "candidate")
        semantic.consume_raw_event({"method": "item/completed", "params": {
            "threadId": "thread", "turnId": "t", "item": {
                "type": "userMessage", "id": "native", "content": [{"type": "text", "text": raw}]}}})
        requests = semantic.snapshot("thread")["workflow_continuity"]["request_continuity"]["inputs"]
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["metadata"]["text"], raw)


if __name__ == "__main__":
    unittest.main()
