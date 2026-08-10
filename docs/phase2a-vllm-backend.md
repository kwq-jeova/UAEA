# UAEA Phase-2A-3 vLLM Backend Adapter

## Status

The adapter, contract validation, and real DS14B OpenAI-compatible smoke test
are complete.

Validated service details:

- `vllm` server starts successfully on WSL2 Ubuntu 24.04
- served model name: `ds14b-awq`
- model path:
  `/opt/uaea-models/models/DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4`
- stable launch shape:
  `--dtype half --max-model-len 16384 --gpu-memory-utilization 0.7`
- stable generation behavior inside `VLLMBackend`:
  clamp temperature to `0.2` minimum and set `chat_template_kwargs.enable_thinking=false`

The deployment environment and model-capacity notes are recorded in
`docs/phase2a-vllm-environment.md`.

## Closure Review

- `LMFBackend` and `VLLMBackend` implement the same `ModelBackend` properties
  and `generate(InferenceRequest) -> InferenceResponse` contract.
- `ModelClient` has no LMF or vLLM branch and retains the frozen Phase-1
  `chat()` compatibility surface.
- Backend selection is implemented by Phase-2 `BackendSettings` and the
  backend registry, outside Phase-1 Runtime.
- Prompt construction, Workflow, Artifact, Observation, Context, and recovery
  semantics remain in the unchanged Phase-1 submodule.

Phase-2A-3 engineering closure status: DONE.

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

Start the validated WSL script:

```powershell
/opt/uaea/scripts/start_vllm_ds14b.sh
```

Stop with:

```powershell
/opt/uaea/scripts/stop_vllm_ds14b.sh
```

Use the same Runtime path through the backend abstraction:

```powershell
Set-Location D:\UAEA
$env:UAEA_BACKEND = "vllm"
$env:UAEA_BACKEND_BASE_URL = "http://127.0.0.1:8001/v1"
$env:UAEA_BACKEND_MODEL = "ds14b-awq"
python main.py
```

The backend request includes a conservative generation profile:

```text
chat_template_kwargs.enable_thinking=false
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

Observed limitation during Phase-1 vLLM benchmark validation:

- `L0-01` direct-answer path still returns a length-capped response.
- `L1-02` structured extraction path still fails to produce a semantic
  observation on the current DS14B AWQ serving stack.
- Backend transport and contract validation pass, but full semantic
  equivalence for the current checkpoint is not yet proven.
