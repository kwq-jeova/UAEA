# UAEA Phase-2A-4 vLLM Environment Preparation

## Status

Environment plan: READY.

Package installation and model deployment: NOT STARTED.

Real DS14B smoke: BLOCKED by the environment and model-capacity gates described
below. Phase-2A-4 does not introduce AWQ, quantization changes, CPU offload,
tensor parallel tuning, CUDA tuning, or model conversion.

The completed package and AWQ decision audit is recorded in
`docs/phase2a-vllm-compatibility-audit.md`.

## 1. Isolation Principle

The vLLM server must use an environment independent from:

- `D:\AI_Agent_FW\.venv`
- `D:\AI_Agent_FW\.venv_lmf_api`
- the Python environment used to launch UAEA Runtime
- the frozen Phase-1 submodule

The inference server and UAEA communicate only through the OpenAI-compatible
HTTP boundary. Backend-specific Python packages must not enter Runtime.

Native Windows is not the recommended first deployment baseline for vLLM. Use
WSL2 with Ubuntu 24.04 LTS or a separate Linux host. Keep the Python environment
on the Linux filesystem, for example `/opt/uaea/vllm_env`; `D:\vllm_env` may be
used for manifests, logs, or downloaded assets, but not as the primary WSL
virtual environment directory.

## 1.1 WSL Model and Runtime Storage Layout

Use separate directories for model assets and execution artifacts:

```text
Source repository:
  /mnt/d/UAEA
  Windows path: D:\UAEA

Python environment:
  /opt/uaea/vllm_env

Model storage:
  /opt/uaea-models/models/
  /opt/uaea-models/models/qwen2.5-0.5b-instruct

Model/cache storage:
  /opt/uaea-models/cache/

Runtime artifacts:
  /opt/uaea-runtime/vllm/logs/
  /opt/uaea-runtime/vllm/pid/
  /opt/uaea-runtime/vllm/benchmark/
```

`/opt/uaea-models` should only contain model-related assets and cache. Runtime
outputs, smoke logs, pid files, and validation snapshots belong under
`/opt/uaea-runtime/vllm/`.

## 2. Hardware Inventory

Inventory captured on 2026-08-05:

| Item | Current value | Assessment |
|---|---|---|
| GPU | NVIDIA GeForce RTX 5090 D v2 | Blackwell-class GPU |
| VRAM | 24,455 MiB | Below raw DS14B BF16 weight size |
| NVIDIA driver | 581.80 | Reports CUDA 13.0 capability |
| Driver CUDA API | 13.0 | Can run compatible older CUDA user-space builds |
| Windows driver mode | WDDM | Prefer WSL2/Linux CUDA path for vLLM |
| Default host Python | 3.13.12 | Do not use as the initial vLLM baseline |

`nvidia-smi` reporting CUDA 13.0 does not require a CUDA 13.0 PyTorch wheel.
The selected vLLM/PyTorch wheel controls the user-space CUDA runtime and must be
validated against the driver and RTX 5090 before model loading.

## 3. Dependency Compatibility Checklist

The first candidate matrix is intentionally conservative:

| Layer | Recommended baseline | Gate |
|---|---|---|
| OS | WSL2 Ubuntu 24.04 LTS or Linux | `nvidia-smi` works inside Linux |
| Python | 3.12.x | Separate venv; do not reuse Python 3.13 LMF env |
| vLLM | 0.26.0 candidate, exact pin | Resolve wheel dependencies before install |
| PyTorch | Version required by the pinned vLLM wheel | Do not pre-pin an unrelated Torch build |
| CUDA runtime | Wheel-provided supported runtime | Confirm RTX 5090 kernels load |
| transformers | Version resolved by vLLM | Confirm Qwen2 config/tokenizer load |
| tokenizer support | `tokenizers` from resolved stack | Validate local tokenizer files |
| sentencepiece | Only if tokenizer loading requests it | Current checkpoint has no sentencepiece file |
| flash-attention | Do not install separately initially | Use vLLM packaged/default kernels first |

PyPI currently exposes vLLM 0.26.0. Before installation, perform dependency
resolution in the isolated Linux environment and record the exact lock:

```bash
python3.12 -m venv /opt/uaea/vllm_env
source /opt/uaea/vllm_env/bin/activate
python -m pip install --upgrade pip
python -m pip install --dry-run "vllm==0.26.0"
```

These commands are a procedure only; they were not executed by this task.
After reviewing the dry-run, install and freeze versions manually. Do not copy
the current LMF stack (`torch 2.12.0.dev+cu128`, Transformers 5.2.0,
bitsandbytes 0.49.2) into the vLLM environment.

## 4. Model Preparation Checklist

Current model source:

```text
D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B
WSL path: /mnt/d/LM_Studio_Models/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B
```

