# Phase-2A Model Artifact Baseline

This document records the Phase-2A model and artifact selection boundary after
the bounded vLLM validation with Qwen2.5-14B-Instruct-AWQ.

## Purpose

Phase-2A validates that the frozen Phase-1 Cognitive Runtime can use a
replaceable inference backend without changing Runtime semantics, Artifact
schema, or benchmark expectations.

The key lesson from the DS14B and Qwen2.5 experiments is:

```text
"14B + AWQ + vLLM + RTX5090D" is not a sufficient compatibility statement.
```

Model selection must record the exact artifact representation and execution
path.

## Required Selection Metadata

Every Phase-2 inference candidate should record:

- model family and checkpoint name
- model artifact path
- quantization method
- quantization representation
- quantization implementation
- serving engine
- serving engine version
- hardware target
- VRAM / memory budget
- max model length used during serving
- backend adapter
- trace and benchmark evidence

## Current Hardware Boundary

```text
GPU: NVIDIA RTX 5090 D v2
VRAM: about 24GB
OS: WSL2 Ubuntu 24.04
Python: 3.12
vLLM: 0.26.0
```

The current validation envelope is bounded. It proves compatibility for the
tested artifact, backend, benchmark levels, and hardware configuration. It does
not prove all 14B AWQ artifacts are safe.

## Artifact Decision Matrix

| Candidate | Artifact representation | Serving path | Result | Production status |
| --- | --- | --- | --- | --- |
| DeepSeek-R1-Distill-Qwen-14B | HF / LLaMA-Factory 4-bit loading path | LMF/HF | L0/L1/L2 PASS | LMF baseline |
| DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4 | compressed-tensors WNA16 | vLLM 0.26.0 / Qwen2 compressed-tensors execution | first-token `!`, logprobs NaN | rejected for current Phase-2A production path |
| Qwen2.5-14B-Instruct-AWQ | traditional AWQ, `quant_method=awq`, `version=gemm` | vLLM 0.26.0 / AutoAWQMarlin | smoke PASS, selected PASS, L0/L1/L2/L3/L4/L5/L6 PASS | current bounded vLLM production candidate |

## DS14B AWQ Conclusion

```text
Artifact:
  /opt/uaea-models/models/DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4

Representation:
  compressed-tensors / WNA16

Observed failure:
  first-token "!" pathology
  logprobs NaN
  selected Phase-1 semantic benchmark failure

Decision:
  not suitable as the current UAEA Phase-2A production artifact on the
  RTX5090D + vLLM 0.26.0 production stack.
```

This is not a claim that the original DS14B checkpoint is damaged. It is also
not a claim that compressed-tensors can never be used. The precise conclusion
is that this artifact and representation do not meet UAEA reliability
requirements under the current hardware and vLLM stack.

## Qwen2.5-14B-AWQ Conclusion

```text
Artifact:
  /opt/uaea-models/models/Qwen2.5-14B-Instruct-AWQ

Representation:
  traditional AWQ / AutoAWQ
  quant_method: awq
  version: gemm

Serving:
  vLLM 0.26.0
  served model: qwen25-14b-awq
  max_model_len: 8192 during bounded validation

Validation:
  minimal prompt smoke: PASS
  chat/completions: PASS
  logprobs: PASS
  selected L0-01/L0-02/L1-02: PASS
  full L0/L1/L2/L3/L4/L5/L6: PASS
```

Qwen2.5-14B-Instruct-AWQ is the current Phase-2A vLLM production candidate for
bounded validation.

## Evidence

Active Qwen2.5-AWQ vLLM trace baseline:

```text
data/inference_traces/qwen25_awq_phase1/qwen25_awq_l0_l2_20260815T065250Z.jsonl
data/inference_traces/qwen25_awq_phase1/qwen25_awq_selected_20260815T065033Z.jsonl
data/inference_traces/vllm_qwen25_phase1_l3_l6.jsonl
data/inference_traces/vllm_qwen25_phase1_l3_l6.enriched.jsonl
```

Active Qwen2.5-AWQ benchmark reports:

```text
data/benchmark_results/qwen25_awq_phase1/
data/benchmark_results/vllm_qwen25/
```

LMF baseline trace:

```text
data/inference_traces/lmf_phase1_l0_l2.jsonl
```

DS14B historical diagnostics:

```text
data/archive/phase2a_ds14b_vllm_failure/
docs/archive/phase2a-vllm-diagnostics/
docs/phase2a-vllm-root-cause-analysis.md
```
