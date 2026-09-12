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
from phase2.web_adapter import WebAdapter
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
        query = str(arguments.get("query") or arguments.get("value") or "").strip()
        if not query:
            return _failed_web_result(
                capability=WEB_SEARCH_CAPABILITY,
                tool=WEB_SEARCH_TOOL,
                message="web.search requires an explicit query.",
                error="query missing",
            )
        max_results = self._max_results(arguments)

        with closing(connect(self.db_path)) as connection:
            initialize(connection)
            access_result = self.adapter.search(connection, query, max_results=max_results)
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

        extra_data = {
            "search_query": query,
            "search_results": [result.to_dict() for result in access_result.search_results],
            "related_access_event_ids": list(access_result.related_access_event_ids),
            "max_results": max_results,
        }
        return _web_tool_result(
            capability=WEB_SEARCH_CAPABILITY,
            tool=WEB_SEARCH_TOOL,
            access_result=access_result,
            event=event,
            evidence_reference=evidence_reference,
            projection=projection,
            success_message=f"Searched web for {query}",
            failure_message=f"Failed to search web for {query}",
            extra_data=extra_data,
        )

    @staticmethod
    def _max_results(arguments: dict[str, Any]) -> int:
        value = arguments.get("max_results", arguments.get("limit", 5))
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return 5
        return max(1, min(parsed, 10))


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
    data: dict[str, Any] = {
        "capability": capability,
        "tool": tool,
        "access_event_id": access_result.access_event_id,
        "web_source_id": web_source_id,
        "url": access_result.url,
        "title": access_result.title,
        "access_status": access_result.status,
        "http_status": access_result.http_status,
        "content_ref": access_result.content_ref,
        "content_sha256": content_sha256,
        "evidence_reference": evidence_reference,
        "evidence_refs": [evidence_reference],
        "projection_metrics": projection.metrics(),
        "bounded_evidence_block": projection.evidence_block(),
    }
    if extra_data:
        data.update(extra_data)
    if access_result.error:
        data["error"] = access_result.error
    message = success_message if access_result.status == "fetched" else failure_message
    return ToolResult(access_result.status == "fetched", message, data)


def _failed_web_result(*, capability: str, tool: str, message: str, error: str) -> ToolResult:
    return ToolResult(
        False,
        message,
        {
            "capability": capability,
            "tool": tool,
            "access_status": "failed",
            "error": error,
        },
    )
