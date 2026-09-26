from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from runtime.action_request import ActionRequest  # noqa: E402
from runtime.capability import ToolResult  # noqa: E402
from runtime.semantic_observation import ExecutionObservation  # noqa: E402


@dataclass(frozen=True)
class DynamicToolBinding:
    """Explicit mapping from an app-server tool name to a UAEA capability."""

    capability: str
    tool_name: str
    description: str
    input_schema: dict[str, Any]

    @classmethod
    def from_registry(
        cls,
        registry: Any,
        capability: str,
        *,
        description: str,
        input_schema: Mapping[str, Any],
    ) -> "DynamicToolBinding":
        metadata = registry.capability_metadata.get(capability)
        if metadata is None:
            raise ValueError(f"Capability is not registered: {capability}")
        return cls(
            capability=metadata.name,
            tool_name=metadata.tool_name,
            description=description,
            input_schema=dict(input_schema),
        )

    def to_app_server_spec(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.tool_name,
            "description": self.description,
            "inputSchema": dict(self.input_schema),
        }


@dataclass(frozen=True)
class HarnessToolDispatch:
    thread_id: str
    turn_id: str
    call_id: str
    tool_name: str
    action_request: ActionRequest
    tool_result: ToolResult
    observation: ExecutionObservation
    max_output_chars: int = 4000

    @property
    def ok(self) -> bool:
        return self.tool_result.ok

    def to_app_server_response(self) -> dict[str, Any]:
        payload = {
            "ok": self.tool_result.ok,
            "capability": self.observation.capability,
            "tool": self.observation.tool_name,
            "status": self.observation.status,
            "message": self.observation.message,
            "data": self.tool_result.data,
        }
        text = _bounded_json_text(payload, self.max_output_chars)
        return {
            "success": self.tool_result.ok,
            "contentItems": [{"type": "inputText", "text": text}],
        }

    def to_trace_metadata(self) -> dict[str, Any]:
        return {
            "harness": {
                "thread_id": self.thread_id,
                "turn_id": self.turn_id,
                "call_id": self.call_id,
                "tool_name": self.tool_name,
            },
            "action_request": self.action_request.to_dict(),
            "execution_observation": self.observation.to_event_metadata(),
        }


class HarnessDynamicToolAdapter:
    """Translate app-server dynamic tool calls into the frozen UAEA boundary."""

    def __init__(
        self,
        registry: Any,
        bindings: list[DynamicToolBinding] | tuple[DynamicToolBinding, ...],
        *,
        max_output_chars: int = 4000,
    ) -> None:
        self.registry = registry
        self.bindings = tuple(bindings)
        self.max_output_chars = max(1, int(max_output_chars))
        self._bindings_by_tool = {binding.tool_name: binding for binding in self.bindings}
        if len(self._bindings_by_tool) != len(self.bindings):
            raise ValueError("Duplicate Harness dynamic tool name")

    def dynamic_tools(self) -> list[dict[str, Any]]:
        return [binding.to_app_server_spec() for binding in self.bindings]

    def dispatch(
        self,
        params: Mapping[str, Any],
        *,
        objective: str = "",
    ) -> HarnessToolDispatch:
        thread_id = str(params.get("threadId") or "")
        turn_id = str(params.get("turnId") or "")
        call_id = str(params.get("callId") or "")
        tool_name = str(params.get("tool") or "")
        arguments = _arguments(params.get("arguments"))
        binding = self._bindings_by_tool.get(tool_name)

        if binding is None:
            action_request = ActionRequest(
                capability=f"harness.unknown.{tool_name or 'tool'}",
                parameters=arguments,
                request_id=call_id,
            )
            result = ToolResult(
                False,
                f"Unknown Harness dynamic tool: {tool_name}",
                {"tool": tool_name, "capability": action_request.capability},
            )
            observation_tool_name = tool_name or "unknown"
        else:
            action_request = ActionRequest(
                capability=binding.capability,
                parameters=arguments,
                request_id=call_id,
            )
            result = self.registry.execute_capability(
                action_request.capability,
                action_request.parameters,
                objective or f"Harness dynamic tool call: {binding.capability}",
            )
            observation_tool_name = binding.tool_name

        observation = ExecutionObservation.from_tool_result(observation_tool_name, result)
        return HarnessToolDispatch(
            thread_id=thread_id,
            turn_id=turn_id,
            call_id=call_id,
            tool_name=tool_name,
            action_request=action_request,
            tool_result=result,
            observation=observation,
            max_output_chars=self.max_output_chars,
        )


def _arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if isinstance(decoded, dict):
            return decoded
    return {}


