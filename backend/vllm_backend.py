from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any

from .models import InferenceError, InferenceRequest, InferenceResponse, TokenUsage


class VLLMBackend:
    """Adapter for a vLLM OpenAI-compatible HTTP server."""

    default_temperature = 0.2
    default_chat_template_kwargs = {"enable_thinking": False}

    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_seconds: int = 300,
        api_key: str = "uaea-local",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key

    @property
    def backend_name(self) -> str:
        return "vllm"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        payload = {
            "model": self.model_name,
            "messages": [dict(message) for message in request.messages],
            "temperature": max(float(request.temperature), self.default_temperature),
            "max_tokens": request.max_tokens,
            "chat_template_kwargs": dict(self.default_chat_template_kwargs),
        }
        http_request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        started_at = time.monotonic()
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
            data = json.loads(raw_body)
            return self._success_response(data, started_at)
        except (TimeoutError, socket.timeout):
            elapsed = time.monotonic() - started_at
            return self._error_response(
                started_at,
                "timeout",
                f"vLLM API request timed out after {elapsed:.1f}s "
                f"(client timeout={self.timeout_seconds}s).",
                retryable=True,
            )
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except OSError:
                body = ""
            return self._error_response(
                started_at,
                f"http_{exc.code}",
                f"vLLM API HTTP {exc.code}: {body[:1000]}",
                retryable=exc.code == 429 or exc.code >= 500,
            )
        except urllib.error.URLError as exc:
            return self._error_response(
                started_at,
                "unavailable",
                f"vLLM API request failed: {exc}",
                retryable=True,
            )
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as exc:
            return self._error_response(
                started_at,
                "invalid_response",
                f"vLLM API returned an invalid response: {exc}",
            )
        except OSError as exc:
            return self._error_response(
                started_at,
                "transport_error",
                f"vLLM API transport failed: {exc}",
                retryable=True,
            )

    def _success_response(self, data: dict[str, Any], started_at: float) -> InferenceResponse:
        choice = data["choices"][0]
        text = choice["message"]["content"]
        if not isinstance(text, str):
            raise ValueError("choices[0].message.content must be a string")
        usage = TokenUsage.from_mapping(data.get("usage"))
        latency_ms = (time.monotonic() - started_at) * 1000
        tokens_per_second = None
        if latency_ms > 0 and usage.completion_tokens > 0:
            tokens_per_second = usage.completion_tokens / (latency_ms / 1000)
        return InferenceResponse(
            text=text,
            backend=self.backend_name,
            model=self.model_name,
            finish_reason=str(choice.get("finish_reason") or ""),
            usage=usage,
            latency_ms=latency_ms,
            ttft_ms=None,
            tokens_per_second=tokens_per_second,
        )

    def _error_response(
        self,
        started_at: float,
        code: str,
        message: str,
        retryable: bool = False,
    ) -> InferenceResponse:
        return InferenceResponse(
            text="",
            backend=self.backend_name,
            model=self.model_name,
            finish_reason="error",
            latency_ms=(time.monotonic() - started_at) * 1000,
            error=InferenceError(code=code, message=message, retryable=retryable),
        )