Observed checkpoint:

| Property | Value |
|---|---|
| Architecture | `Qwen2ForCausalLM` |
| Model type | `qwen2` |
| Declared dtype | `bfloat16` |
| Quantization config | none |
| Maximum positions | 131,072 |
| Weights | 4 safetensors shards, 27.51 GiB total |
| Index | `model.safetensors.index.json` present |
| Tokenizer | `tokenizer.json` and `tokenizer_config.json` present |
| Config | `config.json` and generation config present |

The checkpoint is already in a vLLM-readable HuggingFace layout, so no format
conversion is indicated. Tokenizer/config loading should be tested before model
allocation.

### Capacity Gate

Raw BF16 weights alone exceed the available 24,455 MiB VRAM. vLLM also needs
runtime allocations and KV cache. Therefore a single-GPU unquantized DS14B
deployment is not expected to fit.

The current LMF server avoids this boundary by requesting bitsandbytes 4-bit at
startup. Reproducing that behavior would be a quantization decision and is
explicitly outside Phase-2A-4. Multi-GPU, CPU offload, reduced precision, or a
pre-quantized checkpoint also require a later explicit decision. Do not start a
full DS14B vLLM load until one capacity path is approved.

## 5. Deployment Flow

```text
Isolated WSL2/Linux vLLM environment
  -> vLLM OpenAI-compatible server
  -> UAEA VLLMBackend
  -> ModelClient
  -> Frozen Phase-1 Runtime
```

The server owns model loading and GPU dependencies. UAEA owns only the endpoint,
served model name, timeout, and backend selection configuration.

After the capacity gate is resolved, the unoptimized server command shape is:

```bash
source /opt/uaea/vllm_env/bin/activate
python -m vllm.entrypoints.openai.api_server \
  --model /mnt/d/LM_Studio_Models/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B \
  --served-model-name DeepSeek-R1-Distill-Qwen-14B \
  --host 0.0.0.0 \
  --port 8001
```

This command is documentation, not an assertion that the current model fits.
No quantization or performance flags are included.

## 6. Real Smoke Procedure

Terminal 1, WSL2/Linux:

1. Activate the isolated environment.
2. Start the vLLM server with the validated DS14B command or
   `/opt/uaea/scripts/start_vllm_ds14b.sh`.
3. Confirm the served model name exactly matches UAEA configuration.

Terminal 2, PowerShell:

```powershell
Set-Location D:\UAEA
.\scripts\smoke_vllm_backend.ps1 `
  -BaseUrl "http://127.0.0.1:8001/v1" `
  -Model "ds14b-awq"
```

Use this input for the Phase-1 backend smoke:

```text
Read README section 1 and evaluate it.
```

Acceptance evidence must come from the trajectory, not only terminal output:

- `document.read_section`: SUCCESS
- Execution Observation: SUCCESS
- Semantic Observation: SUCCESS
- Workflow Artifact: COMPLETE
- `finish_reason`: not `length` or `error`
- recovery behavior: unchanged

## 7. Benchmark Preparation

Existing reference:

| Backend | End-to-end smoke latency | TTFT | Tokens/s | GPU | VRAM |
|---|---:|---:|---:|---:|---:|
| LMFBackend | 320.1 s | unavailable | not recorded | not comparable | not comparable |
| VLLMBackend | pending | pending | pending | pending | pending |

After the real smoke passes, run identical UAEA inference workloads:

```powershell
python benchmark\inference\run_benchmark.py `
  --backend vllm `
  --base-url http://127.0.0.1:8001/v1 `
  --model DeepSeek-R1-Distill-Qwen-14B `
  --output data\vllm-baseline.json
```

Compare against LMF using the same prompt set, token budgets, model semantics,
and warm/cold-run policy. The current adapter is non-streaming, so TTFT cannot
be measured yet. The NVIDIA collector is point-in-time rather than peak
sampling; its GPU/VRAM values must be labeled accordingly.

## 8. Readiness Gates

1. WSL2/Linux NVIDIA access verified.
2. Python 3.12 isolated environment created manually.
3. vLLM dependency dry-run reviewed and versions frozen.
4. Qwen2 config and tokenizer load without allocating model weights.
5. Capacity strategy approved outside this preparation task.
6. `/v1/models` responds with `ds14b-awq`.
7. UAEA smoke trajectory satisfies all lifecycle assertions.
8. Phase-1 `24/24` and Phase-2 backend tests remain green.

Current preparation verification:

```text
Phase-1 L0-L6/core scripted benchmark: 24 passed, 0 failed
Phase-2 backend tests: 22 passed, 0 failed
vLLM DS14B OpenAI-compatible API smoke: PASS
Backend integration closure: PASS
Phase-1 submodule: clean at de0ecb0
Packages installed by Phase-2A-4: none
```
