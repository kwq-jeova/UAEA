from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


RECOVERY_SCHEMA = "uaea.recovery_observation.v1"


def recovery_observation(data: Mapping[str, Any]) -> dict[str, Any] | None:
    """Describe new-attempt options; never grant policy or dispatch an action."""
    existing = data.get("recovery")
    if isinstance(existing, dict) and existing.get("schema") == RECOVERY_SCHEMA:
        return deepcopy(existing)
    if (data.get("execution_succeeded") is False
            and (data.get("execution_status") == "http_failure"
                 or data.get("error_kind") in {"local_file_failure", "content_challenge"})):
        # A reported endpoint/file/content failure cannot establish a global outage.
        kind = data.get("error_kind") or data.get("execution_status")
        return {
            "schema": RECOVERY_SCHEMA, "reason": data.get("reason") or kind,
            "state": "blocked_attempt", "retryable": False,
            "failure_scope": data.get("failure_scope", "this_action_only"),
            "global_web_availability": "not_determined_by_this_failure",
            "http_status": data.get("http_status"),
            "requires_current_policy_validation": True,
            "interaction_failure_grants_authorization": False,
            "legal_next_steps": [
                {"action": ("verify_accessible_file_reference" if kind == "local_file_failure"
                            else "review_endpoint_or_source"),
                 "use_observed_references_only": True, "bypass_security": False,
                 "automatic": False},
                {"action": "report_blocked", "preserve_unfinished_request": True,
                 "workflow_completed": False}],
        }
    if (data.get("execution_status") in {"network_failure", "timeout"}
            and data.get("execution_succeeded") is False
            and data.get("capability") in {"web.search", "web.fetch"}):
        provider = data.get("requested_provider")
        step = {"action": "retry_capability", "capability": data["capability"],
                "preserve_other_arguments": True, "requires_current_policy_validation": True,
                "new_action_identity_required": True, "automatic": False}
        if data["capability"] == "web.search":
            # A suggestion cannot grant provider switching, even if the failed
            # proposal requested it. A new attempt is checked by the same policy.
            step["argument_updates"] = {"allow_fallback": False, **({"provider": provider} if provider else {})}
        else:
            step["argument_updates"] = {}
        return {"schema": RECOVERY_SCHEMA, "reason": data.get("reason"),
                "retryable": True, "state": "recoverable_failure",
                "transport_failure": deepcopy(data.get("transport_failure", {})),
                "retry_scope": "same_provider_or_url_new_attempt",
                "requires_current_policy_validation": True,
                "interaction_failure_grants_authorization": False,
                "failure_scope": "this_action_only",
                "global_web_availability": "not_determined_by_this_failure",
                "legal_next_steps": [step, {"action": "report_blocked",
                    "preserve_unfinished_request": True, "workflow_completed": False}]}
    if (data.get("execution_status") != "validation_failed"
            and data.get("error_kind") != "semantic_validation"):
        return None
    constraints = list(data.get("active_constraints") or [])
    authorization = data.get("authorization") or {}
    switch = authorization.get("provider_switch", authorization)
    state = switch.get("state")
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
        "failure_scope": data.get("failure_scope", "this_action_only"),
        "global_web_availability": "not_determined_by_this_failure",
        "legal_next_steps": [],
    }
    if (data.get("capability") == "web.search"
            and "provider_switch" in authorization
            and data.get("reason") in {"authorization_unknown", "authorization_denied"}):
        result["failure_scope"] = "web.provider_fallback"
        result["authorization"]["scope"] = "web.provider_fallback"
        result["failure_explanation"] = (
            "Only the provider-fallback proposal was rejected. This is not a denial "
            "of same-provider search or evidence that the network is unavailable. "
            "A new same-provider request with allow_fallback=false must pass current policy.")
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
                          "argument_updates": updates, "preserve_other_arguments": True,
                          "requires_current_policy_validation": True,
                          "new_action_identity_required": True, "automatic": False})
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
    steps.append({"action": "report_blocked", "preserve_unfinished_request": True,
                  "workflow_completed": False})
    result["state"] = "recoverable_failure" if retryable else "blocked"
    return result
