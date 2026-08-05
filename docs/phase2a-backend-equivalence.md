# UAEA Phase-2A-2 Backend Equivalence Validation

## Purpose

Phase-2A-2 verifies that inference implementations can change behind the
`ModelBackend` contract without changing the frozen Phase-1 Runtime lifecycle.
This is a control-plane equivalence check, not a claim that a deterministic
mock has the same language quality as DS14B.

## Boundary Review

```text
Frozen Phase-1 Agent
  -> ModelClient.chat(...)
  -> ModelBackend.generate(InferenceRequest)
  -> InferenceResponse or structured InferenceError
```

Prompt construction, action interpretation, Workflow state, Observations,
Artifact lifecycle, and recovery remain owned by Phase-1. Backends only convert
an engine-neutral request into generated text and inference metadata.

The Runtime does not receive LLaMA-Factory, OpenAI wire-format, Transformers,
bnb, CUDA, or quantization objects.

## Compared Backends

### LMFBackend

Production adapter for the existing OpenAI-compatible LLaMA-Factory API. It
owns HTTP transport, response conversion, latency and token metadata, and
structured transport errors.

### MockBackend

Deterministic validation adapter with no network dependency. It records input
requests, returns stable responses, and can emit timeout, unavailable, or
invalid-response failures through the same `InferenceError` contract.

## Equivalence Contract

| Component | Expected |
|---|---|
| Workflow lifecycle | Identical and owned by Phase-1 |
| Artifact state | Identical and owned by Phase-1 |
| Recovery behavior | Identical controlled failure boundary |
| Observation format | Identical Runtime-owned format |
| Backend metadata | Backend-specific |

Backend switching is performed by dependency injection into the Phase-2
Runtime factory. The constructed Agent type and frozen lifecycle implementation
do not change.

## Validation Coverage

Contract tests cover normal generation, metadata preservation, timeout,
unavailable backend, invalid response, Phase-1-compatible `RuntimeError`
conversion, and backend switching.

The frozen L0-L6 benchmark remains the regression authority for Workflow,
Artifact, Context, and recovery semantics.

## Verification Result

```text
Phase-2 backend tests: 17 passed, 0 failed
Frozen Phase-1 L0-L6/core benchmark: 24 passed, 0 failed
Phase-1 submodule status: clean at de0ecb0
```

A real `python main.py` smoke request was sent through `LMFBackend` to the
existing local LLaMA-Factory-compatible API. The request completed in about
320.1 seconds and produced successful `document.read_section` execution, a
Semantic Observation, a `COMPLETE` Workflow Artifact, and `finish_reason=stop`.
The high latency is an inference performance observation, not a backend
contract or Runtime lifecycle failure.

## Conclusion

Inference backend selection is an implementation detail behind `ModelClient`.
Future vLLM or API adapters must implement the same request, response, and error
contract and pass the frozen Phase-1 regression suite.

`VLLMBackend` now implements this contract. Its adapter-level equivalence is
covered by contract tests; real-model semantic equivalence remains pending a
running vLLM service.
