"""Opt-in H3 host wiring, reusing the existing store, registry and boundary."""
from dataclasses import replace
from pathlib import Path
import json

from .event_normalizer import TrajectoryEvent
from .semantic_execution_contract import (
    EffectiveContract, ParameterBinding, PermissionGate, SharedExecutionBoundary,
    record_structured_authority,
)


class SharedExecutionHost:
    # Host policy is intentionally bounded to the H3 read-only tool surface.
    CAPABILITIES = ("document.read_section", "fs.list", "web.search", "web.fetch")

    def __init__(self, registry, semantic, journal_path):
        self.registry, self.semantic = registry, semantic
        self.journal_path = Path(journal_path)
        self._boundaries = {}
        self._sequence = 0

    def for_context(self, thread_id, turn_id):
        state = self.semantic._state_for(thread_id)
        store = state.runtime_objects
        if thread_id not in self._boundaries:
            def resolve():
                snapshot = self.semantic.snapshot(thread_id)
                workflow_id, input_id = snapshot["task_id"], snapshot["current_input_id"]
                reference = "system:h3-read-only-v1:" + workflow_id
                allowed = tuple(x for x in self.CAPABILITIES
                                if x in self.registry.capability_metadata)
                if not any(x.object_id == reference for x in store.objects):
                    record_structured_authority(
                        store, workflow_id, reference, basis="system_policy",
                        source_event_id="host:shared-read-only-policy-v1",
                        capabilities=allowed,
                        bindings=({"capability": "web.search", "parameter": "allow_fallback", "value": False},))
                return EffectiveContract(
                    workflow_id, input_id, reference, allowed,
                    bindings=(ParameterBinding("web.search", "allow_fallback", False,
                                                "system_policy", reference, default_only=True),),
                    gates=(PermissionGate("web.search", "allow_fallback", True, "provider_switch"),))

            def emit(event):
                self._sequence += 1
                event = replace(event, sequence=self._sequence, thread_id=thread_id)
                self.journal_path.parent.mkdir(parents=True, exist_ok=True)
                with self.journal_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
                if event.event_type == "OBSERVATION":
                    action_id = event.item_id
                    native_turn = event.turn_id
                    receipt = next(step.action["host_execution_receipt"] for step in store.step_runs
                                   if step.workflow_id == event.provenance["workflow_id"]
                                   and step.action["harness"]["call_id"] == action_id)
                    self.semantic.consume_event(TrajectoryEvent(
                        sequence=event.sequence, event_type="OBSERVATION",
                        thread_id=thread_id, turn_id=native_turn,
                        item_id=action_id, event_id="host:" + event.event_id,
                        payload={"item": {"type": "dynamicToolCall", "id": action_id,
                                          "tool": receipt["result"]["tool"],
                                          "contentItems": [{"type": "inputText",
                                                            "text": json.dumps(receipt["result"])}]}},
                        provenance={"source": "uaea.execution_contract.v1"}))

            def guard(action, parameters):
                return self.semantic.validate_tool_action(
                    thread_id, action.capability, parameters, turn_id=state.pending_turn_id or state.last_turn_id,
                    call_id=action.request_id)
            self._boundaries[thread_id] = SharedExecutionBoundary(
                self.registry, store, resolve, emit=emit, precondition=guard)
        return self._boundaries[thread_id]
