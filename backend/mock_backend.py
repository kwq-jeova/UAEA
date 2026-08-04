from __future__ import annotations

from typing import Literal

from .models import InferenceError, InferenceRequest, InferenceResponse, TokenUsage


FailureMode = Literal["timeout", "unavailable", "invalid_response"]


class MockBackend:
    """Deterministic backend for validating the engine-neutral contract."""

    def __init__(
        self,
        response_text: str = "mock response",
        failure_mode: FailureMode | None = None,
        model_name: str = "mock-model",
    ) -> None:
        self.response_text = response_text
        self.failure_mode = failure_mode
        self._model_name = model_name
        self.requests: list[InferenceRequest] = []

    @property
    def backend_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        self.requests.append(request)
        if self.failure_mode is not None:
            return self._failure_response(self.failure_mode)

        completion_tokens = max(1, len(self.response_text.split()))
        prompt_tokens = sum(len(str(message.get("content", "")).split()) for message in request.messages)
        return InferenceResponse(
            text=self.response_text,
            backend=self.backend_name,
            model=self.model_name,
            finish_reason="stop",
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            latency_ms=0.0,
        )

    def _failure_response(self, mode: FailureMode) -> InferenceResponse:
        messages = {
            "timeout": "Mock inference timed out.",
            "unavailable": "Mock inference backend is unavailable.",
            "invalid_response": "Mock backend produced an invalid response.",
        }
        return InferenceResponse(
            text="",
            backend=self.backend_name,
            model=self.model_name,
            finish_reason="error",
            error=InferenceError(
                code=mode,
                message=messages[mode],
                retryable=mode in {"timeout", "unavailable"},
            ),
        )
