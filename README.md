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
