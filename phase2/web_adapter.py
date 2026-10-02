from __future__ import annotations

import hashlib
import base64
import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from uuid import uuid4

from memory.sqlite_store import insert_web_access_event
from phase2.serpapi_backend import SERPAPI_ENDPOINT, SerpApiFailure, google_search
from phase2.network_observability import NetworkObservation, observe_open, observe_read


DEFAULT_USER_AGENT = "UAEA-Phase2-WebAdapter/0.1"
DEFAULT_SEARCH_URL_TEMPLATES = (
    "https://duckduckgo.com/html/?q={query}",
    "https://www.bing.com/search?q={query}",
)
SUPPORTED_SEARCH_PROVIDERS = frozenset({"duckduckgo", "bing", "google"})
SEARCH_PROVIDER_ALIASES = {
    "ddg": "duckduckgo",
    "duckduckgo": "duckduckgo",
    "duckduckgo.com": "duckduckgo",
    "bing": "bing",
    "bing.com": "bing",
    "www.bing.com": "bing",
    "google": "google",
    "google.com": "google",
    "www.google.com": "google",
}
SUPPORTED_SOURCE_TYPES = frozenset({"academic", "forum", "news", "documentation", "general"})
SUPPORTED_FRESHNESS = frozenset({"day", "week", "month", "year", "recent", "any"})
PROVIDER_CONSTRAINT_SUPPORT = {
    "www.google.com": {
        "language": "partial_hl_and_lr",
        "region": "partial_gl",
        "exclude_domains": "best_effort_query_shaping_and_post_filter",
        "preferred_domains": "best_effort_query_shaping",
        "source_types": "best_effort_query_shaping",
        "freshness": "best_effort_query_shaping",
    },
    "duckduckgo.com": {
        "language": "partial",
        "region": "partial",
        "exclude_domains": "best_effort_query_shaping_and_post_filter",
        "preferred_domains": "best_effort_query_shaping",
        "source_types": "best_effort_query_shaping",
        "freshness": "unsupported",
    },
    "www.bing.com": {
        "language": "partial",
        "region": "partial",
        "exclude_domains": "best_effort_query_shaping_and_post_filter",
        "preferred_domains": "best_effort_query_shaping",
        "source_types": "best_effort_query_shaping",
        "freshness": "unsupported",
    },
}


class WebSearchConstraintError(ValueError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


@dataclass(frozen=True)
class WebSearchConstraints:
    provider: str = ""
    allow_fallback: bool = True
    allow_fallback_specified: bool = field(default=False, compare=False)
    language: str = ""
    region: str = ""
    exclude_domains: tuple[str, ...] = field(default_factory=tuple)
    preferred_domains: tuple[str, ...] = field(default_factory=tuple)
    source_types: tuple[str, ...] = field(default_factory=tuple)
    freshness: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "allow_fallback": self.allow_fallback,
            "language": self.language,
            "region": self.region,
            "exclude_domains": list(self.exclude_domains),
            "preferred_domains": list(self.preferred_domains),
            "source_types": list(self.source_types),
            "freshness": self.freshness,
        }


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


@dataclass(frozen=True)
class WebAccessResult:
    access_event_id: str
    url: str
    status: str
    http_status: int | None
    content_ref: str
    title: str
    error: str = ""
    search_results: tuple[WebSearchResult, ...] = field(default_factory=tuple)
    related_access_event_ids: tuple[str, ...] = field(default_factory=tuple)


