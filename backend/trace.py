from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable
from uuid import uuid4

from .models import InferenceRequest, InferenceResponse


@dataclass(frozen=True)
class TokenizerTrace:
    name: str = ""
    path: str = ""
    revision: str = ""
    chat_template_hash: str = ""


@dataclass(frozen=True)
class StopDetail:
    matched_stop: str = ""
    matched_eos: bool = False
    length_limited: bool = False


@dataclass(frozen=True)
class InferenceTraceRecord:
    trace_id: str
    request_id: str
    case_id: str
    phase: str
    backend: str
    model_artifact: str
    model_version: str
    tokenizer: TokenizerTrace
    rendered_prompt: str
    input_tokens: int
    input_token_ids: list[int] = field(default_factory=list)
    generation_config: dict[str, Any] = field(default_factory=dict)
    output_text_excerpt: str = ""
    output_tokens: int = 0
    output_token_ids: list[int] = field(default_factory=list)
    finish_reason: str = ""
    stop_detail: StopDetail = field(default_factory=StopDetail)
    latency_ms: float = 0.0
    ttft_ms: float | None = None
    tokens_per_second: float | None = None
    backend_metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class TraceSink(Protocol):
    def write(self, record: InferenceTraceRecord) -> None:
        ...


class JsonlTraceSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: InferenceTraceRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


class TracingBackend:
    """Backend decorator that emits inference trace records outside Phase-1 Runtime."""

    def __init__(
        self,
        backend: Any,
        trace_sink: TraceSink | None = None,
        trace_defaults: Mapping[str, Any] | None = None,
    ) -> None:
        self.backend = backend
        self.trace_sink = trace_sink
        self.trace_defaults = dict(trace_defaults or {})

    @property
    def backend_name(self) -> str:
        return str(getattr(self.backend, "backend_name", "") or "")

    @property
    def model_name(self) -> str:
        return str(getattr(self.backend, "model_name", "") or "")

    def generate(self, request: InferenceRequest) -> InferenceResponse:
        started_at = time.monotonic()
        response = self.backend.generate(request)
        if self.trace_sink is not None:
            try:
                record = build_trace_record(
                    request=request,
                    response=response,
                    backend_name=self.backend_name,
                    model_name=self.model_name,
                    trace_defaults=self.trace_defaults,
                    wrapper_latency_ms=(time.monotonic() - started_at) * 1000,
                )
                self.trace_sink.write(record)
            except Exception:
                # Diagnostics must never block inference completion.
                pass
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self.backend, name)


def build_trace_record(
    request: InferenceRequest,
    response: InferenceResponse,
    backend_name: str,
    model_name: str,
    trace_defaults: Mapping[str, Any] | None = None,
    wrapper_latency_ms: float | None = None,
) -> InferenceTraceRecord:
    trace_context = _merged_trace_context(request.trace_context, trace_defaults)
    metadata = _safe_dict(response.backend_metadata)
    tokenizer = _build_tokenizer_trace(trace_context, metadata)
    rendered_prompt = _render_prompt(request.messages, tokenizer, trace_context)
    input_token_ids = _tokenize_prompt(rendered_prompt, request.messages, tokenizer, trace_context)
    output_token_ids = _tokenize_text(response.text, tokenizer, trace_context)
    input_tokens = _safe_int(
        response.usage.prompt_tokens or trace_context.get("input_tokens") or len(input_token_ids)
    )
    if input_tokens <= 0:
        input_tokens = len(input_token_ids)
    output_tokens = _safe_int(
        response.usage.completion_tokens or trace_context.get("output_tokens") or len(output_token_ids)
    )
    if output_tokens <= 0:
        output_tokens = len(output_token_ids)

    trace_id = str(trace_context.get("trace_id") or response.trace_id or request.request_id or uuid4())
    request_id = str(request.request_id or trace_context.get("request_id") or trace_id)
    case_id = str(trace_context.get("case_id") or request.request_id or request.task_type or trace_id)
    phase = str(trace_context.get("phase") or _infer_phase(request.messages, request.task_type))
    model_artifact = str(
        trace_context.get("model_artifact")
        or metadata.get("model_artifact")
        or metadata.get("served_model")
        or response.model
        or model_name
    )
    model_version = str(
        trace_context.get("model_version")
        or metadata.get("model_version")
        or metadata.get("revision")
        or ""
    )
    generation_config = _build_generation_config(request, trace_context, metadata)
    stop_detail = _build_stop_detail(response, generation_config, metadata)
    error = response.error.to_dict() if response.error is not None else None
    output_text_excerpt = _excerpt(response.text, 4000)

    return InferenceTraceRecord(
        trace_id=trace_id,
        request_id=request_id,
        case_id=case_id,
        phase=phase,
        backend=str(trace_context.get("backend") or backend_name or response.backend or ""),
        model_artifact=model_artifact,
        model_version=model_version,
        tokenizer=tokenizer,
        rendered_prompt=rendered_prompt,
        input_tokens=input_tokens,
        input_token_ids=input_token_ids,
        generation_config=generation_config,
        output_text_excerpt=output_text_excerpt,
        output_tokens=output_tokens,
        output_token_ids=output_token_ids,
        finish_reason=str(response.finish_reason or ""),
        stop_detail=stop_detail,
        latency_ms=float(response.latency_ms or wrapper_latency_ms or 0.0),
        ttft_ms=response.ttft_ms,
        tokens_per_second=response.tokens_per_second,
        backend_metadata=metadata,
        error=error,
    )


