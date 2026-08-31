# Phase-2B Memory Architecture Test Fixtures

> Status: test design baseline
> Scope: fixtures for architecture validation
> Non-goal: extractor implementation, Memory Policy implementation, retrieval,
> SQLite schema, embeddings, or Memory Store implementation

## Purpose

Phase-2B Memory should be validated from realistic use cases, not only from
field design. The first reusable fixture models a long mixed conversation where
project-relevant architecture work is interleaved with unrelated associations,
temporary ideas, failed experiments, benchmark facts, superseded decisions, and
explicit constraints.

The fixture is:

```text
data/memory_test_fixtures/long_context_mixed_100.json
```

## Test Principle

The expected output is not a conversation summary.

The expected output is a candidate and outcome structure:

```text
100-turn conversation
  -> expected Memory Candidates
  -> expected active / dormant / deferred / rejected outcomes
  -> traceable evidence references
```

This validates the key boundary:

```text
Conversation Context != Memory
```

## Fixture Coverage

The first fixture covers:

- explicit durable constraints
- inferred preference
- benchmark-backed technical fact
- failure lesson
- supersession candidate
- unresolved issue
- rejected overgeneralized candidate
- unrelated project associations / noise
- language preference
- filesystem safety constraint

## Architecture Expectations

The fixture encodes these expectations:

- Memory Candidates remain atomic claims.
- Candidate evidence is referenced, not duplicated.
- Scope remains a hypothesis at candidate stage.
- Explicit and inferred provenance remain distinguishable.
- Rejected Candidate is not Memory.
- Supersession is represented as an expected outcome, not as Candidate
  admission authority.
- The expected Memory structure is much smaller than the 100-turn input.

## Current Validation

Current tests only validate fixture structure and Candidate compatibility. They
do not implement extraction or policy.

Test command:

```text
python -m unittest tests.memory.test_architecture_fixtures -v
```

Direct evaluator command:

```text
python scripts/evaluate_memory_fixture.py data/memory_test_fixtures/long_context_mixed_100.json --json
```

The same fixture should be reused later to test:

```text
Extractor
  -> Candidate
  -> Policy
  -> Memory Element
```
