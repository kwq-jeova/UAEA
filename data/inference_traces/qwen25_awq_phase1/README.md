# Qwen2.5-14B-AWQ Phase-1 vLLM Trace Baseline

This directory contains the active Phase-2A vLLM baseline traces for:

```text
model artifact: /opt/uaea-models/models/Qwen2.5-14B-Instruct-AWQ
served model: qwen25-14b-awq
backend: VLLMBackend
vLLM: 0.26.0
quantization: auto_awq / AutoAWQMarlin
```

Selected validation:

```text
qwen25_awq_selected_20260815T065033Z.jsonl

L0-01: PASS
L0-02: PASS
L1-02: PASS
```

Full L0-L2 validation:

```text
qwen25_awq_l0_l2_20260815T065250Z.jsonl

L0: 2/2 PASS
L1: 4/4 PASS
L2: 2/2 PASS
```

Trace comparison against the LMF baseline:

| Trace | Records | Cases | Phase distribution | Finish | Length limited | Errors |
| --- | ---: | --- | --- | --- | ---: | ---: |
| LMF baseline | 15 | L0-01, L0-02, L1-01, L1-02, L1-03, L1-04, L2-01, L2-02 | chat_answer=3, planner=8, observation_answer=4 | stop=15 | 0 | 0 |
| Qwen2.5-AWQ vLLM | 15 | L0-01, L0-02, L1-01, L1-02, L1-03, L1-04, L2-01, L2-02 | chat_answer=3, planner=8, observation_answer=4 | stop=15 | 0 | 0 |

Token totals:

```text
LMF baseline:
  input_tokens: 17064
  output_tokens: 8602

Qwen2.5-AWQ vLLM:
  input_tokens: 17252
  output_tokens: 2968
```

Interpretation:

```text
Qwen2.5-14B-AWQ preserves the Phase-1 L0-L2 runtime semantics through vLLM:
direct answer, tool routing, semantic observation, and artifact generation all
pass without modifying Phase-1 Runtime or benchmark expectations.
```

