from __future__ import annotations

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
        "freshness",
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
        extra_data = {
            "search_query": query,
            "raw_search_result_count": len(raw_search_results),
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
                "fallback_occurred",
                "fallback_reason",
                "constraint_application",
                "provider_constraint_support",
                "search_provider",
                "evidence_relevance",
                "post_filtering",
            ):
                if key in event_metadata:
                    extra_data[key] = event_metadata[key]
        eligibility = _evidence_eligibility(extra_data, raw_search_results)
        if eligibility["candidate_status"] == "low_relevance":
            extra_data["raw_search_result_domains"] = []
        candidate_results = _eligible_results(raw_search_results, eligibility["candidate_status"])
        citable_results = _citable_results(raw_search_results, eligibility["candidate_status"])
        extra_data.update(
            {
                "evidence_eligibility": eligibility,
                "candidate_evidence_results": candidate_results,
                "citable_results": citable_results,
                "search_results": candidate_results,
            }
        )
        extra_data["search_contract"] = _search_contract(extra_data)
        if eligibility["candidate_status"] == "low_relevance":
            extra_data["bounded_evidence_block"] = _low_relevance_evidence_block(query, extra_data)
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
        "projection_metrics": projection.metrics(),
        "bounded_evidence_block": projection.evidence_block(),
    }
    if extra_data:
        data.update(extra_data)
    if access_result.error:
        data["error"] = access_result.error
    message = success_message if access_result.status == "fetched" else failure_message
    return ToolResult(access_result.status == "fetched", message, data)


def _model_visible_evidence_reference(
    evidence_reference: dict[str, Any],
    extra_data: dict[str, Any] | None,
) -> dict[str, Any]:
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
        "error": error,
    }
    if extra_data:
        data.update(extra_data)
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
        "page_evidence_requires_fetch": candidate_status != "low_relevance",
        "citation_policy": (
            "Only cite URLs present in citable_results or later web.fetch results. "
            "Do not invent, assume, or cite preferred-domain URLs that are absent from returned evidence."
        ),
        "repeat_query_policy": (
            "After low_relevance, do not repeat the same query unchanged. "
            "Reformulate meaningful domain terms before searching again, or report that evidence was not found."
        ),
        "recommended_next_action": _search_recommended_next_action(candidate_status),
    }


def _search_recommended_next_action(candidate_status: str) -> str:
    if candidate_status == "low_relevance":
        return "Revise the search query with different domain terms; do not repeat the same query unchanged."
    if candidate_status == "uncertain":
        return "Do not list or cite URLs yet; revise the query or fetch a returned candidate before making page-level claims."
    if candidate_status == "constraints_partially_satisfied":
        return "State that provider constraints were only partially satisfied; fetch only returned URLs that are relevant."
    if candidate_status == "relevant":
        return "Use web.fetch on selected returned URLs before making page-level claims."
    return "Do not cite results until evidence eligibility is established."


def _search_success_message(query: str, data: dict[str, Any]) -> str:
    contract = data.get("search_contract") if isinstance(data.get("search_contract"), dict) else {}
    candidate_status = str(contract.get("candidate_status") or "")
    provider = str(data.get("search_provider") or "unknown")
    fallback = " with fallback" if data.get("fallback_occurred") else ""
    if candidate_status == "low_relevance":
        return (
            f"Actual provider {provider}{fallback} returned low-relevance candidate results for {query}; "
            "do not cite, do not call this Google, and do not repeat the same query unchanged."
        )
    if candidate_status == "uncertain":
        return (
            f"Actual provider {provider}{fallback} returned uncertain candidate evidence for {query}; "
            "citable_results is empty, so do not list or invent URLs and do not call this Google."
        )
    if candidate_status == "constraints_partially_satisfied":
        return f"Actual provider {provider}{fallback} returned partially constraint-satisfied candidates for {query}; do not call this Google."
    return f"Actual provider {provider}{fallback} searched web for {query}."


def _evidence_eligibility(data: dict[str, Any], raw_search_results: list[dict[str, str]]) -> dict[str, Any]:
    relevance = data.get("evidence_relevance") if isinstance(data.get("evidence_relevance"), dict) else {}
    post_filtering = data.get("post_filtering") if isinstance(data.get("post_filtering"), dict) else {}
    relevance_status = str(relevance.get("status") or "not_validated")
    preferred_missing = bool(post_filtering.get("preferred_domain_missing"))
    if not raw_search_results or relevance_status == "low_relevance":
        candidate_status = "low_relevance"
    elif relevance_status == "relevant" and preferred_missing:
        candidate_status = "constraints_partially_satisfied"
    elif relevance_status == "relevant":
        candidate_status = "relevant"
    elif relevance_status == "uncertain":
        candidate_status = "uncertain"
    else:
        candidate_status = "uncertain"
    return {
        "candidate_status": candidate_status,
        "relevance_status": relevance_status,
        "raw_search_result_count": len(raw_search_results),
        "candidate_evidence_count": len(_eligible_results(raw_search_results, candidate_status)),
        "citable_result_count": len(_citable_results(raw_search_results, candidate_status)),
        "raw_results_retained_in": [
            "web_access_event.content_ref",
            "web_access_event.metadata.results",
            "trajectory.raw_event",
        ],
    }


def _eligible_results(raw_search_results: list[dict[str, str]], candidate_status: str) -> list[dict[str, Any]]:
    if candidate_status == "low_relevance":
        return []
    return [
        {
            **result,
            "evidence_eligibility": candidate_status,
            "citable": candidate_status == "relevant",
        }
        for result in raw_search_results
    ]


def _citable_results(raw_search_results: list[dict[str, str]], candidate_status: str) -> list[dict[str, Any]]:
    if candidate_status != "relevant":
        return []
    return [
        {
            **result,
            "evidence_eligibility": "relevant",
            "citable": True,
        }
        for result in raw_search_results
    ]


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


def _low_relevance_evidence_block(query: str, data: dict[str, Any]) -> str:
    provider = str(data.get("search_provider") or "unknown")
    requested_provider = data.get("requested_provider") or "none"
    actual_provider = data.get("actual_provider") or "none"
    relevance = data.get("evidence_relevance") if isinstance(data.get("evidence_relevance"), dict) else {}
    matched = ", ".join(str(item) for item in relevance.get("matched_terms") or []) or "none"
    domains = ", ".join(str(item) for item in data.get("raw_search_result_domains") or []) or "none"
    return "\n".join(
        [
            "[WEB SEARCH RESULT CONTRACT]",
            f"query: {query}",
            f"requested_provider: {requested_provider}",
            f"actual_provider: {actual_provider}",
            f"fallback_occurred: {bool(data.get('fallback_occurred'))}",
            f"actual_search_provider: {provider}",
            "candidate_status: low_relevance",
            "citable_results: 0",
            "candidate_evidence_results: 0",
            f"raw_search_result_count: {data.get('raw_search_result_count') or 0}",
            f"raw_result_domains: {domains}",
            f"matched_terms: {matched}",
            "action: revise_query",
            "citation_policy: do not cite these raw search results as evidence.",
            "raw_results_retained_in: web_access_event.content_ref, web_access_event.metadata.results, trajectory.raw_event",
        ]
    )
