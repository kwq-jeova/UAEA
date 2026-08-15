# Phase-2A Qwen2.5-AWQ vLLM Equivalence Report

This report records the bounded Phase-1 capability validation for
Qwen2.5-14B-Instruct-AWQ through the Phase-2A VLLMBackend.

## Scope

```text
Runtime: frozen Phase-1 Runtime
Backend: VLLMBackend
Model artifact: /opt/uaea-models/models/Qwen2.5-14B-Instruct-AWQ
Served model: qwen25-14b-awq
Quantization: traditional AWQ / AutoAWQ, quant_method=awq, version=gemm
Serving engine: vLLM 0.26.0
Hardware: RTX 5090 D v2, about 24GB VRAM
```

No Phase-1 Runtime core logic, benchmark expectations, or Artifact schema were
modified for this validation.

## Overall Status

| Level | Cases | Result |
| --- | ---: | --- |
| L0 | 2 | 2/2 PASS |
| L1 | 4 | 4/4 PASS |
| L2 | 2 | 2/2 PASS |
| L3 | 2 | 2/2 PASS |
| L4 | 2 | 2/2 PASS |
| L5 | 2 | 2/2 PASS |
| L6 | 5 | 5/5 PASS |
| Total | 19 | 19/19 PASS |

## Extended Capability Validation L3-L6

| Level | Summary | Semantic result |
| --- | --- | --- |
| L3 | multi-step workflow continuation | PASS |
| L4 | workflow artifact synthesis and correction path | PASS |
| L5 | long interaction / repeated answer and workflow path | PASS |
| L6 | retry, recovery, and artifact answer boundaries | PASS |

Per-level reports:

```text
data/benchmark_results/vllm_qwen25/L3_20260815T1514.json
data/benchmark_results/vllm_qwen25/L4_20260815T1514.json
data/benchmark_results/vllm_qwen25/L5_20260815T1514.json
data/benchmark_results/vllm_qwen25/L6_20260815T1514.json
```

L3-L6 trace:

```text
data/inference_traces/vllm_qwen25_phase1_l3_l6.jsonl
data/inference_traces/vllm_qwen25_phase1_l3_l6.enriched.jsonl
```

The raw trace is the direct benchmark output. The enriched trace is a
diagnostic sidecar generated through the active vLLM `/tokenize` endpoint to
populate input and output token-id arrays without changing the Runtime.

## L3-L6 Trace Summary

```text
records: 55
cases: L3-01, L3-02, L4-01, L4-02, L5-01, L5-02, L6-01, L6-02, L6-03, L6-04, L6-05
phases:
  planner: 20
  observation_answer: 17
  chat_answer: 10
  artifact_answer: 5
  phase1_runtime: 3
finish_reason:
  stop: 55
length_limited: 0
errors: 0
```

The enriched trace contains:

```text
input_token_ids: present for 55/55 records
output_token_ids: present for 55/55 records
backend metadata: present
tokenizer metadata: present
generation metadata: present
latency_ms: present
```

## Semantic Outcome

The vLLM Qwen2.5-AWQ path preserves the Phase-1 benchmark semantics for all
bounded L0-L6 cases:

- direct answer routing
- tool-only routing
- tool-then-answer routing
- workflow planning
- workflow continuation
- semantic observation creation
- artifact creation
- workflow artifact answer
- correction artifact path
- retry / recovery boundary cases

No benchmark failure was observed in L3-L6. Therefore no failure classification
was needed for transport, backend adapter, generation, tokenizer/template, or
model artifact.

## LMF Comparison

Known LMF baseline:

```text
Qwen2.5-14B-Instruct through LMF/HF 4-bit path:
  L0 2/2 PASS
  L1 4/4 PASS
  L2 2/2 PASS
```

Qwen2.5-AWQ vLLM result:

```text
L0 2/2 PASS
L1 4/4 PASS
L2 2/2 PASS
L3 2/2 PASS
L4 2/2 PASS
L5 2/2 PASS
L6 5/5 PASS
```

The L0-L2 semantic baseline agrees with the existing LMF result. L3-L6 were not
rerun through LMF in this closing pass, per the constraint to avoid repeating
expensive LMF benchmark work.

## Model Selection Conclusion

DS14B compressed-tensors WNA16 remains rejected for the current Phase-2A vLLM
production path:

```text
DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4
compressed-tensors WNA16
vLLM 0.26.0 on RTX 5090 D v2
first-token "!" pathology and logprobs NaN
```

Qwen2.5-14B-Instruct-AWQ is validated as the current Phase-2A vLLM production
candidate:

```text
Qwen2.5-14B-Instruct-AWQ
traditional AWQ / GEMM
vLLM 0.26.0 on RTX 5090 D v2
L0-L6 PASS
```

The compatibility boundary must include the model artifact representation and
execution path. It is not sufficient to describe a deployment as only
`14B + AWQ + vLLM + RTX5090D`.

## Remaining Gaps

- This validates the bounded Phase-1 benchmark capability set, not open-ended
  production workload behavior.
- LMF Qwen2.5 L3-L6 was not rerun in this closing pass.
- The enriched token-id trace depends on the active vLLM `/tokenize` endpoint
  and is recorded as diagnostic evidence, separate from the raw benchmark trace.
