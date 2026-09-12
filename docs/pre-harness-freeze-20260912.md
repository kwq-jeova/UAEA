# UAEA Pre-Harness Baseline

Date: 2026-09-12

This document records the Phase-1 / Phase-2 state before any Codex Harness
integration. It is a preservation boundary, not a new runtime design.

## Freeze Scope

The baseline preserves:

- the Phase-1 runtime submodule and its L0-L6 benchmark behavior;
- the Phase-1 capability registration and observation boundary;
- the Phase-1 `ActionRequest` and Cognition-level turn-relation work;
- the Phase-2 backend contract and runtime factory;
- the current Web capability path for `web.search` and `web.fetch`;
- SQLite source history and `EvidenceReference` integration;
- candidate/evidence fixtures and evaluators;
- JSONL trajectories, benchmark reports, and the Qwen2.5 AWQ capability-boundary
  experiment artifacts;
- current vLLM startup scripts and documented model/inference constraints.

No Runtime, Web, Memory, or backend redesign is part of this freeze.

## Phase-1 Frozen Baseline

The preserved Phase-1 control-plane path is:

```text
Agent
  -> action proposal
  -> action normalization
  -> capability/tool validation
  -> execution
  -> ExecutionObservation
  -> cognition/answer
```

The current implementation also preserves the following verified extensions:

- dynamic capability registration;
- capability metadata and agent-facing capability visibility;
- `ActionRequest`;
- normalized `ToolResult` and `ExecutionObservation`;
- Cognition-level `TurnRelationRecord` for reference, challenge, and
  continuation inputs;
- trace visibility for capability and observation identity.

The Phase-1 runtime remains a historical and experimental baseline. It is not
being reshaped to match a future Harness.

## Phase-1 Validation

Recorded validation at freeze:

```text
python -m unittest discover -s tests -t . -v
128 tests: PASS

runtime/phase1-runtime/tests/runtime_benchmark/phase1_runtime_benchmark.py
--mode scripted --level all --json
24/24: PASS
```

The saved Qwen2.5 capability-boundary artifacts are under:

```text
data/phase1_qwen25_14b_awq_capability_boundary/
```

The live vLLM endpoint was not running during the freeze audit. Existing real
Qwen2.5 AWQ validation remains the evidence for the serving baseline.

## Phase-2 Frozen Baseline

The current Phase-2 state contains:

- `ModelBackend`, `VLLMBackend`, `ModelClient`, and runtime factory boundaries;
- the vLLM OpenAI-compatible transport path;
- `web.search` and `web.fetch` registered through the capability boundary;
- Web adapter execution with SQLite source history;
- bounded evidence projection and `EvidenceReference`;
- JSONL trajectory and execution-observation tracing;
- candidate/evidence fixture validation without automatic Memory promotion.

The current Phase-2 Web path is preserved as a probe and reference
implementation. It is not declared to be the future generic Agent runtime.

## Known Architecture Findings

These findings are intentionally frozen rather than repaired in this
checkpoint:

- WebShell has accumulated semantic routing and refinement behavior.
- Workflow/runtime semantics can leak into Web observation interpretation.
- Observation can still be confused with a new task in some cognition paths.
- Continuation ownership is not yet a fully settled boundary.
- Runtime, Tool, Skill, and Workflow concepts have some duplicated lifecycle
  responsibilities.
- The current implementation is suitable for historical replay and A/B
  comparison, not yet a proof of the final Harness boundary.

## Hardware and Inference Boundary

The current physical experiment boundary is:

```text
Host: Windows 11
Linux runtime: WSL2 Ubuntu 24.04.x
GPU: NVIDIA RTX 5090 D v2
VRAM: 24 GB class, single GPU
Model: Qwen2.5-14B-Instruct-AWQ
Quantization: traditional AWQ, approximately 4-bit
Serving: vLLM
Endpoint: http://127.0.0.1:8001/v1
Served model: qwen25-14b-awq
Max model length: 8192 in the bounded validation script
GPU memory utilization: 0.7 in the current startup script
```

The current vLLM script uses the isolated environment:

```text
/opt/uaea/vllm_env
```

and model assets outside the repository:

```text
/opt/uaea-models/models/Qwen2.5-14B-Instruct-AWQ
/opt/uaea-models/cache
```

No Harness integration may silently change quantization, precision, context
length, KV policy, GPU utilization, concurrency, or model artifact.

## Reuse Matrix

