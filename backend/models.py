from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_mapping(cls, usage: Mapping[str, Any] | None) -> "TokenUsage":
        values = dict(usage or {})
        prompt_tokens = _safe_int(values.get("prompt_tokens"))
        completion_tokens = _safe_int(values.get("completion_tokens"))
        total_tokens = _safe_int(values.get("total_tokens")) or prompt_tokens + completion_tokens
        return cls(prompt_tokens, completion_tokens, total_tokens)

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True)
class InferenceRequest:
    messages: Sequence[Mapping[str, Any]]
    task_type: str = "semantic_inference"
    context_metadata: Mapping[str, Any] = field(default_factory=dict)
    generation_config: Mapping[str, Any] = field(default_factory=dict)
    trace_context: Mapping[str, Any] = field(default_factory=dict)
    max_tokens: int = 256
    temperature: float = 0.1
    request_id: str = ""


@dataclass(frozen=True)
class InferenceError:
    code: str
    message: str
    retryable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }


@dataclass(frozen=True)
class InferenceMetadata:
    backend: str
    model: str
    finish_reason: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    ttft_ms: float | None = None
    tokens_per_second: float | None = None
    backend_metadata: Mapping[str, Any] = field(default_factory=dict)
    trace_id: str = ""


@dataclass(frozen=True)
class InferenceResponse:
    text: str
    backend: str
    model: str
    finish_reason: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    ttft_ms: float | None = None
    tokens_per_second: float | None = None
    backend_metadata: Mapping[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    error: InferenceError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def content(self) -> str:
        return self.text

    @property
    def metadata(self) -> InferenceMetadata:
        return InferenceMetadata(
            backend=self.backend,
            model=self.model,
            finish_reason=self.finish_reason,
            usage=self.usage,
            latency_ms=self.latency_ms,
            ttft_ms=self.ttft_ms,
            tokens_per_second=self.tokens_per_second,
            backend_metadata=self.backend_metadata,
            trace_id=self.trace_id,
        )


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
