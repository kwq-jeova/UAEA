from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from .semantic_authority import SEMANTIC_AUTHORITY_SCHEMA, has_execution_authority


ADDITIONAL_CONTEXT_APPLICATION = "application"
ADDITIONAL_CONTEXT_UNTRUSTED = "untrusted"
ADDITIONAL_CONTEXT_KINDS = frozenset(
    {ADDITIONAL_CONTEXT_APPLICATION, ADDITIONAL_CONTEXT_UNTRUSTED}
)

CODEX_SOURCE_REVISION = "rust-v0.154.0"
CODEX_SOURCE_COMMIT = "6b9826e3aa83b1a5947db50f4332cb9c65f1b340"

HARNESS_INPUT_SURFACES = (
    "turn/start.input",
    "turn/start.additionalContext",
    "turn/start.model",
    "turn/start.sandboxPolicy",
    "turn/start.cwd",
    "turn/start.approvalPolicy",
    "turn/start.responsesapiClientMetadata",
    "turn/start.outputSchema",
    "turn/steer.additionalContext",
    "dynamicToolCall.response",
)

HARNESS_OUTPUT_METHODS = (
    "turn/started",
    "turn/completed",
    "item/started",
    "item/completed",
    "rawResponseItem/completed",
    "rawResponse/completed",
    "thread/tokenUsage/updated",
    "error",
    "item/tool/call",
    "item/commandExecution/outputDelta",
    "item/commandExecution/terminalInteraction",
)

RUNTIME_FACT_MODEL_PROVIDER = "uaea_local_vllm"
RUNTIME_FACT_MODEL = "qwen25-14b-awq"


@dataclass(frozen=True)
class AdditionalContextEntry:
    """Pinned Codex app-server additionalContext entry shape."""

    value: str
    kind: str = ADDITIONAL_CONTEXT_APPLICATION

    def to_app_server(self) -> dict[str, str]:
        if self.kind not in ADDITIONAL_CONTEXT_KINDS:
            raise ValueError(f"Unsupported additionalContext kind: {self.kind}")
        return {"kind": self.kind, "value": self.value}


def application_context(value: str) -> AdditionalContextEntry:
    return AdditionalContextEntry(value=value, kind=ADDITIONAL_CONTEXT_APPLICATION)


def untrusted_context(value: str) -> AdditionalContextEntry:
    return AdditionalContextEntry(value=value, kind=ADDITIONAL_CONTEXT_UNTRUSTED)


