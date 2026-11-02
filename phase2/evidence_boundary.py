"""Observable evidence facts. No semantic relevance or content-period inference."""
from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path
from typing import Any

SCHEMA = "uaea.evidence_boundary.v1"


def candidate_view(data: dict[str, Any], results: list[dict]) -> dict[str, Any]:
    """Visibility/citation of a search hit establishes origin, never research relevance."""
    event_id = str(data["access_event_id"])
    candidates = []
    for index, item in enumerate(results):
        if (not isinstance(item.get("title"), str) or not item["title"]
                or not isinstance(item.get("url"), str)
                or not item["url"].startswith(("https://", "http://"))):
            continue
        candidates.append({
            **item, "source_id": f"{event_id}:result:{index}",
            "source_event_id": event_id,
            "citation_scope": "search_result_only",
            "semantic_relevance": "unassessed",
            "constraints_satisfied": "not_established",
            "page_acquired": False,
            **({"source_date_kind": "search_provider_label",
                "source_date_anchor": data.get("accessed_at")}
               if item.get("source_date_text") else {}),
        })
    diagnostic = dict(data.get("evidence_relevance") or {})
    diagnostic.update(role="lexical_diagnostic_only", semantic_authority=False)
    return {
        "evidence_boundary": {"schema": SCHEMA, "citation_scope": "search_result_only",
                              "semantic_relevance": "unassessed",
                              "constraints_satisfied": "not_established",
                              "page_evidence_requires_fetch": True},
        "evidence_status": "candidates_available",
        "evidence_relevance": diagnostic,
        "evidence_counts": {
            "raw": int((data.get("search_transport") or {}).get(
                "backend_raw", data.get("raw_search_result_count", len(results)))),
            "retained": len(candidates), "visible": len(candidates),
            "discovery_citable": len(candidates), "page_content_acquired": 0,
        },
        **({"search_transport": {**data["search_transport"], "model_visible": len(candidates),
                                "visibility_basis": "capability_projection_before_harness_budget"}}
           if data.get("search_transport") else {}),
        "candidate_evidence_results": candidates,
        "search_results": candidates,
        # Compatibility name: these may be cited as search hits ONLY.
        "citable_results": candidates,
    }


class _PublicationParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.claims = []
        self._json = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("property", "").lower() == "article:published_time":
            value = attrs.get("content")
            if value:
                self.claims.append({"field": "meta.article:published_time", "value": value})
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._json = []

    def handle_data(self, data):
        if self._json is not None:
            self._json.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._json is not None:
            try:
                self._visit(json.loads("".join(self._json)), "jsonld")
            except (ValueError, RecursionError):
                pass
            self._json = None

    def _visit(self, value, path):
        if isinstance(value, dict):
            # Only source-declared page/article entities. No dates inferred from body text.
            types = value.get("@type", [])
            if isinstance(types, str):
                types = [types]
            if not isinstance(types, list):
                types = []
            if ({x for x in types if isinstance(x, str)} & {"Article", "NewsArticle", "BlogPosting", "WebPage"}
                    and isinstance(value.get("datePublished"), str)):
                self.claims.append({"field": path + ".datePublished", "value": value["datePublished"]})
            for key, item in value.items():
                if isinstance(item, (dict, list)):
                    self._visit(item, path + "." + key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                self._visit(item, f"{path}[{index}]")


def temporal_facts(event: dict[str, Any]) -> dict[str, Any]:
    facts = {
        "accessed_at": event.get("accessed_at"), "accessed_at_origin": "runtime_access_event",
        "published_at": None, "publication_status": "unknown",
        "publication_claims": [],
        "content_period": {"value": None, "status": "unknown",
                           "origin": "requires_source_grounded_model_interpretation"},
    }
    if event.get("access_status") != "fetched" or event.get("source_type") == "web_search_results":
        return facts
    resolved = event.get("raw", {}).get("content_ref_resolved") or event.get("content_ref") or ""
    path = Path(resolved)
    if not path.is_file() or path.suffix.lower() not in {".html", ".htm"}:
        return facts
    parser = _PublicationParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    claims = []
    for claim in parser.claims:
        if len(claim["value"]) <= 100:
            claims.append({**claim, "source_event_id": event["access_event_id"],
                           "content_sha256": event.get("content_sha256")})
    facts["publication_claims"] = claims
    normalized = {}
    for claim in claims:
        try:
            value = datetime.fromisoformat(claim["value"].replace("Z", "+00:00"))
            key = value.isoformat()
        except ValueError:
            continue
        normalized.setdefault(key, claim["value"])
    if len(normalized) == 1:
        facts.update(published_at=next(iter(normalized.values())), publication_status="source_declared")
    elif normalized:
        facts["publication_status"] = "conflicting_source_declarations"
    return facts
