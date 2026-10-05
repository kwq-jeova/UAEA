# Phase-2B Memory Architecture Test Fixtures

> Status: RESEARCH_FOUNDATION
> Role: RESEARCH_FOUNDATION / 100-turn 验收思想
> Phase: Phase-2B fixture checkpoint
> Still valid: 结构 fixture 仍复用，不是 extractor/policy 已实现
> Superseded: 无
> Current reference: [Documentation Guide](../../README.md)
> Governance reviewed: 2026-10-02（文档治理，不等于新实验验证）
> 保留研究思想与未决问题；旧 runtime wiring 不是当前接入合同，未宣称认知功能已实现。

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
