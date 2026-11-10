"""Small opt-in UAEA execution boundary, independent of a host's wire protocol.

EffectiveContract is supplied by trusted application code, NEVER decoded from model
output. Model interpretations are candidates stored separately. No NLU or planner.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from threading import RLock
from typing import Any, Callable

from runtime.action_request import ActionRequest
from runtime.capability import ToolResult
from runtime.semantic_observation import ExecutionObservation
from runtime.runtime_objects import RuntimeObjectRecord
from .event_normalizer import TrajectoryEvent
from .semantic_interpretation import request_record
from .workflow_continuity import record_attempt, record_outcome
from .observation_boundary import CapabilityInputError, scoped_failure

SCHEMA = "uaea.execution_contract.v1"


@dataclass(frozen=True)
class ParameterBinding:
    capability: str
    parameter: str
    value: Any
    basis: str
    reference: str
    input_id: str = ""
    default_only: bool = False


@dataclass(frozen=True)
class PermissionGate:
    capability: str
    parameter: str
    value: Any
    permission: str


@dataclass(frozen=True)
class Authorization:
    permission: str
    state: str
    basis: str
    reference: str
    input_id: str = ""


@dataclass(frozen=True)
class RequiredParameter:
    capability: str
    parameter: str
    when_present: str = ""


@dataclass(frozen=True)
class EffectiveContract:
    workflow_id: str
    input_id: str
    policy_reference: str
    allowed_capabilities: tuple[str, ...]
    bindings: tuple[ParameterBinding, ...] = ()
    gates: tuple[PermissionGate, ...] = ()
    authorizations: tuple[Authorization, ...] = ()
    required: tuple[RequiredParameter, ...] = ()

    @property
    def state_id(self) -> str:
        return sha256(json.dumps(asdict(self), sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def validate(self) -> None:
        if not self.workflow_id or not self.input_id or not self.policy_reference:
            raise ValueError("A host-owned effective contract is required")
        for fact in (*self.bindings, *self.authorizations):
            if fact.basis not in {"system_policy", "user_confirmation"} or not fact.reference:
                raise ValueError("Model provenance is not execution authority")
        if any(x.state not in {"granted", "denied"} for x in self.authorizations):
            raise ValueError("Missing authorization remains unknown")
        identities = [(x.capability, x.parameter) for x in self.bindings
                      if not x.input_id or x.input_id == self.input_id]
        if len(identities) != len(set(identities)):
            raise ValueError("Effective bindings must be resolved before execution")
        permissions = [x.permission for x in self.authorizations
                       if not x.input_id or x.input_id == self.input_id]
        if len(permissions) != len(set(permissions)):
            raise ValueError("Effective authorizations must be resolved before execution")



def record_structured_authority(store, workflow_id: str, reference: str, *, basis: str,
                                source_event_id: str, input_id="", capabilities=(),
                                bindings=(), authorizations=()):
    """Trusted host ingress only, never exposed as a model tool or NLU promotion.

    The host must authenticate the policy/structured confirmation before calling.
    Merely pointing at an original natural-language request is NOT confirmation.
    """
    if basis not in {"system_policy", "user_confirmation"} or not source_event_id:
        raise ValueError("An authenticated host policy/confirmation event is required")
    if not reference or any(x.object_id == reference for x in store.objects):
        raise ValueError("Authority identity must be new and independent of candidates")
    record = RuntimeObjectRecord(
        object_type="execution_authority", object_id=reference,
        owner=workflow_id, status="active", source_event_ids=[source_event_id],
        metadata={"basis": basis, "input_id": input_id,
                  "capabilities": list(capabilities), "bindings": deepcopy(list(bindings)),
                  "authorizations": deepcopy(list(authorizations))},
    )
    store.objects.append(record)
    return record


def _validate_sources(store, contract):
    def source(reference, basis):
        record = next((x for x in store.objects if x.object_id == reference), None)
        if (record is None or record.object_type != "execution_authority"
                or record.owner != contract.workflow_id or record.status != "active"
                or not record.source_event_ids or record.metadata["basis"] != basis
                or record.metadata["input_id"] not in {"", contract.input_id}):
            raise ValueError("Authority source is unknown, inactive, or outside its scope")
        return record.metadata
    root = source(contract.policy_reference, "system_policy")
    if not set(contract.allowed_capabilities) <= set(root["capabilities"]):
        raise ValueError("Capability permission exceeds the recorded host policy")
    for binding in contract.bindings:
        if binding.input_id not in {"", contract.input_id}:
            continue
        evidence = source(binding.reference, binding.basis)
        if not any(x["capability"] == binding.capability and x["parameter"] == binding.parameter
                   and _same(x["value"], binding.value) for x in evidence["bindings"]):
            raise ValueError("Binding is not supported by its structured authority source")
    for grant in contract.authorizations:
        if grant.input_id not in {"", contract.input_id}:
            continue
        evidence = source(grant.reference, grant.basis)
        if not any(x["permission"] == grant.permission and x["state"] == grant.state
                   for x in evidence["authorizations"]):
            raise ValueError("Authorization is not supported by its structured source")

def _same(left, right):
    return type(left) is type(right) and left == right


def decide(action: ActionRequest, contract: EffectiveContract) -> dict[str, Any]:
    contract.validate()
    parameters = deepcopy(action.parameters)
    decision = {
        "schema": SCHEMA, "action_id": action.request_id,
        "capability": action.capability, "input_id": contract.input_id,
        "workflow_id": contract.workflow_id, "effective_state_id": contract.state_id,
        "policy_reference": contract.policy_reference,
        "proposed_parameters": deepcopy(parameters), "effective_parameters": parameters,
        "parameter_sources": {key: {"basis": "action_proposal"} for key in parameters},
        "authorization": {}, "allowed": True, "reason": "allowed", "retryable": False,
    }

    def reject(reason):
        decision.update(allowed=False, reason=reason, retryable=True)

    if action.capability not in contract.allowed_capabilities:
        reject("capability_not_authorized")
        return decision
    for binding in contract.bindings:
        if binding.capability != action.capability or binding.input_id not in {"", contract.input_id}:
            continue
        if binding.default_only and binding.parameter in parameters:
            continue
        if binding.parameter in parameters and not _same(parameters[binding.parameter], binding.value):
            reject("explicit_constraint_conflict")
            return decision
        parameters[binding.parameter] = deepcopy(binding.value)
        decision["parameter_sources"][binding.parameter] = {
            "basis": binding.basis, "reference": binding.reference,
            "supplied_by_contract": binding.parameter not in action.parameters,
        }
    for gate in contract.gates:
        if gate.capability != action.capability or not _same(parameters.get(gate.parameter), gate.value):
            continue
        grant = next((x for x in contract.authorizations if x.permission == gate.permission
                      and x.input_id in {"", contract.input_id}), None)
        decision["authorization"][gate.permission] = (
            {"state": grant.state, "basis": grant.basis, "reference": grant.reference}
            if grant else {"state": "unknown"})
        if grant is None or grant.state != "granted":
            reject("authorization_unknown" if grant is None else "authorization_denied")
            return decision
    for requirement in contract.required:
        if (requirement.capability == action.capability
                and (not requirement.when_present or requirement.when_present in parameters)
                and requirement.parameter not in parameters):
            reject("missing_required_parameter")
            return decision
    return decision


@dataclass(frozen=True)
class ContractOutcome:
    action: ActionRequest
    decision: dict[str, Any]
    result: ToolResult
    observation: ExecutionObservation


class SharedExecutionBoundary:
    """Resolve authority, invoke the existing Registry, record before wire delivery.

    Opt-in, single-process prototype. Receipt deduplication is process-local and
    requires the same stable action identity; it is not crash-safe exactly-once I/O.
    A sink may persist canonical events. Sink failure never causes automatic re-execution.
    """
    def __init__(self, registry, store, resolve_contract: Callable[[], EffectiveContract],
                 *, emit: Callable[[TrajectoryEvent], None] | None = None,
                 precondition: Callable | None = None):
        self.registry = registry
        self.store = store
        self.resolve_contract = resolve_contract
        self.emit = emit
        self.precondition = precondition
        self.events: list[TrajectoryEvent] = []
        self._receipts: dict[tuple[str, str], tuple[str, ContractOutcome]] = {}
        self._lock = RLock()

    def _record(self, event_type, payload, *, workflow_id, input_id, action_id="", turn_id=""):
        event = TrajectoryEvent(
            sequence=len(self.events) + 1, event_type=event_type,
            thread_id=workflow_id, turn_id=turn_id, event_id=f"contract:{len(self.events) + 1}",
            item_id=action_id or input_id,
            payload=deepcopy(payload), provenance={
                "source": SCHEMA, "workflow_id": workflow_id, "input_id": input_id},
        )
        self.events.append(event)
        if self.emit:
            self.emit(event)

    def execute(self, action: ActionRequest, *, objective="", expected_state_id=None, turn_id="") -> ContractOutcome:
        with self._lock:
            return self._execute(action, objective=objective, expected_state_id=expected_state_id, turn_id=turn_id)

    def _execute(self, action, *, objective, expected_state_id, turn_id):
        if not action.request_id:
            raise ValueError("Stable action identity is required")
        action = ActionRequest(action.capability, deepcopy(action.parameters),
                               action.request_id, action.goal_ref, action.continuation_ref)
        contract = self.resolve_contract()
        contract.validate()
        identity = (contract.workflow_id, action.request_id)
        fingerprint = json.dumps(action.to_dict(), sort_keys=True, ensure_ascii=False)
        prior = self._receipts.get(identity)
        if prior:
            if prior[0] != fingerprint:
                raise ValueError("Action identity reused with different proposal")
            return deepcopy(prior[1])
        _validate_sources(self.store, contract)
        request = request_record(self.store, contract.workflow_id, contract.input_id)
        decision = decide(action, contract)
        from .request_continuity import request_snapshot
        decision["retained_request_ids"] = request_snapshot(
            self.store, contract.workflow_id)["retained_input_ids"]
        decision["request_satisfaction"] = "not_established"
        workflow = next((x for x in self.store.workflow_runs if x.workflow_id == contract.workflow_id), None)
        if request.status != "retained" or workflow is None or workflow.status != "active":
            decision.update(allowed=False, reason="request_not_active", retryable=False)
        if expected_state_id is not None and expected_state_id != contract.state_id:
            decision.update(allowed=False, reason="stale_contract", retryable=True)
        if self.precondition is not None and action.capability in contract.allowed_capabilities:
            guard = self.precondition(action, deepcopy(decision["effective_parameters"]))
            decision["compatibility_guard"] = deepcopy(guard)
            if decision["allowed"] and not guard.get("valid"):
                decision.update(allowed=False, reason="legacy_semantic_constraint_conflict", retryable=True)
        tool = self.registry.capability_to_tool.get(action.capability, action.capability)
        step = record_attempt(
            self.store, contract.workflow_id, call_id=action.request_id,
            turn_id=turn_id or contract.input_id, tool=tool, arguments=action.parameters,
            user_request=request.metadata["text"], input_id=contract.input_id,
            provenance={"source": SCHEMA},
        )
        step.action["execution_contract"] = deepcopy(decision)
        facts = dict(workflow_id=contract.workflow_id, input_id=contract.input_id,
                     action_id=action.request_id, turn_id=turn_id or contract.input_id)
        # Failure to record a decision prevents execution.
        self._record("EXECUTION_DECISION", decision, **facts)
        called = False
        if not decision["allowed"]:
            guard = decision.get("compatibility_guard") or {}
            result = ToolResult(False, "Rejected before capability execution", {
                "execution_status": "validation_failed", "execution_succeeded": False,
                "capability_called": False, "reason": decision["reason"],
                "failure_stage": "contract_validation", "retryable": decision["retryable"],
                "capability": action.capability,
                "effective_state_id": decision["effective_state_id"],
                "authorization": deepcopy(decision["authorization"]),
                **({key: deepcopy(guard[key]) for key in ("active_constraints", "semantic_items")
                    if key in guard}),
                **({"semantic_resolution_id": guard["effective_state_id"]}
                   if "effective_state_id" in guard else {}),
                **({"requested_provider": decision["effective_parameters"].get("provider")}
                   if action.capability == "web.search" else {}),
            })
        else:
            called = True
            step.status = "running"
            try:
                result = self.registry.execute_capability(
                    action.capability, deepcopy(decision["effective_parameters"]), objective)
                data = deepcopy(result.data)
                data.setdefault("execution_succeeded", result.ok)
                succeeded = data["execution_succeeded"]
                result = ToolResult(succeeded if type(succeeded) is bool else result.ok,
                                    result.message, data)
                result.data.setdefault("execution_status", "success" if result.ok else "failed")
            except CapabilityInputError as exc:
                result = exc.tool_result()
            except Exception as exc:
                # A handler might have produced effects before raising. Do not auto-retry.
                result = ToolResult(False, "Capability outcome is unknown", {
                    "execution_status": "execution_unknown", "execution_succeeded": None,
                    "reason": type(exc).__name__, "retryable": False,
                })
            result.data["capability_called"] = True
        result.data.update(capability=action.capability, tool=tool)
        result.data = scoped_failure(action.capability, result.data)
        from .recovery_observation import recovery_observation
        recovery = recovery_observation(result.data)
        if recovery is not None:
            result.data["recovery"] = recovery
        observation = ExecutionObservation.from_tool_result(tool, result)
        observation = ExecutionObservation(
            observation_id="execution:" + sha256(f"{contract.workflow_id}:{action.request_id}".encode()).hexdigest(),
            capability=observation.capability, tool_name=observation.tool_name,
            status=("unknown" if result.data["execution_status"] == "execution_unknown"
                    else observation.status),
            message=observation.message, data=observation.data,
        )
        record_outcome(step, observation.to_event_metadata(),
                       {"status": result.data["execution_status"], "data": result.data})
        step.action["outcome"]["excerpt_delivery"] = "not_established"
        if result.data["execution_status"] == "execution_unknown":
            step.status = "unknown"
        step.action["host_execution_receipt"] = {
            "execution_observation": observation.to_event_metadata(),
            "result": {"ok": result.ok, "capability": action.capability, "tool": tool,
                       "status": result.data["execution_status"], "message": result.message,
                       "data": deepcopy(result.data)}}
        outcome = ContractOutcome(action, deepcopy(decision), result, observation)
        # Save authority and outcome BEFORE any projection/journal delivery can raise.
        self._receipts[identity] = (fingerprint, deepcopy(outcome))
        self._record("OBSERVATION", {
            "decision": decision, "execution_observation": observation.to_event_metadata(),
            "capability_called": called,
        }, **facts)
        return deepcopy(outcome)
