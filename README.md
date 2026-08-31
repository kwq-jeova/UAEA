# UAEA

UAEA is the Unified Autonomous Evolution Architecture.

The project separates a stable cognitive runtime from replaceable inference
platforms. Phase-1 freezes the agent control plane. Phase-2A introduces an
inference runtime abstraction so model serving engines and model artifacts can
change without redefining workflow, observation, artifact, or recovery
semantics.

## 1. Project Vision

UAEA is designed around three long-running goals:

- Cognitive runtime: preserve stable agent semantics for goals, workflows,
  tools, semantic observations, artifacts, and failure handling.
- Agent evolution pipeline: keep runtime traces and artifacts structured enough
  to support future memory, reflection, evaluation, and improvement loops.
- Inference abstraction: allow LMF, vLLM, local Transformers, OpenAI-compatible
  APIs, TensorRT-LLM, SGLang, or other inference runtimes to be selected behind
  a common contract.

The governing rule is:

```text
Cognitive Runtime stable
  -> Inference contract stable
  -> Backend implementation replaceable
```

## 2. Architecture Overview

Phase-1 is included as a frozen Git submodule:

```text
runtime/phase1-runtime
tag: v1.0.0-phase1-runtime
commit: de0ecb0e8837c848f842a996fa2dad1c93666f2f
```

Phase-1 freezes the Runtime Control Plane:

- Workflow lifecycle
- Goal / Intent relation
- Cursor execution model
- Capability execution
- Execution Observation
- Semantic Observation
- Artifact lifecycle
- Failure handling
- L0-L6 benchmark semantics

Phase-2A lives outside the frozen submodule:

```text
backend/             ModelBackend contract and adapters
benchmark/inference/ inference-only measurement framework
tests/               Phase-2A contract tests
docs/                architecture and validation records
data/                benchmark, trace, and diagnostic artifacts
```

Runtime path:

```text
User
  -> Phase-1 Cognitive Runtime
  -> ModelBackend Contract
  -> Backend Adapter
  -> Inference Platform
```

Current backend adapters:

- `LMFBackend`
- `VLLMBackend`
- `TransformersBackend`
- `MockBackend`

Trace layer:

```text
InferenceRequest
  -> TracingBackend
  -> InferenceTraceRecord
  -> JSONL trace sink
```

Trace records are emitted outside the frozen Phase-1 Runtime and may include
backend, model artifact, tokenizer metadata, rendered prompt, token ids,
generation config, finish reason, latency, and token usage.

## 3. Current Progress

| Area | Status |
| --- | --- |
| Phase-1 Cognitive Runtime Freeze | PASS |
| LMF baseline | PASS |
| ModelBackend contract | PASS |
| Inference trace layer | PASS |
| vLLM transport/API | PASS |
| vLLM backend adapter | PASS |
| vLLM semantic migration | bounded L0-L6 PASS |

Current production baseline:

```text
LMFBackend
DeepSeek-R1-Distill-Qwen-14B
HF/LLaMA-Factory 4-bit loading path
Phase-1 L0/L1/L2: PASS
```

Current vLLM production candidate:

```text
VLLMBackend
Qwen2.5-14B-Instruct-AWQ
traditional AWQ / auto_awq / GEMM
Phase-1 L0/L1/L2/L3/L4/L5/L6: PASS
```

Rejected vLLM artifact:

```text
DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4
compressed-tensors WNA16
Rejected for current production use due to first-token `!` pathology and
logprobs NaN under vLLM 0.26.0 on the current RTX 5090 D environment.
```

The DS14B result does not mean the original checkpoint is damaged, and it does
not mean compressed-tensors is globally unusable. The compatibility boundary is
the specific artifact representation, vLLM execution path, engine version, and
hardware envelope.

## 4. Validation Status

