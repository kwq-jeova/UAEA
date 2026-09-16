from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


USER_INPUT = "USER_INPUT"
AGENT_OUTPUT = "AGENT_OUTPUT"
TOOL_CALL = "TOOL_CALL"
TOOL_RESULT = "TOOL_RESULT"
OBSERVATION = "OBSERVATION"
COMMAND_EXECUTION = "COMMAND_EXECUTION"
TOKEN_USAGE = "TOKEN_USAGE"
CONTEXT_COMPACTION = "CONTEXT_COMPACTION"
TURN_STARTED = "TURN_STARTED"
TURN_COMPLETED = "TURN_COMPLETED"
PRE_TURN_CONTEXT = "PRE_TURN_CONTEXT"
ERROR = "ERROR"
CANCELLED = "CANCELLED"
RAW_EVENT = "RAW_EVENT"


@dataclass(frozen=True)
class TrajectoryEvent:
    """UAEA-neutral event contract derived from a raw Harness event."""

    sequence: int
    event_type: str
    thread_id: str = ""
    turn_id: str = ""
    item_id: str = ""
    event_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_event_reference: dict[str, Any] = field(default_factory=dict)
    raw_event: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, include_raw: bool = True) -> dict[str, Any]:
        data = {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "identity": {
                "thread_id": self.thread_id,
                "turn_id": self.turn_id,
                "item_id": self.item_id,
                "event_id": self.event_id,
            },
            "payload": self.payload,
            "provenance": self.provenance,
            "raw_event_reference": self.raw_event_reference,
        }
        if include_raw:
            data["raw_event"] = self.raw_event
        return data


