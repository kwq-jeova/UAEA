from __future__ import annotations

import json
import unittest
from copy import deepcopy

from harness.io_contract import turn_context_payload
from harness.semantic_state_adapter import HarnessSemanticStateAdapter
from harness.scoped_semantics import ScopedSemanticResolver
from harness.semantic_authority import (
    EXECUTION_CONSTRAINT, INTERPRETATION, SEMANTIC_AUTHORITY_SCHEMA,
    has_execution_authority, user_directive_basis,
)
from harness.semantic_promotion_audit import build_promotion_audit
from runtime.runtime_objects import RuntimeObjectStore


def _source(input_id="input1", event_type="USER_INPUT"):
    return {"thread_id": "thread", "turn_id": "t1", "input_id": input_id,
            "source_event_type": event_type, "event_id": "event1"}


def _bind(resolver, *, value="web.provider=google", basis=None, strength="hard", source=None,
          scope="task", owner="task"):
    return resolver.bind(kind="capability_constraint", key="web.provider", value=value,
                         scope=scope, owner=owner, provenance=source or _source(),
                         promotion_basis=basis, strength=strength)


class SemanticAuthorityTests(unittest.TestCase):
    def test_strength_and_provenance_alone_do_not_grant_authority(self):
        resolver = ScopedSemanticResolver(RuntimeObjectStore())
        record = _bind(resolver)
        self.assertEqual(record.metadata["authority_level"], INTERPRETATION)
        self.assertFalse(has_execution_authority(record.metadata))
        self.assertEqual(resolver.resolve(task_id="task", input_id="input1").constraints, [])
        self.assertEqual(len(resolver.items()), 1)

    def test_authority_requires_basis_not_strength(self):
        resolver = ScopedSemanticResolver(RuntimeObjectStore())
        basis = user_directive_basis(_source(), key="web.provider", value="web.provider=google")
        record = _bind(resolver, basis=basis, strength="soft")
        self.assertTrue(has_execution_authority(record.metadata))
        self.assertEqual(record.metadata["authority_level"], EXECUTION_CONSTRAINT)
        self.assertEqual(resolver.resolve(task_id="task", input_id="input1").constraints, ["web.provider=google"])

    def test_basis_is_bound_to_the_input_and_exact_interpretation(self):
        for field, value in (("input_id", "other-input"), ("key", "other-key"),
                             ("value", "web.provider=bing")):
            with self.subTest(field=field):
                resolver = ScopedSemanticResolver(RuntimeObjectStore())
                basis = user_directive_basis(_source(), key="web.provider", value="web.provider=google")
                basis[field] = value
                record = _bind(resolver, basis=basis)
                self.assertFalse(has_execution_authority(record.metadata))
                self.assertEqual(resolver.resolve(task_id="task", input_id="input1").constraints, [])
                self.assertEqual(record.status, "active")

    def test_agent_source_cannot_create_user_authority(self):
        source = _source(event_type="AGENT_OUTPUT")
        with self.assertRaises(ValueError):
            user_directive_basis(source, key="web.provider", value="web.provider=google")
        resolver = ScopedSemanticResolver(RuntimeObjectStore())
        basis = user_directive_basis(_source(), key="web.provider", value="web.provider=google")
        record = _bind(resolver, basis=basis, source=source)
        self.assertFalse(has_execution_authority(record.metadata))

    def test_goal_or_world_interpretation_is_not_a_web_directive(self):
        with self.assertRaises(ValueError):
            user_directive_basis(_source(), key="world.google_available", value="false")
        metadata = {"kind": "capability_constraint", "key": "world.google_available", "value": "false",
                    "authority_level": EXECUTION_CONSTRAINT, "provenance": _source(),
                    "promotion_basis": {"type": "existing_web_user_directive", "input_id": "input1",
                                        "key": "world.google_available", "value": "false"}}
        self.assertFalse(has_execution_authority(metadata))

    def test_interpretation_cannot_supersede_or_scope_override_a_directive(self):
        resolver = ScopedSemanticResolver(RuntimeObjectStore())
        basis = user_directive_basis(_source(), key="web.provider", value="web.provider=google")
        directive = _bind(resolver, basis=basis)
        interpretation = _bind(resolver, value="web.provider=bing")
        _bind(resolver, value="web.provider=duckduckgo", scope="turn", owner="input1")
        self.assertEqual(directive.status, "active")
        self.assertEqual(interpretation.status, "active")
        effective = resolver.resolve(task_id="task", input_id="input1")
        self.assertEqual(effective.constraints, ["web.provider=google"])
        self.assertEqual(len(effective.interpretation_items), 1)

    def test_directive_replacement_retains_previous_record(self):
        resolver = ScopedSemanticResolver(RuntimeObjectStore())
        old = _bind(resolver, basis=user_directive_basis(_source(), key="web.provider", value="web.provider=google"))
        new_source = _source("input2")
        new = _bind(resolver, value="web.provider=bing", source=new_source,
                    basis=user_directive_basis(new_source, key="web.provider", value="web.provider=bing"))
        self.assertEqual(old.status, "superseded")
        self.assertEqual(old.metadata["superseded_by"], new.object_id)
        self.assertEqual(len(resolver.items()), 2)
        self.assertEqual(resolver.resolve(task_id="task", input_id="input2").constraints, ["web.provider=bing"])

    def test_old_record_missing_authority_is_retained_without_grandfathering(self):
        resolver = ScopedSemanticResolver(RuntimeObjectStore())
        record = _bind(resolver)
        record.metadata.pop("authority_level")
        record.metadata.pop("promotion_basis")
        effective = resolver.resolve(task_id="task", input_id="input1")
        self.assertEqual(effective.constraints, [])
        self.assertEqual(effective.interpretation_items[0].object_id, record.object_id)

    def test_source_extraction_retained_without_becoming_a_boundary(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn("thread", "研究商业化应用，商业论坛和开发论坛都可以", turn_id="t1")
        snapshot = adapter.snapshot("thread")
        self.assertIn("exclude:commercial_promotional", snapshot["source_preferences"])
        self.assertEqual(snapshot["constraints"], [])
        self.assertEqual(projection.payload["constraints"], [])
        self.assertTrue(projection.payload["interpretations"])
        self.assertTrue(all(item["authority_level"] == INTERPRETATION for item in projection.payload["interpretations"]))
        self.assertTrue(all(item["metadata"]["provenance"]["input_id"]
                            for item in snapshot["semantic_items"]))

    def test_projection_and_validation_share_authority_across_turns(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("thread", "只使用 Google，不允许 fallback", turn_id="t1")
        projection = adapter.prepare_turn("thread", "继续研究，论坛资料也可以", turn_id="t2")
        decision = adapter.validate_tool_action("thread", "web.search", {
            "provider": "google", "allow_fallback": False, "query": "agent applications",
        }, turn_id="t2", call_id="call1")
        self.assertTrue(decision["valid"])
        self.assertEqual(decision["active_constraints"], projection.payload["constraints"])
        self.assertEqual(decision["effective_state_id"], projection.payload["effective_state_id"])
        self.assertNotIn("prefer:forums", decision["active_constraints"])
        self.assertTrue(all(has_execution_authority(item["metadata"]) for item in decision["semantic_items"]))
        self.assertTrue(all(item["metadata"]["promotion_basis"]["input_id"]
                            for item in decision["semantic_items"]))

    def test_projection_separates_authority_and_untrusted_context(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn("thread", "只使用 Google，不允许 fallback，论坛资料也可以", turn_id="t1")
        before = deepcopy(projection.payload)
        context = turn_context_payload([], semantic_projection=projection.payload)
        trusted = context["uaea.semantic_state_projection"]
        hints = context["uaea.semantic_interpretations"]
        self.assertEqual(trusted["kind"], "application")
        self.assertEqual(hints["kind"], "untrusted")
        authority = json.loads(trusted["value"])
        self.assertEqual(authority["constraints"], projection.payload["constraints"])
        self.assertNotIn("source_preferences", authority)
        self.assertNotIn("topic", authority)
        self.assertIn("prefer:forums", json.loads(hints["value"])["source_preferences"])
        report = build_promotion_audit(adapter.snapshot("thread"), stage="PRE_TURN", additional_context=context)
        source_item = next(item for item in report["items"] if item["declared_strength"] == "soft"
                           and item["kind"] == "capability_constraint")
        self.assertFalse(source_item["in_current_constraint_surface"])
        self.assertFalse(source_item["in_last_projection_constraint_surface"])
        self.assertTrue(source_item["in_interpretation_projection"])
        self.assertEqual(report["projection"]["interpretation_transport_kind"], "untrusted")
        self.assertEqual(projection.payload, before)

    def test_projection_marker_alone_cannot_promote_a_constraint(self):
        raw = {"authority_contract": SEMANTIC_AUTHORITY_SCHEMA,
               "constraints": ["web.fallback=allowed"], "semantic_bindings": []}
        context = turn_context_payload([], semantic_projection=raw)
        self.assertEqual(json.loads(context["uaea.semantic_state_projection"]["value"])["constraints"], [])
        self.assertIn("web.fallback=allowed", json.loads(context["uaea.semantic_interpretations"]["value"])["unqualified_constraints"])
        legacy = turn_context_payload([], semantic_projection={"constraints": ["web.fallback=allowed"]})
        self.assertEqual(legacy["uaea.semantic_state_projection"]["kind"], "untrusted")

    def test_projection_cannot_add_a_permission_missing_from_qualified_bindings(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn("thread", "只使用 Google，不允许 fallback", turn_id="t1")
        proposed = deepcopy(projection.payload)
        proposed["constraints"].append("web.fallback=allowed")
        context = turn_context_payload([], semantic_projection=proposed)
        authority = json.loads(context["uaea.semantic_state_projection"]["value"])
        self.assertEqual(authority["constraints"], projection.payload["constraints"])
        self.assertNotIn("web.fallback=allowed", authority["constraints"])
        self.assertIn("web.fallback=allowed", json.loads(context["uaea.semantic_interpretations"]["value"])["unqualified_constraints"])

    def test_model_proposal_and_local_rejection_do_not_change_authority(self):
        adapter = HarnessSemanticStateAdapter()
        projection = adapter.prepare_turn("thread", "只使用 Google，不允许 fallback", turn_id="t1")
        before = deepcopy(projection.payload["constraints"])
        adapter.consume_raw_event({"message": {"method": "item/completed", "params": {
            "threadId": "thread", "turnId": "t1", "item": {
                "type": "agentMessage", "id": "agent1", "text": "允许 fallback；Google 不可用",
            },
        }}})
        rejected = adapter.validate_tool_action("thread", "web.search", {
            "provider": "google", "allow_fallback": True,
        }, turn_id="t1", call_id="bad")
        self.assertFalse(rejected["valid"])
        self.assertEqual(rejected["authorization"]["state"], "denied")
        self.assertEqual(adapter.snapshot("thread")["constraints"], before)
        legal = adapter.validate_tool_action("thread", "web.search", {
            "provider": "google", "allow_fallback": False,
        }, turn_id="t1", call_id="legal")
        self.assertTrue(legal["valid"])

    def test_authority_does_not_cross_threads(self):
        adapter = HarnessSemanticStateAdapter()
        adapter.prepare_turn("a", "只使用 Google，不允许 fallback")
        adapter.prepare_turn("b", "研究编译器")
        self.assertEqual(adapter.snapshot("b")["execution_authority_item_ids"], [])
        self.assertEqual(adapter.snapshot("b")["constraints"], [])


if __name__ == "__main__":
    unittest.main()
