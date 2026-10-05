from __future__ import annotations

import contextvars
import functools
import inspect
import json
import logging
import os
import re
import stat
import threading
import time
import weakref
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


START_TAG = "<tool_call>"
END_TAG = "</tool_call>"
SCHEMA = "uaea.generation_diagnostic.v1"


class GenerationDiagnostics:
    """Bounded side-channel observations; never supplies a parser result."""

    def __init__(self, path: Path, *, max_bytes: int = 8 * 1024 * 1024,
                 fragment_chars: int = 4096, max_chunks: int = 256) -> None:
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.fragment_chars = fragment_chars
        self.max_chunks = max_chunks
        self._lock = threading.Lock()
        self._sequence = 0
        self._limited = False
        self._scope: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
            "uaea_generation_diagnostic", default=None,
        )
        self._contexts: weakref.WeakKeyDictionary[Any, dict[str, Any]] = weakref.WeakKeyDictionary()
        self._secrets = tuple(value for name, value in os.environ.items()
                              if re.search(r"KEY|TOKEN|PASSWORD|SECRET", name, re.I) and len(value) >= 8)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise ValueError("Generation diagnostic destination must be a regular file")
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        self._bytes = os.fstat(fd).st_size
        self._file = os.fdopen(fd, "a", encoding="utf-8")

    def redact(self, text: str) -> str:
        for secret in self._secrets:
            text = text.replace(secret, "[REDACTED]")
        # Redact before truncation, including incomplete secret values in a stream.
        text = re.sub(r"https?://[^\s\"<>]+", self._redact_url, text, flags=re.I)
        text = re.sub(
            r'''(?i)((?:["']?)(?:api[_-]?key|serpapi_key|authorization|password|access_token|secret|token)(?:["']?)\s*[:=]\s*)[^\n,}]*''',
            r"\1[REDACTED]", text,
        )
        text = re.sub(r"(?i)\bBearer\s+[^\s\"']*", "Bearer [REDACTED]", text)
        return re.sub(r"\b[A-Za-z0-9_-]{48,}\b", "[REDACTED_LONG_TOKEN]", text)

    @staticmethod
    def _redact_url(match: re.Match[str]) -> str:
        url = match.group(0)
        url = re.sub(r"(https?://)[^/@]+@", r"\1[REDACTED]@", url, flags=re.I)
        return url.split("?", 1)[0].split("#", 1)[0] + (
            "?[REDACTED]" if "?" in url or "#" in url else ""
        )

    def fragment(self, text: str) -> dict[str, Any]:
        safe_text = self.redact(text)
        start = safe_text.find(START_TAG)
        # No prompts/history; only generated tool regions plus a short text boundary.
        redacted = safe_text[max(0, start - 96):] if start >= 0 else safe_text[-256:]
        was_redacted = safe_text != text
        truncated = len(redacted) > self.fragment_chars
        if truncated:
            half = self.fragment_chars // 2
            redacted = redacted[:half] + "\n[DIAGNOSTIC_TRUNCATED]\n" + redacted[-half:]
        return {"generated_chars": len(text), "tool_start_tags": text.count(START_TAG),
                "tool_end_tags": text.count(END_TAG), "fragment": redacted,
                "fragment_truncated": truncated, "fragment_redacted": was_redacted}

    def _safe_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.redact(value)[:self.fragment_chars + 64]
        if isinstance(value, dict):
            return {key: self._safe_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._safe_value(item) for item in value]
        return value

    def record(self, stage: str, **payload: Any) -> None:
        try:
            with self._lock:
                if self._limited or self._file.closed:
                    return
                self._sequence += 1
                row = {"schema": SCHEMA, "sequence": self._sequence,
                       "observed_at": datetime.now(timezone.utc).isoformat(),
                       "monotonic_ns": time.monotonic_ns(), "source": "uaea.vllm_diagnostic_observer",
                       "stage": stage, **self._safe_value(payload)}
                line = json.dumps(row, ensure_ascii=True) + "\n"
                size = len(line.encode("utf-8"))
                if self._bytes + size > self.max_bytes - 1024:
                    self._limited = True
                    row = {"schema": SCHEMA, "sequence": self._sequence,
                           "stage": "diagnostic_limit", "max_bytes": self.max_bytes}
                    line = json.dumps(row) + "\n"
                    if self._bytes + len(line) > self.max_bytes:
                        return
                self._file.write(line)
                self._file.flush()
                self._bytes += len(line.encode("utf-8"))
        except Exception:
            # Diagnostic I/O must not change generation/parser success or failure.
            pass

    def observe(self, callback: Callable[[], Any]) -> Any:
        try:
            return callback()
        except Exception:
            return None

    def parser_wrapper(self, original: Callable[..., Any], *, streaming: bool) -> Callable[..., Any]:
        signature = inspect.signature(original)

        @functools.wraps(original)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            def prepare() -> dict[str, Any]:
                values = signature.bind(*args, **kwargs).arguments
                request = values.get("request")
                text = values.get("current_text" if streaming else "model_output", "")
                scope = {"response_id": getattr(request, "request_id", None),
                         "parser_mode": "streaming" if streaming else "full",
                         "parser_error_observed": False}
                self.record("hermes_input", **scope, **self.fragment(text),
                            previous_chars=len(values.get("previous_text", "")),
                            delta_chars=len(values.get("delta_text", "")),
                            max_output_tokens=getattr(request, "max_output_tokens", None),
                            skip_special_tokens=getattr(request, "skip_special_tokens", None))
                return scope

            scope = self.observe(prepare) or {}
            token = self._scope.set(scope)
            try:
                result = original(*args, **kwargs)
                self.observe(lambda: self.record(
                    "hermes_outcome", **scope,
                    tools_called=getattr(result, "tools_called", None),
                    tool_call_count=len(getattr(result, "tool_calls", None) or []),
                    content_chars=len(getattr(result, "content", None) or ""),
                    returned_none=result is None,
                ))
                return result
            except Exception as exc:
                self.record("parser_raised", **scope, exception_type=type(exc).__name__)
                raise
            finally:
                self._scope.reset(token)

        return wrapped

    def generation_wrapper(self, original: Callable[..., Any], *, streaming: bool) -> Callable[..., Any]:
        @functools.wraps(original)
        def wrapped(context: Any, output: Any, *args: Any, **kwargs: Any) -> Any:
            def observe_output() -> None:
                completion = output.outputs[0]
                state = self._contexts.setdefault(context, {"chunks": 0, "tokens": 0, "last_chunks": []})
                state["chunks"] += 1
                state["tokens"] += len(completion.token_ids or [])
                previous = getattr(context, "_accumulated_text", "") if streaming else ""
                chunk = {"chunk_index": state["chunks"], "char_start": len(previous),
                         "char_end": len(previous) + len(completion.text),
                         "delta_chars": len(completion.text), "delta_tokens": len(completion.token_ids or [])}
                state["last_chunks"] = (state["last_chunks"] + [chunk])[-8:]
                identity = {"engine_request_id": output.request_id}
                if not streaming:
                    identity["response_id"] = getattr(getattr(context, "request", None), "request_id", None)
                terminal = bool(output.finished or completion.finish_reason is not None)
                if state["chunks"] <= self.max_chunks:
                    self.record("generation_chunk", **identity, **chunk, finished=terminal)
                if terminal:
                    self.record("generation_finished", **identity,
                                finish_reason=completion.finish_reason,
                                stop_reason=completion.stop_reason, output_finished=output.finished,
                                chunk_count=state["chunks"], generated_tokens=state["tokens"],
                                chunk_metadata_truncated=state["chunks"] > self.max_chunks,
                                last_chunks=state["last_chunks"], **self.fragment(previous + completion.text))

            self.observe(observe_output)
            return original(context, output, *args, **kwargs)

        return wrapped

    def error_handler(self) -> logging.Handler:
        owner = self

        class Handler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                def observe_error() -> None:
                    scope = owner._scope.get()
                    if scope is None:
                        return
                    scope["parser_error_observed"] = True
                    exc = record.exc_info[1] if record.exc_info else None
                    owner.record("hermes_error", **scope,
                                 exception_type=type(exc).__name__ if exc else None,
                                 json_error_line=getattr(exc, "lineno", None),
                                 json_error_column=getattr(exc, "colno", None),
                                 json_error_position=getattr(exc, "pos", None))
                owner.observe(observe_error)

        return Handler(level=logging.ERROR)

    def close(self) -> None:
        with self._lock:
            self._file.close()


