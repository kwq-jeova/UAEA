# Phase-2B Runtime Web / Context / KV Feasibility Rehearsal

> Status: feasibility rehearsal
> Scope: networking access, context construction, and KV/context overflow risk
> Non-goal: modifying Phase-1 Runtime, implementing browser automation,
> implementing Memory Policy, or adding retrieval

## 1. Current Runtime Boundary

Phase-1 Runtime is frozen.

Frozen external turn boundary:

```text
runtime.agent_runtime.Agent.handle(user_input)
```

Frozen authority order:

```text
Current User Input
  > Intent Relation
  > Active Goal
  > Active Workflow
  > Workflow Artifact
  > Semantic Observation
  > Conversation Context
```

Current tool boundary is local and sandboxed:

```text
document.read_file
document.read_section
document.write_file
fs.list
fs.mkdir
```

Current model access is already network-shaped, but local:

```text
ModelClient.chat(...)
  -> OpenAI-compatible HTTP endpoint
  -> local LMF / vLLM backend
```

This means Phase-1 already has a network client pattern for model serving, but
does not have a user-facing web research capability.

## 2. Feasibility Verdict

Adding Web access is feasible only if it is introduced outside Phase-1 core
semantics.

Recommended boundary:

```text
Phase-2 Web Research Adapter
  -> web_search / fetch_page
  -> Source Event
  -> SQLite Source History
  -> EvidenceReference
```

Do not first implement:

- autonomous browsing
- browser automation
- background agents
- schedulers
- website login workflows
- retrieval-augmented Runtime prompt injection

The first useful target is not "a web assistant". The first target is:

```text
external evidence capture
```

## 3. Minimal Web Research Tool Shape

The smallest useful tool should record:

```text
query
timestamp
URL
title
source domain
retrieved excerpt / page text hash
fetch status
latency
raw response metadata
```

It should produce a source record, not a Memory.

```text
User asks research question
  -> Web Research Adapter
  -> Web Source Record
  -> EvidenceReference(source_kind="web_page" or "web_search_result")
```

The assistant may answer from the web evidence in the current turn, but durable
memory should still require Candidate and Policy later.

## 4. Runtime Integration Options

### Option A: Outside Runtime, recommended first

```text
User / experiment script
  -> Web Research Adapter
  -> SQLite source_ingestion.sqlite
  -> manual EvidenceReference / Candidate tests
```

Pros:

- zero Phase-1 Runtime modification
- clean source/evidence validation
- easier to classify errors
- no planner/tool routing changes

Cons:

- not yet an integrated assistant tool

This is the recommended first experiment.

### Option B: Phase-2 wrapper around frozen Runtime

```text
Phase-2 Assistant Shell
  -> decides when to call Web Research Adapter
  -> records source events
  -> passes bounded evidence summary to Agent.handle(...)
```

Pros:

- starts to behave like a local work assistant
- keeps Phase-1 `Agent.handle` unchanged

Cons:

- requires clear prompt projection boundary
- wrapper can accidentally bypass Runtime authority if not constrained

This is feasible after Option A.

### Option C: Add web capability inside Phase-1 ToolRegistry

Not recommended now.

It would modify the frozen capability surface and planner prompt, creating a
Phase-1 semantic contract change.

## 5. Context Construction Risk

Current Phase-1 context behavior is bounded by turns and compact string limits,
not by true tokenizer budget.

Known current behavior:

- `ContextManager.max_recent_turns = 8`
- recent conversation is trimmed by turn count
- planner projection includes active goal, workflow, semantic context,
  document context, and artifact context
- large execution observations truncate content before model context
- workflow artifacts truncate content to bounded character limits

This is useful but insufficient for Web.

Web pages and search results can be large and repetitive. If raw web page text
is injected into prompt context, the system can create:

- prompt overflow
- poor planning due to noisy evidence
- higher KV cache pressure
- stale external facts being reused as if current
- citation/provenance loss

Therefore Web evidence should enter Runtime prompt only through a projection:

