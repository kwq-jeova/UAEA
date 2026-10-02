from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from phase2.network_observability import observe_open, observe_read


SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


class SerpApiFailure(Exception):
    def __init__(self, status: str, reason: str, *, http_status: int | None = None,
                 http_attempted: bool = True) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.http_status = http_status
        self.http_attempted = http_attempted


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def google_search(parameters: dict[str, Any], *, timeout: int, max_bytes: int,
                  user_agent: str) -> dict[str, Any]:
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if not key:
        raise SerpApiFailure("configuration_error", "credential_missing", http_attempted=False)
    if any(char.isspace() for char in key):
        raise SerpApiFailure("configuration_error", "credential_invalid", http_attempted=False)
    # Only the transport sees the authenticated URL. Never propagate its exceptions or response errors.
    query = urllib.parse.urlencode({**parameters, "engine": "google", "api_key": key})
    request = urllib.request.Request(SERPAPI_ENDPOINT + "?" + query, headers={"User-Agent": user_agent})
    try:
        with observe_open(urllib.request.build_opener(_NoRedirect()).open, request, timeout=timeout) as response:
            body = observe_read(response, max_bytes + 1)
        if len(body) > max_bytes:
            raise SerpApiFailure("response_error", "response_too_large", http_status=200)
        payload = json.loads(body)
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            status, reason = "authentication_failure", "credential_rejected"
        elif exc.code == 429:
            status, reason = "rate_limited", "backend_rate_limited"
        else:
            status, reason = "http_failure", "http_error"
        raise SerpApiFailure(status, reason, http_status=exc.code) from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        timed_out = isinstance(exc, TimeoutError) or (
            isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, TimeoutError)
        )
        raise SerpApiFailure("timeout" if timed_out else "network_failure",
                             "request_timeout" if timed_out else "network_error") from None
    except (ValueError, UnicodeError):
        raise SerpApiFailure("response_error", "invalid_backend_response", http_status=200) from None
    if not isinstance(payload, dict):
        raise SerpApiFailure("response_error", "invalid_backend_response", http_status=200)
    if payload.get("error"):
        raise SerpApiFailure("backend_failure", "backend_error", http_status=200)
    metadata = payload.get("search_metadata", {})
    reported = payload.get("search_parameters", {})
    if (not isinstance(metadata, dict) or metadata.get("status") != "Success"
            or not isinstance(reported, dict) or reported.get("engine") != "google"
            or not isinstance(payload.get("organic_results", []), list)):
        raise SerpApiFailure("response_error", "invalid_backend_response", http_status=200)
    return _redact_credentials(payload, key)


def _redact_credentials(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return {_redact_credentials(str(name), key): _redact_credentials(item, key) for name, item in value.items()
                if str(name).lower() not in {"api_key", "serpapi_key", "authorization", "access_token"}}
    if isinstance(value, list):
        return [_redact_credentials(item, key) for item in value]
    if isinstance(value, str):
        for representation in {key, urllib.parse.quote(key, safe=""), urllib.parse.quote_plus(key)}:
            value = value.replace(representation, "[REDACTED]")
        return value
    return value
