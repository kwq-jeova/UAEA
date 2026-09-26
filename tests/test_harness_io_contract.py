from __future__ import annotations

import unittest
import json

from harness.io_contract import (
    ADDITIONAL_CONTEXT_APPLICATION,
    ADDITIONAL_CONTEXT_UNTRUSTED,
    CODEX_SOURCE_COMMIT,
    CODEX_SOURCE_REVISION,
    HARNESS_INPUT_SURFACES,
    HARNESS_OUTPUT_METHODS,
    additional_context_payload,
    application_context,
    effective_capability_context,
    effective_capability_state,
    effective_capability_summary,
    runtime_fact_summary,
    runtime_facts_context,
    turn_context_payload,
    untrusted_context,
)


class HarnessIoContractTests(unittest.TestCase):
    def test_additional_context_uses_pinned_app_server_entry_shape(self):
        payload = additional_context_payload(
            {
                "uaea.application": application_context("stable runtime fact"),
                "uaea.untrusted": untrusted_context("external page text"),
            }
        )

        self.assertEqual(
            payload["uaea.application"],
            {"kind": ADDITIONAL_CONTEXT_APPLICATION, "value": "stable runtime fact"},
        )
        self.assertEqual(
            payload["uaea.untrusted"],
            {"kind": ADDITIONAL_CONTEXT_UNTRUSTED, "value": "external page text"},
        )

    def test_additional_context_rejects_string_shortcut_and_unknown_kind(self):
        with self.assertRaises(ValueError):
            additional_context_payload({"uaea.bad": {"kind": "application", "value": 7}})
        with self.assertRaises(ValueError):
            additional_context_payload({"uaea.bad": {"kind": "system", "value": "x"}})
        with self.assertRaises(ValueError):
            additional_context_payload({"uaea.bad": "plain text"})  # type: ignore[arg-type]

    def test_runtime_facts_are_app_server_additional_context_entries(self):
        facts = runtime_facts_context()

        self.assertEqual(
            {
                "uaea.runtime_facts.model",
                "uaea.runtime_facts.execution",
                "uaea.runtime_facts.capabilities",
                "uaea.runtime_facts.web_limits",
            },
            set(facts),
        )
        self.assertTrue(
            all(entry["kind"] == ADDITIONAL_CONTEXT_APPLICATION for entry in facts.values())
        )
        self.assertIn("uaea_local_vllm", facts["uaea.runtime_facts.model"]["value"])
        self.assertIn("qwen25-14b-awq", facts["uaea.runtime_facts.model"]["value"])
        self.assertIn(
            "does not mean UAEA dynamic Web capabilities are unavailable",
            facts["uaea.runtime_facts.execution"]["value"],
        )
        self.assertIn("best-effort", facts["uaea.runtime_facts.web_limits"]["value"])

    def test_effective_capability_state_is_derived_from_dynamic_tools(self):
        tools = [
            {"name": "web_search"},
            {"name": "web_fetch"},
            {"name": "read_section"},
            {"name": "list_files"},
        ]

        state = effective_capability_state(tools)

        self.assertTrue(state["capabilities"]["web.search"]["available"])
        self.assertTrue(state["capabilities"]["web.fetch"]["available"])
        self.assertTrue(state["capabilities"]["document.read_section"]["available"])
        self.assertTrue(state["capabilities"]["fs.list"]["available"])
        self.assertEqual(state["execution_planes"]["harness_native_shell"]["network"], "disabled")
        self.assertEqual(
            state["resolution"]["external_or_recent_public_information"],
            "web.search",
        )
        self.assertTrue(
            any("does not disable UAEA web.search" in rule for rule in state["routing_rules"])
        )

    def test_effective_capability_context_is_structured_turn_projection(self):
        context = effective_capability_context([{"name": "web_search"}, {"name": "web_fetch"}])
        entry = context["uaea.effective_capability_state"]
        state = json.loads(entry["value"])

        self.assertEqual(entry["kind"], ADDITIONAL_CONTEXT_APPLICATION)
        self.assertEqual(state["schema"], "uaea.effective_capability_state.v0")
        self.assertTrue(state["capabilities"]["web.search"]["available"])
        self.assertFalse(state["capabilities"]["fs.list"]["available"])

    def test_turn_context_combines_runtime_facts_and_effective_capabilities(self):
        payload = turn_context_payload([{"name": "web_search"}, {"name": "web_fetch"}])

        self.assertIn("uaea.runtime_facts.model", payload)
        self.assertIn("uaea.effective_capability_state", payload)
        self.assertTrue(
            all(entry["kind"] == ADDITIONAL_CONTEXT_APPLICATION for entry in payload.values())
        )
        self.assertIn("web_available=True", effective_capability_summary([{"name": "web_search"}, {"name": "web_fetch"}]))

    def test_contract_surfaces_are_explicitly_scoped(self):
        self.assertEqual(CODEX_SOURCE_REVISION, "rust-v0.154.0")
        self.assertEqual(
            CODEX_SOURCE_COMMIT,
            "6b9826e3aa83b1a5947db50f4332cb9c65f1b340",
        )
        self.assertIn("turn/start.additionalContext", HARNESS_INPUT_SURFACES)
        self.assertIn("turn/steer.additionalContext", HARNESS_INPUT_SURFACES)
        self.assertIn("dynamicToolCall.response", HARNESS_INPUT_SURFACES)
        self.assertIn("item/tool/call", HARNESS_OUTPUT_METHODS)
        self.assertIn("thread/tokenUsage/updated", HARNESS_OUTPUT_METHODS)
        self.assertIn(
            "model=uaea_local_vllm/qwen25-14b-awq",
            runtime_fact_summary(),
        )


if __name__ == "__main__":
    unittest.main()