def install_generation_diagnostics(path: Path) -> GenerationDiagnostics:
    """Opt-in, process-local hooks for the installed vLLM Responses/Hermes surface."""
    import vllm
    from vllm.entrypoints.openai.responses.context import ParsableContext, SimpleContext
    from vllm.tool_parsers.hermes_tool_parser import Hermes2ProToolParser, logger

    recorder = GenerationDiagnostics(path)
    Hermes2ProToolParser.extract_tool_calls = recorder.parser_wrapper(
        Hermes2ProToolParser.extract_tool_calls, streaming=False,
    )
    Hermes2ProToolParser.extract_tool_calls_streaming = recorder.parser_wrapper(
        Hermes2ProToolParser.extract_tool_calls_streaming, streaming=True,
    )
    SimpleContext.append_output = recorder.generation_wrapper(SimpleContext.append_output, streaming=True)
    ParsableContext.append_output = recorder.generation_wrapper(ParsableContext.append_output, streaming=False)
    logger.addHandler(recorder.error_handler())
    recorder.record("diagnostic_installed", vllm_version=vllm.__version__,
                    parser_class="Hermes2ProToolParser", fragment_chars=recorder.fragment_chars,
                    max_chunks=recorder.max_chunks, max_bytes=recorder.max_bytes,
                    behavior="observe_only", prompt_recording=False)
    return recorder
