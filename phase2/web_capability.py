from __future__ import annotations

import hashlib

from phase2.evidence_boundary import candidate_view, temporal_facts

import sys
from contextlib import closing
from pathlib import Path
from typing import Any

from memory.sqlite_store import (
    connect,
    evidence_reference_for_web_access_event,
    get_web_access_event,
    initialize,
)
from phase2.web_adapter import WebAdapter, WebSearchConstraintError, normalize_search_constraints
from phase2.web_context import ProjectionLimits, project_web_access_events


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE1_ROOT = PROJECT_ROOT / "runtime" / "phase1-runtime"
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from runtime.capability import CapabilityMetadata, ToolResult  # noqa: E402


WEB_FETCH_CAPABILITY = "web.fetch"
WEB_FETCH_TOOL = "web_fetch"
WEB_SEARCH_CAPABILITY = "web.search"
WEB_SEARCH_TOOL = "web_search"
WEB_SEARCH_ARGUMENTS = frozenset(
    {
        "query",
        "value",
        "max_results",
        "limit",
        "provider",
        "allow_fallback",
        "language",
        "region",
        "exclude_domains",
        "preferred_domains",
        "source_types",
        "freshness", "published_from", "published_to",
    }
)


def web_fetch_metadata() -> CapabilityMetadata:
    return CapabilityMetadata(
        name=WEB_FETCH_CAPABILITY,
        tool_name=WEB_FETCH_TOOL,
        version="0.1",
        permission="network",
        produces_observation=True,
        context_cost="bounded",
        future_phase="phase-2",
    )


def web_search_metadata() -> CapabilityMetadata:
    return CapabilityMetadata(
        name=WEB_SEARCH_CAPABILITY,
        tool_name=WEB_SEARCH_TOOL,
        version="0.1",
        permission="network",
        produces_observation=True,
        context_cost="bounded",
        future_phase="phase-2",
    )


