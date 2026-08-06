# UAEA Phase-2A-4 vLLM Compatibility Audit

> Audit date: 2026-08-05
> Status: completed; installation pending
> Scope: compatibility analysis only

No package, CUDA toolkit, NVIDIA driver, model file, or quantized checkpoint was
installed or modified during this audit. The frozen Phase-1 submodule remains
unchanged.

## 1. Baselines

### Hardware

| Item | Verified value |
|---|---|
| GPU | NVIDIA GeForce RTX 5090 D v2 |
| VRAM | 24,455 MiB |
| Compute capability | 12.0 |
| Driver | 581.80 |
| Windows driver CUDA report | 13.0 |

### Phase-1 LMF Reference

This is a reference only. It must not be copied or modified.

```text
D:\AI_Agent_FW\.venv_lmf_api
Python 3.13.12
torch 2.12.0.dev20260408+cu128
torchvision 0.27.0.dev20260407+cu128
torchaudio 2.11.0.dev20260407+cu128
bitsandbytes 0.49.2
transformers 5.2.0
CUDA runtime 12.8
cuDNN 9.2.0
CUDA available True
```

The version `0.27.0` for torchvision above is the live verified package value;
`2.27.0` in the audit request was a transcription error.

### Phase-2A WSL2 Environment

```text
Distribution: Ubuntu 24.04.4 LTS
Kernel: 6.18.33.2-microsoft-standard-WSL2
Environment: /opt/uaea/vllm_env
Python: 3.12.3
pip: 26.2.1
GPU visibility: PASS
nvidia-smi: PASS
nvcc/CUDA toolkit: not installed
PyTorch: not installed
vLLM: not installed
```

WSL currently sees about 15 GiB RAM and 4 GiB swap. Windows has 31.5 GiB
physical RAM. This matters for local quantization, but not for installing a
precompiled vLLM wheel.

## 2. Current vLLM Compatibility

PyPI metadata observed during the audit:

| Property | vLLM 0.26.0 |
|---|---|
| Release status | Current stable PyPI release |
| Python | `>=3.10,<3.15` |
| Linux wheel | `cp38-abi3-manylinux_2_28_x86_64` |
| PyTorch | exactly `2.11.0` |
| torchvision | exactly `0.26.0` |
| torchaudio | exactly `2.11.0` |
| Transformers | `>=5.5.3` |
| Documented default compiled CUDA | 12.9 |
| Verified v0.26.0 GitHub x86_64 asset | CUDA 12.9 |

Python 3.12.3 is inside the supported range. Ubuntu 24.04 satisfies the
manylinux glibc floor. The precompiled wheel path does not require a local CUDA
toolkit or `nvcc`; it uses wheel-provided CUDA user-space libraries and the WSL
GPU driver bridge.

Official vLLM installation guidance states:

- GPU compute capability 7.5 or higher is required.
- Blackwell requires CUDA 12.8 or newer.
- vLLM CUDA extensions are binary-coupled to their PyTorch and CUDA builds.
- a fresh environment is recommended.

RTX 5090 D compute capability 12.0 and the verified cu128 Phase-1 Torch runtime
provide strong compatibility evidence. They do not guarantee that every vLLM,
FlashAttention, Triton, or quantization kernel has an optimized consumer
Blackwell path. A load test remains mandatory.

### Version Recommendation

```text
Recommended vLLM version:
vLLM 0.26.0 standard PyPI wheel with its complete pinned dependency resolution

Reason:
Current stable release; Python 3.12 support; exact stable Torch 2.11 dependency;
official Linux wheel; Blackwell minimum CUDA requirement satisfied; no local
CUDA toolkit or source build required.

Risk:
Consumer RTX 5090 kernel coverage can still expose runtime-specific failures.
The stack is newer than Phase-1 LMF and uses Transformers >=5.5.3. PyPI metadata
for Torch 2.11 resolves CUDA 13 NVIDIA components while current vLLM docs and
the attached release asset identify CUDA 12.9 binaries. The complete resolver
plan must therefore be reviewed as one binary set before installation.

Alternative:
Use the explicit vLLM 0.26.0 cu129 release asset if the standard PyPI resolution
is ambiguous and its dependency dry-run is coherent. vLLM 0.25.1 is a rollback
candidate, but it uses the same Torch 2.11 / Transformers >=5.5.3 dependency
family and does not remove the core compatibility risks. No cu128 v0.26.0
x86_64 release asset was present in the GitHub release audit.
```

