# UAEA Phase-2A-5 vLLM Small Model Smoke Validation

## 1. Objective

Validate the vLLM engine, CUDA kernel execution, OpenAI-compatible API, UAEA
`VLLMBackend`, and frozen Runtime integration using a small model. This is not
a DS14B deployment, model-quality evaluation, quantization exercise, or
performance-tuning task.

## 2. Environment

| Component | Value |
|---|---|
| OS | WSL2 Ubuntu 24.04.4 LTS |
| Python | 3.12.3 |
| vLLM | 0.26.0 |
| PyTorch | 2.11.0+cu130 |
| CUDA user-space runtime | 13.0 |
| GPU | NVIDIA GeForce RTX 5090 D v2, compute capability 12.0 |
| Driver | 581.80 |

The server environment is `/opt/uaea/vllm_env`. It remains separate from the
Windows Runtime process and the frozen Phase-1 submodule.

## 3. Model

| Property | Value |
|---|---|
| Repository | `Qwen/Qwen2.5-0.5B-Instruct` |
| Local path | `/opt/uaea-models/qwen2.5-0.5b-instruct` |
| HF cache | `/opt/uaea-models/cache` |
| Revision | `7ae557604adf67be50417f59c2c2f167def9a775` |
| Weight file | `model.safetensors`, 988,097,824 bytes |
| Weight SHA-256 | `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe` |

The official Hugging Face endpoint was unreachable during preparation. The
same repository was downloaded with Hugging Face CLI through
`HF_ENDPOINT=https://hf-mirror.com`, with Xet disabled because the mirror's CAS
request returned HTTP 401:

```bash
export HF_HOME=/opt/uaea-models/cache
export HF_ENDPOINT=https://hf-mirror.com
export HF_HUB_DISABLE_XET=1
/opt/uaea/vllm_env/bin/hf download Qwen/Qwen2.5-0.5B-Instruct \
  --local-dir /opt/uaea-models/qwen2.5-0.5b-instruct \
  --max-workers 1
```

No model file is stored under `/opt/uaea` or in the Git repository.

## 4. Commands

Start the server from WSL:

```bash
cd /mnt/d/UAEA
bash scripts/start_vllm_small_model_smoke.sh
```

The script sets the compatibility environment required by the current WSL2
stack:

```bash
CUDA_HOME=/opt/uaea/vllm_env/lib/python3.12/site-packages/nvidia/cu13
PATH=/opt/uaea/vllm_env/bin:$CUDA_HOME/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
VLLM_USE_V2_MODEL_RUNNER=0
VLLM_USE_FLASHINFER_SAMPLER=0
```

Validate the model list, generation, backend response, and Runtime path from a
second PowerShell terminal:

```powershell
Set-Location D:\UAEA
python scripts\validate_vllm_small_model.py --runtime
```

The existing interactive `main.py` path can be checked with:

```powershell
$env:UAEA_BACKEND = "vllm"
$env:UAEA_BACKEND_BASE_URL = "http://127.0.0.1:8001/v1"
$env:UAEA_BACKEND_MODEL = "Qwen2.5-0.5B-Instruct"
python main.py
```

## 5. Results

Status: COMPLETED WITH SMALL-MODEL SEMANTIC LIMITATION.

Validated:

- vLLM server started with explicit local model path.
- `/v1/models` returned `Qwen2.5-0.5B-Instruct`.
- `VLLMBackend` completed a direct generation request.
- OpenAI-compatible response included finish reason and token usage.
- `main.py -> runtime_factory -> ModelClient -> VLLMBackend -> vLLM API`
  returned a runtime response without changing Phase-1 lifecycle code.
- Smoke server was stopped after validation and GPU memory returned to idle.

Direct backend generation:

| Metric | Value |
|---|---|
| Response status | `ok=true` |
| Finish reason | `stop` |
| Latency | `34599.443 ms` |
| Prompt tokens | `28` |
| Completion tokens | `94` |
| Total tokens | `122` |
| Throughput | `2.7168 tokens/sec` |

GPU snapshot:

| Stage | Memory | Utilization |
|---|---|---|
| Before backend generation | `23180 / 24455 MiB` | `0%` |
| After backend generation | `23182 / 24455 MiB` | `39%` |
| After server stop | `0 / 24455 MiB` | `0%` |

Runtime path result:

| Path | Result |
|---|---|
| `validate_vllm_small_model.py --runtime` | Runtime reached `VLLMBackend` and returned a response |
| `main.py` with `UAEA_BACKEND=vllm` | Runtime reached `VLLMBackend` and returned a response |
| Phase-1 planner protocol | Not validated by this 0.5B model |
| Semantic Observation / Artifact creation | Not produced by the 0.5B model smoke run |

The trajectory for the runtime validation contained planner and snapshot events,
but no capability execution, Semantic Observation, or Workflow Artifact events.
The model answered as a generic assistant instead of producing the Phase-1
planner action format. This is acceptable for Phase-2A-5 because the purpose is
backend engine/API execution, not DS14B semantic equivalence.

Observed failed startup paths before the final successful configuration:

| Attempt | Result |
|---|---|
| Default vLLM 0.26 V1/V2 runner | Failed with `RuntimeError: UVA is not available` |
| `VLLM_USE_V2_MODEL_RUNNER=0` only | Model loaded, then FlashInfer sampling JIT required CUDA tooling |
| Add `CUDA_HOME` and venv `ninja` | JIT reached compilation, then failed on CUDA/CCCL header mismatch |
| Add `VLLM_USE_FLASHINFER_SAMPLER=0` | Server started and API smoke passed |

## 6. Limitations

- A 0.5B model validates transport and engine execution, not DS14B semantic
  equivalence.
- The model may fail the Phase-1 planner protocol because model capability is
  intentionally outside this smoke test. Such a failure does not invalidate a
  successful backend transport and CUDA-kernel result.
- The adapter is non-streaming, so TTFT is not available.
- No AWQ, GPTQ, bitsandbytes, offload, tensor parallelism, or kernel tuning is
  introduced.
