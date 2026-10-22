from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from runtime.context_manager import ContextManager  # noqa: E402
from runtime.runtime_objects import RuntimeObjectStore, WorkflowRunRecord  # noqa: E402
from runtime.semantic_observation import (  # noqa: E402
    ExecutionObservation,
    SemanticObservation,
)

from .event_normalizer import (  # noqa: E402
    AGENT_OUTPUT,
    CANCELLED,
    COMMAND_EXECUTION,
    ERROR,
    OBSERVATION,
    PRE_TURN_CONTEXT,
    TOOL_CALL,
    TOOL_RESULT,
    TURN_COMPLETED,
    TURN_STARTED,
    USER_INPUT,
    TrajectoryEvent,
    HarnessEventNormalizer,
)
from .scoped_semantics import EffectiveSemanticState, ScopedSemanticResolver  # noqa: E402
from .request_continuity import (  # noqa: E402
    REQUEST_OPERATIONS, request_inputs, request_snapshot, retain_request_input,
)
from .workflow_continuity import (  # noqa: E402
    execution_projection, record_attempt, record_outcome, turn_receipt, workflow_snapshot,
)
from .semantic_authority import (  # noqa: E402
    INTERPRETATION, SEMANTIC_AUTHORITY_SCHEMA, authority_level, compact_semantic_bindings,
    user_directive_basis,
)


SEMANTIC_STATE_SCHEMA = "uaea.harness_semantic_state.v0"
SEMANTIC_PROJECTION_SCHEMA = "uaea.semantic_projection.v0"
MAX_TEXT_CHARS = 240
MAX_LIST_ITEMS = 6
MAX_OBSERVATIONS = 6


class ProjectionCapacityError(ValueError):
    """No complete authority-preserving projection fits the configured budget."""

    def __init__(self, *, required_chars: int, budget_chars: int) -> None:
        super().__init__("Effective semantic state exceeds projection budget; constraints were not dropped")
        self.required_chars = required_chars
        self.budget_chars = budget_chars


@dataclass(frozen=True)
class SemanticProjection:
    """Bounded, typed context intended for one upcoming Harness turn."""

    semantic_scope_id: str
    thread_id: str
    payload: dict[str, Any]
    projection_id: str = ""

    def to_context_value(self) -> str:
        return _projection_json(self.payload)


@dataclass
class _SemanticState:
    semantic_scope_id: str
    thread_id: str
    context_manager: ContextManager = field(default_factory=ContextManager)
    runtime_objects: RuntimeObjectStore = field(default_factory=RuntimeObjectStore)
    topic: str = ""
    source_preferences: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    semantic_constraint_provenance: list[dict[str, Any]] = field(default_factory=list)
    task_evolution: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    turn_count: int = 0
    completed_turn_count: int = 0
    last_turn_id: str = ""
    last_relation: dict[str, str] = field(
        default_factory=lambda: {
            "relation": "new_task",
            "target_ref": "",
            "reason": "no prior semantic state",
        }
    )
    last_user_input: str = ""
    last_agent_output: str = ""
    last_tool_call: dict[str, Any] = field(default_factory=dict)
    last_execution_observation: ExecutionObservation | None = None
    semantic_observations: list[dict[str, Any]] = field(default_factory=list)
    projection_ids: list[str] = field(default_factory=list)
    last_projection: dict[str, Any] = field(default_factory=dict)
    last_terminal_state: str = ""
    last_error: str = ""
    pending_user_input: str = ""
    pending_relation: dict[str, str] | None = None
    pending_turn_id: str = ""
    input_turn_ids: set[str] = field(default_factory=set)
    action_decisions: list[dict[str, Any]] = field(default_factory=list)
    current_input_id: str = ""
    current_task_id: str = ""
    prepared_input_applied: bool = False
    ownership_binding: dict[str, str] = field(default_factory=dict)
    turn_receipts: list[dict[str, Any]] = field(default_factory=list)
    request_operation: str = "retain"