Nightly vLLM or a source build is not recommended for the first baseline.

## 3. PyTorch Selection Strategy

| Option | Blackwell | Binary/kernel risk | Assessment |
|---|---|---|---|
| A. Install stable cu128 Torch first | Torch supports Blackwell | No verified matching vLLM 0.26.0 cu128 release asset; extension ABI can diverge | Reject for initial baseline |
| B. Install nightly cu128 Torch first | Existing LMF baseline proves basic GPU support | High ABI risk for vLLM C++/CUDA extensions; likely source-build path | Reject for initial vLLM baseline |
| C. Let selected vLLM wheel resolve dependencies | Uses pinned stable Torch and matched compiled extensions | Lowest mismatch risk; still requires lock review | Recommended |

### Decision

Use Option C with the standard `vLLM==0.26.0` Linux wheel. Do not preinstall
Torch independently or force the Phase-1 cu128 nightly baseline into this
environment. Capture the complete resolver plan before installation and freeze
the resulting package set afterward.

Expected core resolution:

```text
vllm 0.26.0
torch 2.11.0
torchvision 0.26.0
torchaudio 2.11.0
transformers >=5.5.3
flashinfer-python 0.6.14
```

The CUDA suffix and NVIDIA component versions must be taken from the actual
resolver output. They are not predeclared as cu128 by this audit.

Do not copy Phase-1's nightly `torch 2.12.0.dev` into this environment.

### Kernel Components

- CUDA: use the selected precompiled wheel; do not install a toolkit initially.
- FlashAttention: do not install a separate `flash-attn` package initially.
  Allow vLLM to select its supported attention backend.
- Triton: accept the version resolved by the vLLM/Torch stack; do not override it.
- FlashInfer/CUTLASS: accept the versions pinned by vLLM 0.26.0.
- Source compilation: deferred. It would require a CUDA toolkit, compiler, and a
  separate build audit.

## 4. DS14B AWQ Compatibility

Current checkpoint:

| Property | Value |
|---|---|
| Architecture | `Qwen2ForCausalLM` |
| Original dtype | BF16 |
| Format | HuggingFace safetensors |
| Weight shards | 4 |
| Weight size | 27.51 GiB |
| Quantization config | none |
| Declared maximum context | 131,072 tokens |

The BF16 checkpoint cannot be served directly on 24,455 MiB because weights
alone exceed VRAM before runtime allocations and KV cache.

### AWQ Tool Decision

| Tool/path | Assessment |
|---|---|
| `llm-compressor` AWQ | Recommended conversion tool; maintained by the vLLM project and includes `Qwen2ForCausalLM` mappings |
| AutoAWQ | Deprecated upstream; use only for compatibility with an existing trusted AutoAWQ checkpoint |
| Trusted published AWQ checkpoint | Operational alternative if provenance, tokenizer identity, config, and semantic quality are verified |

Recommended future conversion form:

```text
BF16 Qwen2 checkpoint
  -> representative calibration dataset
  -> llm-compressor AWQ W4A16 asymmetric quantization
  -> separate HuggingFace AWQ output directory
  -> quality and lineage validation
  -> vLLM serving with AWQ auto-detection/explicit quantization setting
```

The original model directory must never be overwritten.

### Expected Memory

Four-bit storage for 14B parameters has a theoretical floor near 6.5 GiB.
Scales, unquantized layers, metadata, allocator reservations, kernels, and
temporary buffers make an operational weight footprint around 7-10 GiB a
reasonable planning range. This is an estimate, not a measured result.

The model has 48 layers, 8 KV heads, and head dimension 128. With BF16 KV cache:

```text
KV cache per token: 196,608 bytes (0.1875 MiB)
8K context:          approximately 1.5 GiB
16K context:         approximately 3 GiB
32K context:         approximately 6 GiB
128K context:        approximately 24 GiB
```

### Serving Feasibility

An AWQ 4-bit model has a credible chance of fitting on the RTX 5090 D at an
initial bounded context of 8K, and likely 16K after measurement. A 32K context
needs explicit memory testing. The declared 131K context is not feasible on this
24GB card because the BF16 KV cache alone approaches total VRAM.

Initial real serving must start with a bounded `max-model-len`, batch/concurrency
of one, and measured free VRAM. These are deployment constraints, not Runtime
semantics.

### Quantization Host Risk