class WebAdapter:
    def __init__(
        self,
        *,
        snapshot_root: Path | str,
        timeout_seconds: int = 20,
        user_agent: str = DEFAULT_USER_AGENT,
        max_snapshot_bytes: int = 2_000_000,
        search_url_template: str | None = None,
        search_url_templates: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        self.snapshot_root = Path(snapshot_root)
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.max_snapshot_bytes = max_snapshot_bytes
        if search_url_templates is not None:
            self.search_url_templates = tuple(str(template) for template in search_url_templates if str(template).strip())
        elif search_url_template is not None:
            self.search_url_templates = (search_url_template,)
        else:
            self.search_url_templates = DEFAULT_SEARCH_URL_TEMPLATES
        if not self.search_url_templates:
            raise ValueError("at least one search URL template is required")
        self.search_url_template = self.search_url_templates[0]

    def fetch_url(
        self,
        connection: sqlite3.Connection,
        url: str,
        *,
        source_type: str = "web_page",
        metadata: dict[str, Any] | None = None,
    ) -> WebAccessResult:
        normalized_url = _normalize_url(url)
        access_event_id = f"WEB-LIVE-{uuid4()}"
        accessed_at = _utc_now()
        started_at = time.monotonic()
        base_metadata = dict(metadata or {})
        base_metadata.update({"adapter": "phase2.web_adapter", "requested_url": normalized_url})
        network = NetworkObservation(normalized_url)
        base_metadata["network_diagnostics"] = network.data
        try:
            with network:
                response_payload = self._http_get(normalized_url)
        except urllib.error.HTTPError as exc:
            return self._record_failure(
                connection,
                access_event_id=access_event_id,
                url=normalized_url,
                accessed_at=accessed_at,
                http_status=exc.code,
                error=f"HTTP {exc.code}: {exc.reason}",
                metadata={**base_metadata, "execution_status": "http_failure", "reason": "http_error",
                          "latency_ms": round((time.monotonic() - started_at) * 1000, 3)},
                source_type=source_type,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            timed_out = isinstance(exc, TimeoutError) or (
                isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, TimeoutError)
            )
            return self._record_failure(
                connection,
                access_event_id=access_event_id,
                url=normalized_url,
                accessed_at=accessed_at,
                http_status=None,
                error=str(exc),
                metadata={**base_metadata, "execution_status": "timeout" if timed_out else "network_failure",
                          "reason": "request_timeout" if timed_out else "network_error",
                          "latency_ms": round((time.monotonic() - started_at) * 1000, 3)},
                source_type=source_type,
            )

        body = response_payload["body"]
        content_type = response_payload["content_type"]
        truncated = len(body) > self.max_snapshot_bytes
        stored_body = body[: self.max_snapshot_bytes]
        title = _extract_title(stored_body, content_type=content_type) or normalized_url
        content_ref = str(self._write_snapshot(access_event_id, normalized_url, stored_body, content_type))
        excerpt = _plain_text_excerpt(stored_body, content_type=content_type)
        event = {
            "access_event_id": access_event_id,
            "url": normalized_url,
            "title": title,
            "domain": urllib.parse.urlparse(normalized_url).netloc,
            "accessed_at": accessed_at,
            "access_status": "fetched",
            "source_type": source_type,
            "source_provenance": "external",
            "http_status": response_payload["status"],
            "content_ref": content_ref,
            "excerpt": excerpt,
            "metadata": {
                **base_metadata,
                "content_type": content_type,
                "latency_ms": round((time.monotonic() - started_at) * 1000, 3),
                "snapshot_truncated": truncated,
            },
        }
        insert_web_access_event(connection, event)
        connection.commit()
        return WebAccessResult(
            access_event_id=access_event_id,
            url=normalized_url,
            status="fetched",
            http_status=response_payload["status"],
            content_ref=content_ref,
            title=title,
        )

    def search(
        self,
        connection: sqlite3.Connection,
        query: str,
        *,
        max_results: int = 5,
        constraints: WebSearchConstraints | None = None,
    ) -> WebAccessResult:
        clean_query = _safe_single_line_text(query)
        if not clean_query:
            raise ValueError("search query missing")
        search_constraints = constraints or WebSearchConstraints()
        effective_query = _shape_search_query(clean_query, search_constraints)
        attempt_event_ids: list[str] = []
        if search_constraints.provider == "google":
            google_result = self._search_google(connection, clean_query, effective_query, max_results, search_constraints)
            if google_result.search_results or not search_constraints.allow_fallback:
                return google_result
            attempt_event_ids.append(google_result.access_event_id)
            template_plan = {"status": "ok", "templates": self.search_url_templates,
                             "fallback_occurred": True,
                             "fallback_reason": google_result.error or "Google returned no eligible candidates"}
        else:
            template_plan = self._search_template_plan(search_constraints)
        if template_plan["status"] == "unsupported":
            return self._record_unsupported_search_provider(
                connection,
                query=clean_query,
                effective_query=effective_query,
                constraints=search_constraints,
                reason=str(template_plan["fallback_reason"]),
            )
        last_result: WebAccessResult | None = None
        templates = list(template_plan["templates"])
        for attempt_index, template in enumerate(templates, start=1):
            search_url = _search_url_for_template(template, effective_query, search_constraints)
            provider = self._search_provider_name(search_url)
            actual_provider = self._actual_provider_name(search_url)
            result = self.fetch_url(
                connection,
                search_url,
                source_type="web_search_results",
                metadata={
                    "query": clean_query,
                    "effective_query": effective_query,
                    "requested_constraints": search_constraints.to_dict(),
                    "requested_provider": search_constraints.provider or None,
                    "actual_provider": actual_provider,
                    "fallback_occurred": bool(template_plan["fallback_occurred"]),
                    "fallback_reason": str(template_plan["fallback_reason"]),
                    "constraint_application": _constraint_application_metadata(search_constraints),
                    "search_provider": provider,
                    "provider_constraint_support": _provider_constraint_support(provider),
                    "search_attempt_index": attempt_index,
                    "search_attempt_count": len(templates),
                },
            )
            attempt_event_ids.append(result.access_event_id)
            last_result = result
            if result.status != "fetched":
                self._mark_search_attempt(
                    connection,
                    result.access_event_id,
                    clean_query,
                    (),
                    parse_status="fetch_failed",
                    fallback_reason=result.error,
                )
                continue
            search_results = self._parse_search_result_event(
                connection,
                result.access_event_id,
                clean_query,
                max_results,
                constraints=search_constraints,
            )
            if search_results:
                return WebAccessResult(
                    access_event_id=result.access_event_id,
                    url=result.url,
                    status=result.status,
                    http_status=result.http_status,
                    content_ref=result.content_ref,
                    title=result.title,
                    error=result.error,
                    search_results=search_results,
                    related_access_event_ids=tuple(attempt_event_ids),
                )
        if last_result is None:
            raise RuntimeError("search did not produce an attempt")
        return WebAccessResult(
            access_event_id=last_result.access_event_id,
            url=last_result.url,
            status=last_result.status,
            http_status=last_result.http_status,
            content_ref=last_result.content_ref,
            title=last_result.title,
            error=last_result.error,
            search_results=(),
            related_access_event_ids=tuple(attempt_event_ids),
        )

    def _parse_search_result_event(
        self,
        connection: sqlite3.Connection,
        access_event_id: str,
        clean_query: str,
        max_results: int,
        *,
        constraints: WebSearchConstraints | None = None,
    ) -> tuple[WebSearchResult, ...]:
        event_row = connection.execute(
            "SELECT metadata_json, content_ref FROM web_access_events WHERE access_event_id = ?",
            (access_event_id,),
        ).fetchone()
        if event_row is None:
            return ()
        snapshot = Path(str(event_row["content_ref"]))
        body = snapshot.read_text(encoding="utf-8", errors="replace") if snapshot.is_file() else ""
        search_constraints = constraints or WebSearchConstraints()
        event_metadata = json.loads(str(event_row["metadata_json"]))
        if event_metadata.get("acquisition_backend") == "serpapi":
            parsed_results = tuple(_parse_google_search_results(json.loads(body)))
        else:
            parsed_results = tuple(_parse_search_results(body, max_results=max_results * 3))
        search_results = _apply_result_constraints(parsed_results, search_constraints, max_results=max_results)
        parse_status = "parsed" if search_results else "no_parsed_results"
        self._mark_search_attempt(
            connection,
            access_event_id,
            clean_query,
            search_results,
            parse_status=parse_status,
            parsed_result_count=len(parsed_results),
            raw_search_results=parsed_results,
            constraints=search_constraints,
        )
        return search_results

    def _mark_search_attempt(
        self,
        connection: sqlite3.Connection,
        access_event_id: str,
        clean_query: str,
        search_results: tuple[WebSearchResult, ...],
        *,
        parse_status: str,
        fallback_reason: str = "",
        parsed_result_count: int | None = None,
        raw_search_results: tuple[WebSearchResult, ...] | None = None,
        constraints: WebSearchConstraints | None = None,
    ) -> None:
        event_row = connection.execute(
            "SELECT metadata_json FROM web_access_events WHERE access_event_id = ?",
            (access_event_id,),
        ).fetchone()
        if event_row is None:
            return
        import json

        excerpt = _format_search_results(clean_query, search_results)
        metadata_payload = json.loads(str(event_row["metadata_json"]))
        metadata_payload["result_count"] = len(search_results)
        metadata_payload["results"] = [item.to_dict() for item in search_results]
        metadata_payload["search_parse_status"] = parse_status
        if parsed_result_count is not None:
            metadata_payload["parsed_result_count_before_filtering"] = parsed_result_count
        if raw_search_results is not None:
            metadata_payload["raw_results_before_filtering"] = [item.to_dict() for item in raw_search_results]
        if parse_status != "fetch_failed" and search_results:
            metadata_payload["evidence_relevance"] = _assess_search_relevance(clean_query, search_results)
        if constraints is not None:
            metadata_payload["post_filtering"] = _post_filtering_metadata(parsed_result_count or len(search_results), search_results, constraints)
        if fallback_reason:
            metadata_payload["fallback_reason"] = fallback_reason
        connection.execute(
            """
            UPDATE web_access_events
            SET excerpt = ?,
                metadata_json = ?
            WHERE access_event_id = ?
            """,
            (
                excerpt,
                json.dumps(metadata_payload, ensure_ascii=False, sort_keys=True),
                access_event_id,
            ),
        )
        connection.commit()

    def _search_google(self, connection: sqlite3.Connection, query: str, effective_query: str,
                       max_results: int, constraints: WebSearchConstraints) -> WebAccessResult:
        parameters: dict[str, Any] = {"q": effective_query, "num": max_results}
        if constraints.language:
            language = constraints.language.split("-")[0]
            parameters.update({"hl": language, "lr": f"lang_{language}"})
        if constraints.region:
            parameters["gl"] = constraints.region.split("-")[0]
        provenance_url = "https://www.google.com/search?" + urllib.parse.urlencode(parameters)
        access_event_id = f"WEB-LIVE-{uuid4()}"
        accessed_at = _utc_now()
        metadata: dict[str, Any] = {
            "adapter": "phase2.web_adapter", "query": query, "effective_query": effective_query,
            "requested_constraints": constraints.to_dict(), "requested_provider": "google",
            "actual_provider": None, "search_provider": None,
            "acquisition_backend": "serpapi", "acquisition_endpoint": SERPAPI_ENDPOINT,
            "fallback_occurred": False, "fallback_reason": "",
            "constraint_application": _constraint_application_metadata(constraints),
            "provider_constraint_support": _provider_constraint_support("www.google.com"),
            "search_attempt_index": 1,
        }
        started_at = time.monotonic()
        network = NetworkObservation(SERPAPI_ENDPOINT)
        metadata["network_diagnostics"] = network.data
        try:
            with network:
                payload = google_search(parameters, timeout=self.timeout_seconds,
                                        max_bytes=self.max_snapshot_bytes, user_agent=self.user_agent)
        except SerpApiFailure as exc:
            metadata.update({"execution_status": exc.status, "reason": exc.reason,
                             "http_attempted": exc.http_attempted,
                             "latency_ms": round((time.monotonic() - started_at) * 1000, 3)})
            failure = self._record_failure(
                connection, access_event_id=access_event_id, url=provenance_url,
                accessed_at=accessed_at, http_status=exc.http_status, error=exc.reason,
                metadata=metadata, source_type="web_search_results",
            )
            return replace(failure, related_access_event_ids=(access_event_id,))
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        content_ref = str(self._write_snapshot(access_event_id, provenance_url, body, "application/json"))
        metadata.update({"actual_provider": "google", "search_provider": "www.google.com",
                         "execution_status": "success", "http_attempted": True,
                         "content_type": "application/json", "snapshot_truncated": False,
                         "latency_ms": round((time.monotonic() - started_at) * 1000, 3)})
        title = f"Google search: {query}"
        insert_web_access_event(connection, {
            "access_event_id": access_event_id, "url": provenance_url, "title": title,
            "domain": "www.google.com", "accessed_at": accessed_at, "access_status": "fetched",
            "source_type": "web_search_results", "source_provenance": "external",
            "http_status": 200, "content_ref": content_ref, "excerpt": "", "metadata": metadata,
        })
        connection.commit()
        results = self._parse_search_result_event(connection, access_event_id, query, max_results,
                                                 constraints=constraints)
        return WebAccessResult(access_event_id, provenance_url, "fetched", 200, content_ref, title,
                               search_results=results, related_access_event_ids=(access_event_id,))

    def _http_get(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with observe_open(urllib.request.urlopen, request, timeout=self.timeout_seconds) as response:
            body = observe_read(response, self.max_snapshot_bytes + 1)
            return {
                "status": int(getattr(response, "status", 200)),
                "content_type": str(response.headers.get("Content-Type") or ""),
                "body": body,
            }

    def _write_snapshot(self, access_event_id: str, url: str, body: bytes, content_type: str) -> Path:
        self.snapshot_root.mkdir(parents=True, exist_ok=True)
        suffix = _snapshot_suffix(url, content_type)
        digest = hashlib.sha256(body).hexdigest()[:12]
        path = self.snapshot_root / f"{access_event_id}-{digest}{suffix}"
        path.write_bytes(body)
        return path

    def _record_failure(
        self,
        connection: sqlite3.Connection,
        *,
        access_event_id: str,
        url: str,
        accessed_at: str,
        http_status: int | None,
        error: str,
        metadata: dict[str, Any],
        source_type: str,
    ) -> WebAccessResult:
        event = {
            "access_event_id": access_event_id,
            "url": url,
            "title": url,
            "domain": urllib.parse.urlparse(url).netloc,
            "accessed_at": accessed_at,
            "access_status": "failed",
            "source_type": source_type,
            "source_provenance": "external",
            "http_status": http_status,
            "content_ref": "",
            "excerpt": "",
            "metadata": {**metadata, "error": error},
        }
        insert_web_access_event(connection, event)
        connection.commit()
        return WebAccessResult(
            access_event_id=access_event_id,
            url=url,
            status="failed",
            http_status=http_status,
            content_ref="",
            title=url,
            error=error,
        )

    def _search_provider_name(self, search_url: str) -> str:
        domain = urllib.parse.urlparse(search_url).netloc
        return domain or "custom"

    def _actual_provider_name(self, search_url: str) -> str:
        return _canonical_provider_for_domain(self._search_provider_name(search_url)) or "custom"

    def _search_template_plan(self, constraints: WebSearchConstraints) -> dict[str, Any]:
        templates = tuple(self.search_url_templates)
        requested_provider = constraints.provider
        if not requested_provider:
            return {
                "status": "ok",
                "templates": templates if constraints.allow_fallback else templates[:1],
                "fallback_occurred": False,
                "fallback_reason": "",
            }
        if requested_provider not in SUPPORTED_SEARCH_PROVIDERS:
            if not constraints.allow_fallback:
                return {
                    "status": "unsupported",
                    "templates": (),
                    "fallback_occurred": False,
                    "fallback_reason": f"unsupported provider: {requested_provider}",
                }
            return {
                "status": "ok",
                "templates": templates,
                "fallback_occurred": True,
                "fallback_reason": f"unsupported provider: {requested_provider}",
            }
        matching = tuple(
            template
            for template in templates
            if _canonical_provider_for_url_template(template) == requested_provider
        )
        if matching:
            if not constraints.allow_fallback:
                return {
                    "status": "ok",
                    "templates": matching,
                    "fallback_occurred": False,
                    "fallback_reason": "",
                }
            fallback_templates = tuple(template for template in templates if template not in matching)
            return {
                "status": "ok",
                "templates": matching + fallback_templates,
                "fallback_occurred": False,
                "fallback_reason": "",
            }
        if constraints.allow_fallback:
            return {
                "status": "ok",
                "templates": templates,
                "fallback_occurred": True,
                "fallback_reason": f"requested provider unavailable in configured templates: {requested_provider}",
            }
        return {
            "status": "unsupported",
            "templates": (),
            "fallback_occurred": False,
            "fallback_reason": f"requested provider unavailable in configured templates: {requested_provider}",
        }

    def _record_unsupported_search_provider(
        self,
        connection: sqlite3.Connection,
        *,
        query: str,
        effective_query: str,
        constraints: WebSearchConstraints,
        reason: str,
    ) -> WebAccessResult:
        access_event_id = f"WEB-LIVE-{uuid4()}"
        accessed_at = _utc_now()
        unsupported_url = f"uaea://unsupported-search-provider/{constraints.provider or 'unknown'}"
        event = {
            "access_event_id": access_event_id,
            "url": unsupported_url,
            "title": f"Unsupported search provider: {constraints.provider}",
            "domain": "unsupported-search-provider",
            "accessed_at": accessed_at,
            "access_status": "unsupported",
            "source_type": "web_search_results",
            "source_provenance": "external",
            "http_status": None,
            "content_ref": "",
            "excerpt": "",
            "metadata": {
                "adapter": "phase2.web_adapter",
                "query": query,
                "effective_query": effective_query,
                "requested_constraints": constraints.to_dict(),
                "requested_provider": constraints.provider or None,
                "actual_provider": None,
                "fallback_occurred": False,
                "fallback_reason": reason,
                "search_provider": None,
                "provider_constraint_support": {},
                "search_parse_status": "unsupported_provider",
                "result_count": 0,
                "results": [],
                "error": reason,
                "execution_status": "unsupported",
                "reason": ("provider_not_implemented" if constraints.provider not in SUPPORTED_SEARCH_PROVIDERS
                           else "provider_not_configured"),
            },
        }
        insert_web_access_event(connection, event)
        connection.commit()
        return WebAccessResult(
            access_event_id=access_event_id,
            url=unsupported_url,
            status="unsupported",
            http_status=None,
            content_ref="",
            title=f"Unsupported search provider: {constraints.provider}",
            error=reason,
            search_results=(),
            related_access_event_ids=(access_event_id,),
        )


def _normalize_url(url: str) -> str:
    clean = _remove_unicode_surrogates(str(url or "")).strip()
    if not clean:
        raise ValueError("url missing")
    parsed = urllib.parse.urlparse(clean)
    if not parsed.scheme:
        clean = f"https://{clean}"
        parsed = urllib.parse.urlparse(clean)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"unsupported URL scheme: {parsed.scheme}")
    return clean


def normalize_search_constraints(arguments: dict[str, Any]) -> WebSearchConstraints:
    provider = _normalize_search_provider(arguments.get("provider"))
    allow_fallback_specified = "allow_fallback" in arguments and arguments.get("allow_fallback") not in (None, "")
    if provider and not allow_fallback_specified:
        raise WebSearchConstraintError(
            "provider was explicitly specified, but fallback policy is missing. "
            "Please retry with allow_fallback=true or allow_fallback=false.",
            details={
                "semantic_status": "ambiguous_provider_fallback_policy",
                "requested_provider": provider,
                "actual_provider": None,
                "fallback_occurred": False,
                "fallback_reason": "provider specified without allow_fallback policy",
                "retry_instruction": "Retry web.search with allow_fallback=true or allow_fallback=false.",
            },
        )
    allow_fallback = _normalize_allow_fallback(arguments.get("allow_fallback", True))
    language = _normalize_short_code(arguments.get("language"), field_name="language")
    region = _normalize_short_code(arguments.get("region"), field_name="region")
    exclude_domains = _normalize_domain_list(arguments.get("exclude_domains"), field_name="exclude_domains")
    preferred_domains = _normalize_domain_list(arguments.get("preferred_domains"), field_name="preferred_domains")
    source_types = _normalize_enum_list(
        arguments.get("source_types"),
        field_name="source_types",
        allowed=SUPPORTED_SOURCE_TYPES,
    )
    freshness = _safe_single_line_text(arguments.get("freshness")).lower()
    if freshness and freshness not in SUPPORTED_FRESHNESS:
        raise ValueError(f"unsupported freshness: {freshness}")
    return WebSearchConstraints(
        provider=provider,
        allow_fallback=allow_fallback,
        allow_fallback_specified=allow_fallback_specified,
        language=language,
        region=region,
        exclude_domains=exclude_domains,
        preferred_domains=preferred_domains,
        source_types=source_types,
        freshness=freshness,
    )


def _normalize_search_provider(value: object) -> str:
    clean = _safe_single_line_text(value).lower()
    if not clean:
        return ""
    normalized = SEARCH_PROVIDER_ALIASES.get(clean)
    if normalized:
        return normalized
    raise ValueError(f"unsupported provider value: {clean}")


def _normalize_allow_fallback(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return True
    if isinstance(value, str):
        clean = _safe_single_line_text(value).lower()
        if clean in {"true", "1", "yes"}:
            return True
        if clean in {"false", "0", "no"}:
            return False
    raise ValueError("allow_fallback must be a boolean")


def _normalize_short_code(value: object, *, field_name: str) -> str:
    clean = _safe_single_line_text(value).lower()
    if not clean:
        return ""
    if field_name == "region" and clean in {"global", "worldwide", "world", "any"}:
        return ""
    if not re.fullmatch(r"[a-z]{2}(?:-[a-z]{2})?", clean):
        raise ValueError(f"{field_name} must be a language/region code such as en or us")
    return clean


def _normalize_domain_list(value: object, *, field_name: str) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of domains")
    domains: list[str] = []
    seen: set[str] = set()
    for item in value:
        domain = _normalize_domain(item, field_name=field_name)
        if domain and domain not in seen:
            domains.append(domain)
            seen.add(domain)
    return tuple(domains)


def _normalize_domain(value: object, *, field_name: str) -> str:
    clean = _safe_single_line_text(value).lower()
    if not clean:
        return ""
    if "://" in clean:
        clean = urllib.parse.urlparse(clean).netloc
    if clean.startswith("*."):
        suffix = clean[2:].strip(".")
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*", suffix):
            raise ValueError(f"{field_name} contains invalid domain pattern: {value}")
        return f"*.{suffix}"
    clean = clean.strip(".")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+", clean):
        raise ValueError(f"{field_name} contains invalid domain: {value}")
    return clean


def _normalize_enum_list(value: object, *, field_name: str, allowed: frozenset[str]) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        clean = _safe_single_line_text(item).lower()
        if not clean:
            continue
        if clean not in allowed:
            raise ValueError(f"unsupported {field_name} value: {clean}")
        if clean not in seen:
            items.append(clean)
            seen.add(clean)
    return tuple(items)


def _shape_search_query(query: str, constraints: WebSearchConstraints) -> str:
    parts = [query]
    for domain in constraints.exclude_domains:
        parts.append(f"-site:{_site_query_domain(domain)}")
    if constraints.preferred_domains:
        preferred = " OR ".join(f"site:{_site_query_domain(domain)}" for domain in constraints.preferred_domains)
        parts.append(f"({preferred})")
    source_terms = _source_type_terms(constraints.source_types)
    if source_terms:
        parts.append(source_terms)
    if constraints.language:
        parts.append(f"language:{constraints.language}")
    if constraints.freshness and constraints.freshness != "any":
        parts.append(constraints.freshness)
    return " ".join(part for part in parts if part).strip()


def _source_type_terms(source_types: tuple[str, ...]) -> str:
    terms = {
        "academic": '(paper OR arxiv OR "conference paper" OR journal)',
        "forum": "(forum OR reddit OR discourse OR stackexchange)",
        "news": "(news OR analysis)",
        "documentation": "(documentation OR docs OR reference)",
        "general": "",
    }
    selected = [terms[item].strip("()") for item in source_types if terms.get(item)]
    return f"({' OR '.join(selected)})" if selected else ""


def _site_query_domain(domain: str) -> str:
    clean = str(domain or "").strip().lower()
    if clean.startswith("*."):
        return f".{clean[2:]}"
    return clean


def _search_url_for_template(template: str, effective_query: str, constraints: WebSearchConstraints) -> str:
    search_url = template.format(query=urllib.parse.quote_plus(effective_query))
    parsed = urllib.parse.urlparse(search_url)
    provider = parsed.netloc.lower()
    query_items = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    if provider.endswith("bing.com"):
        if constraints.language:
            query_items.append(("setlang", constraints.language))
        if constraints.region:
            query_items.append(("cc", constraints.region))
    elif provider.endswith("duckduckgo.com") and constraints.region:
        query_items.append(("kl", constraints.region))
    if query_items == urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        return search_url
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query_items)))


