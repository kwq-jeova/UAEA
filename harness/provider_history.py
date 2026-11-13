from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from .recovery_observation import recovery_observation
from .observation_boundary import observation_boundary


REJECTED = "REJECTED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class TerminalAttempt:
    call_id: str
    state: str
    reason: str
    outcome: Mapping[str, Any]


@dataclass(frozen=True)
class HistoryProjection:
    request: dict[str, Any]
    decisions: tuple[dict[str, Any], ...]


class HistoryProjectionBindingError(ValueError):
    """A Goal Call ID cannot identify conflicting proposals or receipts."""


def _goal_tool(call):
    return str(call.get("name") or "").split(".")[-1] == "goal_hypothesis"


def _validate_goal_bindings(request):
    calls = {}
    outputs = {}
    goal_ids = set()
    for field in ("input", "previous_input_messages"):
        items = request.get(field)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            cid = item.get("call_id")
            if item.get("type") == "function_call" and _goal_tool(item):
                if not isinstance(cid, str) or not cid.strip():
                    raise HistoryProjectionBindingError("Goal history has no usable Call ID")
            if not isinstance(cid, str):
                continue
            if item.get("type") == "function_call":
                calls.setdefault(cid, []).append(item)
                if _goal_tool(item):
                    goal_ids.add(cid)
            elif item.get("type") == "function_call_output":
                outputs.setdefault(cid, []).append(item)
    for cid in goal_ids:
        proposals = {(c.get("name"), json.dumps(c.get("arguments"), sort_keys=True),
                      json.dumps(c.get("internal_chat_message_metadata_passthrough"), sort_keys=True))
                     for c in calls[cid]}
        receipts = {json.dumps(o.get("output"), sort_keys=True) for o in outputs.get(cid, [])}
        if len(proposals) != 1 or len(receipts) > 1:
            raise HistoryProjectionBindingError("Conflicting Goal history for Call ID: " + cid)


class HistoryProjectionBudgetError(ValueError):
    """Required per-call history identity/result facts cannot fit; do not forward."""


_FACT_PREFIX = "Historical runtime observation, not a tool invocation or user authorization:\n"


def _fact_text(fact):
    return _FACT_PREFIX + json.dumps(fact, ensure_ascii=False)


def _json_payload(output):
    payload = output.get("output") if output else None
    if isinstance(payload, list):
        payload = "\n".join(str(p.get("text") or "") for p in payload if isinstance(p, dict))
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            return None
    return payload if isinstance(payload, dict) else None


def _goal_attempt(call, output):
    """Only this call's arguments and receipt. Never consult a Goal head or another call."""
    raw = call.get("arguments")
    try:
        arguments = json.loads(raw) if isinstance(raw, str) else None
        if not isinstance(arguments, dict):
            arguments = None
        if arguments is not None:
            json.dumps(arguments, allow_nan=False)
    except (ValueError, TypeError):
        arguments = None
    receipt = _json_payload(output)
    # Goal Sideband receipts are top-level; unknown shapes must not supply a commit.
    known_receipt = receipt if receipt and receipt.get("kind") == "goal_hypothesis_receipt" else {}
    committed = known_receipt.get("committed")
    accepted = known_receipt.get("ok")
    return {
        "operation": arguments.get("operation", "UNKNOWN") if arguments else "UNKNOWN",
        "target_candidate_id": arguments.get("candidate_id", "UNKNOWN") if arguments else "UNKNOWN",
        "submitted_arguments": arguments,
        "arguments_sha256": hashlib.sha256(raw.encode()).hexdigest() if isinstance(raw, str) else None,
        "arguments_visibility": "complete" if arguments is not None else "unavailable_invalid_or_missing",
        "proposal_text_visibility": ("complete" if isinstance(arguments.get("hypothesis"), str) else "missing")
                                    if arguments is not None else "unavailable_invalid_or_missing",
        "host_result": {
            "accepted": accepted if type(accepted) is bool else "UNKNOWN",
            "committed": committed if type(committed) is bool else "UNKNOWN",
            "saved_version_id": known_receipt.get("candidate_id", "UNKNOWN") if committed is True else "UNKNOWN",
            "error": str(known_receipt["error"])[:800] if "error" in known_receipt else "UNKNOWN",
            "error_complete": len(str(known_receipt["error"])) <= 800 if "error" in known_receipt else "UNKNOWN",
            "head_effect": "not_committed_by_this_call" if committed is False else "UNKNOWN",
            "current_head": "UNKNOWN",
            "scope": "this_call_only; current heads are separate Host state",
        },
        "is_saved_goal_version": False,
        "authorizes_action": False,
    }


