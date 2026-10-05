from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .recovery_observation import recovery_observation
from .observation_boundary import factual_web_message, observation_boundary


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from runtime.action_request import ActionRequest  # noqa: E402
from runtime.capability import ToolResult  # noqa: E402
from runtime.semantic_observation import ExecutionObservation  # noqa: E402


IDENTITY_FIELDS = frozenset({
    "title", "url", "path", "handle", "content_ref", "source_kind", "source_id",
    "source_event_id", "observation_id", "request_id", "thread_id", "turn_id",
    "item_id", "event_id", "call_id", "owner", "scope", "sha256", "hash",
    "object_id", "effective_state_id", "access_event_id", "web_source_id", "location",
})


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
    semantic_validation: dict[str, Any] | None = None
    max_output_chars: int = 4000

    @property
    def ok(self) -> bool:
        return self.tool_result.ok

    def to_app_server_response(self) -> dict[str, Any]:
        data = _model_visible_tool_data(
            self.observation.capability,
            self.tool_result.data,
        )
        if data.get("execution_status") == "validation_failed":
            if self.semantic_validation is not None:
                for key in ("active_constraints", "effective_state_id", "authorization"):
                    data[key] = self.semantic_validation[key]
                data["policy_validation_passed"] = self.semantic_validation["valid"]
                if self.observation.capability == "web.search":
                    data["authorization"] = {**data["authorization"], "scope": "web.provider_fallback"}
            if self.observation.capability == "web.search" and data.get("http_attempted") is False:
                data.setdefault("requested_provider", self.action_request.parameters.get("provider"))
                data.setdefault("actual_provider", None)
            recovery = recovery_observation(data)
            if recovery is not None:
                data["recovery"] = recovery
                data["authorization"] = recovery["authorization"]
        if self.observation.capability in {"web.search", "web.fetch"}:
            data["observation_boundary"] = observation_boundary()
        payload = {
            "ok": self.tool_result.ok,
            "capability": self.observation.capability,
            "tool": self.observation.tool_name,
            "status": data.get("execution_status", self.observation.status),
            "message": factual_web_message(self.observation.capability, data, self.observation.message),
            "identity": {"thread_id": self.thread_id, "turn_id": self.turn_id,
                         "call_id": self.call_id, "observation_id": self.observation.observation_id},
            "data": data,
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
            "semantic_validation": dict(self.semantic_validation or {}),
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
        self._semantic_state_adapter: Any | None = None
        if len(self._bindings_by_tool) != len(self.bindings):
            raise ValueError("Duplicate Harness dynamic tool name")

    def bind_semantic_state_adapter(self, adapter: Any) -> None:
        self._semantic_state_adapter = adapter

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
        semantic_validation: dict[str, Any] | None = None

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
            if self._semantic_state_adapter is not None:
                semantic_validation = self._semantic_state_adapter.validate_tool_action(
                    thread_id,
                    action_request.capability,
                    action_request.parameters,
                    turn_id=turn_id,
                    call_id=call_id,
                )
            if semantic_validation is not None and not semantic_validation.get("valid"):
                conflicts = list(semantic_validation.get("conflicts") or [])
                result = ToolResult(
                    False,
                    "Action rejected by UAEA semantic authority: "
                    + "; ".join(conflicts),
                    {
                        "capability": binding.capability,
                        "tool": binding.tool_name,
                        "execution_status": "validation_failed",
                        "execution_succeeded": False,
                        "http_attempted": False,
                        "reason": "semantic_constraint_conflict",
                        "failure_explanation": "Action was rejected before execution by UAEA semantic validation.",
                        "requested_provider": arguments.get("provider"),
                        "actual_provider": None,
                        "fallback_occurred": False,
                        "error_kind": "semantic_validation",
                        "semantic_status": "constraint_conflict",
                        "retryable": True,
                        "active_constraints": semantic_validation.get("active_constraints", []),
                        "effective_state_id": semantic_validation.get("effective_state_id", ""),
                        "semantic_items": semantic_validation.get("semantic_items", []),
                        "proposed_action": semantic_validation.get("proposed_action", {}),
                        "conflicts": conflicts,
                        "retry_instruction": (
                            "Retry with an action that satisfies the active semantic "
                            "constraints and their ownership/scope; do not change "
                            "the user's policy or silently rewrite the proposed action."
                        ),
                        "provenance": semantic_validation.get("provenance", {}),
                        "authorization": semantic_validation.get("authorization", {}),
                    },
                )
            else:
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
            semantic_validation=semantic_validation,
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


def _model_visible_tool_data(capability: str, data: Mapping[str, Any]) -> dict[str, Any]:
    """Project capability output for the Harness model without mutating provenance."""

    projected = dict(data)
    if capability in {"web.search", "web.fetch"}:
        projected.pop("network_diagnostics", None)
    if capability in {"web.search", "web.fetch"} and data.get("execution_succeeded") is False:
        projected = {key: data[key] for key in (
            "capability", "tool", "access_event_id", "web_source_id", "access_status", "status",
            "execution_status", "execution_succeeded", "http_attempted", "reason",
            "failure_explanation", "requested_provider", "actual_provider", "fallback_occurred",
            "acquisition_backend",
            "fallback_reason", "requested_constraints", "http_status", "error", "error_kind",
            "semantic_status", "retryable", "retry_instruction",
            "validation_source", "unsupported_fields",
            "evidence_status", "evidence_evaluation", "citable_results",
            "active_constraints", "effective_state_id", "semantic_items",
            "proposed_action", "conflicts", "authorization",
        ) if key in data}
        if data.get("error_kind") == "semantic_validation" and "recommended_next_action" in data:
            projected["recommended_next_action"] = data["recommended_next_action"]
        if data.get("error_kind") == "semantic_validation":
            projected["semantic_items"] = [
                {"item_id": item["object_id"], "owner": item["owner"],
                 "scope": item["metadata"]["scope"], "value": item["metadata"]["value"],
                 "provenance": {key: item["metadata"]["provenance"].get(key)
                                for key in ("thread_id", "turn_id", "event_id")}}
                for item in data.get("semantic_items", [])
            ]
            authorization = data.get("authorization", {})
            projected["authorization"] = {
                "state": authorization.get("state"), "model_proposal": authorization.get("model_proposal"),
                "source_items": [{"item_id": item["object_id"], "owner": item["owner"],
                                  "scope": item["metadata"]["scope"],
                                  "source_turn_id": item["metadata"]["provenance"].get("turn_id")}
                                 for item in authorization.get("source_items", [])],
            }
        return projected
    if projected.get("error_kind") == "semantic_validation" and "semantic_items" in projected:
        projected["semantic_items"] = [
            {"item_id": item["object_id"], "owner": item["owner"], "status": item["status"],
             "kind": item["metadata"]["kind"], "scope": item["metadata"]["scope"],
             "value": item["metadata"]["value"],
             "provenance": {key: item["metadata"]["provenance"].get(key)
                            for key in ("thread_id", "turn_id", "event_id")}}
            for item in projected["semantic_items"]
        ]
    if capability != "web.search":
        return projected

    contract = projected.get("search_contract")
    eligibility = projected.get("evidence_eligibility")
    candidate_status = ""
    if isinstance(contract, Mapping):
        candidate_status = str(contract.get("candidate_status") or "")
    if not candidate_status and isinstance(eligibility, Mapping):
        candidate_status = str(eligibility.get("candidate_status") or "")

    if candidate_status != "low_relevance":
        return projected

    # Raw results remain in the ToolResult/SQLite/trajectory provenance path.
    # The App Server receives only the bounded semantic outcome.
    for key in (
        "raw_search_results",
        "raw_results_before_filtering",
        "raw_result_domains",
        "raw_search_result_domains",
        "search_results",
        "candidate_evidence_results",
        "citable_results",
    ):
        if key in projected:
            projected[key] = []
    projected["bounded_evidence_block"] = (
        "[WEB SEARCH RESULT CONTRACT]\n"
        "candidate_status: low_relevance\n"
        "citable_results: 0\n"
        "action: revise_query\n"
        "citation_policy: do not cite or summarize low-relevance raw search results as evidence."
    )
    projected["model_visible_evidence"] = {
        "candidate_status": "low_relevance",
        "citable_results": [],
        "recommended_next_action": "revise_query",
        "citation_policy": (
            "Do not cite or summarize low-relevance raw search results as evidence."
        ),
    }
    return projected


def _bounded_json_text(payload: dict[str, Any], max_chars: int) -> str:
    budget = max(1, int(max_chars))
    data = payload.get("data", {})
    if isinstance(data, dict) and data.get("recovery"):
        text = json.dumps(payload, ensure_ascii=False, default=str)
        if len(text) <= budget:
            return text
        compact = {key: payload[key] for key in ("ok", "capability", "tool", "status", "identity") if key in payload}
        compact["message"] = _truncate_text(str(payload.get("message") or ""), 120)
        compact["data"] = {key: data[key] for key in (
            "execution_status", "execution_succeeded", "http_attempted", "reason",
            "requested_provider", "actual_provider", "fallback_occurred", "recovery",
            "error_kind", "semantic_status", "active_constraints", "effective_state_id",
            "semantic_items", "authorization", "retryable", "retry_instruction",
            "validation_source", "policy_validation_passed", "observation_boundary",
        ) if key in data}
        if "error" in data:
            compact["data"]["error"] = _truncate_text(str(data["error"]), 400)
        text = json.dumps(compact, ensure_ascii=False, default=str)
        if len(text) > budget:
            for key in ("active_constraints", "effective_state_id", "semantic_items",
                        "authorization", "retryable", "retry_instruction", "semantic_status"):
                compact["data"].pop(key, None)
            text = json.dumps(compact, ensure_ascii=False, default=str)
        if len(text) > budget:
            raise ValueError("Tool rejection recovery contract exceeds projection budget")
        return text
    if (payload.get("capability") == "web.search" and isinstance(data, dict)
            and data.get("execution_succeeded") is True):
        return _bounded_search_evidence(payload, budget)
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
        "message": _truncate_text(str(payload.get("message") or ""),
                                  min(120, max(20, budget // 4)) if isinstance(data, dict) and data.get("observation_boundary")
                                  else max(20, budget // 4)),
        "data": _fallback_data(payload, budget),
    }
    if "identity" in payload:
        fallback["identity"] = payload["identity"]
    text = json.dumps(fallback, ensure_ascii=False, default=str)
    if len(text) > budget:
        raise ValueError("Tool result identity/contract exceeds projection budget")
    return text


def _bounded_search_evidence(payload: dict[str, Any], budget: int) -> str:
    data = payload["data"]
    candidates = [dict(item) for item in data.get("citable_results", [])
                  if isinstance(item, dict) and isinstance(item.get("title"), str)
                  and item["title"] and isinstance(item.get("url"), str) and item["url"]]
    contract = data.get("search_contract") or {}
    eligibility = data.get("evidence_eligibility") or {}
    status = contract.get("candidate_status") or eligibility.get("candidate_status") or data.get("evidence_status")
    if status == "low_relevance":
        candidates = []
    projected = {key: data[key] for key in (
        "access_event_id", "web_source_id", "execution_status", "execution_succeeded",
        "http_attempted", "reason", "requested_provider", "actual_provider",
        "acquisition_backend", "fallback_occurred", "evidence_status",
        "observation_boundary",
    ) if key in data}
    projected.update({
        "_tool_output_truncated": True,
        "search_query": _truncate_text(str(data.get("search_query") or ""), 180),
        "fallback_reason": _truncate_text(str(data.get("fallback_reason") or ""), 120),
        "search_contract": {
            "evidence_level": "search_results_only", "candidate_status": status,
            "page_evidence_requires_fetch": True,
            "citation_policy": "Only cite retained citable_results URLs; fetch before page-level claims.",
        },
        "eligible_result_count": len(candidates),
    })
    reference = data.get("evidence_reference")
    if isinstance(reference, dict):
        projected["evidence_reference"] = {key: reference[key] for key in
            ("source_kind", "source_id", "source_event_id", "location") if key in reference}
    bounded = {**payload, "message": _truncate_text(str(payload.get("message") or ""), 160), "data": projected}
    # Drop descriptions before candidate quantity. Never truncate a retained title/URL pair.
    for count in range(min(3, len(candidates)), -1, -1):
        for snippet_chars in (120, 0):
            retained = []
            for item in candidates[:count]:
                candidate = {"title": item["title"], "url": item["url"]}
                if snippet_chars and item.get("snippet"):
                    candidate["snippet"] = _truncate_text(str(item["snippet"]), snippet_chars)
                retained.append(candidate)
            projected["citable_results"] = retained
            projected["citable_result_count"] = count
            projected["search_contract"]["citable_result_count"] = count
            projected["omitted_eligible_result_count"] = len(candidates) - count
            projected["recommended_next_action"] = "fetch_selected_candidate" if count else "revise_query"
            if data.get("observation_boundary"):
                bounded["message"] = _truncate_text(factual_web_message("web.search", projected, ""), 160)
            if candidates and not count:
                projected["projection_status"] = "identity_exceeds_budget"
                projected["recommended_next_action"] = "report_projection_limit"
                bounded["message"] = "Search executed, but no complete candidate identity fits the projection budget. No URL was supplied."
            text = json.dumps(bounded, ensure_ascii=False, default=str)
            if len(text) <= budget:
                return text
    raise ValueError("Search execution/provenance identity exceeds projection budget")


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
            "status",
            "execution_status",
            "execution_succeeded",
            "http_attempted",
            "reason",
            "failure_explanation",
            "validation_source", "policy_validation_passed", "observation_boundary",
            "evidence_status",
            "evidence_evaluation",
            "error_kind",
            "semantic_status",
            "retryable",
            "retry_instruction",
            "effective_state_id",
            "active_constraints",
            "proposed_action",
            "conflicts",
            "semantic_items",
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
            "acquisition_backend",
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
            "path", "handle", "content_ref", "section_index", "section_title",
            "sha256", "source_kind", "source_id", "source_event_id",
            "evidence_reference", "evidence_refs", "authorization",
            "access_event_id", "web_source_id",
        ):
            if key in data:
                minimal_data[key] = data[key] if key == "observation_boundary" or (key in IDENTITY_FIELDS and isinstance(data[key], str)) else \
                    _bound_value(data[key], string_limit=160, list_limit=5)
    result = {
        "ok": bool(payload.get("ok")),
        "capability": str(payload.get("capability") or ""),
        "tool": str(payload.get("tool") or ""),
        "status": str(payload.get("status") or ""),
        "message": _truncate_text(str(payload.get("message") or ""), 240),
        "data": minimal_data,
    }
    if "identity" in payload:
        result["identity"] = payload["identity"]
    return result


def _fallback_data(payload: dict[str, Any], budget: int) -> dict[str, Any]:
    data = payload.get("data")
    fallback: dict[str, Any] = {"_tool_output_truncated": True}
    if not isinstance(data, dict):
        return fallback
    for key in ("path", "handle", "content_ref", "section_index", "sha256", "source_kind",
                "source_id", "source_event_id", "evidence_reference", "evidence_refs"):
        if key in data:
            fallback[key] = data[key] if key in IDENTITY_FIELDS and isinstance(data[key], str) else \
                _bound_value(data[key], string_limit=80, list_limit=2)
    if data.get("execution_succeeded") is False:
        return {**fallback, "_tool_output_truncated": True, **{
            key: data[key] for key in (
                "execution_status", "execution_succeeded", "reason", "http_attempted",
                "requested_provider", "actual_provider", "fallback_occurred", "evidence_status",
                "acquisition_backend",
                "error_kind", "semantic_status", "retryable", "effective_state_id",
                "active_constraints", "authorization", "semantic_items",
                "validation_source", "policy_validation_passed", "observation_boundary",
            ) if key in data
        }, **({"error": _truncate_text(str(data["error"]), 160)} if data.get("error") else {})}
    for key in (
        "search_query",
        "search_provider",
        "requested_provider",
        "actual_provider",
        "acquisition_backend",
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
        **{key: fallback[key] for key in (
            "path", "handle", "content_ref", "section_index", "sha256", "source_kind",
            "source_id", "source_event_id", "evidence_reference", "evidence_refs",
        ) if key in fallback},
        "_tool_output_truncated": True,
        "search_provider": str(data.get("search_provider") or ""),
        "requested_provider": data.get("requested_provider"),
        "actual_provider": data.get("actual_provider"),
        "acquisition_backend": data.get("acquisition_backend"),
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
            str(key): item if key == "observation_boundary" or (key in IDENTITY_FIELDS and isinstance(item, str)) else
            _bound_value(item, string_limit=string_limit, list_limit=list_limit)
            for key, item in value.items()
        }
    return value


def _truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    suffix = "\n...[field truncated]"
    keep = max(0, max_chars - len(suffix))
    return value[:keep] + suffix
