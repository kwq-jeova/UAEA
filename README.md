# UAEA Phase-2A

Phase-2A adds an inference backend abstraction without changing the frozen
Phase-1 Runtime lifecycle.

Phase-1 is included as a Git submodule at:

```text
runtime/phase1-runtime
```

Pinned baseline:

```text
tag: v1.0.0-phase1-runtime
commit: de0ecb0e8837c848f842a996fa2dad1c93666f2f
```

Phase-2A source lives outside the submodule:

```text
backend/             model backend contracts and adapters
benchmark/inference/ inference-only measurement framework
tests/               Phase-2A contract tests
docs/                initialization and migration records
```

The governing rule is: inference backends may change, while Goal, Workflow,
Artifact, Context, and recovery semantics remain frozen.

Run the Phase-2A Runtime through the replaceable backend layer:

```text
python main.py
```

Phase-2A progress:

- Phase-2A-1 Model Backend API: DONE
- Phase-2A-2 Backend Equivalence Validation: DONE
- Phase-2A-3 vLLM Backend Adapter: DONE (DS14B vLLM API smoke passed)
- Phase-2A-4 vLLM Compatibility Audit: DONE (installation pending)
- Phase-2A-5 vLLM Small Model Smoke Validation: DONE (bounded engine/API/backend smoke passed)
- Phase-2A-5 vLLM Backend Integration Closure: PASS (DS14B OpenAI-compatible API verified)
- Production backend: `LMFBackend`
- Validation backend: `MockBackend`
- Available alternate adapter: `VLLMBackend`
- Future adapter: external API backend

See `docs/phase2a-model-backend.md` for the API boundary and
`docs/phase2a-backend-equivalence.md` for equivalence validation.
See `docs/phase2a-vllm-backend.md` for selection and smoke instructions.
See `docs/phase2a-vllm-environment.md` for the isolated deployment checklist.
See `docs/phase2a-vllm-compatibility-audit.md` for the selected vLLM, PyTorch,
CUDA, Blackwell, and AWQ compatibility decisions.
See `docs/phase2a-vllm-small-model-smoke.md` for the bounded engine and Runtime
integration validation.

## Phase-1 Runtime Baseline

Phase-1 goal:

Build a reliable Runtime Control Plane.

Frozen components:

- Workflow lifecycle
- Goal / Intent relation
- Cursor execution model
- Capability execution
- Observation model
- Artifact model
- Failure handling
- L0-L6 benchmark logic

Core architecture:

```text
Session / Project
  -> Goal Hypothesis
  -> Task
  -> Workflow
  -> Step
  -> Capability Action
  -> Capability Execution
  -> Execution Observation
  -> Semantic Observation
  -> Answer / Artifact
  -> Trajectory Event
  -> Future SQLite Ledger
```

## Phase-1 Runtime on vLLM Backend

```text
Phase-1 Runtime
  -> ModelBackend API
  -> VLLMBackend
  -> vLLM Server
```

Run the Phase-1 benchmark against vLLM:

```text
python benchmark_phase1_vllm.py
```

Validation targets:

- vLLM serving PASS
- Backend contract PASS
- Phase-1 benchmark PASS
- Runtime behavior equivalent PASS

## WSL Model and Runtime Storage Layout

Phase-2A keeps source, Python packages, model assets, and execution artifacts in
separate locations:

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

Future DS14B/AWQ artifacts should be placed under `/opt/uaea-models/models/`.
Generated logs, pid files, smoke outputs, and benchmark snapshots belong under
`/opt/uaea-runtime/vllm/`.

Run Phase-2A tests from the repository root:

```text
python -m unittest discover -s tests -t . -v
```