class WebFetchCapability:
    def __init__(
        self,
        *,
        db_path: Path | str,
        adapter: WebAdapter,
        projection_limits: ProjectionLimits | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.adapter = adapter
        self.projection_limits = projection_limits or ProjectionLimits()

    def __call__(self, arguments: dict[str, Any], objective: str) -> ToolResult:
        url = str(arguments.get("url") or arguments.get("value") or "").strip()
        if not url:
            return _failed_web_result(
                capability=WEB_FETCH_CAPABILITY,
                tool=WEB_FETCH_TOOL,
                message="web.fetch requires an explicit URL.",
                error="url missing",
            )

        with closing(connect(self.db_path)) as connection:
            initialize(connection)
            access_result = self.adapter.fetch_url(
                connection,
                url,
                metadata={"capability": WEB_FETCH_CAPABILITY, "objective": objective},
            )
            projection = project_web_access_events(
                connection,
                [access_result.access_event_id],
                limits=self.projection_limits,
            )
            event = get_web_access_event(connection, access_result.access_event_id)
            evidence_reference = evidence_reference_for_web_access_event(
                connection,
                access_result.access_event_id,
            ).to_dict()

        return _web_tool_result(
            capability=WEB_FETCH_CAPABILITY,
            tool=WEB_FETCH_TOOL,
            access_result=access_result,
            event=event,
            evidence_reference=evidence_reference,
            projection=projection,
            success_message=f"Fetched web source {access_result.url}",
            failure_message=f"Failed to fetch web source {access_result.url}",
        )


class WebSearchCapability:
    def __init__(
        self,
        *,
        db_path: Path | str,
        adapter: WebAdapter,
        projection_limits: ProjectionLimits | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.adapter = adapter
        self.projection_limits = projection_limits or ProjectionLimits()

    def __call__(self, arguments: dict[str, Any], objective: str) -> ToolResult:
        unknown_fields = sorted(set(arguments) - WEB_SEARCH_ARGUMENTS)
        if unknown_fields:
            return _failed_web_result(
                capability=WEB_SEARCH_CAPABILITY,
                tool=WEB_SEARCH_TOOL,
                message=f"web.search received unsupported fields: {', '.join(unknown_fields)}.",
                error="unsupported fields",
                extra_data={"unsupported_fields": unknown_fields},
            )
        query = str(arguments.get("query") or arguments.get("value") or "").strip()
        if not query:
            return _failed_web_result(
                capability=WEB_SEARCH_CAPABILITY,
                tool=WEB_SEARCH_TOOL,
                message="web.search requires an explicit query.",
                error="query missing",
            )
        try:
            max_results = self._max_results(arguments)
            constraints = normalize_search_constraints(arguments)
        except ValueError as exc:
            extra_data = exc.details if isinstance(exc, WebSearchConstraintError) else None
            return _failed_web_result(
                capability=WEB_SEARCH_CAPABILITY,
                tool=WEB_SEARCH_TOOL,
                message=f"web.search argument validation failed: {exc}",
                error=str(exc),
                extra_data=extra_data,
            )

        with closing(connect(self.db_path)) as connection:
            initialize(connection)
            access_result = self.adapter.search(
                connection,
                query,
                max_results=max_results,
                constraints=constraints,
            )
            projection = project_web_access_events(
                connection,
                [access_result.access_event_id],
                limits=self.projection_limits,
            )
            event = get_web_access_event(connection, access_result.access_event_id)
            evidence_reference = evidence_reference_for_web_access_event(
                connection,
                access_result.access_event_id,
            ).to_dict()

        event_metadata = event.get("metadata") if event else {}
        if not isinstance(event_metadata, dict):
            event_metadata = {}
        raw_search_results = _raw_search_results(event_metadata, access_result)
        candidate_search_results = [result.to_dict() for result in access_result.search_results]
        extra_data = {
            "search_query": query,
            "raw_search_result_count": int((event_metadata.get("search_transport") or {}).get(
                "backend_raw", len(raw_search_results))),
            "parsed_search_result_count": len(raw_search_results),
            "raw_search_result_domains": _result_domains(raw_search_results),
            "related_access_event_ids": list(access_result.related_access_event_ids),
            "max_results": max_results,
            "requested_constraints": constraints.to_dict(),
            "search_semantics": {
                "web.search": "source discovery and candidate acquisition from a search results page",
                "web.fetch": "page-level evidence acquisition for a specific URL",
            },
        }
        if event:
            for key in (
                "effective_query",
                "requested_provider",
                "actual_provider",
                "acquisition_backend",
                "fallback_occurred",
                "fallback_reason",
                "constraint_application",
                "provider_constraint_support",
                "search_provider",
                "evidence_relevance",
                "post_filtering",
                "execution_status",
                "publication_filter",
                "search_transport",
                "reason",
            ):
                if key == "evidence_relevance" and (access_result.status != "fetched" or not candidate_search_results):
                    continue
                if key in event_metadata:
                    extra_data[key] = event_metadata[key]
        transport = extra_data.get("search_transport")
        if transport:
            extra_data["search_transport"] = {**transport,
                "candidate_projected": len(candidate_search_results),
                "model_visible": len(candidate_search_results),
                "visibility_basis": "capability_projection_before_harness_budget"}
        if access_result.status != "fetched":
            outcome = _execution_outcome(access_result, event)
            extra_data.update(_unevaluated_evidence("execution_not_successful"))
            extra_data.update(outcome)
            return _web_tool_result(
                capability=WEB_SEARCH_CAPABILITY, tool=WEB_SEARCH_TOOL,
                access_result=access_result, event=event, evidence_reference=evidence_reference,
                projection=projection, success_message="", failure_message=outcome["failure_explanation"],
                extra_data=extra_data,
            )
        if not candidate_search_results:
            empty_reason = ("candidates_filtered_out" if raw_search_results else
                            "no_parsed_candidates" if (transport or {}).get("backend_raw") else "no_candidates")
            extra_data.update(_unevaluated_evidence(empty_reason))
            extra_data["raw_search_result_domains"] = []
            extra_data["bounded_evidence_block"] = (
                "[WEB EXECUTION RESULT]\nexecution_status: success\n"
                "evidence_evaluation: not performed; no candidates survived parsing/filtering. "
                "This is not proof that the provider returned no results."
            )
            return _web_tool_result(
                capability=WEB_SEARCH_CAPABILITY, tool=WEB_SEARCH_TOOL,
                access_result=access_result, event=event, evidence_reference=evidence_reference,
                projection=projection,
                success_message=f"Search executed; no candidates survived parsing/filtering for {query}. Check search_transport diagnostics.",
                failure_message="", extra_data=extra_data,
            )
        extra_data["access_event_id"] = access_result.access_event_id
        extra_data["accessed_at"] = event.get("accessed_at") if event else None
        eligibility = _evidence_eligibility(extra_data, candidate_search_results)
        extra_data.update(candidate_view(extra_data, candidate_search_results))
        extra_data["evidence_eligibility"] = eligibility
        extra_data["evidence_evaluation"] = {
            "performed": True, "scope": "lexical_diagnostic_only",
            "semantic_relevance_performed": False,
        }
        extra_data["search_contract"] = _search_contract(extra_data)
        return _web_tool_result(
            capability=WEB_SEARCH_CAPABILITY,
            tool=WEB_SEARCH_TOOL,
            access_result=access_result,
            event=event,
            evidence_reference=evidence_reference,
            projection=projection,
            success_message=_search_success_message(query, extra_data),
            failure_message=f"Failed to search web for {query}",
            extra_data=extra_data,
        )

    @staticmethod
    def _max_results(arguments: dict[str, Any]) -> int:
        value = arguments.get("max_results", arguments.get("limit", 5))
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise ValueError("max_results must be an integer")
        if parsed < 1 or parsed > 10:
            raise ValueError("max_results must be between 1 and 10")
        return parsed


def _web_tool_result(
    *,
    capability: str,
    tool: str,
    access_result,
    event: dict[str, Any] | None,
    evidence_reference: dict[str, Any],
    projection,
    success_message: str,
    failure_message: str,
    extra_data: dict[str, Any] | None = None,
) -> ToolResult:
    web_source_id = str(event.get("web_source_id") or "") if event else ""
    content_sha256 = str(event.get("content_sha256") or "") if event else ""
    model_visible_evidence_reference = _model_visible_evidence_reference(evidence_reference, extra_data)
    data: dict[str, Any] = {
        "capability": capability,
        "tool": tool,
        "access_event_id": access_result.access_event_id,
        "web_source_id": web_source_id,
        "url": access_result.url,
        "title": access_result.title,
        "access_status": access_result.status,
        "status": access_result.status,
        "http_status": access_result.http_status,
        "content_ref": access_result.content_ref,
        "content_sha256": content_sha256,
        "evidence_reference": model_visible_evidence_reference,
        "evidence_refs": [model_visible_evidence_reference],
        "temporal_facts": temporal_facts(event) if event else {},
        "projection_metrics": projection.metrics(),
        "bounded_evidence_block": projection.evidence_block(),
        **({"source_excerpt": {
            "source_event_id": projection.sources[0].access_event_id,
            "content_sha256": projection.sources[0].content_sha256,
            "text": projection.sources[0].projected_text,
            "text_sha256": hashlib.sha256(
                projection.sources[0].projected_text.encode("utf-8")).hexdigest(),
            "scope": "projected_page_excerpt",
        }} if capability == WEB_FETCH_CAPABILITY and projection.sources else {}),
    }
    if extra_data:
        data.update(extra_data)
    event_metadata = event.get("metadata") if event else None
    if isinstance(event_metadata, dict) and isinstance(event_metadata.get("network_diagnostics"), dict):
        data["network_diagnostics"] = event_metadata["network_diagnostics"]
    if access_result.error:
        data["error"] = access_result.error
    outcome = _execution_outcome(access_result, event)
    data.update(outcome)
    data["status"] = outcome["execution_status"]
    if capability == WEB_SEARCH_CAPABILITY and "evidence_counts" not in data:
        data["evidence_boundary"] = {
            "schema": "uaea.evidence_boundary.v1", "citation_scope": "search_result_only",
            "semantic_relevance": "unassessed", "constraints_satisfied": "not_established"}
        data["evidence_counts"] = {
            "raw": int(data.get("raw_search_result_count") or 0) if outcome["execution_succeeded"] else 0,
            "retained": 0, "visible": 0, "discovery_citable": 0, "page_content_acquired": 0}

    if isinstance(data.get("evidence_evaluation"), dict) and data["evidence_evaluation"].get("performed") is False:
        data["evidence_refs"] = []
    if not outcome["execution_succeeded"]:
        data.update(_unevaluated_evidence("execution_not_successful"))
        data["evidence_refs"] = []
        data["bounded_evidence_block"] = (
            "[WEB EXECUTION RESULT]\n"
            f"execution_status: {outcome['execution_status']}\nreason: {outcome['reason']}\n"
            f"failure_explanation: {outcome['failure_explanation']}\n"
            "evidence_evaluation: not performed; no successful execution evidence."
        )
        failure_message = outcome["failure_explanation"]
    message = success_message if access_result.status == "fetched" else failure_message
    return ToolResult(access_result.status == "fetched", message, data)


def _unevaluated_evidence(reason: str) -> dict[str, Any]:
    return {
        "evidence_status": None,
        "evidence_evaluation": {"performed": False, "reason": reason},
        "candidate_evidence_results": [], "citable_results": [], "search_results": [],
    }


def _execution_outcome(access_result, event: dict[str, Any] | None) -> dict[str, Any]:
    metadata = event.get("metadata", {}) if event else {}
    if not isinstance(metadata, dict):
        metadata = {}
    if access_result.status == "fetched":
        return {"execution_status": "success", "execution_succeeded": True,
                "http_attempted": True, "reason": None}
    status = str(metadata.get("execution_status") or (
        "unsupported" if access_result.status == "unsupported" else "network_failure"
    ))
    reason = str(metadata.get("reason") or (
        "provider_not_implemented" if status == "unsupported" else "execution_failed"
    ))
    provider = str(metadata.get("requested_provider") or "Requested")
    explanations = {
        "provider_not_implemented": f"{provider.title()} provider is not implemented in the current runtime. No HTTP request to this provider was attempted.",
        "provider_not_configured": f"{provider.title()} provider has no configured search endpoint. No search was executed.",
        "request_timeout": "The HTTP request timed out. No usable results were acquired.",
        "network_error": "The HTTP request failed because of a network error. No usable results were acquired.",
        "http_error": f"The endpoint returned HTTP {access_result.http_status}. No usable results were acquired.",
        "credential_missing": "Google search requires SERPAPI_KEY in the private runtime environment. No search was executed.",
        "credential_invalid": "The Google acquisition credential has an invalid format. No search was executed.",
        "credential_rejected": "The Google acquisition backend rejected the credential or access permission. No usable results were acquired.",
        "backend_rate_limited": "The Google acquisition backend returned a rate/quota limit. No usable results were acquired.",
        "backend_error": "The Google acquisition backend reported an execution error. No usable results were acquired.",
        "invalid_backend_response": "The Google acquisition backend did not return a valid confirmed Google SERP response.",
        "response_too_large": "The Google acquisition response exceeded the configured size limit.",
    }
    return {
        "execution_status": status, "execution_succeeded": False, "reason": reason,
        "http_attempted": bool(metadata.get("http_attempted", status != "unsupported")),
        "failure_explanation": explanations.get(reason, f"Web execution failed: {access_result.error}"),
    }


def _model_visible_evidence_reference(
    evidence_reference: dict[str, Any],
    extra_data: dict[str, Any] | None,
) -> dict[str, Any]:
    evaluation = extra_data.get("evidence_evaluation") if isinstance(extra_data, dict) else None
    if isinstance(evaluation, dict) and evaluation.get("performed") is False:
        return {**evidence_reference, "summary": (
            "No eligible search candidates were acquired; this reference is diagnostic provenance only."
        )}
    contract = extra_data.get("search_contract") if isinstance(extra_data, dict) else {}
    if not isinstance(contract, dict) or contract.get("candidate_status") != "low_relevance":
        return evidence_reference
    sanitized = dict(evidence_reference)
    sanitized["summary"] = (
        "Low-relevance raw search results were retained internally for provenance; "
        "citable_results is empty, so these raw results are not model-visible evidence."
    )
    return sanitized


def _failed_web_result(
    *,
    capability: str,
    tool: str,
    message: str,
    error: str,
    extra_data: dict[str, Any] | None = None,
) -> ToolResult:
    data = {
        "capability": capability,
        "tool": tool,
        "access_status": "failed",
        "status": "validation_failed",
        "execution_status": "validation_failed",
        "execution_succeeded": False,
        "http_attempted": False,
        "reason": "invalid_action",
        **_unevaluated_evidence("validation_not_successful"),
        "error": error,
        "validation_source": "capability_input",
        "retryable": True,
    }
    if extra_data:
        data.update(extra_data)
    if isinstance(extra_data, dict) and extra_data.get("semantic_status"):
        data.setdefault("error_kind", "semantic_validation")
        data.setdefault("retryable", True)
        data.setdefault(
            "recommended_next_action",
            "Retry the same capability with the missing semantic constraint resolved.",
        )
    return ToolResult(
        False,
        message,
        data,
    )


def _search_contract(data: dict[str, Any]) -> dict[str, Any]:
    eligibility = data.get("evidence_eligibility") if isinstance(data.get("evidence_eligibility"), dict) else {}
    candidate_status = str(eligibility.get("candidate_status") or "not_validated")
    search_results = data.get("search_results")
    candidate_count = len(search_results) if isinstance(search_results, list) else 0
    citable_results = data.get("citable_results")
    citable_count = len(citable_results) if isinstance(citable_results, list) else 0
    provider = str(data.get("search_provider") or "unknown")
    requested_provider = data.get("requested_provider")
    actual_provider = data.get("actual_provider")
    fallback_occurred = bool(data.get("fallback_occurred"))
    fallback_reason = str(data.get("fallback_reason") or "")
    return {
        "evidence_level": "search_results_only",
        "candidate_status": candidate_status,
        "candidate_result_count": candidate_count,
        "citable_result_count": citable_count,
        "raw_search_result_count": int(data.get("raw_search_result_count") or 0),
        "constraint_enforcement": "best_effort",
        "requested_provider": requested_provider,
        "actual_provider": actual_provider,
        "fallback_occurred": fallback_occurred,
        "fallback_reason": fallback_reason,
        "actual_search_provider": provider,
        "provider_truthfulness": (
            "Report requested_provider, actual_provider, fallback_occurred, and actual_search_provider from the tool result. "
            "Do not claim Google was used unless actual_provider or actual_search_provider explicitly reports Google."
        ),
        "page_evidence_requires_fetch": True,
        "citation_scope": "search_result_only",
        "semantic_relevance": "unassessed",
        "constraints_satisfied": "not_established",
        "citation_policy": (
            "Returned URLs may be shown as search hits with unverified snippets. "
            "Only use returned identities; fetch before page-level claims. "
            "Discovery citation does not verify semantic relevance or user constraints."
        ),
        "repeat_query_policy": (
            "Use lexical diagnostics as hints only. Assess returned candidates and fetch as needed. "
            "Preserve retained user requirements when reformulating; query changes do not revoke them."
        ),
        "recommended_next_action": _search_recommended_next_action(candidate_status),
    }


def _search_recommended_next_action(candidate_status: str) -> str:
    return "Assess candidate relevance and user requirements; fetch selected returned URLs before page-level claims."


def _search_success_message(query: str, data: dict[str, Any]) -> str:
    count = len(data.get("candidate_evidence_results") or [])
    return (f"Search executed using {data.get('actual_provider')} ({data.get('search_provider')}); {count} candidates retained. "
            "Lexical relevance is diagnostic only. Search-hit citations do not establish page content "
            "or satisfaction of user requirements.")


def _evidence_eligibility(data: dict[str, Any], raw_search_results: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "candidate_status": "candidates_available",
        "relevance_status": "unassessed",
        "lexical_diagnostic": (data.get("evidence_relevance") or {}).get("status"),
        "raw_search_result_count": int(data.get("raw_search_result_count", len(raw_search_results))),
        "candidate_evidence_count": len(raw_search_results),
        "citable_result_count": len(raw_search_results),
        "citation_scope": "search_result_only",
        "semantic_relevance": "unassessed",
        "raw_results_retained_in": ["web_access_event.content_ref", "web_access_event.metadata.results"],
    }


def _result_domains(results: list[dict[str, str]]) -> list[str]:
    from urllib.parse import urlparse

    domains: list[str] = []
    for result in results:
        domain = urlparse(str(result.get("url") or "")).netloc.lower().strip(".")
        if domain:
            domains.append(domain)
    return domains


def _raw_search_results(event_metadata: Any, access_result: Any) -> list[dict[str, str]]:
    if isinstance(event_metadata, dict):
        raw = event_metadata.get("raw_results_before_filtering")
        if isinstance(raw, list):
            return [dict(item) for item in raw if isinstance(item, dict)]
    return [result.to_dict() for result in access_result.search_results]
