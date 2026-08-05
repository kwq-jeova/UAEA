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
- Phase-2A-3 vLLM Backend Adapter: DONE (real smoke pending service)
- Production backend: `LMFBackend`
- Validation backend: `MockBackend`
- Available alternate adapter: `VLLMBackend`
- Future adapter: external API backend

See `docs/phase2a-model-backend.md` for the API boundary and
`docs/phase2a-backend-equivalence.md` for equivalence validation.
See `docs/phase2a-vllm-backend.md` for selection and smoke instructions.

Run Phase-2A tests from the repository root:

```text
python -m unittest discover -s tests -t . -v
```