class HarnessSemanticStateAdapter:
    """Thin Harness-to-UAEA semantic state probe.

    This adapter consumes normalized Harness events and maintains only bounded
    semantic organization. It does not execute tools, run a planner, infer an
    ActiveGoal, or call a second model.
    """

    def __init__(
        self,
        *,
        normalizer: HarnessEventNormalizer | None = None,
        scope_resolver: Callable[[str], str] | None = None,
        max_projection_chars: int = 2400,
    ) -> None:
        self.normalizer = normalizer or HarnessEventNormalizer(
            source="codex_app_server.semantic_state_adapter"
        )
        self.scope_resolver = scope_resolver or (
            lambda thread_id: f"thread:{thread_id or 'unknown-thread'}"
        )
        self.max_projection_chars = max(600, int(max_projection_chars))
        self._states: dict[str, _SemanticState] = {}

    def prepare_turn(
        self,
        thread_id: str,
        user_input: str,
        *,
        turn_id: str = "",
        request_operation: str = "retain",
    ) -> SemanticProjection:
        if request_operation not in REQUEST_OPERATIONS:
            raise ValueError("Unsupported request operation")
        state = self._state_for(thread_id)
        state.request_operation = request_operation
        text = _compact_text(user_input, 500)
        relation = self._classify_relation(state, text)
        state.pending_user_input = text
        state.pending_relation = relation
        state.pending_turn_id = str(turn_id)
        state.current_input_id = f"input:{uuid4()}"
        state.prepared_input_applied = False
        state.context_manager.set_turn_relation(
            relation["relation"],
            target_ref=relation["target_ref"],
            reason=relation["reason"],
        )

        self._apply_user_input(state, TrajectoryEvent(
            sequence=0, event_type=USER_INPUT, thread_id=state.thread_id,
            turn_id=str(turn_id), event_id=state.current_input_id,
            payload={"text": text},
            provenance={"source": "harness.semantic_state_adapter.pre_turn_input"},
        ))
        state.pending_user_input = text
        state.pending_relation = relation
        state.pending_turn_id = str(turn_id)
        state.prepared_input_applied = True
        payload = self._projection_payload(state, relation=relation)
        projection = self._bounded_projection(SemanticProjection(
            semantic_scope_id=state.semantic_scope_id, thread_id=state.thread_id,
            payload=payload,
        ))
        projection_record = state.runtime_objects.create_projection(
            projection_type="semantic_state",
            consumer="harness.turn.start",
            content=projection.to_context_value(),
            source_object_ids=self._projection_source_ids(state),
        )
        state.projection_ids.append(projection_record.projection_id)
        projection = SemanticProjection(
            semantic_scope_id=state.semantic_scope_id,
            thread_id=state.thread_id,
            payload=projection.payload,
            projection_id=projection_record.projection_id,
        )
        state.projection_ids = state.projection_ids[-MAX_LIST_ITEMS:]
        state.last_projection = dict(projection.payload)
        return projection

    def consume_raw_event(
        self,
        raw_event: Mapping[str, Any],
        *,
        raw_event_reference: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for event in self.normalizer.normalize(
            raw_event,
            raw_event_reference=raw_event_reference,
        ):
            result = self.consume_event(event)
            if result is not None:
                results.append(result)
        return results

    def consume_event(self, event: TrajectoryEvent) -> dict[str, Any] | None:
        if not event.thread_id:
            return None
        state = self._state_for(event.thread_id)
        if event.turn_id:
            state.last_turn_id = event.turn_id
        if event.event_type == TURN_STARTED:
            state.pending_turn_id = event.turn_id or state.pending_turn_id
            if state.prepared_input_applied:
                self._bind_native_input(state, event)
            return None
        if event.event_type == PRE_TURN_CONTEXT:
            return None
        if event.event_type == USER_INPUT:
            self._apply_user_input(state, event)
            return None
        if event.event_type == AGENT_OUTPUT:
            state.last_agent_output = _compact_text(
                _event_text(event.payload),
                600,
            )
            return None
        if event.event_type == TOOL_CALL:
            item = event.payload.get("item") or event.payload.get("raw_response_item") or event.payload
            arguments = item.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except ValueError:
                    arguments = {"unparsed_arguments": arguments}
            state.last_tool_call = {
                "tool": str(item.get("tool") or item.get("name") or ""),
                "arguments": _bounded_value(arguments, 500),
                "thread_id": event.thread_id,
                "turn_id": event.turn_id,
                "item_id": event.item_id,
                "event_id": event.event_id,
                "sequence": event.sequence,
            }
            self._record_attempt(state, event, item, arguments)
            return None
        if event.event_type in {TOOL_RESULT, OBSERVATION, COMMAND_EXECUTION}:
            if (
                event.event_type == COMMAND_EXECUTION
                and (not isinstance(event.payload.get("item"), Mapping)
                     or event.payload.get("method") == "item/started")
            ):
                if event.payload.get("method") == "item/started":
                    item = event.payload.get("item") or {}
                    self._record_attempt(state, event, item, {"command": item.get("command")})
                return None
            if self._has_observation_event(state, event):
                return None
            return self._record_observation(state, event)
        if event.event_type in {ERROR, CANCELLED}:
            state.last_error = _compact_text(
                _event_text(event.payload) or json.dumps(
                    event.payload,
                    ensure_ascii=False,
                    default=str,
                ),
                500,
            )
            retrying = bool((event.payload.get("params") or {}).get("willRetry"))
            if not isinstance(event.payload.get("item"), Mapping) and not retrying:
                ScopedSemanticResolver(state.runtime_objects).expire_turn(state.current_input_id)
            return None
        if event.event_type == TURN_COMPLETED:
            self._finalize_pending_input(state, event)
            state.completed_turn_count += 1
            state.last_terminal_state = _turn_terminal_state(event)
            if not any(receipt["turn_id"] == event.turn_id for receipt in state.turn_receipts):
                for step in state.runtime_objects.step_runs:
                    if (step.action.get("harness", {}).get("turn_id") == event.turn_id
                            and step.status == "proposed"):
                        step.status = ("cancelled" if state.last_terminal_state in
                                       {"cancelled", "canceled", "interrupted"} else "outcome_missing")
                state.turn_receipts.append(turn_receipt(
                    state.runtime_objects, state.current_task_id, event.turn_id, state.last_terminal_state,
                ))
            ScopedSemanticResolver(state.runtime_objects).expire_turn(state.current_input_id)
            return self.snapshot(event.thread_id)
        return None

    def validate_tool_action(
        self,
        thread_id: str,
        capability: str,
        arguments: Mapping[str, Any],
        *,
        turn_id: str = "",
        call_id: str = "",
    ) -> dict[str, Any]:
        """Validate a proposed action against the current Phase-1 semantic state."""

        state = self._state_for(thread_id)
        self._materialize_pending_input(state, turn_id=turn_id)
        effective = self._effective_state(state)
        normalized_capability = str(capability or "")
        proposed = {
            "capability": normalized_capability,
            "arguments": _bounded_value(dict(arguments), 900),
        }
        conflicts: list[str] = []
        required_provider = _constraint_value(effective.constraints, "web.provider")
        fallback_policy = _constraint_value(effective.constraints, "web.fallback")
        authorization = {
            "state": "granted" if fallback_policy == "allowed" else
                     "denied" if fallback_policy == "forbidden" else "unknown",
            "source_items": [deepcopy(item.to_dict()) for item in effective.execution_constraint_items
                             if item.metadata.get("key") == "web.fallback"],
            "model_proposal": arguments.get("allow_fallback"),
        }
        requested_provider = _normalize_provider(arguments.get("provider"))
        if normalized_capability == "web.search":
            if required_provider and requested_provider != required_provider:
                conflicts.append(
                    f"provider must be {required_provider}; proposed {requested_provider or 'unspecified'}"
                )
            if fallback_policy == "forbidden" and _normalize_bool(arguments.get("allow_fallback")) is not False:
                conflicts.append("fallback is forbidden for the current task")
            if _normalize_bool(arguments.get("allow_fallback")) is True and fallback_policy != "allowed":
                conflicts.append("fallback permission is not granted by user semantic policy; a model proposal is not authorization")
            excluded = [value.split("=", 1)[1] for value in effective.constraints
                        if value.startswith("web.exclude_provider=")]
            if requested_provider in excluded:
                conflicts.append(f"provider {requested_provider} is excluded by semantic state")
            if excluded and _normalize_bool(arguments.get("allow_fallback")) is not False:
                conflicts.append("fallback may select an excluded provider; use allow_fallback=false")

        decision = {
            "valid": not conflicts,
            "semantic_status": "accepted" if not conflicts else "constraint_conflict",
            "thread_id": state.thread_id,
            "turn_id": str(turn_id or state.last_turn_id),
            "call_id": str(call_id or ""),
            "capability": normalized_capability,
            "active_constraints": effective.constraints,
            "effective_state_id": effective.resolution_id,
            "semantic_items": [deepcopy(item.to_dict()) for item in effective.execution_constraint_items],
            "proposed_action": proposed,
            "authorization": authorization if normalized_capability == "web.search" else {},
            "conflicts": conflicts,
            "provenance": {
                "source": "phase1.context_manager.semantic_state",
                "semantic_scope_id": state.semantic_scope_id,
                "thread_id": state.thread_id,
                "turn_id": str(turn_id or state.last_turn_id),
                "call_id": str(call_id or ""),
            },
        }
        state.action_decisions.append(dict(decision))
        state.action_decisions = state.action_decisions[-MAX_OBSERVATIONS:]
        for step in state.runtime_objects.step_runs:
            if (step.workflow_id == state.current_task_id
                    and step.action.get("harness", {}).get("call_id") == call_id):
                step.action["validation"] = {"valid": decision["valid"],
                                            "effective_state_id": effective.resolution_id,
                                            "conflicts": list(conflicts)}
                if not decision["valid"] and "outcome" not in step.action:
                    step.status = "rejected"
        return decision

    def snapshot(self, thread_id: str) -> dict[str, Any]:
        state = self._state_for(thread_id)
        effective = self._effective_state(state)
        return {
            "schema": SEMANTIC_STATE_SCHEMA,
            "authority_contract": SEMANTIC_AUTHORITY_SCHEMA,
            "semantic_scope_id": state.semantic_scope_id,
            "thread_id": state.thread_id,
            "turn_count": state.turn_count,
            "completed_turn_count": state.completed_turn_count,
            "last_turn_id": state.last_turn_id,
            "topic": state.topic,
            "source_preferences": list(state.source_preferences),
            "constraints": list(state.constraints),
            "task_id": state.current_task_id,
            "ownership_binding": dict(state.ownership_binding),
            "current_input_id": state.current_input_id,
            "effective_state_id": effective.resolution_id,
            "semantic_items": [deepcopy(item.to_dict()) for item in ScopedSemanticResolver(state.runtime_objects).items()],
            "effective_semantic_item_ids": [item.object_id for item in effective.items],
            "execution_authority_item_ids": [item.object_id for item in effective.execution_constraint_items],
            "semantic_constraint_provenance": list(state.semantic_constraint_provenance),
            "task_evolution": list(state.task_evolution),
            "turn_relation": dict(state.last_relation),
            "references": list(state.references),
            "open_questions": list(state.open_questions),
            "last_user_input": state.last_user_input,
            "last_agent_output": state.last_agent_output,
            "last_tool_call": dict(state.last_tool_call),
            "last_execution_observation": (
                state.last_execution_observation.to_event_metadata()
                if state.last_execution_observation is not None
                else None
            ),
            "semantic_observations": list(state.semantic_observations),
            "last_terminal_state": state.last_terminal_state,
            "last_error": state.last_error,
            "action_decisions": list(state.action_decisions),
            "projection_ids": list(state.projection_ids),
            "last_projection": dict(state.last_projection),
            "workflow_continuity": workflow_snapshot(
                state.runtime_objects, state.current_task_id, state.turn_receipts,
            ),
            "phase1_projection_count": len(state.runtime_objects.projections),
            "phase1_runtime_snapshot": state.runtime_objects.snapshot(),
            "phase1_context": {
                "turn_relation": (
                    {
                        "relation": state.context_manager.turn_relation.relation,
                        "target_ref": state.context_manager.turn_relation.target_ref,
                        "reason": state.context_manager.turn_relation.reason,
                    }
                    if state.context_manager.turn_relation is not None
                    else None
                ),
                "semantic_context": (
                    state.context_manager.semantic_context.summary
                    if state.context_manager.semantic_context is not None
                    else ""
                ),
                "execution_context": (
                    {
                        "capability": state.context_manager.execution_context.capability,
                        "status": state.context_manager.execution_context.status,
                        "observation_id": state.context_manager.execution_context.observation_id,
                    }
                    if state.context_manager.execution_context is not None
                    else None
                ),
            },
        }

    def state_for(self, thread_id: str) -> dict[str, Any]:
        return self.snapshot(thread_id)

    def snapshots(self) -> dict[str, dict[str, Any]]:
        return {
            state.thread_id: self.snapshot(state.thread_id)
            for state in self._states.values()
        }

    def _state_for(self, thread_id: str) -> _SemanticState:
        normalized_thread_id = str(thread_id or "unknown-thread")
        state = self._states.get(normalized_thread_id)
        if state is None:
            state = _SemanticState(
                semantic_scope_id=self.scope_resolver(normalized_thread_id),
                thread_id=normalized_thread_id,
            )
            self._states[normalized_thread_id] = state
        return state

    def _apply_user_input(self, state: _SemanticState, event: TrajectoryEvent) -> None:
        text = _compact_text(_event_text(event.payload), 500)
        if not text:
            return
        if state.prepared_input_applied and text == state.pending_user_input:
            self._bind_native_input(state, event)
            return
        if event.turn_id in state.input_turn_ids:
            return
        relation = state.pending_relation or self._classify_relation(state, text)
        if not state.current_input_id or not state.pending_user_input:
            state.current_input_id = event.event_id or f"input:{uuid4()}"
        self._bind_task_owner(state, text, relation)
        state.last_relation = relation
        state.context_manager.set_turn_relation(
            relation["relation"],
            target_ref=relation["target_ref"],
            reason=relation["reason"],
        )
        state.last_user_input = text
        state.turn_count += 1
        state.input_turn_ids.add(event.turn_id or f"sequence:{event.sequence}")
        state.pending_user_input = ""
        state.pending_relation = None
        state.pending_turn_id = ""

        resolver = ScopedSemanticResolver(state.runtime_objects)
        provenance = self._semantic_provenance(state, event, text)
        retain_request_input(state.runtime_objects, state.current_task_id,
                             input_id=state.current_input_id, text=text,
                             provenance=provenance, operation=state.request_operation)
        state.request_operation = "retain"
        scope = _semantic_scope(text)
        owner = self._semantic_owner(state, scope)
        if (not state.topic
                or state.ownership_binding["reason"] == "explicit_task_boundary"):
            resolver.bind(kind="topic", key="topic", value=_topic_from_input(text),
                          scope="task", owner=state.current_task_id, provenance=provenance,
                          strength="soft")
        for value in _source_constraints(text):
            resolver.bind(kind="capability_constraint", key=value, value=value,
                          scope=scope, owner=owner, provenance=provenance, strength="soft")
        self._apply_semantic_constraints(state, event, text)
        reference = _reference_from_input(text)
        if reference:
            resolver.bind(kind="reference", key=f"reference:{reference}", value=reference,
                          scope="task", owner=state.current_task_id, provenance=provenance)
        question = _question_from_input(text)
        if question:
            resolver.bind(kind="open_question", key=f"question:{question}", value=question,
                          scope="task", owner=state.current_task_id, provenance=provenance,
                          strength="soft")
        evolution = _compact_text(text, 180)
        if not state.task_evolution or state.task_evolution[-1] != evolution:
            state.task_evolution.append(evolution)
        _trim_list(state.task_evolution)
        self._effective_state(state)

    def _bind_task_owner(
        self, state: _SemanticState, text: str, relation: Mapping[str, str],
    ) -> None:
        # Relation is a hint; an explicit task boundary authorizes owner change.
        switch = _explicit_task_boundary(text)
        if not state.current_task_id or switch:
            previous = state.runtime_objects.active_workflow()
            if previous is not None:
                previous.status = "inactive"
            task = WorkflowRunRecord(task_summary=_topic_from_input(text), status="active",
                                     source_user_intent=text)
            state.runtime_objects.workflow_runs.append(task)
            state.runtime_objects.active_workflow_id = task.workflow_id
            state.current_task_id = task.workflow_id
            reason = "explicit_task_boundary" if switch else "initial_task"
        else:
            reason = "same_task_relation" if relation["relation"] != "new_task" else "no_explicit_owner_change"
        state.ownership_binding = {"task_id": state.current_task_id, "reason": reason,
                                   "relation_signal": str(relation["relation"])}

    @staticmethod
    def _semantic_owner(state: _SemanticState, scope: str) -> str:
        if scope == "turn":
            return state.current_input_id
        if scope == "task":
            return state.current_task_id
        return state.semantic_scope_id

    @staticmethod
    def _semantic_provenance(
        state: _SemanticState, event: TrajectoryEvent, text: str,
    ) -> dict[str, Any]:
        return {"source": "phase1.semantic_observation.boundary",
                "source_text_excerpt": _compact_text(text, 240),
                "thread_id": event.thread_id, "turn_id": event.turn_id,
                "item_id": event.item_id, "event_id": event.event_id,
                "sequence": event.sequence, "input_id": state.current_input_id,
                "source_event_type": event.event_type,
                "raw_event_reference": dict(event.raw_event_reference),
                "native_provenance": dict(event.provenance)}

    @staticmethod
    def _effective_state(state: _SemanticState) -> EffectiveSemanticState:
        effective = ScopedSemanticResolver(state.runtime_objects).resolve(
            task_id=state.current_task_id, input_id=state.current_input_id,
        )
        state.constraints = effective.constraints
        state.source_preferences = [str(item.metadata["value"]) for item in effective.interpretation_items
                                    if str(item.metadata["value"]).startswith(("prefer:", "exclude:"))]
        state.references = effective.values("reference")
        state.open_questions = effective.values("open_question")
        topics = effective.values("topic")
        state.topic = topics[-1] if topics else ""
        state.semantic_constraint_provenance = [
            {"constraint": item.metadata["value"], "owner": item.owner,
             "scope": item.metadata["scope"], "strength": item.metadata["strength"],
             **item.metadata["provenance"]}
            for item in effective.execution_constraint_items
        ]
        summary = ""
        if state.semantic_observations:
            summary = state.semantic_observations[-1]["execution_observation"]["message"]
        state.context_manager.set_semantic_context(
            "boundaries: " + "; ".join(effective.constraints) + (f"\nobservation: {summary}" if summary else "")
        )
        return effective

    @staticmethod
    def _bind_native_input(state: _SemanticState, event: TrajectoryEvent) -> None:
        if event.turn_id:
            state.pending_turn_id = event.turn_id
            state.input_turn_ids.add(event.turn_id)
        for item in (ScopedSemanticResolver(state.runtime_objects).items()
                     + request_inputs(state.runtime_objects, state.current_task_id)):
            provenance = item.metadata["provenance"]
            if provenance.get("input_id") != state.current_input_id:
                continue
            if event.turn_id:
                provenance["turn_id"] = event.turn_id
            if event.event_type == USER_INPUT:
                provenance.update({"item_id": event.item_id, "event_id": event.event_id,
                                   "sequence": event.sequence,
                                   "raw_event_reference": dict(event.raw_event_reference),
                                   "native_provenance": dict(event.provenance)})
            if event.event_id and event.event_id not in item.source_event_ids:
                item.source_event_ids.append(event.event_id)

    def _finalize_pending_input(
        self,
        state: _SemanticState,
        event: TrajectoryEvent,
    ) -> None:
        if state.prepared_input_applied:
            self._bind_native_input(state, event)
            return
        if not state.pending_user_input:
            return
        if state.pending_turn_id and event.turn_id and state.pending_turn_id != event.turn_id:
            return
        synthetic = TrajectoryEvent(
            sequence=event.sequence,
            event_type=USER_INPUT,
            thread_id=event.thread_id,
            turn_id=event.turn_id or state.pending_turn_id,
            item_id="pending-user-input",
            event_id=f"{event.event_id}:pending-user-input",
            payload={"text": state.pending_user_input},
            provenance={"source": "harness.semantic_state_adapter.pending_input"},
            raw_event_reference={},
            raw_event={},
        )
        self._apply_user_input(state, synthetic)

    def _materialize_pending_input(self, state: _SemanticState, *, turn_id: str = "") -> None:
        if state.prepared_input_applied:
            self._bind_native_input(state, TrajectoryEvent(
                sequence=0, event_type=TURN_STARTED, thread_id=state.thread_id,
                turn_id=turn_id,
            ))
            return
        if not state.pending_user_input:
            return
        if state.pending_turn_id and turn_id and state.pending_turn_id != turn_id:
            return
        synthetic = TrajectoryEvent(
            sequence=0,
            event_type=USER_INPUT,
            thread_id=state.thread_id,
            turn_id=turn_id or state.pending_turn_id,
            item_id="pending-user-input-before-action",
            event_id=f"pending-user-input:{turn_id or state.pending_turn_id}",
            payload={"text": state.pending_user_input},
            provenance={"source": "harness.semantic_state_adapter.pending_before_action"},
            raw_event_reference={},
            raw_event={},
        )
        self._apply_user_input(state, synthetic)

    def _apply_semantic_constraints(
        self,
        state: _SemanticState,
        event: TrajectoryEvent,
        text: str,
    ) -> None:
        scope = _semantic_scope(text)
        resolver = ScopedSemanticResolver(state.runtime_objects)
        if _contains_any(text.lower(), ("取消搜索限制", "取消长期搜索限制", "revoke search constraints")):
            resolver.revoke_constraints(owner=self._semantic_owner(state, scope),
                                        provenance=self._semantic_provenance(state, event, text))
        for key, value in _capability_constraints(text):
            provenance = self._semantic_provenance(state, event, text)
            resolver.bind(kind="capability_constraint", key=key, value=value,
                          scope=scope, owner=self._semantic_owner(state, scope),
                          provenance=provenance,
                          promotion_basis=user_directive_basis(provenance, key=key, value=value))

    def _record_observation(
        self,
        state: _SemanticState,
        event: TrajectoryEvent,
    ) -> dict[str, Any]:
        item = event.payload.get("item") or event.payload.get("raw_response_item")
        item_map = dict(item) if isinstance(item, Mapping) else dict(event.payload)
        result = _tool_result_payload(item_map)
        tool_name = str(
            result.get("tool")
            or item_map.get("tool")
            or item_map.get("command")
            or state.last_tool_call.get("tool")
            or "harness.execution"
        )
        status_value = str(item_map.get("status") or "")
        ok = result.get("ok", item_map.get("success"))
        execution_data = result.get("data") if isinstance(result.get("data"), Mapping) else {}
        if isinstance(execution_data.get("execution_succeeded"), bool):
            ok = execution_data["execution_succeeded"]
        if isinstance(ok, bool):
            status = "success" if ok else "failure"
        elif isinstance(item_map.get("exitCode"), int):
            status = "success" if item_map["exitCode"] == 0 else "failure"
        else:
            status = "success" if status_value in {"completed", "success"} else "failure"
        message = str(result.get("message") or "") or _event_text(item_map) or status_value or "Harness execution observation"
        observation = ExecutionObservation(
            observation_id=f"harness-event:{event.event_id}",
            capability=str(result.get("capability") or tool_name),
            tool_name=tool_name,
            status=status,
            message=_compact_text(message, 500),
            data={"item": _bounded_value({key: value for key, value in item_map.items()
                                         if key not in {"contentItems", "output"}}, 1400),
                  "result": result} if result else _bounded_value(item_map, 1400),
        )
        state.last_execution_observation = observation
        state.context_manager.set_execution_context(
            observation.capability,
            observation.status,
            observation.message,
            observation.observation_id,
        )
        semantic = SemanticObservation.from_sections(
            {
                "task": state.topic or state.last_user_input or "Harness execution",
                "facts": observation.message,
                "key_points": f"{observation.tool_name}: {observation.status}",
                "boundaries": "\n".join(state.constraints),
                "open_questions": "\n".join(state.open_questions[-2:]),
                "confidence": "low",
            },
            fallback_task=state.topic or "Harness execution",
            source_observation_id=observation.observation_id,
            raw_text=observation.message,
        )
        state.context_manager.set_semantic_context(semantic.compact_summary())
        record = {
            "execution_observation": observation.to_event_metadata(),
            "semantic_observation": semantic.to_dict(),
            "provenance": {
                "semantic_scope_id": state.semantic_scope_id,
                "task_id": state.current_task_id,
                "thread_id": event.thread_id,
                "turn_id": event.turn_id,
                "item_id": event.item_id,
                "event_id": event.event_id,
                "sequence": event.sequence,
                "event_type": event.event_type,
                "source": event.provenance.get("source"),
                "raw_event_reference": dict(event.raw_event_reference),
            },
        }
        step = self._record_attempt(state, event, item_map, item_map.get("arguments", {}), result)
        if step is not None:
            record["provenance"]["call_id"] = step.action["harness"]["call_id"]
            record_outcome(step, record["execution_observation"], result)
        state.semantic_observations.append(record)
        state.semantic_observations = state.semantic_observations[-MAX_OBSERVATIONS:]
        return record

    def _has_observation_event(self, state: _SemanticState, event: TrajectoryEvent) -> bool:
        item = event.payload.get("item") or event.payload.get("raw_response_item") or event.payload
        call_id = _call_identity(event, item, _tool_result_payload(item))
        existing = next((record for record in state.semantic_observations if
            (
                record.get("provenance", {}).get("event_id") == event.event_id
                or (call_id and record.get("provenance", {}).get("call_id") == call_id
                    and record["provenance"].get("thread_id") == event.thread_id
                    and record["provenance"].get("turn_id") == event.turn_id)
                or (
                    record.get("provenance", {}).get("thread_id") == event.thread_id
                    and record.get("provenance", {}).get("turn_id") == event.turn_id
                    and record.get("provenance", {}).get("item_id") == event.item_id
                )
            )
        ), None)
        if existing is not None:
            self._record_attempt(state, event, item, item.get("arguments", {}), _tool_result_payload(item))
        return existing is not None

    @staticmethod
    def _record_attempt(state, event, item, arguments, result=None):
        return record_attempt(
            state.runtime_objects, state.current_task_id,
            call_id=_call_identity(event, item, result or {}), turn_id=event.turn_id,
            tool=str(item.get("tool") or item.get("name") or item.get("command") or "harness.execution"),
            arguments=arguments,
            user_request=state.last_user_input, input_id=state.current_input_id,
            provenance={"thread_id": event.thread_id, "turn_id": event.turn_id,
                        "item_id": event.item_id, "event_id": event.event_id,
                        "sequence": event.sequence, "event_type": event.event_type,
                        "raw_event_reference": dict(event.raw_event_reference)},
        )

    def _projection_payload(
        self,
        state: _SemanticState,
        *,
        relation: Mapping[str, str],
    ) -> dict[str, Any]:
        effective = self._effective_state(state)
        observations = [
            {
                "observation_id": item["execution_observation"]["observation_id"],
                "capability": item["execution_observation"]["capability"],
                "status": item["execution_observation"]["status"],
                "message": _compact_text(
                    item["execution_observation"]["message"],
                    180,
                ),
            }
            for item in [record for record in state.semantic_observations
                         if record["provenance"].get("task_id") == state.current_task_id][-3:]
        ]
        payload = {
            "schema": SEMANTIC_PROJECTION_SCHEMA,
            "authority_contract": SEMANTIC_AUTHORITY_SCHEMA,
            "semantic_scope_id": state.semantic_scope_id,
            "topic": state.topic,
            "source_preferences": list(state.source_preferences[-MAX_LIST_ITEMS:]),
            "constraints": effective.constraints,
            "task_id": state.current_task_id,
            "effective_state_id": effective.resolution_id,
            "semantic_bindings": [
                {"item_id": item.object_id, "kind": item.metadata["kind"],
                 "key": item.metadata["key"], "value": item.metadata["value"],
                 "owner": item.owner, "scope": item.metadata["scope"],
                 "strength": item.metadata["strength"], "authority_level": authority_level(item.metadata),
                 "promotion_basis": deepcopy(item.metadata["promotion_basis"]),
                 "provenance": {key: item.metadata["provenance"][key]
                                for key in ("input_id", "source_event_type")}}
                for item in effective.execution_constraint_items
            ],
            "interpretations": [
                {"item_id": item.object_id, "value": item.metadata["value"],
                 "authority_level": INTERPRETATION}
                for item in effective.interpretation_items
            ],
            "task_evolution": list(state.task_evolution[-3:]),
            "turn_relation": dict(relation),
            "references": list(state.references[-MAX_LIST_ITEMS:]),
            "open_questions": list(state.open_questions[-MAX_LIST_ITEMS:]),
            "relevant_observations": observations,
            "workflow_continuation": {
                "initial_request": _compact_text(state.runtime_objects.active_workflow().source_user_intent, 140),
                "request_history": [text for text in state.task_evolution[-2:-1]
                                    if text != _compact_text(state.runtime_objects.active_workflow().source_user_intent, 180)],
                "assistant_proposal": _compact_text(state.last_agent_output, 200),
                "assistant_output_is_execution_evidence": False,
            },
            "workflow_execution": execution_projection(workflow_snapshot(
                state.runtime_objects, state.current_task_id, state.turn_receipts,
            )),
        }
        workflow = workflow_snapshot(state.runtime_objects, state.current_task_id, state.turn_receipts)
        action_request = workflow["last_action_request"].get("user_request")
        if (action_request and action_request != workflow["initial_request"]
                and _compact_text(action_request, 180) not in payload["workflow_continuation"]["request_history"]):
            payload["workflow_continuation"]["last_action_request"] = _compact_text(action_request, 100)
        origin = workflow["action_request_origin"].get("user_request")
        if origin and origin != action_request:
            # Keep history as history: an earlier action-bearing request is not an active Goal.
            history = payload["workflow_continuation"]["request_history"]
            payload["workflow_continuation"]["request_history"] = list(dict.fromkeys(
                [_compact_text(origin, 180), *history]))
        requests = workflow["request_continuity"]
        if requests["inputs"]:
            retained = [item for item in requests["inputs"] if item["status"] == "retained"]
            continuation = payload["workflow_continuation"]
            active_ids = set(requests["retained_input_ids"])
            if workflow["last_action_request"].get("input_id") not in active_ids:
                continuation.pop("last_action_request", None)
            continuation["initial_request"] = _compact_text(retained[0]["metadata"]["text"], 140) if retained else ""
            previous = [item for item in retained[1:] if item["object_id"] != state.current_input_id]
            history = [previous[0], previous[-1]] if previous else []
            # These are ordered user contributions, not independently inferred active tasks.
            continuation["request_history"] = list(dict.fromkeys(
                _compact_text(item["metadata"]["text"], 180) for item in history
                if item["metadata"]["text"] != action_request
                or "last_action_request" not in continuation))
            if requests["state"] == "cancelled":
                payload["workflow_continuation"] = {"request_state": "cancelled", "initial_request": "",
                                                     "request_history": []}
                for key in ("topic", "task_evolution", "references", "open_questions", "interpretations"):
                    payload[key] = "" if key == "topic" else []
            elif retained and retained[0]["metadata"]["operation"] in {"replace", "append"}:
                payload["topic"] = continuation["initial_request"]
                payload["task_evolution"] = [_compact_text(item["metadata"]["text"], 180) for item in retained[-3:]]
                continuation.pop("assistant_proposal", None)
        return payload

    def _bounded_projection(self, projection: SemanticProjection) -> SemanticProjection:
        payload = projection.payload
        if _projection_size(payload) <= self.max_projection_chars:
            return projection
        bounded = deepcopy(payload)
        bindings, shared = compact_semantic_bindings(payload.get("semantic_bindings", []))
        if shared:
            bounded["semantic_bindings"] = bindings
            bounded["semantic_binding_defaults"] = shared
        if _projection_size(bounded) <= self.max_projection_chars:
            return SemanticProjection(
                semantic_scope_id=projection.semantic_scope_id,
                thread_id=projection.thread_id,
                payload=bounded,
                projection_id=projection.projection_id,
            )
        bounded["task_evolution"] = list(payload.get("task_evolution", []))[-1:]
        bounded["references"] = list(payload.get("references", []))[-2:]
        bounded["open_questions"] = list(payload.get("open_questions", []))[-2:]
        bounded["relevant_observations"] = list(payload.get("relevant_observations", []))[-1:]
        bounded["interpretations"] = list(payload.get("interpretations", []))[-2:]
        if _projection_size(bounded) > self.max_projection_chars:
            bounded["relevant_observations"] = []
        if _projection_size(bounded) > self.max_projection_chars:
            bounded["task_evolution"] = []
            bounded["references"] = []
            bounded["open_questions"] = []
            bounded["source_preferences"] = []
            bounded["interpretations"] = []
            bounded["topic"] = _compact_text(bounded["topic"], 80)
        if _projection_size(bounded) > self.max_projection_chars:
            bounded["compact_wire"] = True
            for key in ("task_evolution", "references", "open_questions", "source_preferences",
                        "interpretations", "relevant_observations", "topic"):
                if not bounded.get(key):
                    bounded.pop(key, None)
        coverage = bounded["workflow_execution"].get("source_coverage")
        search = bounded["workflow_execution"].get("last_search_action")
        if search and _projection_size(bounded) > self.max_projection_chars:
            search["query"] = _compact_text(search["query"], 100)
        if coverage and _projection_size(bounded) > self.max_projection_chars:
            continuation = bounded["workflow_continuation"]
            continuation.pop("assistant_proposal", None)
            continuation.pop("assistant_output_is_execution_evidence", None)
            bounded["workflow_execution"].pop("candidate", None)
            while coverage["sources"] and _projection_size(bounded) > self.max_projection_chars:
                coverage["sources"].pop()
                coverage["omitted_sources"] += 1
        # Retain the minimal continuation and factual receipt before optional prose.
        for excerpt_size in (120, 100, 80):
            if _projection_size(bounded) <= self.max_projection_chars:
                break
            continuation = bounded["workflow_continuation"]
            continuation.pop("assistant_proposal", None)
            continuation.pop("assistant_output_is_execution_evidence", None)
            continuation["initial_request"] = _compact_text(continuation["initial_request"], excerpt_size)
            continuation["request_history"] = [_compact_text(text, excerpt_size)
                                               for text in continuation["request_history"]]
            if continuation.get("last_action_request"):
                continuation["last_action_request"] = _compact_text(continuation["last_action_request"], excerpt_size)
            bounded["workflow_execution"].pop("candidate", None)
            bounded.pop("topic", None)
            bounded["turn_relation"] = {"relation": payload["turn_relation"]["relation"]}
        if _projection_size(bounded) > self.max_projection_chars:
            # The envelope and binding owners retain scope identity; this header duplicates it.
            bounded.pop("semantic_scope_id", None)
        if coverage and _projection_size(bounded) > self.max_projection_chars:
            for key in ("failed", "pending"):
                if coverage.get(key) == 0:
                    coverage.pop(key, None)
            # Outcome status already states success/failure; retain all original facts in snapshot.
            attempt = bounded["workflow_execution"].get("last_attempt", {})
            if attempt.get("execution_status"):
                attempt.pop("state", None)
            if attempt.get("execution_succeeded") is True and attempt.get("http_attempted") is True:
                attempt.pop("http_attempted", None)
            receipt = bounded["workflow_execution"].get("previous_turn", {})
            if receipt.get("terminal") == "completed":
                receipt.pop("terminal", None)
            if _projection_size(bounded) > self.max_projection_chars:
                # This surface always counts distinct URLs; snapshot retains the explicit unit.
                coverage.pop("unit", None)
        required_chars = _projection_size(bounded)
        if required_chars > self.max_projection_chars and search:
            # Diagnostic action text is optional; effective constraints never are.
            bounded["workflow_execution"].pop("last_search_action", None)
            required_chars = _projection_size(bounded)
        if required_chars > self.max_projection_chars:
            raise ProjectionCapacityError(
                required_chars=required_chars, budget_chars=self.max_projection_chars,
            )
        return SemanticProjection(
            semantic_scope_id=projection.semantic_scope_id,
            thread_id=projection.thread_id,
            payload=bounded,
            projection_id=projection.projection_id,
        )

    def _projection_source_ids(self, state: _SemanticState) -> list[str]:
        return ([item.object_id for item in self._effective_state(state).items]
                + request_snapshot(state.runtime_objects, state.current_task_id)["retained_input_ids"]) + [
            f"semantic_observation:{item['execution_observation']['observation_id']}"
            for item in state.semantic_observations[-3:]
        ]

    @staticmethod
    def _classify_relation(state: _SemanticState, text: str) -> dict[str, str]:
        if not state.topic and not state.last_user_input:
            return {
                "relation": "new_task",
                "target_ref": "",
                "reason": "no prior semantic state",
            }
        if _contains_any(text, ("第一个方向", "第二个方向", "上述", "前面", "这个方向", "该方向")):
            target = _reference_from_input(text)
            return {
                "relation": "reference",
                "target_ref": target,
                "reason": "current request references an earlier task direction",
            }
        if _contains_any(text, ("质疑", "不对", "错误", "重新检查", "真的吗", "不是这样")):
            return {
                "relation": "challenge",
                "target_ref": "semantic_state:last",
                "reason": "current request challenges prior semantic state",
            }
        if _contains_any(
            text,
            (
                "继续",
                "展开",
                "进一步",
                "在此基础上",
                "内容是",
                "主题是",
                "搜索内容",
                "我指的是",
                "实际上我指的是",
                "哪些方向",
                "只关注",
                "重点关注",
                "不要商业",
            ),
        ):
            return {
                "relation": "continuation",
                "target_ref": "semantic_state:last",
                "reason": "current request continues the existing topic",
            }
        return {
            "relation": "new_task",
            "target_ref": "",
            "reason": "no prior-context relation marker detected",
        }


def semantic_projection_context(
    projection: SemanticProjection | Mapping[str, Any] | None,
) -> dict[str, dict[str, str]]:
    if projection is None:
        return {}
    payload = projection.payload if isinstance(projection, SemanticProjection) else dict(projection)
    return {
        "uaea.semantic_state_projection": {
            "kind": "application",
            "value": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        }
    }


def _projection_json(payload: Mapping[str, Any]) -> str:
    if payload.get("compact_wire"):
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _projection_size(payload: Mapping[str, Any]) -> int:
    from .io_contract import turn_context_payload

    context = turn_context_payload((), semantic_projection=payload)
    wire_chars = sum(len(context[key]["value"]) for key in
                     ("uaea.semantic_state_projection", "uaea.semantic_interpretations"))
    return max(len(_projection_json(payload)), wire_chars)


def _call_identity(event: TrajectoryEvent, item: Mapping[str, Any], result: Mapping[str, Any]) -> str:
    identity = result.get("identity") if isinstance(result.get("identity"), Mapping) else {}
    return str(identity.get("call_id") or item.get("call_id") or item.get("callId")
               or (event.item_id if item.get("type") in {"dynamicToolCall", "commandExecution"}
                   or event.event_type == TOOL_CALL else ""))


def _event_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        parts: list[str] = []
        for key in ("text", "message", "content", "delta", "aggregatedOutput"):
            item = value.get(key)
            if isinstance(item, str):
                parts.append(item)
        for key in ("item", "raw_response_item", "content", "contentItems", "input", "output"):
            item = value.get(key)
            if isinstance(item, (Mapping, list)):
                nested = _event_text(item)
                if nested:
                    parts.append(nested)
        return "\n".join(dict.fromkeys(part.strip() for part in parts if part.strip()))
    if isinstance(value, list):
        return "\n".join(
            part for item in value if (part := _event_text(item).strip())
        )
    return ""


def _tool_result_payload(item: Mapping[str, Any]) -> dict[str, Any]:
    values = [item.get("output")]
    values.extend(entry.get("text") for entry in item.get("contentItems") or [] if isinstance(entry, Mapping))
    for value in values:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                continue
        if isinstance(value, Mapping) and isinstance(value.get("ok"), bool):
            return deepcopy(dict(value))
    return {}


def _topic_from_input(text: str) -> str:
    value = re.sub(r"^[\s，。:：]+", "", text)
    value = re.sub(r"^(请|帮我|请你|我想|我们来)\s*", "", value)
    return _compact_text(value, 180)


def _source_constraints(text: str) -> list[str]:
    values: list[str] = []
    if "论文" in text or "学术" in text:
        values.append("prefer:academic_papers")
    if "论坛" in text:
        values.append("prefer:forums")
    if "商业" in text or "宣传" in text:
        values.append("exclude:commercial_promotional")
    if "不要博客" in text:
        values.append("exclude:blogs")
    return values


def _semantic_scope(text: str) -> str:
    lower = text.lower()
    if _contains_any(lower, ("以后", "从现在起", "长期", "直到撤销", "所有搜索", "always", "until revoked")):
        return "explicit_until_revoked"
    if _contains_any(lower, ("整个会话", "本会话", "跨任务", "this session", "across tasks")):
        return "cross_task"
    if _contains_any(lower, ("本轮", "这一轮", "这个回合", "this turn")):
        return "turn"
    return "task"


def _explicit_task_boundary(text: str) -> bool:
    return _contains_any(text.lower(), (
        "新任务", "新的任务", "新的普通主题", "切换话题", "换个话题", "另一个任务",
        "new task", "different task", "switch topic",
    ))


def _capability_constraints(text: str) -> list[tuple[str, str]]:
    """Small existing Web extraction surface, independent of ownership/lifecycle."""
    lower = text.lower()
    providers = r"(google|谷歌|bing|必应|duckduckgo|ddg)"
    aliases = {"谷歌": "google", "必应": "bing", "ddg": "duckduckgo"}
    values: list[tuple[str, str]] = []
    negative = list(re.finditer(r"(不要|禁止|不使用|do not use)\s*(使用|用)?\s*" + providers, lower))
    positive_text = lower
    for match in reversed(negative):
        positive_text = positive_text[:match.start()] + " " * (match.end() - match.start()) + positive_text[match.end():]
    positive = re.search(
        r"(?<!不要)(?<!不)(仅使用|只使用|必须使用|仅用|只用|只从|仅从|指定|改用|改为|only use)\s*" + providers,
        positive_text,
    ) or re.search(providers + r"\s*(only|站点|搜索引擎)", positive_text)
    if positive:
        provider = next(value for value in positive.groups() if value in {"google", "谷歌", "bing", "必应", "duckduckgo", "ddg"})
        provider = aliases.get(provider, provider)
        values.append(("web.provider", f"web.provider={provider}"))
        if _contains_any(positive.group(0), ("仅", "只", "必须", "指定", "only")):
            values.append(("web.fallback", "web.fallback=forbidden"))
    for match in negative:
        provider = aliases.get(match.group(3), match.group(3))
        values.append((f"web.exclude_provider:{provider}", f"web.exclude_provider={provider}"))
    fallback = list(re.finditer(
        r"(不允许|禁止|不要|允许)\s*(fallback|降级)|\b(no|without|do not|allow)\s+fallback\b", lower,
    ))
    if fallback:
        token = fallback[-1].group(1) or fallback[-1].group(3)
        policy = "allowed" if token in {"允许", "allow"} else "forbidden"
        values.append(("web.fallback", f"web.fallback={policy}"))
    return values


def _reference_from_input(text: str) -> str:
    if "第一个方向" in text:
        return "direction:first"
    if "第二个方向" in text:
        return "direction:second"
    if _contains_any(text, ("上述", "前面", "这个方向", "该方向")):
        return "semantic_state:last"
    return ""


def _question_from_input(text: str) -> str:
    if "？" in text or "?" in text or _contains_any(text, ("哪些", "什么", "如何", "为什么", "值得")):
        return _compact_text(text, 180)
    return ""


def _contains_any(text: str, values: tuple[str, ...]) -> bool:
    return any(value in text for value in values)


def _compact_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else text[:limit] + "\n... [truncated]"


def _bounded_value(value: Any, max_chars: int) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            result[str(key)] = _bounded_value(item, max_chars)
        return result
    if isinstance(value, list):
        return [_bounded_value(item, max_chars) for item in value[:MAX_LIST_ITEMS]]
    if isinstance(value, str):
        return _compact_text(value, max_chars)
    return value


def _trim_list(values: list[str]) -> None:
    del values[:-MAX_LIST_ITEMS]


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _constraint_value(values: list[str], prefix: str) -> str:
    marker = f"{prefix}="
    for value in reversed(values):
        text = str(value or "")
        if text.startswith(marker):
            return text[len(marker) :]
    return ""


def _normalize_provider(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "")


def _normalize_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _turn_terminal_state(event: TrajectoryEvent) -> str:
    turn = event.payload.get("turn")
    if isinstance(turn, Mapping):
        return str(turn.get("status") or event.event_type).lower()
    return event.event_type