def _merged_trace_context(
    request_trace_context: Mapping[str, Any] | None,
    trace_defaults: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(trace_defaults or {})
    merged.update(dict(request_trace_context or {}))
    return merged


def _safe_dict(value: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _excerpt(text: str, limit: int) -> str:
    text = str(text or "")
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... [trace excerpt truncated]"


def _infer_phase(messages: Sequence[Mapping[str, Any]], task_type: str) -> str:
    system_text = "\n".join(
        str(message.get("content") or "")
        for message in messages
        if str(message.get("role") or "").lower() == "system"
    ).lower()
    if "semantic action planner" in system_text or "planner" in system_text:
        return "planner"
    if "workflow artifact" in system_text:
        return "artifact_answer"
    if "semantic observation" in system_text or "execution observation" in system_text:
        return "observation_answer"
    if "answer ordinary questions directly" in system_text or "directly answer" in system_text:
        return "chat_answer"
    return str(task_type or "inference")


def _build_generation_config(
    request: InferenceRequest,
    trace_context: Mapping[str, Any],
    backend_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    config = dict(request.generation_config or {})
    config.setdefault("max_tokens", request.max_tokens)
    config.setdefault("temperature", request.temperature)
    config.setdefault("task_type", request.task_type)
    if trace_context.get("chat_template_kwargs") is not None:
        config.setdefault("chat_template_kwargs", dict(trace_context.get("chat_template_kwargs") or {}))
    if backend_metadata.get("chat_template_kwargs") is not None:
        config.setdefault("backend_chat_template_kwargs", dict(backend_metadata.get("chat_template_kwargs") or {}))
    return config


def _build_stop_detail(
    response: InferenceResponse,
    generation_config: Mapping[str, Any],
    backend_metadata: Mapping[str, Any],
) -> StopDetail:
    matched_stop = ""
    for key in ("matched_stop", "stop"):
        value = backend_metadata.get(key)
        if isinstance(value, str) and value.strip():
            matched_stop = value.strip()
            break
    matched_eos = bool(backend_metadata.get("matched_eos"))
    if not matched_eos:
        eos_token_id = backend_metadata.get("eos_token_id")
        if eos_token_id is not None and str(response.finish_reason or "") == "stop":
            matched_eos = True
    length_limited = str(response.finish_reason or "") == "length"
    if not length_limited:
        max_tokens = generation_config.get("max_tokens")
        if isinstance(max_tokens, int) and max_tokens > 0 and str(response.finish_reason or "") == "length":
            length_limited = True
    return StopDetail(
        matched_stop=matched_stop,
        matched_eos=matched_eos,
        length_limited=length_limited,
    )


def _build_tokenizer_trace(
    trace_context: Mapping[str, Any],
    backend_metadata: Mapping[str, Any],
) -> TokenizerTrace:
    tokenizer_name = str(
        trace_context.get("tokenizer_name")
        or trace_context.get("tokenizer")
        or backend_metadata.get("tokenizer_name")
        or backend_metadata.get("tokenizer")
        or ""
    )
    tokenizer_path = str(trace_context.get("tokenizer_path") or backend_metadata.get("tokenizer_path") or "")
    tokenizer_revision = str(
        trace_context.get("tokenizer_revision")
        or backend_metadata.get("tokenizer_revision")
        or ""
    )
    chat_template_hash = str(trace_context.get("chat_template_hash") or backend_metadata.get("chat_template_hash") or "")

    tokenizer = _load_tokenizer(
        tokenizer_path,
        tokenizer_revision,
        bool(dict(trace_context or {}).get("local_files_only", True)),
    )
    if tokenizer is not None:
        tokenizer_name = tokenizer_name or str(getattr(tokenizer, "name_or_path", "") or "")
        tokenizer_path = tokenizer_path or str(getattr(tokenizer, "name_or_path", "") or "")
        chat_template = str(getattr(tokenizer, "chat_template", "") or "")
        if chat_template and not chat_template_hash:
            chat_template_hash = hashlib.sha256(chat_template.encode("utf-8")).hexdigest()

    return TokenizerTrace(
        name=tokenizer_name,
        path=tokenizer_path,
        revision=tokenizer_revision,
        chat_template_hash=chat_template_hash,
    )


@lru_cache(maxsize=8)
def _load_tokenizer(
    tokenizer_path: str,
    tokenizer_revision: str,
    local_files_only: bool,
):
    if not tokenizer_path:
        return None
    try:
        from transformers import AutoTokenizer
    except Exception:
        return None
    try:
        return AutoTokenizer.from_pretrained(
            tokenizer_path,
            revision=tokenizer_revision or None,
            local_files_only=local_files_only,
            trust_remote_code=True,
        )
    except Exception:
        return None


def _render_prompt(
    messages: Sequence[Mapping[str, Any]],
    tokenizer: TokenizerTrace,
    trace_context: Mapping[str, Any],
) -> str:
    rendered_prompt = str(trace_context.get("rendered_prompt") or "")
    if rendered_prompt:
        return rendered_prompt
    tokenizer_obj = _load_tokenizer(
        tokenizer.path,
        tokenizer.revision,
        bool(dict(trace_context or {}).get("local_files_only", True)),
    )
    if tokenizer_obj is not None and hasattr(tokenizer_obj, "apply_chat_template"):
        chat_template_kwargs = dict(trace_context.get("chat_template_kwargs") or {})
        add_generation_prompt = bool(trace_context.get("add_generation_prompt", True))
        try:
            rendered = tokenizer_obj.apply_chat_template(
                [dict(message) for message in messages],
                tokenize=False,
                add_generation_prompt=add_generation_prompt,
                **chat_template_kwargs,
            )
            if isinstance(rendered, str) and rendered.strip():
                return rendered
        except Exception:
            pass
    return _canonical_render_messages(messages)


def _canonical_render_messages(messages: Sequence[Mapping[str, Any]]) -> str:
    chunks: list[str] = []
    for message in messages:
        role = str(message.get("role") or "unknown").strip() or "unknown"
        content = str(message.get("content") or "")
        chunks.append(f"<|{role}|>\n{content}")
    return "\n\n".join(chunks)


def _tokenize_prompt(
    rendered_prompt: str,
    messages: Sequence[Mapping[str, Any]],
    tokenizer: TokenizerTrace,
    trace_context: Mapping[str, Any],
) -> list[int]:
    tokenizer_obj = _load_tokenizer(
        tokenizer.path,
        tokenizer.revision,
        bool(dict(trace_context or {}).get("local_files_only", True)),
    )
    if tokenizer_obj is None:
        return []
    try:
        if hasattr(tokenizer_obj, "apply_chat_template"):
            chat_template_kwargs = dict(trace_context.get("chat_template_kwargs") or {})
            add_generation_prompt = bool(trace_context.get("add_generation_prompt", True))
            token_ids = tokenizer_obj.apply_chat_template(
                [dict(message) for message in messages],
                tokenize=True,
                add_generation_prompt=add_generation_prompt,
                return_tensors=None,
                **chat_template_kwargs,
            )
            if isinstance(token_ids, list):
                return [int(token_id) for token_id in token_ids]
            if token_ids is not None:
                return [int(token_id) for token_id in list(token_ids)]
        tokenized = tokenizer_obj.encode(rendered_prompt, add_special_tokens=False)
        return [int(token_id) for token_id in tokenized]
    except Exception:
        return []


def _tokenize_text(
    text: str,
    tokenizer: TokenizerTrace,
    trace_context: Mapping[str, Any],
) -> list[int]:
    tokenizer_obj = _load_tokenizer(
        tokenizer.path,
        tokenizer.revision,
        bool(dict(trace_context or {}).get("local_files_only", True)),
    )
    if tokenizer_obj is None:
        return []
    try:
        tokenized = tokenizer_obj.encode(str(text or ""), add_special_tokens=False)
        return [int(token_id) for token_id in tokenized]
    except Exception:
        return []
