"""Opt-in Goal observation/adoption at the Host boundary; no planner or Agent Loop."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from runtime.context_manager import GoalHypothesisRecord
from runtime.runtime_objects import ActiveGoalRecord, RuntimeObjectRecord, utc_now
from .semantic_interpretation import request_record

SCHEMA = "uaea.goal_integration.v1"
RELATIONS = ("form", "continue", "revise", "switch", "resume")
PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "minLength": 1, "maxLength": 600},
        "relation": {"type": "string", "enum": list(RELATIONS)},
        "target_goal_id": {"type": ["string", "null"],
                           "description": "An existing adopted Goal ID, never a task/effective-state/input ID. Use null if none."},
        "quote": {"type": "string", "minLength": 1, "maxLength": 500},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "conflicts_with": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        "evidence_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 4,
                         "description": "ExecutionObservation.observation_id from actual Capability results only. "
                             "Input IDs, Goal IDs and model summaries are not Evidence. Use [] if no Observation."},
    },
    "required": ["summary", "relation", "target_goal_id", "quote", "confidence",
                 "conflicts_with", "evidence_ids"],
    "additionalProperties": False,
}
FINAL_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"},
                   "goal_hypothesis": {"anyOf": [PROPOSAL_SCHEMA, {"type": "null"}]}},
    "required": ["answer", "goal_hypothesis"], "additionalProperties": False,
}


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def decode_final(text):
    value = json.loads(text)
    if (not isinstance(value, dict) or set(value) != {"answer", "goal_hypothesis"}
            or not isinstance(value["answer"], str)):
        raise ValueError("Expected negotiated Goal final envelope")
    return value


class GoalIntegration:
    def __init__(self, semantic, journal_path, *, mode="off", input_actor="operator",
                 projection="optional"):
        if mode not in {"off", "shadow", "adopt"}:
            raise ValueError("Unknown Goal mode")
        if projection not in {"none", "optional"}:
            raise ValueError("Unknown Goal projection mode")
        self.projection = projection
        if input_actor not in {"operator", "test_driver"}:
            raise ValueError("Unknown Host input actor")
        self.semantic, self.mode, self.input_actor = semantic, mode, input_actor
        self.path = Path(journal_path)

    def _state(self, thread_id):
        state = self.semantic._state_for(thread_id)
        if not state.current_task_id:
            raise ValueError("Goal requires a registered task/request")
        return state

    def _event(self, thread_id, event, payload):
        # Persist before state mutation; journal failure cannot silently adopt.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = {"schema": SCHEMA, "event": event, "thread_id": thread_id,
               "mode": self.mode, "projection": self.projection, "payload": payload,
               "changes_tool_authorization": False, "completes_workflow": False,
               "writes_memory": False}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
        return row

    def _request(self, state, input_id):
        record = request_record(state.runtime_objects, state.current_task_id, input_id)
        if record.status != "retained":
            raise ValueError("Goal request is no longer retained")
        origin = record.metadata.get("host_input_origin", {})
        if (origin.get("channel") != "registered_user_entry"
                or origin.get("input_id") != input_id
                or origin.get("raw_text_sha256") != record.metadata["raw_text_sha256"]):
            raise ValueError("Goal source is not a registered Host user input")
        return record

    def candidates(self, state):
        return [x for x in state.runtime_objects.objects
                if x.object_type == "goal_hypothesis_candidate"
                and x.owner == state.current_task_id]

    def observe_final(self, thread_id, *, input_id, turn_id, model_event_id, text):
        if self.mode == "off":
            return None
        state = self._state(thread_id)
        request = self._request(state, input_id)
        if (input_id != state.current_input_id or not turn_id or not model_event_id
                or request.metadata["provenance"].get("turn_id") != turn_id):
            raise ValueError("Goal output does not belong to the registered current turn")
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if not isinstance(parsed, dict) or "goal_hypothesis" not in parsed:
            self._event(thread_id, "NO_GOAL_PROPOSAL", {
                "input_id": input_id, "turn_id": turn_id, "model_event_id": model_event_id,
                "reason": "optional_final_envelope_not_present"})
            return None
        value = decode_final(text)
        proposal = value["goal_hypothesis"]
        if proposal is None:
            self._event(thread_id, "NO_GOAL_PROPOSAL",
                        {"input_id": input_id, "turn_id": turn_id, "model_event_id": model_event_id})
            return None
        if (not isinstance(proposal, dict) or set(proposal) != set(PROPOSAL_SCHEMA["required"])
                or proposal["relation"] not in RELATIONS
                or proposal["confidence"] not in {"low", "medium", "high"}):
            raise ValueError("Invalid Goal proposal fields")
        for key, limit in [("summary", 600), ("quote", 500)]:
            if not isinstance(proposal[key], str) or not 0 < len(proposal[key]) <= limit:
                raise ValueError("Invalid Goal text")
        if proposal["quote"] not in request.metadata["text"]:
            raise ValueError("Goal quote is not from its registered original request")
        reference_validation = self._references(state, proposal)
        identity = "goal-candidate:" + sha256(
            f"{thread_id}:{turn_id}:{model_event_id}".encode()).hexdigest()[:24]
        existing = next((x for x in self.candidates(state) if x.object_id == identity), None)
        if existing:
            if existing.metadata["proposal"] != proposal:
                raise ValueError("Goal model identity reused with different content")
            return existing
        hypothesis = GoalHypothesisRecord(proposal["summary"], proposal["confidence"], "inferred")
        record = RuntimeObjectRecord(
            object_id=identity, object_type="goal_hypothesis_candidate",
            owner=state.current_task_id, status="candidate",
            source_object_ids=[input_id], source_event_ids=[model_event_id],
            metadata={"schema": SCHEMA, "hypothesis": asdict(hypothesis),
                      "proposal": deepcopy(proposal), "input_id": input_id, "turn_id": turn_id,
                      "request_sha256": request.metadata["raw_text_sha256"],
                      "source_kind": "model_final_proposal", "authority_level": "interpretation",
                      "semantic_correctness": "not_established", "quote_verified": True,
                      "reference_validation": reference_validation,
                      "base_goal_state_sha256": digest(self._goal_state(state))})
        self._event(thread_id, "GOAL_CANDIDATE", record.to_dict())
        state.runtime_objects.objects.append(record)
        self.checkpoint(thread_id)
        return record

    def _references(self, state, proposal):
        known_candidates = {x.object_id for x in self.candidates(state)}
        known_evidence = {x.execution_observation_id for x in state.runtime_objects.step_runs
                          if x.workflow_id == state.current_task_id and x.execution_observation_id}
        unresolved = {}
        for key, known in [("conflicts_with", known_candidates), ("evidence_ids", known_evidence)]:
            refs = proposal[key]
            if (not isinstance(refs, list) or len(refs) > 4
                    or any(not isinstance(ref, str) or not 0 < len(ref) <= 200 for ref in refs)):
                raise ValueError("Invalid Goal reference fields")
            unresolved[key] = [ref for ref in refs if ref not in known]
        target = proposal["target_goal_id"]
        if target is not None and (not isinstance(target, str) or not 0 < len(target) <= 200):
            raise ValueError("Invalid Goal target identity")
        unresolved["target_goal_id"] = ([] if target is None or target in {
            x.metadata.get("adopted_goal_id") for x in self.candidates(state)} else [target])
        return {"valid": not any(unresolved.values()), "unresolved": unresolved,
                "source_link_is_not_content_support": True}

    @staticmethod
    def _goal_state(state):
        return {"active_goal_id": state.runtime_objects.active_goal_id,
                "goals": [x.to_dict() for x in state.runtime_objects.active_goals]}

    def control(self, thread_id, command):
        """Called only by Host user entry, never from model/tool/event decoding."""
        parts = command.split()
        if parts == ["/goal", "status"]:
            return self.snapshot(thread_id)
        if (len(parts) != 3 or parts[0] != "/goal"
                or parts[1] not in {"adopt", "revise", "switch", "suspend", "resume", "reject"}):
            raise ValueError("Use /goal status or /goal adopt|revise|switch|suspend|resume|reject ID")
        if self.mode != "adopt":
            raise ValueError("Goal adoption is disabled; use explicit adopt mode")
        state = self._state(thread_id)
        store = state.runtime_objects
        operation, target_id = parts[1:]
        candidate = next((x for x in self.candidates(state) if x.object_id == target_id), None)
        goals = deepcopy(store.active_goals)
        active_id = store.active_goal_id
        owned = {x.metadata.get("adopted_goal_id") for x in store.objects
                 if x.object_type == "goal_hypothesis_candidate" and x.owner == state.current_task_id}
        active = next((x for x in goals if x.goal_id == active_id), None)
        if active is not None and active.goal_id not in owned:
            raise ValueError("Active Goal belongs to another owner/path")
        candidate_status = None
        if operation in {"adopt", "revise", "switch", "reject"}:
            if candidate is None or candidate.status != "candidate":
                raise ValueError("Goal candidate is unknown or no longer pending")
            request = self._request(state, candidate.metadata["input_id"])
            if candidate.metadata["request_sha256"] != request.metadata["raw_text_sha256"]:
                raise ValueError("Goal candidate original request mismatch")
            proposal = candidate.metadata["proposal"]
            if operation != "reject" and not self._references(state, proposal)["valid"]:
                raise ValueError("Candidate has unresolved references; cannot adopt")
            if (operation != "reject" and candidate.metadata["base_goal_state_sha256"]
                    != digest(self._goal_state(state))):
                raise ValueError("Goal proposal is stale; request a new proposal for the current state")
            if operation == "reject":
                candidate_status = "rejected"
            elif operation == "revise":
                if (active is None or proposal["relation"] != "revise"
                        or proposal["target_goal_id"] != active_id):
                    raise ValueError("Revision must explicitly target the current Goal")
                active.goal_summary = proposal["summary"]
                active.source_goal_hypothesis = proposal["summary"]
                candidate_status = "adopted"
            else:
                if operation == "adopt" and active is not None:
                    raise ValueError("Use explicit revise/switch for an existing ActiveGoal")
                if proposal["relation"] not in {"form", "switch"}:
                    raise ValueError("Initial adoption/switch needs a form/switch proposal")
                if active is not None:
                    active.status = "suspended"
                goal = ActiveGoalRecord(
                    goal_summary=proposal["summary"], source_goal_hypothesis=proposal["summary"],
                    source_user_intent=request.metadata["text"][:500])
                goals.append(goal)
                active_id = goal.goal_id
                active = goal
                candidate_status = "adopted"
        else:
            goal = next((x for x in goals if x.goal_id == target_id and x.goal_id in owned), None)
            if goal is None:
                raise ValueError("Goal is not owned by this task")
            if operation == "suspend":
                if target_id != active_id:
                    raise ValueError("Only the current Goal can be suspended")
                goal.status = "suspended"
                active_id = ""
            else:
                if goal.status != "suspended":
                    raise ValueError("Only a suspended Goal can be resumed")
                if active is not None:
                    active.status = "suspended"
                goal.status = "active"
                active_id = goal.goal_id
        prior = {x.goal_id: x.to_dict() for x in store.active_goals}
        for goal in goals:
            if goal.goal_id in prior and goal.to_dict() != prior[goal.goal_id]:
                goal.updated_at = utc_now()
        control_id = "goal-control:" + str(uuid4())
        decision_id = "goal-decision:" + str(uuid4())
        after = {"active_goal_id": active_id, "goals": [x.to_dict() for x in goals]}
        decision = RuntimeObjectRecord(
            object_id=decision_id, object_type="goal_adoption_decision", owner=state.current_task_id,
            status="recorded", source_object_ids=[control_id] + ([candidate.object_id] if candidate else []),
            metadata={"operation": operation, "target_id": target_id,
                      "basis": "explicit_host_user_control", "actor": self.input_actor,
                      "before_sha256": digest(self._goal_state(state)),
                      "after": after, "state_sha256": digest(after)})
        control = RuntimeObjectRecord(
            object_id=control_id, object_type="goal_control_input", owner=state.current_task_id,
            status="recorded", metadata={"text": command, "raw_text_sha256": sha256(command.encode()).hexdigest(),
                                         "channel": "registered_goal_control", "actor": self.input_actor})
        self._event(thread_id, "GOAL_CONTROL_INPUT", control.to_dict())
        self._event(thread_id, "GOAL_DECISION", decision.to_dict())
        store.objects.append(control)
        store.objects.append(decision)
        store.active_goals = goals
        store.active_goal_id = active_id
        if candidate_status:
            candidate.status = candidate_status
            if candidate_status == "adopted":
                candidate.metadata["adopted_goal_id"] = active_id
        self.restore_context(thread_id)
        self.checkpoint(thread_id)
        return decision.to_dict()

    def restore_context(self, thread_id):
        """Rebuild only the Goal view from Host records, never a model summary."""
        state = self._state(thread_id)
        goal = state.runtime_objects.active_goal()
        if goal is None:
            state.context_manager.active_goal_context = None
        else:
            state.context_manager.set_active_goal_context(
                goal.goal_id, goal.status, goal.goal_summary,
                workflow_count=len(goal.workflow_ids), artifact_count=len(goal.artifact_ids),
                source_goal_hypothesis=goal.source_goal_hypothesis)

    def snapshot(self, thread_id):
        state = self._state(thread_id)
        store = state.runtime_objects
        return {"schema": SCHEMA, "thread_id": thread_id, "workflow_id": state.current_task_id,
                "mode": self.mode, "projection": self.projection, "active_goal_id": store.active_goal_id,
                "goals": [x.to_dict() for x in store.active_goals],
                "candidates": [x.to_dict() for x in self.candidates(state)],
                "decisions": [x.to_dict() for x in store.objects if x.object_type == "goal_adoption_decision"],
                "controls": [x.to_dict() for x in store.objects if x.object_type == "goal_control_input"],
                "goal_completion_established": False, "tool_authorization_from_goal": False}

    def checkpoint(self, thread_id):
        value = self.snapshot(thread_id)
        target = self.path.with_name("goal-state.json")
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps({"snapshot": value, "sha256": digest(value)},
                                   ensure_ascii=False, indent=2))
        temp.replace(target)

    def recover_checkpoint(self, thread_id):
        """Goal-only recovery; original Host requests and decisions must already exist."""
        state = self._state(thread_id)
        saved = json.loads(self.path.with_name("goal-state.json").read_text())
        value = saved["snapshot"]
        if (saved["sha256"] != digest(value) or value["thread_id"] != thread_id
                or value["workflow_id"] != state.current_task_id or value["mode"] != self.mode):
            raise ValueError("Goal checkpoint identity/integrity mismatch")
        store = state.runtime_objects
        decisions = [x for x in store.objects if x.object_type == "goal_adoption_decision"]
        expected = decisions[-1].metadata["after"] if decisions else {"active_goal_id": "", "goals": []}
        after = {"active_goal_id": value["active_goal_id"], "goals": value["goals"]}
        if after != expected:
            raise ValueError("Checkpoint cannot override the authoritative Host decision ledger")
        for candidate in value["candidates"]:
            current = next((x for x in self.candidates(state) if x.object_id == candidate["object_id"]), None)
            if current is None or current.to_dict() != candidate:
                raise ValueError("Goal candidate ledger mismatch")
            self._request(state, current.metadata["input_id"])
        original_controls = [x.to_dict() for x in store.objects if x.object_type == "goal_control_input"]
        if value.get("controls") != original_controls:
            raise ValueError("Checkpoint has no matching original Host control ledger")
        for decision in decisions:
            control = next((x for x in store.objects if x.object_id == decision.source_object_ids[0]), None)
            if (control is None or control.object_type != "goal_control_input"
                    or control.metadata.get("channel") != "registered_goal_control"
                    or sha256(control.metadata["text"].encode()).hexdigest()
                        != control.metadata["raw_text_sha256"]):
                raise ValueError("Goal decision has no original Host control input")
        self._event(thread_id, "GOAL_CONTEXT_RECOVERED",
                    {"state_sha256": digest(after), "basis": "existing_host_decision_ledger"})
        store.active_goals = [ActiveGoalRecord(**x) for x in after["goals"]]
        store.active_goal_id = after["active_goal_id"]
        self.restore_context(thread_id)

    def context(self, thread_id):
        if self.mode == "off" or self.projection == "none":
            return {}
        state = self._state(thread_id)
        snap = self.snapshot(thread_id)
        active = state.runtime_objects.active_goal()
        owned = {x.metadata.get("adopted_goal_id") for x in self.candidates(state)}
        # A retained Goal from another task is not this task's adopted objective.
        other_task_goal = active is not None and active.goal_id not in owned
        if other_task_goal:
            active = None
        current_active_id = active.goal_id if active else ""
        candidates = self.candidates(state)[-3:]
        decisions = [x for x in state.runtime_objects.objects
                     if x.object_type == "goal_adoption_decision"]
        return {
            "uaea.goal_state": {"kind": "application", "value": json.dumps({
                "schema": SCHEMA, "mode": self.mode, "active_goal_id": current_active_id,
                "other_task_goal_retained": other_task_goal,
                "decision_id": decisions[-1].object_id if decisions else None,
                "state_sha256": digest(self._goal_state(state)),
                "status": active.status if active else "none",
                "goal_completion_established": False, "goal_is_not_authorization": True,
                "final_envelope_contract": FINAL_SCHEMA,
                "instruction": "Native tool calls/results keep their original protocol. Never replace a tool call "
                    "with this envelope or a claim of execution. Only when ready to answer, optionally use a complete "
                    "JSON final envelope: answer plus goal_hypothesis. Plain final text retains the answer but creates no "
                    "Goal candidate. No forced provider response_format/outputSchema is applied. "
                    "Propose intent, not hidden reasoning; quote the current original request exactly. "
                    "Use null for ordinary dialogue without a useful Goal proposal. "
                    "Model proposals and compaction summaries cannot adopt/revise/complete Goals. "
                    "Only separate explicit Host user control can adopt. Active Goal is a task objective, not source truth."},
                ensure_ascii=False)},
            "uaea.goal_hypotheses": {"kind": "untrusted", "value": json.dumps({
                "active_objective": active.goal_summary if active else None,
                "active_goal_id": current_active_id,
                "recent_candidates": [{"id": x.object_id, "status": x.status,
                    "summary": x.metadata["hypothesis"]["hypothesis"], "relation": x.metadata["proposal"]["relation"]}
                    for x in candidates],
                "semantic_correctness": "not_established", "source_evidence": False}, ensure_ascii=False)}
        }
