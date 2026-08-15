from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, Sequence

from backend.model_client import ModelBackend
from backend.models import InferenceRequest
from backend.trace import TraceSink, TracingBackend


@dataclass(frozen=True)
class WorkloadCase:
    case_id: str
    category: str
    messages: list[dict[str, Any]]
    max_tokens: int = 256
    temperature: float = 0.1
    generation_config: dict[str, Any] = field(default_factory=dict)
    trace_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkSample:
    case_id: str
    category: str
    backend: str
    model: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    ttft_ms: float | None
    tokens_per_second: float | None
    sm_utilization_percent: float | None
    vram_used_mb: float | None
    kv_cache_used_mb: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SystemMetricsCollector(Protocol):
    def sample(self) -> dict[str, float | None]:
        ...


class NullSystemMetricsCollector:
    def sample(self) -> dict[str, float | None]:
        return {
            "sm_utilization_percent": None,
            "vram_used_mb": None,
            "kv_cache_used_mb": None,
        }


class InferenceBenchmarkRunner:
    def __init__(
        self,
        metrics_collector: SystemMetricsCollector | None = None,
        trace_sink: TraceSink | None = None,
        trace_defaults: dict[str, Any] | None = None,
    ) -> None:
        self.metrics_collector = metrics_collector or NullSystemMetricsCollector()
        self.trace_sink = trace_sink
        self.trace_defaults = dict(trace_defaults or {})

    def run(self, backend: ModelBackend, workloads: Sequence[WorkloadCase]) -> list[BenchmarkSample]:
        traced_backend: ModelBackend = backend
        if self.trace_sink is not None:
            traced_backend = TracingBackend(backend, self.trace_sink, self.trace_defaults)
        samples: list[BenchmarkSample] = []
        for workload in workloads:
            request_trace_context = {
                **self.trace_defaults,
                **dict(workload.trace_context or {}),
                "case_id": workload.case_id,
                "phase": workload.category,
            }
            result = traced_backend.generate(
                InferenceRequest(
                    messages=workload.messages,
                    max_tokens=workload.max_tokens,
                    temperature=workload.temperature,
                    request_id=workload.case_id,
                    generation_config=dict(workload.generation_config or {}),
                    trace_context=request_trace_context,
                )
            )
            physical = self.metrics_collector.sample()
            metadata = result.metadata
            samples.append(
                BenchmarkSample(
                    case_id=workload.case_id,
                    category=workload.category,
                    backend=metadata.backend,
                    model=metadata.model,
                    finish_reason=metadata.finish_reason,
                    prompt_tokens=metadata.usage.prompt_tokens,
                    completion_tokens=metadata.usage.completion_tokens,
                    latency_ms=metadata.latency_ms,
                    ttft_ms=metadata.ttft_ms,
                    tokens_per_second=metadata.tokens_per_second,
                    sm_utilization_percent=physical.get("sm_utilization_percent"),
                    vram_used_mb=physical.get("vram_used_mb"),
                    kv_cache_used_mb=physical.get("kv_cache_used_mb"),
                )
            )
        return samples
