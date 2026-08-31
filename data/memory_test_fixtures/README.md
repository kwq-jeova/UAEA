# Phase-2B Memory Architecture Test Fixtures

This directory stores deterministic Memory architecture fixtures.

Current scope:

```text
long conversation input
expected Memory Candidates
expected semantic outcomes
no extractor implementation
no Memory Policy implementation
no SQLite schema
```

The fixtures are designed to test whether the Memory Candidate boundary can
survive noisy multi-turn input without turning full conversation history into
Memory.

The first fixture is:

```text
long_context_mixed_100.json
```

It models a 100-turn UAEA architecture session containing project goals,
explicit constraints, benchmark facts, failure localization, superseded
decisions, inferred preferences, unresolved issues, and unrelated project
associations.

Evaluate the fixture with:

```text
python scripts/evaluate_memory_fixture.py data/memory_test_fixtures/long_context_mixed_100.json --json
```
