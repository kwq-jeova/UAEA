# Phase-2A Data Archive Index

This directory is an index for Phase-2A historical data archives.

Files are not deleted during Phase-2A cleanup. Historical diagnostics remain
available so that failed model/backend combinations can be audited later.

## Archived Topics

| Topic | Location | Status | Current relevance |
| --- | --- | --- | --- |
| DS14B AWQ vLLM failure investigation | `data/archive/phase2a_ds14b_vllm_failure/` | historical | evidence for rejecting DS14B compressed-tensors WNA16 as the current production artifact |

## Active Baselines Kept Outside Archive

The following files remain active and are intentionally not moved:

```text
data/inference_traces/lmf_phase1_l0_l2.jsonl
data/inference_traces/qwen25_awq_phase1/
data/inference_traces/vllm_qwen25_phase1_l3_l6.jsonl
data/inference_traces/vllm_qwen25_phase1_l3_l6.enriched.jsonl
data/benchmark_results/qwen25_awq_phase1/
data/benchmark_results/vllm_qwen25/
data/diagnostics/vllm_*qwen25_14b_awq_simple_20260815T064048Z.json
```

These are referenced by the current Phase-2A baseline documentation.

## Policy

Archive by adding indexed evidence. Do not delete historical diagnostics and do
not move active baseline files that are still referenced by current documents.
