# Phase-2A Inference Benchmark

This framework measures inference-engine behavior independently from the
Phase-1 Runtime benchmark.

Initial UAEA workloads cover:

- planner requests
- semantic observation generation
- workflow artifact extraction

Generic backend metadata supplies latency, finish reason, token usage, and
tokens per second. Physical GPU measurements are supplied by a separate
benchmark collector so CUDA, quantization, and KV-cache details do not leak
into the Runtime-facing `ModelBackend` interface.

TTFT remains `null` for non-streaming adapters. A future streaming backend may
populate it without changing Phase-1 lifecycle behavior.

Run the current Transformers/LLaMA-Factory endpoint benchmark after the local
API is available:

```text
python -m benchmark.inference.run_benchmark \
  --base-url http://127.0.0.1:8000/v1 \
  --model DeepSeek-R1-Distill-Qwen-14B \
  --output benchmark/inference/results/transformers.json
```

The initial NVIDIA collector records point-in-time SM utilization and VRAM via
`nvidia-smi`. Continuous peak sampling and backend-specific KV-cache metrics
remain future work.