| Component | Status |
| --- | --- |
| Phase-1 Runtime | PASS |
| LMF Backend | PASS |
| ModelBackend Contract | PASS |
| Trace Layer | PASS |
| DS14B HF/LLaMA-Factory 4-bit | PASS |
| DS14B AWQ compressed-tensors vLLM | Rejected |
| Qwen2.5-14B-AWQ vLLM smoke | PASS |
| Qwen2.5-14B-AWQ Phase-1 selected cases | PASS |
| Qwen2.5-14B-AWQ Phase-1 L0/L1/L2 | PASS |
| Qwen2.5-14B-AWQ Phase-1 L3/L4/L5/L6 | PASS |

Qwen2.5-14B-AWQ validation artifacts:

```text
data/benchmark_results/qwen25_awq_phase1/
data/inference_traces/qwen25_awq_phase1/
```

Historical DS14B failure diagnostics are archived under:

```text
data/archive/phase2a_ds14b_vllm_failure/
docs/archive/phase2a-vllm-diagnostics/
```

The active DS14B root-cause summary remains:

```text
docs/phase2a-vllm-root-cause-analysis.md
```

The current model/artifact selection baseline is:

```text
docs/phase2a-model-artifact-baseline.md
docs/phase2a-vllm-qwen25-equivalence-report.md
```

## 5. Running Validation

Run Phase-2A unit tests from the repository root:

```text
python -m unittest discover -s tests -t . -v
```

Run the frozen Phase-1 benchmark through vLLM:

```text
python benchmark_phase1_vllm.py \
  --base-url http://127.0.0.1:8001/v1 \
  --model qwen25-14b-awq \
  --level L0 \
  --json \
  --trace-output data/inference_traces/qwen25_awq_phase1/example.jsonl
```

The bounded Qwen2.5-AWQ L0-L6 baseline was generated with:

```text
data/inference_traces/qwen25_awq_phase1/qwen25_awq_l0_l2_20260815T065250Z.jsonl
data/inference_traces/vllm_qwen25_phase1_l3_l6.jsonl
data/inference_traces/vllm_qwen25_phase1_l3_l6.enriched.jsonl
data/benchmark_results/qwen25_awq_phase1/
data/benchmark_results/vllm_qwen25/
```

vLLM model assets are stored outside the repository:

```text
/opt/uaea-models/models/
/opt/uaea-models/cache/
/opt/uaea/vllm_env
```

Generated vLLM runtime logs belong outside source control:

```text
/opt/uaea-runtime/vllm/
```

## 6. Engineering Principle

Preserve evidence, isolate variables, validate abstraction.

Failed experiments are retained and archived instead of hidden. Passing
benchmarks are accepted only when Phase-1 Runtime semantics and benchmark
expectations remain unchanged.

Next roadmap boundary:

```text
Phase-2A: bounded vLLM production validation complete for Phase-1 L0-L6
Phase-2A next: harden production serving and monitoring without changing Phase-1
Phase-2B: define Memory Boundary Architecture before SQLite implementation
```

Current Phase-2B Memory architecture baseline:

```text
docs/phase2b-memory-boundary-architecture.md
docs/phase2b-memory/memory-architecture-boundary-v0.1.md
docs/phase2b-memory/python-environment.md
```

Phase-2B review conclusion:

```text
Conversation Context != Memory

Memory Element
  + lifecycle_state
  + representation_facets
  + confidence
  + validity_boundary
  + evidence_references
  + relationship_edges
```

Episodic, semantic, and procedural/habit forms are treated as representation
facets, not mutually exclusive memory types. Consolidation is a state
transition process. Dormant is a lifecycle state. SQLite remains a persistence
adapter and does not define the Memory architecture.

Phase-2B implementation slice:

```text
Memory Candidate domain model
Structural validation
Evidence references
Scope hypothesis
Candidate lifecycle
```

Phase-2B architecture test fixture:

```text
data/memory_test_fixtures/long_context_mixed_100.json
docs/phase2b-memory/memory-architecture-test-fixtures.md
python -m unittest tests.memory.test_architecture_fixtures -v
python scripts/evaluate_memory_fixture.py data/memory_test_fixtures/long_context_mixed_100.json --json
```
