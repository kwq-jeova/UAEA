from __future__ import annotations

from typing import Any

from .interface import InferenceRequest, ModelBackend


class Phase1ModelClientBridge:
    """Expose a ModelBackend through the frozen Phase-1 ModelClient contract."""

    def __init__(self, backend: ModelBackend) -> None:
        self.backend = backend
        self.model_name = backend.model_name
        self.last_finish_reason: str | None = None
        self.last_usage: dict[str, Any] | None = None
        self.last_inference_metadata = None

    def chat(self, messages: list[dict], max_tokens: int = 256, temperature: float = 0.1) -> str:
        result = self.backend.generate(
            InferenceRequest(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        )
        self.last_inference_metadata = result.metadata
        self.last_finish_reason = result.metadata.finish_reason
        self.last_usage = result.metadata.usage.to_dict()
        return result.content
