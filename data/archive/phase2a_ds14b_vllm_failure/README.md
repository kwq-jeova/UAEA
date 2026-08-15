# Phase-2A DS14B vLLM Failure Archive

This archive preserves historical diagnostics for the rejected Phase-2A vLLM
candidate:

```text
DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4
quantization: compressed-tensors WNA16
backend: vLLM 0.26.0
hardware: RTX 5090 D v2, 24GB VRAM
```

The experiment series was created to explain why selected Phase-1 semantic
benchmark cases produced first-token `!`, `finish_reason=length`, and logprobs
NaN under the DS14B AWQ vLLM path while LMF/HF baseline remained valid.

Conclusion:

```text
The failure was localized below Phase-1 Runtime and backend contract.
The rejected path is the DS14B AWQ compressed-tensors WNA16 artifact combined
with vLLM's Qwen2/compressed-tensors execution path on the current environment.
```

Status:

```text
historical
not active production candidate
kept for engineering traceability
```

Active Phase-2A vLLM production candidate after this archive:

```text
Qwen2.5-14B-Instruct-AWQ
quantization: traditional AWQ / auto_awq
```