### Direct Reuse

- Qwen2.5-14B-Instruct-AWQ model artifact;
- isolated vLLM environment and startup script;
- vLLM endpoint and served model naming;
- CUDA/PyTorch/vLLM serving stack already validated;
- JSONL trajectory format and saved benchmark artifacts;
- SQLite source history database schema and source snapshots;
- `EvidenceReference` and bounded evidence projection;
- memory fixture evaluator and candidate structural tests;
- current Phase-1 and Phase-2 regression tests.

### Thin Adapter Reuse

- `ModelBackend` / `ModelClient` boundary;
- `ActionRequest`;
- `ExecutionObservation`;
- Tool/Capability result normalization;
- Web capability result to observation conversion;
- trace/event normalization between execution infrastructure and UAEA
  cognition;
- future Harness result to UAEA observation conversion.

The adapter must preserve evidence identity, provenance, execution status, and
trace references. It must not import Harness execution state into UAEA Goal
Hypothesis.

### Legacy / Reference Only

- generic Phase-1 workflow orchestration;
- WebShell semantic routing and refinement heuristics;
- generic continuation logic;
- duplicated tool/workflow lifecycle plumbing;
- any future Harness-provided retry, todo, subagent, or context machinery.

These files remain available for replay and A/B comparison. They are not
targets for further expansion during Harness integration.

### UAEA Core Research

Harness must not own or replace:

- Goal Hypothesis;
- Problem Space and Problem Boundary;
- active constraints and active hypotheses;
- epistemic state and epistemic update;
- uncertainty and evidence quality;
- Working Memory, Episodic Memory, and Long-term Memory;
- Candidate versus Memory versus Truth boundaries;
- SQLite-backed cognitive history;
- trajectory evaluation;
- post-training dataset construction;
- LoRA or layered adaptation research.

## Harness Compatibility Assessment

The current infrastructure is compatible in principle with a thin Harness
adapter because inference already crosses an HTTP/backend boundary and the
runtime already has explicit action and observation concepts.

The following items are verified prerequisites:

- the current local inference path is OpenAI-compatible at
  `http://127.0.0.1:8001/v1`;
- the served model identity is `qwen25-14b-awq`;
- Phase-1 and Phase-2 do not require direct access to CUDA or model weights;
- Web and SQLite execution can be represented as bounded observations.

The following items are not yet verified and must remain explicit unknowns:

- whether the target Harness accepts this exact local Responses/agentic
  protocol;
- whether its tool-call schema matches the current Qwen2.5 chat behavior;
- whether its reasoning parser is compatible with Qwen2.5 AWQ output;
- whether Harness context and retry behavior add material prompt/KV overhead;
- whether Harness launches another model/runtime process or consumes GPU memory;
- whether Harness requires a different vLLM endpoint mode or server flags;
- whether its Web/MCP layer can be disabled in favor of the existing Web
  capability;
- whether its continuation/subagent abstractions can be kept outside UAEA
  Cognition state.

No claim of Harness compatibility is made until these unknowns are tested
against the unchanged local vLLM stack.

## Minimal Feasibility Plan

The next checkpoint should be a compatibility probe, not a migration:

1. Keep the current vLLM server command and Qwen2.5 AWQ artifact unchanged.
2. Start with a no-tool local model request through the candidate Harness
   protocol.
3. Verify model identity, response shape, token/finish metadata, and endpoint
   behavior.
4. Add one deterministic local capability through a thin adapter.
5. Verify that the returned Harness event can be normalized to an existing
   `ExecutionObservation`.
6. Reuse the existing SQLite/trajectory sink without moving Goal Hypothesis
   into Harness state.
7. Compare ordinary answer, capability execution, failure, and continuation
   traces against the saved Pre-Harness baseline.

The probe must record CPU/RAM overhead, GPU residency, KV/context changes,
protocol differences, and any required vLLM parameter change. A parameter
change that affects the existing benchmark envelope requires a separate
experiment and is not part of the baseline.

## Explicit Stop Point

This checkpoint stops before:

- Harness installation or migration;
- Runtime deletion or replacement;
- Web rewrite;
- Goal Engine, Problem Manager, or Entropy Manager;
- Memory redesign;
- LMF/Harness parallel integration;
- model, quantization, precision, context, KV, or GPU policy changes.

The freeze tag identifies the preserved Pre-Harness state. Future Harness work
must be measured against this state rather than silently modifying it.
