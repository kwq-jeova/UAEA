# Phase-2B Memory Directory Plan

> Status: planning only
> Scope: directory-level architecture
> Non-goal: creating implementation packages in this step

## 1. Current Decision

Do not create the full `memory/` implementation tree yet.

Phase-2B is still at boundary architecture stage. Creating many empty
directories now would imply module boundaries before Memory Candidate, Policy,
Retrieval, and Persistence responsibilities are stable.

For now, keep implementation changes to boundary markers only:

```text
docs/phase2b-memory-boundary-architecture.md
docs/phase2b-memory-directory-plan.md
docs/phase2b-memory/memory-architecture-boundary-v0.1.md
docs/phase2b-memory/python-environment.md
memory/README.md
data/memory/README.md
```

`memory/README.md` is a source-boundary marker, not a Memory implementation.
`data/memory/README.md` keeps the runtime-data path visible while SQLite
database files remain ignored.

## 2. Future Directory Shape

When implementation starts, the likely top-level shape is:

```text
D:\UAEA\
├── runtime\
│   └── phase1-runtime\          # frozen, do not modify for Memory
│
├── backend\                     # Phase-2A inference abstraction
│
├── memory\                      # Phase-2B Memory subsystem, future
│   ├── boundary\                # intake/export boundaries
│   ├── candidates\              # Memory Candidate records and extraction
│   ├── policy\                  # lifecycle and persistence policy
│   ├── consolidation\           # candidate -> durable memory, future
│   ├── retrieval\               # query/ranking/projection, future
│   └── persistence\             # SQLite adapter, future
│
├── docs\
│   ├── phase2b-memory-boundary-architecture.md
│   ├── phase2b-memory-directory-plan.md
│   └── archive\
│
└── data\
    ├── benchmark_results\
    ├── inference_traces\
    └── memory\                  # future local SQLite / exports
```

This is a target shape, not an instruction to create these directories now.

## 3. What Belongs In Phase-2B

Phase-2B should own:

- Memory Boundary
- Memory Candidate
- Memory Policy
- candidate provenance
- lifecycle metadata
- Context Distillation boundary
- Retrieval Projection boundary
- SQLite persistence adapter boundary

Phase-2B should not own:

- Phase-1 Runtime lifecycle semantics
- Artifact schema changes
- benchmark expectation changes
- vLLM backend behavior
- reflection and cognition synthesis as final products
- LoRA training corpus generation

## 4. Minimal First Implementation Layout

When the architecture is approved, start with the smallest useful layout:

```text
memory\
├── boundary\
├── candidates\
├── policy\
└── persistence\

data\
└── memory\
```

Do not add `retrieval/` until there is an accepted Memory record format. Do not
add `consolidation/` until candidate policy and persistence are exercised.

## 5. Deferred Directories

| Directory | Defer because |
| --- | --- |
| `memory/retrieval/` | retrieval should not exist before accepted memory semantics are stable |
| `memory/consolidation/` | consolidation risks becoming reflection/cognition prematurely |
| `memory/reflection/` | Reflection is a later phase, not Phase-2B boundary design |
| `memory/cognition/` | Cognition Assets are downstream of Memory and Reflection |
| `memory/training/` | training corpus generation is outside Phase-2B |

## 6. Documentation Placement

Keep the top-level Phase-2B boundary index in root `docs/`, and keep focused
Phase-2B Memory design notes under `docs/phase2b-memory/`:

```text
docs/phase2b-memory-boundary-architecture.md
docs/phase2b-memory-directory-plan.md
docs/phase2b-memory/memory-architecture-boundary-v0.1.md
docs/phase2b-memory/python-environment.md
```

The nested directory is now the active location for Memory-specific lifecycle
and environment documents. It still does not imply Memory implementation has
started.

## 7. Data Placement

Future local memory data should live under:

```text
data/memory/
```

Expected future contents:

- SQLite database
- candidate export fixtures
- retrieval test fixtures
- migration snapshots

Do not store model weights, credentials, or runtime service logs under
`data/memory/`.

## 8. Current Action

Current action is architecture and environment-boundary only:

```text
Create architecture documents.
Create README boundary markers.
Create isolated .venv_memory locally.
Run sqlite3 smoke test.
Do not implement SQLite.
Do not create Memory schema.
Do not modify frozen Phase-1 Runtime.
```