def _constraint_application_metadata(constraints: WebSearchConstraints) -> dict[str, Any]:
    requested = constraints.to_dict()
    return {
        "requested_constraints": requested,
        "provider_enforced_constraints": [],
        "best_effort_constraints": [
            name
            for name, value in requested.items()
            if value
        ],
        "notes": (
            "Search providers do not provide hard guarantees for these constraints through the current adapter. "
            "UAEA preserves the request, applies query shaping where possible, and post-filters excluded domains."
        ),
    }


def _provider_constraint_support(provider: str) -> dict[str, str]:
    normalized = str(provider or "").lower()
    if normalized in PROVIDER_CONSTRAINT_SUPPORT:
        return PROVIDER_CONSTRAINT_SUPPORT[normalized]
    canonical = _canonical_provider_for_domain(normalized)
    if canonical == "duckduckgo":
        return PROVIDER_CONSTRAINT_SUPPORT["duckduckgo.com"]
    if canonical == "bing":
        return PROVIDER_CONSTRAINT_SUPPORT["www.bing.com"]
    if canonical == "google":
        return PROVIDER_CONSTRAINT_SUPPORT["www.google.com"]
    return {
        "language": "unknown",
        "region": "unknown",
        "exclude_domains": "best_effort_query_shaping_and_post_filter",
        "preferred_domains": "best_effort_query_shaping",
        "source_types": "best_effort_query_shaping",
        "freshness": "unsupported",
    }