def project_provider_history(request: Mapping[str, Any], *, max_goal_history_bytes: int = 24000) -> HistoryProjection:
    """Project terminal tool attempts without mutating factual Responses history."""
    projected = copy.deepcopy(dict(request))
    decisions: list[dict[str, Any]] = []
    goal_facts = []
    _validate_goal_bindings(projected)
    if max_goal_history_bytes <= 0:
        raise ValueError("Goal failure history budget must be positive")
    for field in ("input", "previous_input_messages"):
        items = projected.get(field)
        if not isinstance(items, list):
            continue
        outputs = {
            str(item.get("call_id")): item
            for item in items
            if isinstance(item, dict) and item.get("type") == "function_call_output"
        }
        output_indices = {str(item.get("call_id")): i for i, item in enumerate(items)
                          if isinstance(item, dict) and item.get("type") == "function_call_output"}
        call_indices = {}
        terminal: dict[str, TerminalAttempt] = {}
        calls: dict[str, dict[str, Any]] = {}
        for call_index, item in enumerate(items):
            if not isinstance(item, dict) or item.get("type") != "function_call":
                continue
            call_id = str(item.get("call_id") or "")
            calls[call_id] = item
            call_indices[call_id] = call_index
            attempt = _terminal_attempt(item, outputs.get(call_id))
            if attempt is not None:
                terminal[call_id] = attempt
        safe_items = []
        emitted: set[str] = set()
        for item in items:
            call_id = str(item.get("call_id") or "") if isinstance(item, dict) else ""
            attempt = terminal.get(call_id)
            if attempt is None or item.get("type") not in {
                "function_call", "function_call_output",
            }:
                safe_items.append(item)
                continue
            call = calls[call_id]
            phase = "proposal" if item["type"] == "function_call" else "outcome"
            fact = {
                "schema": "uaea.terminal_attempt_fact.v1",
                "source": "runtime_history_projection",
                "call_id": call_id,
                "tool": call.get("name"),
                "phase": phase,
                "state": attempt.state,
                "reason": attempt.reason,
                "terminal": True,
                "replayable": False,
                "observation": {**attempt.outcome, "observation_boundary": observation_boundary()},
            }
            if _goal_tool(call):
                fact["goal_attempt"] = _goal_attempt(call, outputs.get(call_id))
                fact["history_position"] = {"field": field, "call_index": call_indices[call_id],
                                            "output_index": output_indices.get(call_id)}
            keep_fact = (call_id not in emitted and
                         (item["type"] == "function_call_output" or call_id not in outputs))
            if keep_fact:
                emitted.add(call_id)
                message = {"type": "message", "role": "user",
                           "content": [{"type": "input_text", "text": _fact_text(fact)}]}
                safe_items.append(message)
                if "goal_attempt" in fact:
                    goal_facts.append((message, fact))
            decisions.append({
                "field": field,
                "call_id": call_id,
                "item_id": item.get("id"),
                "turn_id": (call.get("internal_chat_message_metadata_passthrough") or {}).get("turn_id"),
                "state": attempt.state,
                "reason": attempt.reason,
                "terminal": True,
                "replayable": False,
                "phase": phase,
                "projection_effect": "terminal_fact" if keep_fact else "coalesced_terminal_reference",
                "raw_sha256": hashlib.sha256(
                    json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest(),
            })
        projected[field] = safe_items
    # Bound this request's newly projected Goal failure facts, including both
    # history arrays. Keep complete metadata first, then fit complete argument objects
    # newest-first. Never truncate identifiers/booleans or borrow a saved Goal's text.
    if goal_facts:
        full_arguments = []
        for _, fact in goal_facts:
            proposal = fact["goal_attempt"]
            full_arguments.append((proposal["submitted_arguments"], proposal["arguments_visibility"],
                                   proposal["proposal_text_visibility"]))
            if proposal["submitted_arguments"] is not None:
                proposal["submitted_arguments"] = None
                proposal["arguments_visibility"] = "omitted_budget"
                if proposal["proposal_text_visibility"] == "complete":
                    proposal["proposal_text_visibility"] = "omitted_budget"
        def size():
            return sum(len(_fact_text(f).encode("utf-8")) for _, f in goal_facts)
        if size() > max_goal_history_bytes:
            raise HistoryProjectionBudgetError("Required Goal failure identities/results exceed history byte budget")
        for (_, fact), (arguments, visibility, text_visibility) in reversed(list(zip(goal_facts, full_arguments))):
            proposal = fact["goal_attempt"]
            before = dict(proposal)
            proposal.update(submitted_arguments=arguments, arguments_visibility=visibility,
                            proposal_text_visibility=text_visibility)
            if size() > max_goal_history_bytes:
                proposal.clear()
                proposal.update(before)
        for message, fact in goal_facts:
            message["content"][0]["text"] = _fact_text(fact)
        decisions.append({"projection_effect": "goal_failure_history_budget",
                          "turn_id": "", "call_id": "", "item_id": "",
                          "goal_failure_facts": len(goal_facts), "bytes": size(),
                          "byte_limit": max_goal_history_bytes,
                          "omitted_argument_calls": [f["call_id"] for _, f in goal_facts
                              if f["goal_attempt"]["arguments_visibility"] == "omitted_budget"]})
    return HistoryProjection(projected, tuple(decisions))


def _terminal_attempt(
    call: Mapping[str, Any], output: Mapping[str, Any] | None,
) -> TerminalAttempt | None:
    call_id = str(call.get("call_id") or "")
    arguments = call.get("arguments")
    try:
        parsed = (
            json.loads(arguments, parse_constant=_reject_constant)
            if isinstance(arguments, str) else arguments
        )
        if not isinstance(parsed, dict):
            raise ValueError("arguments must be an object")
        json.dumps(parsed, allow_nan=False)
    except (ValueError, TypeError):
        return TerminalAttempt(call_id, REJECTED, "malformed_arguments", {
            "execution_succeeded": False,
            "result_available": False,
            "error": "Tool arguments were not a valid JSON object; the attempt was rejected.",
            "recovery": recovery_observation({"execution_status": "validation_failed",
                                               "reason": "malformed_arguments", "retryable": True}),
        })
    if output is None:
        return None
    payload = output.get("output")
    if isinstance(payload, list):
        payload = "\n".join(
            str(part.get("text") or "") for part in payload if isinstance(part, dict)
        )
    if isinstance(payload, str):
        stripped = payload.strip()
        if stripped == "request_user_input is unavailable in Default mode":
            return TerminalAttempt(call_id, REJECTED, "interaction_unavailable", {
                "execution_succeeded": False, "result_available": False,
                "error": stripped,
                "recovery": recovery_observation({"execution_status": "validation_failed",
                                                   "reason": "interaction_unavailable", "retryable": False}),
            })
        if stripped == "aborted" or stripped == "Tool execution aborted":
            return TerminalAttempt(call_id, CANCELLED, "execution_aborted", {
                "execution_succeeded": False, "result_available": False,
            })
        if stripped.startswith("failed to parse function arguments:"):
            return TerminalAttempt(call_id, REJECTED, "argument_parse_failure", {
                "execution_succeeded": False, "result_available": False,
            })
        if stripped == "dynamic tool call was cancelled before receiving a response":
            return TerminalAttempt(call_id, CANCELLED, "execution_cancelled", {
                "execution_succeeded": False, "result_available": False,
            })
        try:
            payload = json.loads(stripped)
        except (ValueError, TypeError):
            return None
    if not isinstance(payload, dict):
        return None
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    status = str(data.get("execution_status") or payload.get("status") or "").lower()
    failed = (
        payload.get("ok") is False or payload.get("success") is False
        or data.get("execution_succeeded") is False
        or status in {
            "rejected", "validation_failed", "failed", "failure", "cancelled",
            "canceled", "interrupted", "aborted", "timeout", "network_failure",
            "unsupported", "configuration_error", "http_error", "partial", "incomplete",
        }
    )
    if not failed:
        return None
    state = (
        CANCELLED if status in {"cancelled", "canceled", "interrupted", "aborted"}
        else REJECTED if status in {"rejected", "validation_failed"}
        or data.get("error_kind") == "semantic_validation"
        else FAILED
    )
    reason = str(data.get("reason") or status or "tool_failure")
    reason = reason[:800]
    observation = {
        key: data[key] for key in (
            "execution_status", "execution_succeeded", "result_available",
            "requested_provider", "actual_provider", "fallback_occurred",
            "http_attempted", "failure_explanation", "semantic_status",
            "failure_stage",
            "failure_scope", "global_web_availability", "error_kind", "http_status",
            "retryable", "retry_instruction", "active_constraints", "effective_state_id", "transport_failure",
            "authorization",
            "validation_source", "policy_validation_passed", "observation_boundary", "error",
        ) if key in data
    }
    observation.setdefault("execution_succeeded", False)
    observation.setdefault("result_available", False)
    message = data.get("error") or payload.get("message")
    if isinstance(message, str):
        observation["error"] = message[:800]
    recovery = recovery_observation(data)
    if recovery is not None:
        observation["recovery"] = recovery
    return TerminalAttempt(call_id, state, reason, observation)


def _reject_constant(value: str) -> Any:
    raise ValueError(f"Non-JSON numeric constant: {value}")