class HarnessEventNormalizer:
    """Normalize Codex app-server JSON-RPC traffic without interpreting meaning."""

    def __init__(self, *, source: str = "codex_app_server") -> None:
        self.source = source
        self._sequence = 0

    def normalize_many(
        self,
        raw_events: Iterable[Mapping[str, Any]],
        *,
        raw_event_reference_prefix: Mapping[str, Any] | None = None,
    ) -> list[TrajectoryEvent]:
        normalized: list[TrajectoryEvent] = []
        for raw_index, raw_event in enumerate(raw_events):
            reference = dict(raw_event_reference_prefix or {})
            reference["raw_index"] = raw_index
            normalized.extend(
                self.normalize(raw_event, raw_event_reference=reference)
            )
        return normalized

    def normalize(
        self,
        raw_event: Mapping[str, Any],
        *,
        raw_event_reference: Mapping[str, Any] | None = None,
    ) -> list[TrajectoryEvent]:
        raw_copy = dict(raw_event)
        message = _message_from_raw(raw_copy)
        if not isinstance(message, dict):
            return [self._event(RAW_EVENT, raw_copy, raw_copy, raw_event_reference)]

        method = str(message.get("method") or "")
        params = _mapping(message.get("params"))
        item = _mapping(params.get("item"))
        turn = _mapping(params.get("turn"))
        event_id = _event_id(message, item, params)
        thread_id = _thread_id(params, item, message)
        turn_id = _turn_id(params, item, message)
        item_id = str(params.get("itemId") or item.get("id") or params.get("callId") or "")
        base_payload = {
            "method": method,
            "message_id": message.get("id"),
            "emitted_at_ms": message.get("emittedAtMs"),
            "params": params,
        }

        if message.get("error") is not None:
            return [
                self._event(
                    ERROR,
                    raw_copy,
                    {"method": method, "error": message["error"]},
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]

        if method == "error":
            return [
                self._event(
                    ERROR,
                    raw_copy,
                    {"method": method, "error": params.get("error"), "params": params},
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]

        if method == "turn/start":
            payload = {
                "input": params.get("input"),
                "additional_context": params.get("additionalContext"),
                "model": params.get("model"),
                "effort": params.get("effort"),
            }
            return [
                self._event(
                    PRE_TURN_CONTEXT,
                    raw_copy,
                    payload,
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]

        if method == "turn/started":
            return [
                self._event(
                    TURN_STARTED,
                    raw_copy,
                    {"turn": turn},
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]

        if method == "turn/completed":
            events = [
                self._event(
                    TURN_COMPLETED,
                    raw_copy,
                    {"turn": turn},
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]
            status = str(turn.get("status") or "")
            if status in {"cancelled", "canceled"}:
                events.append(
                    self._event(
                        CANCELLED,
                        raw_copy,
                        {"turn": turn},
                        raw_event_reference,
                        thread_id=thread_id,
                        turn_id=turn_id,
                        item_id=item_id,
                        event_id=event_id,
                    )
                )
            elif turn.get("error") or status == "failed":
                events.append(
                    self._event(
                        ERROR,
                        raw_copy,
                        {"turn": turn, "error": turn.get("error")},
                        raw_event_reference,
                        thread_id=thread_id,
                        turn_id=turn_id,
                        item_id=item_id,
                        event_id=event_id,
                    )
                )
            return events

        if method == "thread/tokenUsage/updated" or method == "rawResponse/completed":
            return [
                self._event(
                    TOKEN_USAGE,
                    raw_copy,
                    base_payload,
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]

        if method == "item/tool/call":
            return [
                self._event(
                    TOOL_CALL,
                    raw_copy,
                    {
                        "namespace": params.get("namespace"),
                        "tool": params.get("tool"),
                        "arguments": params.get("arguments"),
                        "call_id": params.get("callId"),
                    },
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=str(params.get("callId") or item_id),
                    event_id=event_id,
                )
            ]

        if method == "item/agentMessage/delta":
            return [
                self._event(
                    AGENT_OUTPUT,
                    raw_copy,
                    {"delta": params.get("delta"), "is_delta": True},
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]

        if method == "item/commandExecution/outputDelta":
            return [
                self._event(
                    COMMAND_EXECUTION,
                    raw_copy,
                    {"delta": params.get("delta"), "is_delta": True},
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]

        if method in {"item/started", "item/completed"} and item:
            return self._normalize_item_event(
                raw_copy,
                raw_event_reference,
                method,
                thread_id,
                turn_id,
                item_id,
                event_id,
                item,
            )

        if method == "rawResponseItem/completed" and item:
            return self._normalize_raw_response_item(
                raw_copy,
                raw_event_reference,
                thread_id,
                turn_id,
                item_id,
                event_id,
                item,
            )

        return [
            self._event(
                RAW_EVENT,
                raw_copy,
                base_payload,
                raw_event_reference,
                thread_id=thread_id,
                turn_id=turn_id,
                item_id=item_id,
                event_id=event_id,
            )
        ]

    def _normalize_item_event(
        self,
        raw_event: dict[str, Any],
        raw_event_reference: Mapping[str, Any] | None,
        method: str,
        thread_id: str,
        turn_id: str,
        item_id: str,
        event_id: str,
        item: Mapping[str, Any],
    ) -> list[TrajectoryEvent]:
        item_type = str(item.get("type") or "")
        status = str(item.get("status") or "")
        payload = {"method": method, "item": dict(item)}

        if item_type == "userMessage":
            return [
                self._event(
                    USER_INPUT,
                    raw_event,
                    payload,
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]
        if item_type == "agentMessage":
            return [
                self._event(
                    AGENT_OUTPUT,
                    raw_event,
                    payload,
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]
        if item_type == "dynamicToolCall":
            event_type = TOOL_CALL if method == "item/started" else TOOL_RESULT
            events = [
                self._event(
                    event_type,
                    raw_event,
                    payload,
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]
            if method == "item/completed":
                events.append(
                    self._event(
                        OBSERVATION,
                        raw_event,
                        payload,
                        raw_event_reference,
                        thread_id=thread_id,
                        turn_id=turn_id,
                        item_id=item_id,
                        event_id=event_id,
                    )
                )
                if status == "failed" or item.get("success") is False:
                    events.append(
                        self._event(
                            ERROR,
                            raw_event,
                            payload,
                            raw_event_reference,
                            thread_id=thread_id,
                            turn_id=turn_id,
                            item_id=item_id,
                            event_id=event_id,
                        )
                    )
            return events
        if item_type == "commandExecution":
            events = [
                self._event(
                    COMMAND_EXECUTION,
                    raw_event,
                    payload,
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]
            if method == "item/completed":
                events.append(
                    self._event(
                        OBSERVATION,
                        raw_event,
                        payload,
                        raw_event_reference,
                        thread_id=thread_id,
                        turn_id=turn_id,
                        item_id=item_id,
                        event_id=event_id,
                    )
                )
                if status == "failed":
                    events.append(
                        self._event(
                            ERROR,
                            raw_event,
                            payload,
                            raw_event_reference,
                            thread_id=thread_id,
                            turn_id=turn_id,
                            item_id=item_id,
                            event_id=event_id,
                        )
                    )
            return events
        if item_type == "contextCompaction":
            return [
                self._event(
                    CONTEXT_COMPACTION,
                    raw_event,
                    payload,
                    raw_event_reference,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    item_id=item_id,
                    event_id=event_id,
                )
            ]
        return [
            self._event(
                RAW_EVENT,
                raw_event,
                payload,
                raw_event_reference,
                thread_id=thread_id,
                turn_id=turn_id,
                item_id=item_id,
                event_id=event_id,
            )
        ]

    def _normalize_raw_response_item(
        self,
        raw_event: dict[str, Any],
        raw_event_reference: Mapping[str, Any] | None,
        thread_id: str,
        turn_id: str,
        item_id: str,
        event_id: str,
        item: Mapping[str, Any],
    ) -> list[TrajectoryEvent]:
        item_type = str(item.get("type") or "")
        role = str(item.get("role") or "")
        payload = {"raw_response_item": dict(item)}
        if item_type == "message" and role == "user":
            event_type = USER_INPUT
        elif item_type == "message" and role in {"assistant", "agent"}:
            event_type = AGENT_OUTPUT
        elif item_type == "function_call":
            event_type = TOOL_CALL
        elif item_type == "function_call_output":
            event_type = TOOL_RESULT
        else:
            event_type = RAW_EVENT
        return [
            self._event(
                event_type,
                raw_event,
                payload,
                raw_event_reference,
                thread_id=thread_id,
                turn_id=turn_id,
                item_id=item_id,
                event_id=event_id,
            )
        ]

    def _event(
        self,
        event_type: str,
        raw_event: dict[str, Any],
        payload: Mapping[str, Any],
        raw_event_reference: Mapping[str, Any] | None,
        *,
        thread_id: str = "",
        turn_id: str = "",
        item_id: str = "",
        event_id: str = "",
    ) -> TrajectoryEvent:
        self._sequence += 1
        reference = dict(raw_event_reference or {})
        message = _message_from_raw(raw_event)
        method = message.get("method") if isinstance(message, dict) else None
        if method and "method" not in reference:
            reference["method"] = method
        return TrajectoryEvent(
            sequence=self._sequence,
            event_type=event_type,
            thread_id=thread_id,
            turn_id=turn_id,
            item_id=item_id,
            event_id=event_id or f"uaea-event-{self._sequence}",
            payload=dict(payload),
            provenance={
                "source": self.source,
                "native_method": method,
                "observed_at": raw_event.get("observed_at"),
                "emitted_at_ms": (
                    message.get("emittedAtMs") if isinstance(message, dict) else None
                ),
            },
            raw_event_reference=reference,
            raw_event=raw_event,
        )


def _message_from_raw(raw_event: Mapping[str, Any]) -> Any:
    message = raw_event.get("message")
    if isinstance(message, dict):
        return message
    line = raw_event.get("line")
    if isinstance(line, str):
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError:
            return raw_event
        if isinstance(decoded, dict):
            return decoded
    return raw_event


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _event_id(
    message: Mapping[str, Any],
    item: Mapping[str, Any],
    params: Mapping[str, Any],
) -> str:
    for value in (
        message.get("id"),
        params.get("callId"),
        params.get("itemId"),
        item.get("id"),
    ):
        if value is not None and value != "":
            return str(value)
    return ""


def _thread_id(
    params: Mapping[str, Any],
    item: Mapping[str, Any],
    message: Mapping[str, Any],
) -> str:
    if params.get("threadId"):
        return str(params["threadId"])
    result = _mapping(message.get("result"))
    thread = _mapping(result.get("thread"))
    if thread.get("id"):
        return str(thread["id"])
    if item.get("threadId"):
        return str(item["threadId"])
    return ""


def _turn_id(
    params: Mapping[str, Any],
    item: Mapping[str, Any],
    message: Mapping[str, Any],
) -> str:
    if params.get("turnId"):
        return str(params["turnId"])
    turn = _mapping(params.get("turn"))
    if turn.get("id"):
        return str(turn["id"])
    result = _mapping(message.get("result"))
    result_turn = _mapping(result.get("turn"))
    if result_turn.get("id"):
        return str(result_turn["id"])
    metadata = _mapping(item.get("internal_chat_message_metadata_passthrough"))
    if metadata.get("turn_id"):
        return str(metadata["turn_id"])
    return ""