def _canonical_provider_for_url_template(template: str) -> str:
    sample_url = str(template or "").replace("{query}", "sample")
    return _canonical_provider_for_domain(urllib.parse.urlparse(sample_url).netloc)


def _canonical_provider_for_domain(domain: str) -> str:
    normalized = str(domain or "").lower().strip(".")
    if normalized.endswith("duckduckgo.com"):
        return "duckduckgo"
    if normalized.endswith("bing.com"):
        return "bing"
    return ""


def _apply_result_constraints(
    results: tuple[WebSearchResult, ...],
    constraints: WebSearchConstraints,
    *,
    max_results: int,
) -> tuple[WebSearchResult, ...]:
    filtered = [
        result
        for result in results
        if not _domain_matches_any(urllib.parse.urlparse(result.url).netloc, constraints.exclude_domains)
    ]
    if constraints.preferred_domains:
        filtered.sort(
            key=lambda result: 0
            if _domain_matches_any(urllib.parse.urlparse(result.url).netloc, constraints.preferred_domains)
            else 1
        )
    return tuple(filtered[:max_results])


def _domain_matches_any(domain: str, candidates: tuple[str, ...]) -> bool:
    normalized = str(domain or "").lower().strip(".")
    for candidate in candidates:
        if candidate.startswith("*."):
            suffix = candidate[2:]
            if normalized == suffix or normalized.endswith(f".{suffix}"):
                return True
            continue
        if normalized == candidate or normalized.endswith(f".{candidate}"):
            return True
    return False


