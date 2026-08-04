from __future__ import annotations

import time
from typing import Any, Protocol

from .models import InferenceRequest, InferenceResponse, TokenUsage


class Phase1ChatClient(Protocol):
    last_finish_reason: str | None
    last_usage: dict[str, Any] | None

    def chat(self, messages: list[dict], max_tokens: int = 256, temperature: float = 0.1) -> str:
        ...


class TransformersBackend:
    """Adapter for the existing LLaMA-Factory/Transformers chat path."""

    def __init__(self, client: Phase1ChatClient, model_name: str = "") -> None:
        self.client = client
        self._model_name = model_name or str(getattr(client, "model_name", "") or "")

    @property
    def backend_name(self) -> str:
        return "transformers"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        started_at = time.monotonic()
        content = self.client.chat(
            messages=[dict(message) for message in request.messages],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )
        latency_ms = (time.monotonic() - started_at) * 1000
        usage = TokenUsage.from_mapping(getattr(self.client, "last_usage", None))
        tokens_per_second = None
        if latency_ms > 0 and usage.completion_tokens > 0:
            tokens_per_second = usage.completion_tokens / (latency_ms / 1000)
        return InferenceResponse(
            text=content,
            backend=self.backend_name,
            model=self.model_name,
            finish_reason=str(getattr(self.client, "last_finish_reason", None) or ""),
            usage=usage,
            latency_ms=latency_ms,
            tokens_per_second=tokens_per_second,
        )
