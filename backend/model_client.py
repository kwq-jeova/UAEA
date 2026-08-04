from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .models import InferenceRequest, InferenceResponse


@runtime_checkable
class ModelBackend(Protocol):
    @property
    def backend_name(self) -> str:
        ...

    @property
    def model_name(self) -> str:
        ...

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        ...


class ModelClient:
    """Engine-neutral client plus the frozen Phase-1 chat compatibility surface."""

    def __init__(self, backend: ModelBackend) -> None:
        self.backend = backend
        self.model_name = backend.model_name
        self.last_finish_reason: str | None = None
        self.last_usage: dict[str, Any] | None = None
        self.last_response: InferenceResponse | None = None

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        response = self.backend.generate(request)
        self.last_response = response
        self.last_finish_reason = response.finish_reason or ("error" if response.error else None)
        self.last_usage = response.usage.to_dict()
        return response

    def chat(self, messages: list[dict], max_tokens: int = 256, temperature: float = 0.1) -> str:
        response = self.generate(
            InferenceRequest(
                task_type="phase1_runtime",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        )
        if response.error is not None:
            raise RuntimeError(response.error.message)
        return response.text
