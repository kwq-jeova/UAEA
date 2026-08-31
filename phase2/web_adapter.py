from __future__ import annotations

import hashlib
import base64
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from uuid import uuid4

from memory.sqlite_store import insert_web_access_event


DEFAULT_USER_AGENT = "UAEA-Phase2-WebAdapter/0.1"
DEFAULT_SEARCH_URL_TEMPLATES = (
    "https://duckduckgo.com/html/?q={query}",
    "https://www.bing.com/search?q={query}",
)


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
        try:
            response_payload = self._http_get(normalized_url)
        except urllib.error.HTTPError as exc:
            return self._record_failure(
                connection,
                access_event_id=access_event_id,
                url=normalized_url,
                accessed_at=accessed_at,
                http_status=exc.code,
                error=f"HTTP {exc.code}: {exc.reason}",
                metadata={**base_metadata, "latency_ms": round((time.monotonic() - started_at) * 1000, 3)},
                source_type=source_type,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return self._record_failure(
                connection,
                access_event_id=access_event_id,
                url=normalized_url,
                accessed_at=accessed_at,
                http_status=None,
                error=str(exc),
                metadata={**base_metadata, "latency_ms": round((time.monotonic() - started_at) * 1000, 3)},
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
    ) -> WebAccessResult:
        clean_query = _safe_single_line_text(query)
        if not clean_query:
            raise ValueError("search query missing")
        attempt_event_ids: list[str] = []
        last_result: WebAccessResult | None = None
        for attempt_index, template in enumerate(self.search_url_templates, start=1):
            search_url = template.format(query=urllib.parse.quote_plus(clean_query))
            result = self.fetch_url(
                connection,
                search_url,
                source_type="web_search_results",
                metadata={
                    "query": clean_query,
                    "search_provider": self._search_provider_name(search_url),
                    "search_attempt_index": attempt_index,
                    "search_attempt_count": len(self.search_url_templates),
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
            search_results = self._parse_search_result_event(connection, result.access_event_id, clean_query, max_results)
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
    ) -> tuple[WebSearchResult, ...]:
        event_row = connection.execute(
            "SELECT metadata_json, content_ref FROM web_access_events WHERE access_event_id = ?",
            (access_event_id,),
        ).fetchone()
        if event_row is None:
            return ()
        snapshot = Path(str(event_row["content_ref"]))
        body = snapshot.read_text(encoding="utf-8", errors="replace") if snapshot.is_file() else ""
        search_results = tuple(_parse_search_results(body, max_results=max_results))
        parse_status = "parsed" if search_results else "no_parsed_results"
        self._mark_search_attempt(connection, access_event_id, clean_query, search_results, parse_status=parse_status)
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

    def _http_get(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            body = response.read(self.max_snapshot_bytes + 1)
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
