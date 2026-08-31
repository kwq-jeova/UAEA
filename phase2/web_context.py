from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

from memory.sqlite_store import (
    evidence_reference_for_web_access_event,
    get_web_access_event,
    get_web_source,
)


DEFAULT_STRUCTURE_TAGS = frozenset({"title", "h1", "h2", "h3", "p", "li", "pre", "code"})
IGNORED_TAGS = frozenset({"script", "style", "nav", "footer", "header", "aside", "noscript"})


@dataclass(frozen=True)
class ProjectionLimits:
    max_sources: int = 3
    per_source_chars: int = 800
    total_chars: int = 2000


@dataclass(frozen=True)
class ProjectedWebSource:
    access_event_id: str
    web_source_id: str
    url: str
    title: str
    domain: str
    accessed_at: str
    access_status: str
    source_type: str
    source_provenance: str
    content_ref: str
    content_sha256: str
    evidence_reference: dict[str, Any]
    projected_text: str
    projected_chars: int
    source_chars: int
    truncated: bool
    failure_reason: str = ""


@dataclass(frozen=True)
class WebContextProjection:
    sources: tuple[ProjectedWebSource, ...]
    dropped_source_count: int
    total_source_chars: int
    total_projected_chars: int
    estimated_prompt_tokens: int
    limits: ProjectionLimits
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def evidence_block(self) -> str:
        lines = [
            "[WEB EVIDENCE BLOCK]",
            f"sources={len(self.sources)} dropped={self.dropped_source_count} "
            f"projected_chars={self.total_projected_chars} estimated_tokens={self.estimated_prompt_tokens}",
        ]
        for index, source in enumerate(self.sources, start=1):
            lines.extend(
                [
                    "",
                    f"[Source {index}]",
                    f"evidence: {source.evidence_reference['source_kind']}:{source.evidence_reference['source_id']}",
                    f"url: {source.url}",
                    f"title: {source.title}",
                    f"domain: {source.domain}",
                    f"accessed_at: {source.accessed_at}",
                    f"status: {source.access_status}",
                    f"source_type: {source.source_type}",
                    f"provenance: {source.source_provenance}",
                    f"content_ref: {source.content_ref}",
                    f"content_sha256: {source.content_sha256}",
                ]
            )
            if source.failure_reason:
                lines.append(f"failure: {source.failure_reason}")
            if source.truncated:
                lines.append("truncated: true")
            if source.projected_text:
                lines.extend(["excerpt:", source.projected_text])
            else:
                lines.append("excerpt: <none>")
        if self.warnings:
            lines.extend(["", "warnings:"])
            lines.extend(f"- {warning}" for warning in self.warnings)
        return "\n".join(lines)

    def metrics(self) -> dict[str, Any]:
        return {
            "context_source_count": len(self.sources),
            "dropped_source_count": self.dropped_source_count,
            "source_chars": self.total_source_chars,
            "projected_chars": self.total_projected_chars,
            "estimated_prompt_tokens": self.estimated_prompt_tokens,
            "max_sources": self.limits.max_sources,
            "per_source_chars": self.limits.per_source_chars,
            "total_chars": self.limits.total_chars,
        }


