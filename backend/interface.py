from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_mapping(cls, usage: Mapping[str, Any] | None) -> "TokenUsage":
        values = dict(usage or {})
        prompt_tokens = int(values.get("prompt_tokens") or 0)
        completion_tokens = int(values.get("completion_tokens") or 0)
        total_tokens = int(values.get("total_tokens") or prompt_tokens + completion_tokens)
        return cls(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True)
class InferenceRequest:
    messages: Sequence[Mapping[str, Any]]
    max_tokens: int = 256
    temperature: float = 0.1
    request_id: str = ""


@dataclass(frozen=True)
class InferenceMetadata:
    backend: str
    model: str
    finish_reason: str = ""
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    ttft_ms: float | None = None
    tokens_per_second: float | None = None


@dataclass(frozen=True)
class InferenceResult:
    content: str
    metadata: InferenceMetadata


@runtime_checkable
class ModelBackend(Protocol):
    @property
    def backend_name(self) -> str:
        ...

    @property
    def model_name(self) -> str:
        ...

    def generate(self, request: InferenceRequest) -> InferenceResult:
        ...