def additional_context_payload(
    entries: Mapping[str, AdditionalContextEntry | Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    payload: dict[str, dict[str, str]] = {}
    for key, entry in entries.items():
        normalized_key = str(key)
        if not normalized_key:
            raise ValueError("additionalContext key must not be empty")
        if isinstance(entry, AdditionalContextEntry):
            payload[normalized_key] = entry.to_app_server()
            continue
        if not isinstance(entry, Mapping):
            raise ValueError(
                f"additionalContext entry for {normalized_key} must be an object"
            )
        kind = str(entry.get("kind") or "")
        value = entry.get("value")
        if not isinstance(value, str):
            raise ValueError(f"additionalContext value for {normalized_key} must be a string")
        payload[normalized_key] = AdditionalContextEntry(value=value, kind=kind).to_app_server()
    return payload


def runtime_facts_context(
    *,
    model_provider: str = RUNTIME_FACT_MODEL_PROVIDER,
    model: str = RUNTIME_FACT_MODEL,
) -> dict[str, dict[str, str]]:
    return additional_context_payload(
        {
            "uaea.runtime_facts.model": application_context(
                "Runtime fact: this Harness session is configured with "
                f"model_provider={model_provider} and model={model}. "
                "If asked what model/provider is actually running, report these "
                "runtime facts rather than relying on generic model self-description."
            ),
            "uaea.runtime_facts.execution": application_context(
                "Runtime fact: Harness native filesystem/shell execution is sandboxed "
                "read-only, and shell network access is disabled. This sandbox network "
                "restriction applies to native shell execution; it does not mean UAEA "
                "dynamic Web capabilities are unavailable."
            ),
            "uaea.runtime_facts.capabilities": application_context(
                "Runtime fact: UAEA dynamic capabilities web.search and web.fetch are "
                "available through the Harness tool-call channel. Use the tool-call "
                "channel when a web search or URL fetch is required; do not print a "
                "JSON tool-call object as the final answer."
            ),
            "uaea.runtime_facts.web_limits": application_context(
                "Runtime fact: web.search is source discovery over search results pages. "
                "Arguments include query, max_results, provider, allow_fallback, language, "
                "region, exclude_domains, preferred_domains, source_types, and freshness. "
                "Use provider for requested search provider semantics. Use preferred_domains "
                "only for result-source domain preference. When provider is set, allow_fallback "
                "must also be set explicitly; otherwise web.search returns a semantic validation "
                "failure and asks for retry with allow_fallback=true or allow_fallback=false. "
                "Constraints are preserved; runtime "
                "results report requested_provider, actual_provider, fallback_occurred, and "
                "fallback_reason. Non-provider source constraints remain best-effort. "
                "If web.search reports low_relevance, do not cite those raw results and do not "
                "repeat the same query unchanged; reformulate meaningful domain terms or report "
                "that usable evidence was not found. web.fetch fetches page-level evidence for a "
                "specific URL. Do not claim Google was used unless runtime results report Google "
                "as the actual provider."
            ),
        }
    )


def effective_capability_state(
    dynamic_tools: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    tools = {str(tool.get("name") or ""): tool for tool in dynamic_tools}
    return {
        "schema": "uaea.effective_capability_state.v0",
        "execution_planes": {
            "harness_native_shell": {
                "available": True,
                "filesystem": "read_only",
                "network": "disabled",
                "scope": "local sandbox commands only",
            },
            "uaea_dynamic_tools": {
                "available": bool(tools),
                "transport": "Harness tool-call channel",
                "tools": sorted(name for name in tools if name),
            },
        },
        "capabilities": {
            "web.search": {
                "available": "web_search" in tools,
                "tool_name": "web_search",
                "purpose": "public web source discovery for current or external information",
                "network_access": "available_through_uaea_capability",
                "evidence_level": "search_results_only",
            },
            "web.fetch": {
                "available": "web_fetch" in tools,
                "tool_name": "web_fetch",
                "purpose": "page-level evidence acquisition for a specific URL",
                "network_access": "available_through_uaea_capability",
            },
            "document.read_section": {
                "available": "read_section" in tools,
                "tool_name": "read_section",
                "purpose": "read one Markdown section from an accessible project file",
            },
            "fs.list": {
                "available": "list_files" in tools,
                "tool_name": "list_files",
                "purpose": "list files under an accessible project directory",
            },
        },
        "resolution": {
            "external_or_recent_public_information": "web.search",
            "specific_url_page_evidence": "web.fetch",
            "project_markdown_section": "document.read_section",
            "project_directory_listing": "fs.list",
        },
        "routing_rules": [
            "Resolve capability state from this object before refusing a request on sandbox grounds.",
            "Harness native shell network disabled does not disable UAEA web.search or web.fetch.",
            "For natural-language requests to 查, 查询, 搜索, look up, search, latest, recent, current, or public web information, use web.search when available.",
            "If provider is specified for web.search, include allow_fallback=true or allow_fallback=false explicitly.",
            "If a user asks for Google and forbids fallback, call web.search with provider=google and allow_fallback=false; if unsupported, report the tool's unsupported result instead of silently using another provider.",
            "If fallback is allowed and actual web.search provider differs from the requested provider, report requested_provider, actual_provider, and fallback_occurred from the tool result.",
            "Do not claim the system cannot access the web when web.search is available; only shell network is disabled.",
        ],
    }


def effective_capability_context(
    dynamic_tools: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> dict[str, dict[str, str]]:
    state = effective_capability_state(dynamic_tools)
    return additional_context_payload(
        {
            "uaea.effective_capability_state": application_context(
                json.dumps(state, ensure_ascii=False, sort_keys=True)
            )
        }
    )


def turn_context_payload(
    dynamic_tools: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    model_provider: str = RUNTIME_FACT_MODEL_PROVIDER,
    model: str = RUNTIME_FACT_MODEL,
    semantic_projection: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, str]]:
    payload = runtime_facts_context(model_provider=model_provider, model=model)
    payload.update(effective_capability_context(dynamic_tools))
    if semantic_projection is not None:
        projection = dict(semantic_projection)
        if projection.get("authority_contract") == SEMANTIC_AUTHORITY_SCHEMA:
            authority_keys = {"schema", "authority_contract", "semantic_scope_id", "task_id",
                              "effective_state_id", "constraints", "semantic_bindings"}
            authority = {key: value for key, value in projection.items() if key in authority_keys}
            context = {key: value for key, value in projection.items() if key not in authority_keys}
            bindings = projection.get("semantic_bindings") or []
            valid_bindings = [binding for binding in bindings
                              if isinstance(binding, Mapping) and has_execution_authority(binding)]
            eligible = {binding["value"] for binding in valid_bindings}
            proposed_constraints = projection.get("constraints") or []
            authority["constraints"] = [value for value in proposed_constraints if value in eligible]
            authority["semantic_bindings"] = valid_bindings
            unqualified = [value for value in proposed_constraints if value not in eligible]
            if unqualified:
                context["unqualified_constraints"] = unqualified
            context.update({"effective_state_id": projection.get("effective_state_id"),
                            "authority_level": "interpretation"})
            payload["uaea.semantic_state_projection"] = application_context(
                json.dumps(authority, ensure_ascii=False, sort_keys=True)
            ).to_app_server()
            payload["uaea.semantic_interpretations"] = untrusted_context(
                json.dumps(context, ensure_ascii=False, sort_keys=True)
            ).to_app_server()
        else:
            payload["uaea.semantic_state_projection"] = untrusted_context(
                json.dumps(projection, ensure_ascii=False, sort_keys=True)
            ).to_app_server()
    return payload


def runtime_fact_summary(
    *,
    model_provider: str = RUNTIME_FACT_MODEL_PROVIDER,
    model: str = RUNTIME_FACT_MODEL,
) -> str:
    labels = (
        f"model={model_provider}/{model}",
        "harness_shell=read-only,no-shell-network",
        "uaea_web=web.search,web.fetch available",
        "web_constraints=provider/fallback preserved,actual provider reported",
    )
    return "; ".join(labels)


def effective_capability_summary(
    dynamic_tools: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> str:
    state = effective_capability_state(dynamic_tools)
    capabilities = state["capabilities"]
    available = sorted(
        name for name, detail in capabilities.items() if isinstance(detail, dict) and detail.get("available")
    )
    shell = state["execution_planes"]["harness_native_shell"]
    return (
        f"effective_capabilities={','.join(available) or 'none'}; "
        f"harness_shell_network={shell['network']}; "
        "web_available="
        f"{capabilities['web.search']['available'] and capabilities['web.fetch']['available']}"
    )