def project_web_access_events(
    connection: Any,
    access_event_ids: Iterable[str],
    *,
    limits: ProjectionLimits | None = None,
) -> WebContextProjection:
    active_limits = limits or ProjectionLimits()
    ordered_ids = [str(access_event_id) for access_event_id in access_event_ids if str(access_event_id).strip()]
    selected_ids = ordered_ids[: max(active_limits.max_sources, 0)]
    dropped = max(0, len(ordered_ids) - len(selected_ids))
    remaining_chars = max(active_limits.total_chars, 0)
    sources: list[ProjectedWebSource] = []
    warnings: list[str] = []
    total_source_chars = 0

    for access_event_id in selected_ids:
        event = get_web_access_event(connection, access_event_id)
        if event is None:
            warnings.append(f"web access event not found: {access_event_id}")
            continue
        web_source = get_web_source(connection, event["web_source_id"])
        if web_source is None:
            warnings.append(f"web source not found: {event['web_source_id']}")
            continue
        reference = evidence_reference_for_web_access_event(connection, access_event_id)
        source_text = _source_text_for_event(event)
        total_source_chars += int(event.get("content_chars") or len(source_text))
        if event["access_status"] != "fetched":
            failure_reason = _failure_reason(event)
            projected_text = ""
            truncated = False
        elif remaining_chars <= 0:
            dropped += 1
            continue
        else:
            allowed_chars = min(active_limits.per_source_chars, remaining_chars)
            projected_text, truncated = _bounded_text(source_text or event["excerpt"], allowed_chars)
            remaining_chars -= len(projected_text)
            failure_reason = ""
        sources.append(
            ProjectedWebSource(
                access_event_id=event["access_event_id"],
                web_source_id=event["web_source_id"],
                url=event["url"],
                title=event["title"],
                domain=event["domain"],
                accessed_at=event["accessed_at"],
                access_status=event["access_status"],
                source_type=event["source_type"],
                source_provenance=event["source_provenance"],
                content_ref=event["content_ref"],
                content_sha256=event["content_sha256"],
                evidence_reference=reference.to_dict(),
                projected_text=projected_text,
                projected_chars=len(projected_text),
                source_chars=int(event.get("content_chars") or len(source_text)),
                truncated=truncated,
                failure_reason=failure_reason,
            )
        )

    total_projected_chars = sum(source.projected_chars for source in sources)
    return WebContextProjection(
        sources=tuple(sources),
        dropped_source_count=dropped,
        total_source_chars=total_source_chars,
        total_projected_chars=total_projected_chars,
        estimated_prompt_tokens=_estimate_tokens(total_projected_chars),
        limits=active_limits,
        warnings=tuple(warnings),
    )


def _source_text_for_event(event: dict[str, Any]) -> str:
    if event.get("source_type") == "web_search_results":
        return _normalize_whitespace(str(event.get("excerpt") or ""))
    content_ref_resolved = str(event.get("raw", {}).get("content_ref_resolved") or "").strip()
    path = Path(content_ref_resolved) if content_ref_resolved else None
    if path is not None and path.is_file():
        raw = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() in {".html", ".htm"}:
            return _extract_structured_html_text(raw)
        return _normalize_whitespace(raw)
    return _normalize_whitespace(str(event.get("excerpt") or ""))


def _extract_structured_html_text(raw_html: str) -> str:
    parser = _StructuredHTMLTextParser()
    parser.feed(raw_html)
    parser.close()
    return "\n".join(parser.blocks)


def _bounded_text(text: str, limit: int) -> tuple[str, bool]:
    normalized = _normalize_whitespace(text)
    if limit <= 0:
        return "", bool(normalized)
    if len(normalized) <= limit:
        return normalized, False
    return normalized[:limit].rstrip(), True


def _normalize_whitespace(text: str) -> str:
    lines = []
    for line in str(text or "").splitlines():
        compact = re.sub(r"\s+", " ", line).strip()
        if compact:
            lines.append(compact)
    return "\n".join(lines)


def _estimate_tokens(char_count: int) -> int:
    if char_count <= 0:
        return 0
    return max(1, (char_count + 3) // 4)


def _failure_reason(event: dict[str, Any]) -> str:
    metadata = event.get("metadata")
    error = metadata.get("error") if isinstance(metadata, dict) else ""
    status = event.get("http_status")
    parts = []
    if status is not None:
        parts.append(f"http_status={status}")
    if error:
        parts.append(str(error))
    return "; ".join(parts) or str(event.get("access_status") or "failed")


class _StructuredHTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._active_tag_stack: list[str] = []
        self._ignored_depth = 0
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in IGNORED_TAGS:
            self._ignored_depth += 1
        if normalized_tag in DEFAULT_STRUCTURE_TAGS and self._ignored_depth == 0:
            self._flush()
            self._active_tag_stack.append(normalized_tag)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in DEFAULT_STRUCTURE_TAGS and self._active_tag_stack:
            self._flush()
            self._active_tag_stack.pop()
        if normalized_tag in IGNORED_TAGS and self._ignored_depth > 0:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0 or not self._active_tag_stack:
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
