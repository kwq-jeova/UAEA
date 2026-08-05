# UAEA Phase-2A-3 vLLM Backend Adapter

## Status

The adapter and contract validation are complete. A real vLLM smoke test is
prepared but has not been run because this Windows host currently has no vLLM
package, launch script, or listening vLLM service.

## Integration Choice

UAEA uses vLLM's OpenAI-compatible HTTP server rather than the Python Engine
API. This preserves the same process boundary as `LMFBackend` and keeps vLLM,
model loading, CUDA, and quantization details outside Runtime.

```text
Frozen Phase-1 Runtime
  -> ModelClient
  -> ModelBackend
       -> LMFBackend  -> LLaMA-Factory API
       -> VLLMBackend -> vLLM OpenAI-compatible API
```

`VLLMBackend` consumes the existing `InferenceRequest` and returns the existing
`InferenceResponse`. `ModelClient` is unchanged.

## Backend Selection

Backend selection is owned by `backend.factory`, outside the frozen Runtime.
The Phase-2 launcher reads:

| Variable | Default |
|---|---|
| `UAEA_BACKEND` | `lmf` |
| `UAEA_BACKEND_BASE_URL` | `8000/v1` for LMF, `8001/v1` for vLLM |
| `UAEA_BACKEND_MODEL` | Frozen Runtime model setting |
| `UAEA_BACKEND_TIMEOUT` | Frozen Runtime timeout setting |
| `UAEA_BACKEND_API_KEY` | `uaea-local` |

No backend selection branch is added to Phase-1 Runtime.

## Real Smoke Procedure

Start a vLLM OpenAI-compatible server separately with its served model name.
No AWQ, quantization, tensor parallel, or CUDA tuning is part of Phase-2A-3.

Then run:

```powershell
Set-Location D:\UAEA
.\scripts\smoke_vllm_backend.ps1 -Model "<served-model-name>"
```

The script first probes `/v1/models`, selects `vllm` through environment
configuration, and launches the same `main.py` Runtime entry. Use the same
minimal request as the LMF smoke:

```text
Read README section 1 and evaluate it.
```

Verify the trajectory contains successful capability execution, Semantic
Observation, and a `COMPLETE` Artifact. Backend failures must remain structured
and reach Phase-1 through the existing controlled `RuntimeError` boundary.

## Baseline Metrics

| Metric | LMFBackend | VLLMBackend |
|---|---:|---:|
| End-to-end smoke latency | 320.1 s | NOT RUN |
| TTFT | Not available in non-streaming adapter | Not available in non-streaming adapter |
| Generation latency | Included in response metadata | Contract-tested; real value pending |
| Tokens/sec | Derived when usage is returned | Contract-tested; real value pending |
| VRAM | External collector only | Real value pending |

The LMF value is the existing Phase-2A-2 smoke result. It was not rerun. These
values are a measurement baseline only; no performance conclusion is valid
until both backends run the same model and workload.

## Validation Boundary

Contract tests verify request conversion, response metadata, unavailable
service handling, invalid response handling, registry selection, and Runtime
factory injection. They prove adapter compatibility, not DS14B semantic
equivalence or vLLM performance.

Verification result:

```text
Phase-2 backend tests: 22 passed, 0 failed
Frozen Phase-1 L0-L6/core benchmark: 24 passed, 0 failed
PowerShell smoke launcher syntax: PASS
Frozen Phase-1 submodule: clean at de0ecb0
```
