# UAEA Phase-2A-1 Model Backend API

## 1. Motivation

Phase-1 correctly separated model proposals from Runtime lifecycle authority,
but its launcher still constructed an HTTP client tied directly to the current
OpenAI-compatible LLaMA-Factory endpoint. Phase-2A-1 removes that physical
dependency from the Phase-2 runtime entry without changing any Phase-1
lifecycle behavior.

## 2. Current Phase-1 Call Path

```text
Frozen Agent
  -> model.chat(messages, max_tokens, temperature)
  -> POST /v1/chat/completions
  -> choices[0].message.content
  -> Phase-1 action / observation / answer parsing
```

Phase-1 remains responsible for prompt construction, context projection,
structured action parsing, semantic observation parsing, finish-reason handling,
Artifact lifecycle, and recovery.

## 3. New Flow

```text
Frozen Agent
  -> backend.model_client.ModelClient
  -> selected backend adapter
       -> LMFBackend  -> OpenAI-compatible LLaMA-Factory API
       -> VLLMBackend -> OpenAI-compatible vLLM API
```

The Phase-2A launcher is `main.py`. It constructs the frozen Agent through
`phase2.runtime_factory.build_agent()` and injects the new ModelClient through
the existing Phase-1 constructor boundary.

No file in `runtime/phase1-runtime` is modified.

The frozen repository still contains its historical direct client for release
reproducibility. Phase-2A development uses the parent repository `main.py`
entry, which injects the replaceable backend client instead.

## 4. API Objects

`backend/models.py` defines:

- `InferenceRequest`: task type, messages, bounded context metadata, generation
  budget, temperature, and request identity.
- `InferenceResponse`: generated text, backend/model identity, token usage,
  latency, finish reason, throughput, and controlled error information.
- `InferenceError`: stable error code, message, and retryability signal.

`backend/model_client.py` defines the engine-neutral `ModelBackend` protocol and
the `ModelClient` facade. `ModelClient.generate()` returns structured responses;
`ModelClient.chat()` preserves the frozen Phase-1 contract and converts backend
errors into `RuntimeError` so existing timeout and PARTIAL Artifact behavior is
unchanged.

## 5. LMF Adapter

`LMFBackend` owns only transport conversion:

- constructs the OpenAI-compatible request
- sends it to `/chat/completions`
- converts choices, finish reason, usage, and latency
- converts unavailable, timeout, HTTP, transport, and invalid-response failures
  into controlled `InferenceError` values

It does not construct prompts or interpret task semantics.

## 6. Extension Plan

```text
ModelClient
  -> LMFBackend
  -> VLLMBackend
  -> future APIModelBackend
```

Future backends must return the same `InferenceResponse` and must not change
Goal, Workflow, Artifact, Context, or recovery semantics.

Backend validation tests are located under `tests/backend/` and run with:

```text
python -m unittest discover -s tests -t . -v
```

## Phase-2A Progress

- Phase-2A-1 Model Backend API: DONE
- Phase-2A-2 Backend Equivalence Validation: DONE
- Phase-2A-3 vLLM Backend Adapter: DONE (real smoke pending service)
- Current production backend: `LMFBackend`
- Deterministic validation backend: `MockBackend`
- Available alternate adapter: `VLLMBackend`
- Future adapter: external API backend

The equivalence contract and validation scope are documented in
`docs/phase2a-backend-equivalence.md`.

## 7. Inference Runtime Interface Evolution

Current assessment:

```text
Current ModelBackend contract is adequate as a transport abstraction.
It is not yet adequate as a traceable inference runtime abstraction.
```

It can support future adapters for vLLM, TensorRT-LLM, SGLang, OpenAI API, and
local transformers as long as each adapter can map requests into:

```text
InferenceRequest -> InferenceResponse
```

However, backend equivalence requires richer diagnostics than the Runtime needs.
Phase-2 should evolve the interface additively:

```text
InferenceRequest
  -> messages
  -> generation_config
  -> context_metadata
  -> trace_context
  -> request_id

InferenceResponse
  -> text
  -> token_usage
  -> finish_reason
  -> latency_ms
  -> backend_metadata
  -> error
  -> trace_id
```

Trace-level fields such as rendered prompt, tokenizer metadata, input token ids,
stop/eos detail, and backend kernel metadata should live in the inference trace
layer, not in the frozen Agent Runtime.

See:

```text
docs/inference-trace-layer-design.md
docs/phase2a-equivalence-matrix.md
```
