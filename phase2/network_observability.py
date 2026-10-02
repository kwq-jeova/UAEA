from __future__ import annotations

import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Callable


_CURRENT: ContextVar[NetworkObservation | None] = ContextVar("uaea_web_network_observation", default=None)


class NetworkObservation:
    """Observe urllib boundaries without replacing its transport or exception behavior."""

    def __init__(self, endpoint: str) -> None:
        self.started = time.monotonic()
        self.data: dict[str, Any] = {
            "request_start": datetime.now(timezone.utc).isoformat(),
            "credential_present": bool(os.environ.get("SERPAPI_KEY", "").strip()),
            "proxy_present": False,
            "proxy_endpoint_redacted": None,
            "proxy_bypassed": None,
            "stage": "not_opened",
            "http_status": None,
            "response_bytes": None,
            "elapsed_ms": 0.0,
            "exception_type": None,
            "network_error_stage": None,
            "error_kind": None,
            "events": [],
        }
        # Only the selected proxy endpoint is retained, never the request URL or query.
        try:
            target = urllib.parse.urlsplit(endpoint)
            proxy = urllib.request.getproxies().get(target.scheme, "")
            parsed = urllib.parse.urlsplit(proxy)
            host = parsed.hostname or ""
            key = os.environ.get("SERPAPI_KEY", "").strip()
            if key:
                for value in {key, urllib.parse.quote(key, safe=""), urllib.parse.quote_plus(key)}:
                    host = host.replace(value, "[REDACTED]")
            if ":" in host:
                host = f"[{host}]"
            port = f":{parsed.port}" if parsed.port is not None else ""
            self.data.update({
                "proxy_present": bool(proxy),
                "proxy_endpoint_redacted": f"{parsed.scheme}://{host}{port}" if proxy else None,
                "proxy_bypassed": urllib.request.proxy_bypass(target.hostname or ""),
            })
        except (OSError, ValueError):
            self.data["proxy_inspection"] = "unavailable"

    def __enter__(self) -> NetworkObservation:
        self.token = _CURRENT.set(self)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.data["elapsed_ms"] = self.elapsed()
        _CURRENT.reset(self.token)

    def elapsed(self) -> float:
        return round((time.monotonic() - self.started) * 1000, 3)

    def mark(self, stage: str, **fields: Any) -> None:
        self.data.update({"stage": stage, "elapsed_ms": self.elapsed(), **fields})
        self.data["events"].append({"stage": stage, "elapsed_ms": self.data["elapsed_ms"], **fields})

    def failure(self, stage: str, error: Exception) -> None:
        cause = error.reason if isinstance(error, urllib.error.URLError) else error
        if isinstance(error, urllib.error.HTTPError):
            kind = "proxy_error" if error.code == 407 else "http_error"
            self.data["http_status"] = error.code
        elif isinstance(cause, ssl.SSLError):
            kind = "ssl_error"
        elif isinstance(cause, TimeoutError):
            kind = "response_read_timeout" if stage == "body_read" else "connection_open_timeout"
        elif isinstance(cause, OSError) and str(cause).startswith("Tunnel connection failed:"):
            kind = "proxy_error"
        else:
            kind = "network_error"
        # Exception messages can contain authenticated URLs; retain only types and fixed categories.
        self.mark(stage, exception_type=type(error).__name__, cause_type=type(cause).__name__,
                  network_error_stage=stage, error_kind=kind)


def observe_open(open_request: Callable[..., Any], request: Any, *, timeout: int):
    observation = _CURRENT.get()
    if observation:
        observation.mark("open", timeout_seconds=timeout)
    try:
        response = open_request(request, timeout=timeout)
    except Exception as error:
        if observation:
            observation.failure("open", error)
        raise
    if observation:
        status = getattr(response, "status", None)
        observation.mark("response_headers", http_status=status if isinstance(status, int) else None)
    return response


def observe_read(response: Any, size: int) -> bytes:
    observation = _CURRENT.get()
    if observation:
        observation.mark("body_read")
    try:
        body = response.read(size)
    except Exception as error:
        if observation:
            observation.failure("body_read", error)
        raise
    if observation:
        observation.mark("body_read_completed", response_bytes=len(body))
    return body
