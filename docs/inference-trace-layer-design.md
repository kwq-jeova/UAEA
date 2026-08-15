# UAEA Inference Trace Layer Design

> 目标：为 UAEA 建立独立于 Agent Runtime 的 inference 可观测层，使 backend migration 可以被归因、复现和比较。

## 1. Design Principle

Phase-1 是 Cognitive Runtime Freeze：

```text
User / Task
  -> Agent Runtime
  -> Goal / Workflow / Observation / Artifact
```

Phase-2A 是 Inference Runtime Abstraction：

```text
Agent Runtime
  -> ModelBackend Contract
  -> Backend Adapter
  -> Inference Engine
```

Inference Trace Layer 位于 backend adapter / benchmark diagnostic layer，不进入 Agent Runtime 核心逻辑。

目标类似 Linux 的：

- tracepoint
- ftrace
- perf

即：应用层语义稳定，底层 kernel/backend 可以替换，同时每次替换都有可观测证据。

## 2. Current Contract Assessment

当前 `ModelBackend` contract 已经足够支撑最小 backend 替换：

```text
ModelBackend.generate(InferenceRequest) -> InferenceResponse
ModelClient.chat(...) -> frozen Phase-1 compatibility surface
```

当前 request/response 已覆盖：

- chat messages
- max token budget
- temperature
- request id
- generated text
- backend/model identity
- token usage
- finish reason
- latency
- structured error

这足以支持：

- LMF / LLaMA-Factory OpenAI-compatible API
- vLLM OpenAI-compatible API
- OpenAI API style adapter
- local transformers adapter
- SGLang / TensorRT-LLM through a dedicated adapter

但它还不足以支撑科学的 backend equivalence validation，因为它没有标准化记录：

- rendered prompt
- input token ids
- tokenizer identity
- complete generation config
- stop/eos detail
- model artifact identity
- backend-specific runtime metadata

结论：

```text
Current contract is adequate as a transport abstraction.
It is not yet adequate as a traceable inference runtime abstraction.
```

## 3. Inference Trace Record

建议新增的 trace record：

```json
{
  "trace_id": "uuid-or-stable-id",
  "request_id": "runtime-request-id",
  "case_id": "benchmark-case-id",
  "phase": "planner|observation_answer|artifact_answer|chat_answer",
  "backend": "lmf|vllm|transformers|openai|sglang|tensorrt_llm",
  "engine": "llama-factory|vllm|transformers|openai|sglang|tensorrt-llm",
  "model_artifact": "artifact-name-or-path",
  "model_version": "revision-or-hash",
  "tokenizer": {
    "name": "tokenizer-name",
    "path": "tokenizer-path",
    "revision": "revision-or-hash",
    "chat_template_hash": "sha256-or-empty"
  },
  "messages": [
    {"role": "system", "content_excerpt": "..."},
    {"role": "user", "content_excerpt": "..."}
  ],
  "rendered_prompt": "backend-rendered-prompt-if-available",
  "input_tokens": 0,
  "input_token_ids": [],
  "generation_config": {
    "max_tokens": 0,
    "temperature": 0.0,
    "top_p": null,
    "top_k": null,
    "repetition_penalty": null,
    "stop": [],
    "eos_token_id": null,
    "pad_token_id": null,
    "enable_thinking": null
  },
  "output_text_excerpt": "...",
  "output_tokens": 0,
  "output_token_ids": [],
  "finish_reason": "stop|length|error",
  "stop_detail": {
    "matched_stop": null,
    "matched_eos": false,
    "length_limited": false
  },
  "latency_ms": 0.0,
  "ttft_ms": null,
  "tokens_per_second": null,
  "backend_metadata": {},
  "error": {
    "code": "",
    "message": "",
    "retryable": false
  }
}
```

## 4. Placement

Trace emission should live here:

```text
Backend Adapter
  -> Trace Builder
  -> Trace Sink
```

Not here:

```text
Agent Runtime
  -> Workflow / Artifact / Observation logic
```

The Agent Runtime may continue to see only:

```text
ModelClient.chat(...)
```

and Phase-2A may separately collect:

```text
InferenceTraceRecord
```

## 5. Trace Sink

Recommended initial sink:

```text
data/inference_traces/*.jsonl
```

Each record is append-only. A later storage layer may map this to SQLite or a
metrics store, but Phase-2A should start with JSONL for inspectability.

## 6. Interface Evolution

Keep the current contract shape:

```text
generate(InferenceRequest) -> InferenceResponse
```

Evolve it additively in Phase-2, not by changing Phase-1:

### Request

```text
InferenceRequest
  messages
  generation_config
  context_metadata
  trace_context
  request_id
```

### Response

```text
InferenceResponse
  text
  token_usage
  finish_reason
  latency_ms
  backend_metadata
  error
  trace_id
```

### Trace

```text
InferenceTraceRecord
  rendered_prompt
  token ids
  tokenizer metadata
  generation config
  stop detail
  backend metadata
```

The trace record should be richer than the Runtime-facing response. Runtime
does not need token ids or backend kernel details to maintain cognition state.

## 7. Backend Support Expectations

| Backend | Contract support | Trace support expectation |
| --- | --- | --- |
| LMFBackend | OpenAI-compatible request/response | Capture request payload, usage, finish reason, model artifact config |
| VLLMBackend | OpenAI-compatible request/response | Capture chat template kwargs, served model, usage, stop detail where exposed |
| TransformersBackend | local chat wrapper | Capture tokenizer/rendered prompt if direct tokenizer access exists |
| OpenAI API | remote API adapter | Capture request payload and response metadata, token ids usually unavailable |
| SGLang | adapter-specific | Capture engine config and tokenizer view when exposed |
| TensorRT-LLM | adapter-specific | Capture engine profile, tokenizer view, stop/eos details where exposed |

## 8. Non-goals

The trace layer must not:

- modify Agent Runtime planning
- modify Artifact schema
- add backend-specific branches to Runtime
- force all backends to expose token ids when the provider cannot return them
- turn migration validation into model-quality optimization

## 9. First Implementation Target

Phase-2A.1 should implement trace collection for:

- LMFBackend
- VLLMBackend
- `L0-01`
- `L0-02`
- `L1-02`

This is enough to identify whether current differences come from:

- prompt rendering
- tokenizer/token ids
- generation config
- stop/eos behavior
- model artifact behavior

