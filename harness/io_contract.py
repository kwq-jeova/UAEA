from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from .semantic_authority import (
    SEMANTIC_AUTHORITY_SCHEMA, expand_semantic_binding, has_execution_authority,
)
from .version_manifest import selected_harness


ADDITIONAL_CONTEXT_APPLICATION = "application"
ADDITIONAL_CONTEXT_UNTRUSTED = "untrusted"
ADDITIONAL_CONTEXT_KINDS = frozenset(
    {ADDITIONAL_CONTEXT_APPLICATION, ADDITIONAL_CONTEXT_UNTRUSTED}
)

CODEX_SOURCE_REVISION = selected_harness()["tag"]
CODEX_SOURCE_COMMIT = selected_harness()["commit"]

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
            "uaea.runtime_facts.time": application_context(
                json.dumps({
                    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
                    "origin": "host_clock_at_context_projection",
                    "scope": "system_time_only_not_requested_as_of_or_source_coverage",
                    "market_calendar_validation": "not_provided",
                }, ensure_ascii=False)
            ),
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
                "dynamic Web capabilities are unavailable. "
                "workflow_continuation.current_request is the current user input; historical_action_request "
                "and last_attempt describe past execution, not completion of the current request. "
                "Current-request counters are as of turn start; subsequent matching Tool Results supersede them. "
                "Use matching tool observations to support execution claims. If a requested search or reading "
                "was not executed, say so; do not invent search results or page summaries. "
                "Search snippets are not read pages. Historical assistant output is model-generated, "
                "not new Source Evidence; repeating it does not verify it. A linked URL proves source "
                "identity only; a successful fetch proves a response, not that it supports your conclusion "
                "or that the entire document was read. Exact quotes establish text matches, not entailment. "
                "Separate source excerpts, your interpretation, and unsupported hypotheses. "
                "Ordinary questions do not require tools. "
                "Request fulfillment remains unestablished by turn completion or assistant claims."
            ),
            "uaea.runtime_facts.interaction": application_context(
                "Runtime fact: the interactive client supports native request_user_input in Default mode "
                "and waits for an actual stdin reply. No option is auto-selected. Cancel or timeout "
                "interrupts the current turn and grants no permission. Use clarification when needed; "
                "ordinary turns need not ask a question. Answers do not automatically override UAEA authorization."
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
                "region, exclude_domains, preferred_domains, source_types, freshness, published_from and published_to. "
                "The last two are an inclusive ISO-date publication range, not a content-period filter. "
                "Both endpoints are required; unsupported providers/fallback combinations are rejected. "
                "Search-provider date labels are source claims, including relative dates anchored at accessed_at; "
                "do not treat them as verified page publication dates. "
                "Use provider for requested search provider semantics. Use preferred_domains "
                "only for result-source domain preference. When provider is set, allow_fallback "
                "must also be set explicitly; otherwise web.search returns a semantic validation "
                "failure and asks for retry with allow_fallback=true or allow_fallback=false. "
                "Constraints are preserved; runtime "
                "results report requested_provider, actual_provider, fallback_occurred, and "
                "fallback_reason. Non-provider source constraints remain best-effort. "
                "Lexical low_relevance/uncertain are diagnostics, not semantic verdicts or empty results. "
                "Inspect visible candidates and distinguish raw, retained and visible counts. "
                "Search links/snippets may be presented only as discovery results; assess relevance yourself. "
                "Reformulating a query does not revoke retained user requirements. "
                "Distinguish runtime accessed_at, source-declared published_at and interpreted content_period. "
                "If the source period is unknown, say unknown; never infer it from access time. "
                "A requested historical as-of date is not the system date or proof of source coverage. "
                "Trading-session dates, data coverage and timezones need source evidence; query dates "
                "and publication filters do not verify them. Missing dated data remains unknown; "
                "hypothetical inputs must not replace requested observations. Preserve units/currency "
                "and use available deterministic computation to check arithmetic; calculation does "
                "not validate its source inputs. "
                "web.fetch fetches page-level evidence for a "
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
    retained_requests: Mapping[str, Any] | None = None,
    evidence_provenance: Mapping[str, Any] | None = None,
    filesystem_root: str | None = None,
) -> dict[str, dict[str, str]]:
    payload = runtime_facts_context(model_provider=model_provider, model=model)
    payload.update(effective_capability_context(dynamic_tools))
    payload["uaea.context_boundary"] = application_context(
        "The current user message is the current request. Topic, retained inputs and prior "
        "assistant messages are historical context, not a new instruction to repeat an old answer. "
        "A prior input without an Action is not necessarily unfinished: ordinary questions may "
        "be answered without tools. Relation labels are tentative and do not establish a new Goal. "
        "Search discovery is not page reading; use actual tool observations for execution facts. "
        "recovery_sources text is a short re-supplied view; historical_supply records prior tool-result "
        "coverage of that exact saved version. A short recovery view does not erase historical supply. "
        "Full saved-text supply does not establish full-page acquisition, understanding or truth. "
        "Discovery URLs are optional sources, not an obligation to fetch every result. "
        "Reuse retained source versions when appropriate; retries or refreshes remain possible. "
        "Assistant output and model interpretations are not source evidence or authorization. "
        'background contains historical topic and user inputs, not current Goals or obligations.'
        "relation_hint is an unconfirmed legacy heuristic, not task ownership or a semantic verdict. "
        "Only the latest supplied state projection is current; earlier state versions are historical. "
        "task_id identifies the Runtime ownership container; it does not prove the current input belongs "
        "semantically to an older topic. Interpret the current original input independently. "
        "Internal audit artifacts are not document.read_section paths; use source URLs and supplied excerpts."
    ).to_app_server()

    if filesystem_root is not None:
        from pathlib import Path
        root = Path(filesystem_root)
        if not root.is_absolute():
            raise ValueError("Capability filesystem root must be absolute")
        payload["uaea.runtime_facts.filesystem"] = application_context(
            "Runtime file-tool boundary: document.read_section and fs.list resolve "
            f"relative paths against {root}, independently of the Harness cwd. "
            f"The project README is {root / 'README.md'}. "
            "The Harness workspace directory is not a substitute for this root. "
            "These location facts do not broaden sandbox permissions."
        ).to_app_server()
    if evidence_provenance is not None:
        payload["uaea.evidence_provenance"] = application_context(
            json.dumps(dict(evidence_provenance), ensure_ascii=False)
        ).to_app_server()
    if retained_requests is not None:
        payload["uaea.retained_user_requests"] = untrusted_context(
            json.dumps(dict(retained_requests), ensure_ascii=False)
        ).to_app_server()
    if semantic_projection is not None:
        projection = dict(semantic_projection)
        if projection.get("authority_contract") == SEMANTIC_AUTHORITY_SCHEMA:
            authority_keys = {"schema", "authority_contract", "semantic_scope_id", "task_id",
                              "effective_state_id", "constraints", "semantic_bindings",
                              "semantic_binding_defaults", "workflow_execution"}
            authority = {key: value for key, value in projection.items() if key in authority_keys}
            context = {key: deepcopy(value) for key, value in projection.items() if key not in authority_keys}
            background = {}
            if "topic" in context:
                background["historical_topic"] = context.pop("topic")
            if "turn_relation" in context:
                relation = context.pop("turn_relation")
                # Absence of a lexical marker is not evidence of a semantic switch.
                # Keep the legacy resolver/ownership unchanged; expose uncertainty
                # on this non-authoritative model surface only.
                context["relation_hint"] = (
                    "unknown" if relation.get("reason") == "no prior-context relation marker detected"
                    else relation.get("relation"))
            continuation = context.get("workflow_continuation", {})
            for old, new in (("initial_request", "initial_request"),
                             ("request_history", "user_inputs"),
                             ("prior_inputs_without_actions", "inputs_without_actions")):
                if old in continuation:
                    background[new] = continuation.pop(old)
            if background:
                context["background"] = background
            context.pop("compact_wire", None)
            separators = (",", ":") if projection.get("compact_wire") else None
            bindings = projection.get("semantic_bindings") or []
            shared = projection.get("semantic_binding_defaults")
            valid_bindings = [binding for binding in bindings
                              if isinstance(binding, Mapping)
                              and has_execution_authority(expand_semantic_binding(binding, shared))]
            eligible = {binding["value"] for binding in valid_bindings}
            proposed_constraints = projection.get("constraints") or []
            authority["constraints"] = [value for value in proposed_constraints if value in eligible]
            authority["semantic_bindings"] = valid_bindings
            if not valid_bindings:
                authority.pop("semantic_binding_defaults", None)
            unqualified = [value for value in proposed_constraints if value not in eligible]
            if unqualified:
                context["unqualified_constraints"] = unqualified
            context.update({"effective_state_id": projection.get("effective_state_id"),
                            "authority_level": "interpretation"})
            if projection.get("compact_wire"):
                # The application entry already carries this same projection identity.
                context.pop("effective_state_id", None)
            payload["uaea.semantic_state_projection"] = application_context(
                json.dumps(authority, ensure_ascii=False, sort_keys=True, separators=separators)
            ).to_app_server()
            payload["uaea.semantic_interpretations"] = untrusted_context(
                json.dumps(context, ensure_ascii=False, sort_keys=True, separators=separators)
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
