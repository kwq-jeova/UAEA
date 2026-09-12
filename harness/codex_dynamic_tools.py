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
        text = json.dumps(payload, ensure_ascii=False, default=str)
        if len(text) > self.max_output_chars:
            text = text[: self.max_output_chars] + "\n...[bounded output truncated]"
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