The current WSL allocation (15 GiB RAM plus 4 GiB swap) is smaller than the
27.51 GiB source weights. Local AWQ conversion is therefore high risk even
though serving the finished AWQ checkpoint may fit. Quantization should occur on
a host with materially more CPU RAM (48-64 GiB planning range) or use a trusted
pre-quantized artifact. No quantization was attempted in this audit.

## 5. Compatibility Matrix

| Layer | Selected direction | Status |
|---|---|---|
| Phase-1 Runtime | frozen at `de0ecb0` | PASS |
| WSL2 Ubuntu 24.04.4 | deployment OS | PASS |
| Python 3.12.3 | vLLM environment | COMPATIBLE |
| NVIDIA driver 581.80 | WSL GPU bridge | PASS |
| RTX 5090 D / SM 12.0 | Blackwell, CUDA >=12.8 required | COMPATIBLE WITH RUNTIME TEST RISK |
| Local CUDA toolkit | not required for precompiled wheel | ABSENT BY DESIGN |
| vLLM 0.26.0 standard wheel | recommended first baseline | INSTALLATION PENDING |
| Stable Torch 2.11 | resolve through vLLM | INSTALLATION PENDING |
| BF16 DS14B | too large for direct single-GPU serving | BLOCKED |
| AWQ DS14B | likely serviceable at bounded context | CONVERSION/ARTIFACT PENDING |

## 6. Recommended Installation Path

This is the next approved shape, not an action performed by this audit:

1. Preserve `/opt/uaea/vllm_env` as the isolated environment.
2. Resolve `vllm==0.26.0` and all pinned dependencies without preinstalling
   Torch or selecting an unrelated CUDA index.
3. Review the resolver output for exact Torch, Transformers, FlashInfer, Triton,
   and NVIDIA package versions.
4. Install only after the resolver plan is accepted.
5. Freeze `pip list`/`pip check` and verify Torch CUDA, compute capability, and a
   small allocation before loading DS14B.
6. Do not attempt BF16 DS14B serving. Resolve the AWQ artifact separately.

Next compatibility step (dependency resolution only):

```bash
source /opt/uaea/vllm_env/bin/activate
python -m pip install --dry-run "vllm==0.26.0"
```

Planned installation command only after the dry-run is accepted:

```bash
source /opt/uaea/vllm_env/bin/activate
python -m pip install "vllm==0.26.0"
```

Neither command has been run by this audit.

## 7. Known Risks

1. Consumer Blackwell support may differ from datacenter Blackwell examples.
2. vLLM compiled extensions require exact Torch/CUDA binary compatibility.
3. Current package metadata spans vLLM CUDA 12.9 binaries and Torch/NVIDIA CUDA
   13 components; the dry-run must confirm a coherent supported resolution.
4. Transformers >=5.5.3 differs from the Phase-1 LMF API's 5.2.0 behavior.
5. AWQ changes model numerics and requires UAEA semantic regression, not only an
   API smoke test.
6. Current WSL RAM is insufficient for a comfortable local quantization job.
7. 24GB VRAM requires bounded context and low initial concurrency.
8. Non-streaming `VLLMBackend` cannot measure TTFT yet.

## 8. Validation Gates After Installation

Before connecting UAEA:

- `pip check` passes.
- Torch reports CUDA available and compute capability 12.0.
- vLLM imports without undefined symbols or kernel architecture errors.
- `/v1/models` returns the exact served model name.
- AWQ artifact records source model, calibration data, tool versions, recipe,
  hashes, and quality comparison.
- Minimal UAEA smoke produces capability success, Semantic Observation, and a
  COMPLETE Artifact.
- Phase-1 scripted benchmark remains 24/24.
- Real LMF versus vLLM comparison uses equivalent prompts and token budgets.

## 9. Sources Consulted

- vLLM PyPI metadata: <https://pypi.org/project/vllm/>
- vLLM 0.26.0 release assets: <https://github.com/vllm-project/vllm/releases/tag/v0.26.0>
- vLLM GPU installation: <https://docs.vllm.ai/en/latest/getting_started/installation/gpu/>
- vLLM quantization support: <https://docs.vllm.ai/en/latest/features/quantization/>
- vLLM AutoAWQ deprecation notice: <https://docs.vllm.ai/en/latest/features/quantization/auto_awq/>
- LLM Compressor AWQ examples: <https://github.com/vllm-project/llm-compressor/tree/main/examples/awq>
- PyTorch 2.11 metadata: <https://pypi.org/project/torch/2.11.0/>
- PyTorch CUDA 12.8 index: <https://download.pytorch.org/whl/cu128>
