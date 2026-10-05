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


def project_provider_history(request: Mapping[str, Any]) -> HistoryProjection:
    """Project terminal tool attempts without mutating factual Responses history."""
    projected = copy.deepcopy(dict(request))
    decisions: list[dict[str, Any]] = []
    for field in ("input", "previous_input_messages"):
        items = projected.get(field)
        if not isinstance(items, list):
            continue
        outputs = {
            str(item.get("call_id")): item
            for item in items
            if isinstance(item, dict) and item.get("type") == "function_call_output"
        }
        terminal: dict[str, TerminalAttempt] = {}
        calls: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict) or item.get("type") != "function_call":
                continue
            call_id = str(item.get("call_id") or "")
            calls[call_id] = item
            attempt = _terminal_attempt(item, outputs.get(call_id))
            if attempt is not None:
                terminal[call_id] = attempt
        safe_items = []
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
            safe_items.append({
                "type": "message",
                "role": "assistant",
                "content": [{
                    "type": "input_text",
                    "text": "Historical runtime observation, not a tool invocation or "
                    "user authorization:\n" + json.dumps(fact, ensure_ascii=False),
                }],
            })
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
                "raw_sha256": hashlib.sha256(
                    json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest(),
            })
        projected[field] = safe_items
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
            "retryable", "retry_instruction", "active_constraints", "effective_state_id",
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