```text
raw web page
  -> source record
  -> evidence summary / excerpt
  -> bounded prompt projection
```

Raw fetched content should stay in SQLite/source files, not in prompt history.

## 6. KV / Context Overflow Rehearsal

The main overflow risk is not SQLite storage. It is prompt projection.

Risk path:

```text
web page text
  + conversation history
  + planner context
  + file/tool output
  + retrieved memory
  -> prompt tokens exceed model context
  -> truncation / timeout / degraded planning
```

Phase-1 already records backend `usage` through the model client and backend
trace layers in other parts of the project. The missing Runtime-level budget is
a strict projection policy.

Recommended rehearsal metrics:

```text
source_bytes
source_chars
projected_chars
estimated_prompt_tokens
actual_prompt_tokens if backend returns usage
completion_tokens
finish_reason
context_source_count
oldest_current_turn_index
dropped_source_count
```

Recommended stress cases:

| Case | Expected behavior |
| --- | --- |
| small search result | projected directly as short evidence summary |
| long web page | raw stored, excerpt projected |
| multiple pages | only ranked summaries projected |
| conflicting pages | project disagreement and provenance, not merged truth |
| stale web page | preserve fetch timestamp and source URL |
| failed fetch | record failed source event, no fabricated content |

## 7. Web Evidence and Memory Weight

The pasted design note highlights a key point:

```text
Memory weight emerges over time.
```

For Web-enabled UAEA, weight should come from interaction history, not from one
source row.

Examples of weight signals:

- same issue appears across multiple sessions
- same source is rechecked after dependency changes
- user corrects a previous interpretation
- external source confirms or contradicts prior project belief
- benchmark result and web source point to the same boundary
- a remembered constraint successfully prevents repeated failure

Therefore the first Web track should accumulate:

```text
Interaction Event
Web Event
Source Record
EvidenceReference
Candidate later
```

not:

```text
Web page
  -> immediate long-term Memory
```

## 8. Recommended Pre-Implementation Plan

Phase W0: no Runtime integration

```text
web query fixture
  -> source record
  -> SQLite
  -> EvidenceReference
```

Phase W1: deterministic web adapter smoke

```text
fixed URL / saved HTML
  -> fetch or load
  -> source_files / web_sources
  -> bounded summary metadata
```

Phase W2: live web research adapter

```text
query
  -> search result metadata
  -> selected page fetch
  -> source records
  -> source trace
```

Phase W3: Phase-2 wrapper experiment

```text
Phase-2 shell
  -> web adapter
  -> bounded evidence projection
  -> frozen Agent.handle(...)
```

Phase W4: Candidate fixture from web evidence

```text
external EvidenceReference
  -> manually constructed Candidate
  -> structural validation
```

Do not implement Runtime web capability inside Phase-1 during these phases.

## 9. Architecture Findings

implementation:

- No Runtime code change is needed for the first Web evidence experiment.

adapter:

- A web adapter should be source-first and evidence-first.
- It should not be a browser automation system at this stage.

database:

- Current `source_ingestion.sqlite` can host web source records if a source kind
  and source file model are added later.
- It should still not become Memory Store.

candidate:

- Existing `EvidenceReference` is sufficient as the bridge if source kinds
  include web source objects.

architecture:

- Real memory "weight" cannot be validated only by schema.
- A longer-running interaction/evidence history is needed before Memory Policy
  is frozen.

runtime:

- Direct modification of Phase-1 ToolRegistry is not justified yet.
- Use a Phase-2 wrapper or offline source adapter first.

## 10. Closure Verdict

Feasible, with boundaries.

```text
Web access: feasible as Phase-2 source adapter
Runtime integration: feasible through wrapper, not Phase-1 core
Context safety: feasible only with bounded projection
KV overflow control: requires metrics and prompt budget policy
Memory Policy: should wait for longer interaction history
```

The next practical slice should be a deterministic Web Source fixture, not a
live autonomous assistant.
