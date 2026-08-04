# UAEA Phase-2A Initialization

> Objective: inference backend migration without Phase-1 lifecycle changes
> Initialized: 2026-08-04

## Phase-1 Dependency

Phase-1 is integrated as a Git submodule:

```text
runtime/phase1-runtime
```

Pinned revision:

```text
tag: v1.0.0-phase1-runtime
commit: de0ecb0e8837c848f842a996fa2dad1c93666f2f
```

The submodule remains detached at the frozen tag. Phase-2A does not patch or
shadow files inside it.

## Integrity Verification

Verification performed before adding Phase-2A code:

```text
python tests/runtime_benchmark/phase1_runtime_benchmark.py --level all --json
passed=24
failed=0
result=PASS
```

Verification after Phase-2A-1 Model Backend integration:

```text
Phase-1 scripted benchmark: passed=24, failed=0
Phase-2A backend tests: passed=10, failed=0
Phase-1 submodule: unchanged at de0ecb0
```

## Backend Boundary

`backend.interface.ModelBackend` accepts an engine-neutral inference request
and returns content plus generic inference metadata. The contract exposes:

- messages, max token budget, and temperature
- generated content
- backend and model identity
- finish reason
- token usage
- latency, optional TTFT, and tokens per second

It does not expose Transformers classes, vLLM classes, CUDA devices,
quantization configuration, or KV-cache implementation.

`LMFBackend` wraps the existing OpenAI-compatible LLaMA-Factory endpoint.
`ModelClient` exposes any backend through the frozen Phase-1 `chat`,
`last_finish_reason`, and `last_usage` contract.

## Current Status

- Backend interface: implemented.
- LLaMA-Factory API adapter: implemented.
- Frozen Phase-1 `chat` compatibility surface: implemented by `ModelClient`.
- Phase-2A Runtime factory and REPL entry: implemented.
- Generic inference benchmark runner: implemented.
- UAEA planner, semantic observation, and artifact workloads: defined.
- vLLM backend: deferred.
- Point-in-time NVIDIA SM/VRAM collector: implemented.
- Continuous GPU peak sampling and KV-cache metrics: deferred.

## Remaining Phase-2A Roadmap

1. Add a real Transformers endpoint smoke test outside Runtime regression.
2. Add a streaming-capable vLLM adapter behind the same interface.
3. Add continuous NVIDIA sampling for peak SM utilization and VRAM.
4. Add vLLM KV-cache metrics and long-context workloads.
5. Compare backend behavior while requiring frozen L0-L6 regression on every
   migration change.