def _post_filtering_metadata(
    parsed_count: int,
    results: tuple[WebSearchResult, ...],
    constraints: WebSearchConstraints,
) -> dict[str, Any]:
    result_domains = [urllib.parse.urlparse(result.url).netloc.lower().strip(".") for result in results]
    preferred_domain_result_count = sum(
        1
        for domain in result_domains
        if _domain_matches_any(domain, constraints.preferred_domains)
    )
    return {
        "exclude_domains_applied": list(constraints.exclude_domains),
        "preferred_domains_applied": list(constraints.preferred_domains),
        "parsed_result_count_before_filtering": parsed_count,
        "result_count_after_filtering": len(results),
        "result_domains_after_filtering": result_domains,
        "preferred_domain_result_count": preferred_domain_result_count,
        "preferred_domain_missing": bool(constraints.preferred_domains and preferred_domain_result_count == 0),
    }


def _assess_search_relevance(query: str, results: tuple[WebSearchResult, ...]) -> dict[str, Any]:
    terms = _query_relevance_terms(query)
    if not results:
        return {
            "status": "low_relevance",
            "matched_terms": [],
            "query_terms": sorted(terms),
            "matched_term_count": 0,
            "query_term_count": len(terms),
            "coverage": 0.0,
            "phrase_match": False,
            "note": "No parsed search results; no candidate evidence eligibility.",
        }
    haystack = " ".join(
        f"{item.title} {item.url} {item.snippet}" for item in results
    ).lower()
    matched = sorted(term for term in terms if term in haystack)
    matched_count = len(matched)
    term_count = len(terms)
    coverage = matched_count / term_count if term_count else 0.0
    phrase_match = _has_multi_term_phrase_match(query, haystack)
    if not terms:
        status = "not_validated"
    elif term_count >= 3 and matched_count < 2 and not phrase_match:
        status = "low_relevance"
    elif coverage >= 0.6 or phrase_match:
        status = "relevant"
    elif matched_count >= 2 or coverage >= 0.4:
        status = "uncertain"
    else:
        status = "low_relevance"
    return {
        "status": status,
        "matched_terms": matched,
        "query_terms": sorted(terms),
        "matched_term_count": matched_count,
        "query_term_count": term_count,
        "coverage": round(coverage, 3),
        "phrase_match": phrase_match,
        "note": (
            "Conservative lexical diagnostic only; execution success does not imply evidence relevance. "
            "A single noisy term match is low relevance for multi-term queries."
        ),
    }


