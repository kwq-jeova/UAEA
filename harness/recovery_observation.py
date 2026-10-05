from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


RECOVERY_SCHEMA = "uaea.recovery_observation.v1"


def recovery_observation(data: Mapping[str, Any]) -> dict[str, Any] | None:
    """Describe new-attempt options; never grant policy or dispatch an action."""
    existing = data.get("recovery")
    if isinstance(existing, dict) and existing.get("schema") == RECOVERY_SCHEMA:
        return deepcopy(existing)
    if (data.get("execution_status") != "validation_failed"
            and data.get("error_kind") != "semantic_validation"):
        return None
    constraints = list(data.get("active_constraints") or [])
    authorization = data.get("authorization") or {}
    state = authorization.get("state")
    if state not in {"unknown", "denied", "granted"}:
        state = "unknown"
    sources = []
    for item in authorization.get("source_items", []):
        metadata = item.get("metadata") or {}
        sources.append({
            "item_id": item.get("item_id") or item.get("object_id"),
            "source_turn_id": item.get("source_turn_id") or (metadata.get("provenance") or {}).get("turn_id"),
        })
    retryable = data.get("retryable") is True
    result = {
        "schema": RECOVERY_SCHEMA,
        "reason": str(data.get("semantic_status") or data.get("reason") or "validation_failed"),
        "retryable": retryable,
        "constraints_known": "active_constraints" in data,
        "active_constraints": constraints,
        "effective_state_id": data.get("effective_state_id", ""),
        "authorization": {"state": state, "source_items": sources,
                          "model_proposal": authorization.get("model_proposal"),
                          "scope": authorization.get("scope", "unspecified")},
        "policy_time": "at_attempt",
        "requires_current_policy_validation": True,
        "interaction_failure_grants_authorization": False,
        "legal_next_steps": [],
    }
    steps = result["legal_next_steps"]
    if data.get("reason") == "interaction_unavailable":
        steps.append({"action": "ask_user_in_conversation", "wait_for_user_reply": True})
    elif retryable and data.get("validation_source") == "capability_input" and not data.get("semantic_status"):
        steps.append({"action": "repair_arguments", "use_current_tool_schema": True,
                      "preserve_active_constraints": True, "requires_current_policy_validation": True})
    elif retryable and data.get("capability") == "web.search":
        provider = next((value.split("=", 1)[1] for value in constraints
                         if value.startswith("web.provider=")), data.get("requested_provider"))
        excluded = {value.split("=", 1)[1] for value in constraints
                    if value.startswith("web.exclude_provider=")}
        if provider not in excluded:
            updates = {"allow_fallback": False}
            if provider:
                updates["provider"] = provider
            steps.append({"action": "retry_capability", "capability": "web.search",
                          "argument_updates": updates, "preserve_other_arguments": True})
            if state == "granted" and "web.fallback=forbidden" not in constraints:
                steps.append({"action": "retry_capability", "capability": "web.search",
                              "argument_updates": {**updates, "allow_fallback": True},
                              "preserve_other_arguments": True})
            elif state == "unknown":
                steps.append({"action": "ask_user_for_fallback_permission",
                              "wait_for_user_reply": True})
        else:
            steps.append({"action": "ask_user_to_resolve_constraints", "wait_for_user_reply": True})
    elif retryable:
        steps.append({"action": "repair_arguments", "use_current_tool_schema": True})
    return result