def _bounded_json_text(payload: dict[str, Any], max_chars: int) -> str:
    budget = max(1, int(max_chars))
    for candidate in (
        payload,
        _bounded_payload(payload, string_limit=800, list_limit=10),
        _bounded_payload(payload, string_limit=240, list_limit=6),
        _bounded_payload(payload, string_limit=80, list_limit=3),
        _minimal_payload(payload),
    ):
        text = json.dumps(candidate, ensure_ascii=False, default=str)
        if len(text) <= budget:
            return text
    fallback = {
        "ok": bool(payload.get("ok")),
        "capability": str(payload.get("capability") or ""),
        "tool": str(payload.get("tool") or ""),
        "status": str(payload.get("status") or ""),
        "message": _truncate_text(str(payload.get("message") or ""), max(20, budget // 4)),
        "data": _fallback_data(payload, budget),
    }
    return json.dumps(fallback, ensure_ascii=False, default=str)


def _bounded_payload(payload: dict[str, Any], *, string_limit: int, list_limit: int) -> dict[str, Any]:
    bounded = _bound_value(payload, string_limit=string_limit, list_limit=list_limit)
    if isinstance(bounded, dict):
        data = bounded.get("data")
        if isinstance(data, dict):
            data["_tool_output_truncated"] = True
    return bounded if isinstance(bounded, dict) else dict(payload)


def _minimal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    minimal_data: dict[str, Any] = {"_tool_output_truncated": True}
    if isinstance(data, dict):
        for key in (
            "capability",
            "tool",
            "access_status",
            "search_query",
            "search_results",
            "raw_search_result_count",
            "raw_search_result_domains",
            "candidate_evidence_results",
            "citable_results",
            "search_contract",
            "evidence_eligibility",
            "evidence_relevance",
            "requested_constraints",
            "requested_provider",
            "actual_provider",
            "fallback_occurred",
            "fallback_reason",
            "effective_query",
            "search_provider",
            "constraint_application",
            "provider_constraint_support",
            "post_filtering",
            "url",
            "title",
            "error",
        ):
            if key in data:
                minimal_data[key] = _bound_value(data[key], string_limit=160, list_limit=5)
    return {
        "ok": bool(payload.get("ok")),
        "capability": str(payload.get("capability") or ""),
        "tool": str(payload.get("tool") or ""),
        "status": str(payload.get("status") or ""),
        "message": _truncate_text(str(payload.get("message") or ""), 240),
        "data": minimal_data,
    }


def _fallback_data(payload: dict[str, Any], budget: int) -> dict[str, Any]:
    data = payload.get("data")
    fallback: dict[str, Any] = {"_tool_output_truncated": True}
    if not isinstance(data, dict):
        return fallback
    for key in (
        "search_query",
        "search_provider",
        "requested_provider",
        "actual_provider",
        "fallback_occurred",
        "fallback_reason",
        "raw_search_result_count",
        "raw_search_result_domains",
        "evidence_eligibility",
        "search_contract",
        "evidence_relevance",
        "citable_results",
        "error",
    ):
        if key in data:
            fallback[key] = _bound_value(data[key], string_limit=120, list_limit=3)
    text = json.dumps(fallback, ensure_ascii=False, default=str)
    if len(text) <= max(1, budget // 2):
        return fallback
    for key in ("raw_search_result_domains", "evidence_relevance", "citable_results"):
        fallback.pop(key, None)
        text = json.dumps(fallback, ensure_ascii=False, default=str)
        if len(text) <= max(1, budget // 2):
            return fallback
    return {
        "_tool_output_truncated": True,
        "search_provider": str(data.get("search_provider") or ""),
        "requested_provider": data.get("requested_provider"),
        "actual_provider": data.get("actual_provider"),
        "fallback_occurred": bool(data.get("fallback_occurred")),
        "fallback_reason": str(data.get("fallback_reason") or ""),
        "evidence_eligibility": _bound_value(data.get("evidence_eligibility") or {}, string_limit=80, list_limit=2),
        "search_contract": _bound_value(data.get("search_contract") or {}, string_limit=80, list_limit=2),
    }


def _bound_value(value: Any, *, string_limit: int, list_limit: int) -> Any:
    if isinstance(value, str):
        return _truncate_text(value, string_limit)
    if isinstance(value, list):
        bounded_items = [_bound_value(item, string_limit=string_limit, list_limit=list_limit) for item in value[:list_limit]]
        if len(value) > list_limit:
            bounded_items.append({"_truncated_items": len(value) - list_limit})
        return bounded_items
    if isinstance(value, tuple):
        return [_bound_value(item, string_limit=string_limit, list_limit=list_limit) for item in value[:list_limit]]
    if isinstance(value, dict):
        return {
            str(key): _bound_value(item, string_limit=string_limit, list_limit=list_limit)
            for key, item in value.items()
        }
    return value


def _truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    suffix = "\n...[field truncated]"
    keep = max(0, max_chars - len(suffix))
    return value[:keep] + suffix