def _query_relevance_terms(query: str) -> set[str]:
    stopwords = {
        "and",
        "the",
        "for",
        "with",
        "from",
        "current",
        "latest",
        "recent",
        "news",
        "paper",
        "papers",
        "forum",
        "forums",
        "language",
        "english",
    }
    lower = query.lower()
    terms = {term for term in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", lower) if term not in stopwords}
    terms.update(re.findall(r"[\u4e00-\u9fff]{2,}", query))
    return terms


def _has_multi_term_phrase_match(query: str, haystack: str) -> bool:
    normalized_query = " ".join(re.findall(r"[a-z0-9]+", query.lower()))
    if not normalized_query:
        return False
    parts = normalized_query.split()
    if len(parts) < 2:
        return False
    if normalized_query in haystack:
        return True
    for index in range(len(parts) - 1):
        if f"{parts[index]} {parts[index + 1]}" in haystack:
            return True
    return False


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _snapshot_suffix(url: str, content_type: str) -> str:
    if "html" in content_type.lower():
        return ".html"
    suffix = Path(urllib.parse.urlparse(url).path).suffix
    return suffix if suffix else ".txt"


def _extract_title(body: bytes, *, content_type: str) -> str:
    if "html" not in content_type.lower():
        return ""
    parser = _TitleParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    parser.close()
    return parser.title


def _plain_text_excerpt(body: bytes, *, content_type: str, limit: int = 1200) -> str:
    text = body.decode("utf-8", errors="replace")
    if "html" in content_type.lower():
        parser = _VisibleTextParser()
        parser.feed(text)
        parser.close()
        text = "\n".join(parser.blocks)
    text = "\n".join(" ".join(line.split()) for line in text.splitlines())
    text = "\n".join(line for line in text.splitlines() if line.strip())
    return text[:limit].rstrip()


def _parse_google_search_results(payload: dict[str, Any]) -> list[WebSearchResult]:
    results: list[WebSearchResult] = []
    seen: set[str] = set()
    for item in payload.get("organic_results", []):
        if not isinstance(item, dict):
            continue
        url, title = item.get("link"), item.get("title")
        if not isinstance(url, str) or not isinstance(title, str) or not title.strip():
            continue
        try:
            parsed = urllib.parse.urlsplit(url)
            valid = parsed.scheme in {"http", "https"} and parsed.hostname
        except ValueError:
            valid = False
        if not valid or url in seen:
            continue
        seen.add(url)
        snippet = item.get("snippet", "")
        results.append(WebSearchResult(title.strip(), url, snippet if isinstance(snippet, str) else ""))
    return results


def _parse_search_results(html: str, *, max_results: int) -> list[WebSearchResult]:
    parser = _SearchResultParser()
    parser.feed(html)
    parser.close()
    return parser.results[:max_results]


def _format_search_results(query: str, results: tuple[WebSearchResult, ...]) -> str:
    lines = [f"Search query: {query}", f"Result count: {len(results)}"]
    for index, result in enumerate(results, start=1):
        lines.append(f"{index}. {result.title}")
        lines.append(f"   url: {result.url}")
        if result.snippet:
            lines.append(f"   snippet: {result.snippet}")
    return "\n".join(lines)


def _safe_single_line_text(value: object) -> str:
    return " ".join(_remove_unicode_surrogates(str(value or "")).split())


def _remove_unicode_surrogates(value: str) -> str:
    return "".join(" " if 0xD800 <= ord(char) <= 0xDFFF else char for char in value)


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = " ".join((self.title + " " + data).split())


class _VisibleTextParser(HTMLParser):
    ignored_tags = frozenset({"script", "style", "noscript", "svg"})
    block_tags = frozenset({"title", "h1", "h2", "h3", "p", "li", "pre", "code"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._ignored_depth = 0
        self._active_depth = 0
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized in self.ignored_tags:
            self._ignored_depth += 1
        if normalized in self.block_tags and self._ignored_depth == 0:
            self._flush()
            self._active_depth += 1

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in self.block_tags and self._active_depth > 0:
            self._flush()
            self._active_depth -= 1
        if normalized in self.ignored_tags and self._ignored_depth > 0:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0 or self._active_depth <= 0:
            return
        text = " ".join(str(data or "").split())
        if text:
            self._buffer.append(text)

    def close(self) -> None:
        self._flush()
        super().close()

    def _flush(self) -> None:
        text = " ".join(self._buffer).strip()
        if text:
            self.blocks.append(text)
        self._buffer.clear()


class _SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[WebSearchResult] = []
        self._active_result_url = ""
        self._active_result_title: list[str] = []
        self._active_snippet: list[str] = []
        self._capture_title = False
        self._capture_snippet = False
        self._bing_result_depth = 0
        self._bing_anchor_open = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        attrs_dict = {key: value or "" for key, value in attrs}
        classes = set(str(attrs_dict.get("class", "")).split())
        if normalized_tag == "li" and "b_algo" in classes:
            self._bing_result_depth = 1
            self._active_result_url = ""
            self._active_result_title = []
            self._active_snippet = []
            return
        if self._bing_result_depth > 0:
            self._bing_result_depth += 1
            if normalized_tag == "a" and not self._active_result_url:
                self._active_result_url = _clean_result_url(attrs_dict.get("href", ""))
                self._active_result_title = []
                self._capture_title = True
                self._bing_anchor_open = True
            elif normalized_tag == "p" and self._active_result_url:
                self._active_snippet = []
                self._capture_snippet = True
            return
        if normalized_tag == "a" and ("result__a" in classes or "result-link" in classes):
            self._active_result_url = _clean_result_url(attrs_dict.get("href", ""))
            self._active_result_title = []
            self._capture_title = True
        if "result__snippet" in classes or "result-snippet" in classes:
            self._active_snippet = []
            self._capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if self._bing_result_depth > 0:
            if normalized_tag == "a" and self._bing_anchor_open:
                self._capture_title = False
                self._bing_anchor_open = False
            elif normalized_tag == "p" and self._capture_snippet:
                self._capture_snippet = False
            elif normalized_tag == "li":
                self._append_result_if_ready()
                self._bing_result_depth = 0
                self._capture_title = False
                self._capture_snippet = False
                self._bing_anchor_open = False
                self._active_result_url = ""
                self._active_result_title = []
                self._active_snippet = []
            else:
                self._bing_result_depth = max(0, self._bing_result_depth - 1)
            return
        if normalized_tag == "a" and self._capture_title:
            self._capture_title = False
            self._append_result_if_ready()
        if self._capture_snippet and normalized_tag in {"a", "div", "span"}:
            self._capture_snippet = False
            if self.results and self._active_snippet:
                latest = self.results[-1]
                self.results[-1] = WebSearchResult(
                    title=latest.title,
                    url=latest.url,
                    snippet=" ".join(" ".join(self._active_snippet).split()),
                )

    def handle_data(self, data: str) -> None:
        text = " ".join(str(data or "").split())
        if not text:
            return
        if self._capture_title:
            self._active_result_title.append(text)
        if self._capture_snippet:
            self._active_snippet.append(text)

    def _append_result_if_ready(self) -> None:
        title = " ".join(" ".join(self._active_result_title).split())
        if title and self._active_result_url:
            snippet = " ".join(" ".join(self._active_snippet).split())
            self.results.append(WebSearchResult(title=title, url=self._active_result_url, snippet=snippet))


def _clean_result_url(url: str) -> str:
    clean = str(url or "").strip()
    parsed = urllib.parse.urlparse(clean)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        query = urllib.parse.parse_qs(parsed.query)
        uddg = query.get("uddg", [""])[0]
        if uddg:
            return urllib.parse.unquote(uddg)
    if parsed.netloc.endswith("bing.com") and parsed.path.startswith("/ck/a"):
        query = urllib.parse.parse_qs(parsed.query)
        encoded_target = query.get("u", [""])[0]
        decoded = _decode_bing_target_url(encoded_target)
        if decoded:
            return decoded
    return clean


def _decode_bing_target_url(encoded_target: str) -> str:
    value = str(encoded_target or "").strip()
    if not value:
        return ""
    if value.startswith("a1"):
        value = value[2:]
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.urlsafe_b64decode((value + padding).encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""
    parsed = urllib.parse.urlparse(decoded)
    if parsed.scheme in {"http", "https"}:
        return decoded
    return ""
