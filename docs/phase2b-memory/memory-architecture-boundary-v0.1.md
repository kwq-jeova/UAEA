# UAEA Phase-2B Memory Architecture Boundary v0.1

> Status: architecture proposal
> Scope: Memory data lifecycle and temporal boundary
> Non-goal: SQLite schema, CRUD implementation, retrieval implementation, or
> Phase-1 Runtime changes

## 1. Design Position

The Phase-2B Memory architecture starts from a negative rule:

```text
Conversation Context != Memory
```

Conversation context is working state. Memory is selected, distilled, validated,
and lifecycle-managed knowledge or experience that may outlive the Runtime
session.

This document extends the existing Memory Boundary Architecture by defining the
temporal lifecycle of Memory data. It does not design tables or implement
SQLite.

## 1A. Architecture Review Update

The current architecture review changes the emphasis from a tier-first model
to an object-state-facet model.

Core decision:

```text
Memory is an object with mutable lifecycle state.
Evidence and provenance should be preserved as append-only references.
Episodic, semantic, and procedural forms are representation facets, not
mutually exclusive memory types.
```

This means the architecture should separate:

- Memory object identity
- lifecycle state
- representation facet
- evidence/provenance graph
- retrieval priority
- validity boundary

The older short-term / mid-term / long-term tier language remains useful as a
policy vocabulary, but it must not be treated as the primary state machine.

## 1B. Current Core Abstraction

The recommended abstraction is:

```text
Runtime Object
  -> Memory Candidate
  -> Memory Element
```

A Memory Element then carries orthogonal dimensions:

```text
Memory Element
  + lifecycle_state
  + representation_facets
  + confidence
  + validity_boundary
  + evidence_references
  + relationship_edges
```

Current lifecycle states:

- working_context
- candidate
- active
- dormant
- reactivated
- superseded
- archived
- expired
- rejected

Current representation facets:

- episodic
- semantic
- procedural / habit
- preference
- constraint
- decision
- failure lesson
- unresolved issue

The facets are not exclusive. A DS14B vLLM failure record can be episodic
because it records a concrete experiment, semantic because it produced an
artifact compatibility principle, and decision-oriented because it rejected a
production artifact for the current stack.

## 1C. Reviewed Lifecycle State Machine

The current state machine is:

```text
Working Context
  -> Observation / Extraction
  -> Memory Candidate
  -> Active Memory
  -> Dormant Memory
  -> Reactivated Memory
  -> Superseded / Archived / Expired / Rejected
```

State meanings:

| State | Meaning |
| --- | --- |
| working_context | Current prompt/session material; not durable Memory. |
| candidate | Extracted content awaiting policy and validation. |
| active | Accepted and eligible for normal retrieval. |
| dormant | Preserved but low retrieval priority because current relevance is weak. |
| reactivated | Dormant or archived memory brought back by new evidence or goal relevance. |
| superseded | Replaced by a newer or more accurate memory while retaining history. |
| archived | Historical record retained outside normal retrieval. |
| expired | Validity boundary closed; retained for audit unless policy later deletes. |
| rejected | Candidate failed policy or validation. |

Short-term, mid-term, and long-term should be interpreted as retrieval and
policy tiers inside active/dormant memory, not as the only lifecycle states.

## 1D. Memory Relationship Model

Memory should be graph-addressable even if the first persistence backend is
SQLite.

Minimum relationship concepts:

| Relationship | Meaning |
| --- | --- |
| derived_from | Memory was extracted from a runtime event, context segment, artifact, or episode. |
| supported_by | Evidence supports the memory's claim or decision. |
| supersedes | Current memory replaces an older memory. |
| superseded_by | Older memory points to the replacing memory. |
| conflicts_with | Two memories cannot both be fully true under the same scope. |
| refines | New memory narrows, clarifies, or scopes an older memory. |
| instance_of | Episode or habit instance supports a broader semantic memory. |
| related_to | Weak association used for retrieval, not proof. |

Relationship edges prevent two failure modes:

- silent overwrite of old memory
- self-reinforcing memory that repeats without evidence

## 1E. Reviewed Concept Status

| Concept | Current status | Reason |
| --- | --- | --- |
| Conversation Context | evidence / working state | It is too noisy and transient to be Memory. |
| Working Memory | renamed to working_context | Avoid implying it is already durable Memory. |
| Candidate Memory | accepted | Required policy boundary between extraction and persistence. |
| Episodic Memory | representation facet | Episodes provide evidence and narrative structure. |
| Semantic Memory | representation facet | Semantic knowledge is an abstraction over evidence. |
| Habit / Procedural Memory | representation facet | Useful for repeated stable behavior, but not semantic knowledge. |
| Consolidation | transition process | It changes state/facet/confidence; it is not a type. |
| Dormant Memory | lifecycle state | Dormancy changes retrieval priority, not object identity. |
| Forgetting | retrieval/status change first | Deletion should be conservative and policy-controlled. |

## 2. Memory Lifecycle Model

Recommended lifecycle:

```text
Working Context
  -> Candidate Memory
  -> Short-Term Memory
  -> Mid-Term Memory
  -> Long-Term Memory
  -> Archive / Superseded / Expired
```

This is not an age ladder. A Memory Element does not become long-term merely
because it is old. Lifetime is driven by:

- relevance
- recurrence
- confidence
- validation
- reuse value
- stability
- dependency
- supersession

### Working Context

Why it exists:

- supports the current turn, prompt projection, and immediate Runtime decision
- preserves bounded local continuity without claiming durable value

Contains:

- recent conversation messages
- active goal context
- active workflow cursor
- latest execution / semantic context
- prompt projection
- temporary summaries

Entry:

- created by the current session and Phase-1 ContextManager

Exit:

- discarded, summarized, or distilled after the active turn/session boundary

Promotion:

- only through Context Distillation or Runtime Object Candidate Extraction

Expiration:

- normally expires when no longer needed for the current session or active
  workflow

Reactivation:

- not directly; a future Memory Projection may reconstruct relevant context,
  but it is not the original Working Context

### Candidate Memory

Why it exists:

- prevents raw context and Runtime objects from becoming Memory automatically
- gives policy a place to evaluate value, evidence, scope, and validity

Contains:

- extracted claim
- source object / event references
- candidate type
- proposed lifecycle tier
- confidence
- evidence summary
- unresolved validation needs

Entry:

- distilled from conversation context
- extracted from Runtime objects, ledger events, semantic observations,
  artifacts, failures, or explicit user statements

Upgrade:

- becomes Short-Term, Mid-Term, or Long-Term only after policy accepts it

Downgrade:

- may be discarded, held for more evidence, or marked rejected

Expiration:

- expires if relevance, evidence, or validation does not materialize

Reactivation:

- allowed if new evidence references the same claim or unresolved issue

### Short-Term Memory

Why it exists:

- holds useful information beyond the immediate prompt but not yet stable
  enough for project-wide or long-term reuse

Contains:

- active user constraints
- unresolved issues
- near-term preferences
- temporary project decisions
- recently validated observations

Entry:

- candidate has enough evidence to be useful soon
- candidate is tied to an active or nearby workflow/project phase

Upgrade:

- repeated use, explicit confirmation, successful reuse, or stronger evidence

Downgrade:

- loses relevance, becomes contradicted, or is scoped down to one session

Expiration:

- when task/project scope closes without durable value

Reactivation:

- allowed if similar task context reappears and the memory is not expired or
  superseded

### Mid-Term Memory

Why it exists:

- preserves project-phase knowledge that is stable enough to guide future work
  but not yet a universal principle

Contains:

- Phase-level architecture decisions
- model/backend compatibility boundaries
- validated project constraints
- recurring user preferences within a project
- proven strategies with bounded applicability

Entry:

- candidate or short-term memory has evidence, reuse value, and project-phase
  scope

Upgrade:

- becomes Long-Term when stable, repeatedly validated, and broadly reusable

Downgrade:

- becomes Short-Term if it is revealed to be local or temporary

Expiration:

- when the project phase ends or dependencies change

Reactivation:

- allowed if a later project phase references the same constraint or decision

### Long-Term Memory

Why it exists:

- stores durable, high-confidence knowledge with provenance and validity
  boundaries

Contains:

- stable user/project preferences
- validated facts
- durable constraints
- architecture decisions
- reusable strategies
- high-confidence lessons from failures or successes

Entry:

- high evidence quality
- clear source provenance
- stable scope
- high reuse value
- no unresolved contradiction

Direct entry:

- allowed for a one-time high-value event only when it is explicit,
  evidence-backed, and has durable scope. Example: a user states a permanent
  project constraint, or an artifact compatibility decision is validated by
  benchmark evidence.

Downgrade:

- to Mid-Term when validity becomes uncertain or scope narrows

Expiration:

- rare; generally prefer supersession or archive over deletion

Reactivation:

- active by default unless expired, disputed, or superseded

### Archive / Superseded / Expired

Why it exists:

- prevents silent overwrite
- preserves historical evidence without presenting stale records as current
  truth

Contains:

- old versions
- contradicted facts
- completed goals with historical value
- expired preferences
- failed candidate decisions

Entry:

- superseded by newer memory
- validity window closed
- dependency changed
- policy demoted out of active memory

Reactivation:

- allowed only through explicit policy if new evidence makes the old record
  relevant again. Reactivation should create a new current version, not mutate
  history silently.

## 3. Memory Object Taxonomy

| Object | Context only | Candidate | Direct Memory | Long-Term requires repeated validation |
| --- | --- | --- | --- | --- |
| Goal | active cursor and unresolved task state | durable objective, unresolved obligation, repeated objective | explicit durable project goal | usually yes unless explicit and high-value |
| Task intent | current user request | recurring intent or durable requirement | explicit persistent intent | often yes |
| Constraint | temporary instruction | project/hardware/security boundary | explicit hard constraint | not always; hard constraints can enter directly |
| Decision | transient action choice | decision with future impact | benchmark-backed architecture decision | often no if evidence is strong |
| Observation | raw execution facts | interpreted or evidence-linked observation | rarely direct | yes, unless external fact is authoritative |
| Fact | prompt-local statement | evidence-backed claim | validated fact with provenance | yes unless source is authoritative |
| Preference | conversational style/local choice | repeated or explicit preference | explicit user preference | no if explicit; yes if inferred |
| Plan | active workflow state | reusable strategy or planned roadmap | rarely direct | yes |
| Failure | local error | failure with learning value | high-value failure memory | not necessarily; one severe failure can persist |
| Solution | one-off answer | solution with reuse value | validated reusable solution | usually yes |
| Strategy | local tactic | successful pattern | proven strategy | yes |
| Unresolved issue | current ambiguity | open question / pending decision | durable project issue | no if explicitly tracked |

## 4. Runtime Object -> Candidate -> Memory

The three layers must remain distinct.

```text
Runtime Object
  -> Memory Candidate
  -> Memory Element
```

### Runtime Object

Runtime Object is owned by Phase-1 lifecycle semantics. It may include:

- ActiveGoalRecord
- WorkflowRunRecord
- WorkflowStepPlanRecord
- StepRunRecord
- WorkflowArtifactRecord
- ExecutionObservation
- SemanticObservation
- Ledger Event

Runtime Object answers:

```text
What is the current system doing, what happened, and what state must be
preserved for lifecycle correctness?
```

### Memory Candidate

Memory Candidate is a Phase-2B extraction product. It answers:

```text
Is there something here that may matter after the Runtime lifecycle boundary?
```

It must carry:

- source references
- candidate type
- extracted content
- proposed lifecycle
- evidence summary
- confidence
- policy status

### Memory Element

Memory Element is an accepted record governed by Memory policy. It answers:

```text
What should UAEA remember, under what scope, with what evidence and validity?
```

It must carry:

- provenance
- lifecycle tier
- validity status
- confidence
- current/superseded/archive state
- retrieval scope

## 5. Context -> Candidate -> Memory Pipeline

Recommended conceptual pipeline:

```text
Raw Context
  -> Observation / Extraction
  -> Memory Candidate
  -> Validation / Policy
  -> Memory Element
```

### Raw Context

Raw context includes user messages, assistant answers, tool result excerpts,
planner projections, and conversation summaries.

It is not Memory. It can be evidence.

### Observation / Extraction

Extraction identifies possible durable content:

- "The user wants X preserved."
- "This hardware boundary affected model selection."
- "This failure pattern exposes a backend/artifact incompatibility."
- "This decision supersedes a previous decision."

Extraction should not decide persistence.

### Candidate Memory

Candidate Memory packages extracted content with provenance and policy metadata.

### Validated Memory

Validated Memory is accepted after policy checks. Validation can be explicit,
evidence-backed, repeated, or benchmark-backed depending on object type.

## 6. Promotion / Demotion Rules

Promotion should be evidence-driven, not age-driven.

### Promotion Inputs

- explicit user confirmation
- repeated recurrence
- successful reuse
- benchmark or test evidence
- stable dependency
- high learning value
- high-cost failure avoidance
- cross-session relevance

### Demotion Inputs

- contradiction
- stale dependency
- lowered confidence
- scope reduction
- supersession
- low reuse value
- policy rejection

### Direct Long-Term Admission

A one-time event may enter Long-Term if it satisfies all of:

- explicit or strongly evidenced
- high impact if forgotten
- clear provenance
- stable scope
- low contradiction risk

Examples:

- "Do not modify Phase-1 Runtime core."
- "Qwen2.5-14B-Instruct-AWQ passed Phase-1 L0-L6 on vLLM."
- "DS14B compressed-tensors WNA16 is rejected for the current vLLM stack."

### Repetition Without Validation

Repeated but unvalidated observations should not automatically become
Long-Term. They may become Mid-Term hypotheses with low/medium confidence and
validation_needed metadata.

### Completed Goals

Completed goals should not be deleted by default. Possible outcomes:

- discard if one-off and low value
- archive if historical but not reusable
- persist as Memory if it captures durable objective, decision, or project
  milestone
- consolidate into a higher-level decision or strategy

## 7. Supersession / Expiration Model

Memory should not silently overwrite old records.

Recommended model:

```text
old_memory
  -> superseded_by: new_memory_id
  -> valid_until: timestamp / event / condition
  -> status: superseded

new_memory
  -> supersedes: old_memory_id
  -> valid_from: timestamp / event / condition
  -> status: current
```

Minimum concepts:

- historical version
- current version
- superseded_by
- supersedes
- valid_from
- valid_until
- supersession_reason
- source_event_ids

### Conflict Handling

When new memory conflicts with old memory:

1. Do not update in place.
2. Create a candidate representing the conflict.
3. Require policy to choose one of:
   - supersede old
   - mark both disputed
   - narrow scope of one record
   - archive old
   - reject new candidate

### Expiration

Expiration is not deletion. Expired Memory should be excluded from normal
retrieval unless a diagnostic or historical query asks for it.

Expiration triggers:

- validity window closes
- project phase ends
- dependency no longer exists
- user preference changes
- confidence decays below threshold

## 8. Phase-1 -> Phase-2 Memory Boundary

Phase-1 remains frozen. Memory is an external consumer.

Recommended flow:

```text
Phase-1 Runtime
  -> Ledger Events / Runtime Snapshot / Artifacts / Semantic Observations
      -> Phase-2 Observation / Extraction Layer
          -> Memory Candidates
              -> Policy
                  -> Memory Store
```

Best Phase-1 sources:

| Phase-1 concept | Memory source value | Notes |
| --- | --- | --- |
| Goal | durable objective, unresolved obligation | only after lifecycle boundary or explicit durability |
| Artifact | reusable output and provenance | store reference/summary/hash first |
| Semantic Observation | structured facts, risks, boundaries, decisions | strong candidate source |
| Failure | high learning value | classify by hidden constraint, boundary collision, recovery |
| Action / Decision | execution choice evidence | persist only if reusable or consequential |
| Execution Observation | factual evidence | usually provenance, not direct memory |
| Context | distillation input | never direct dump |
| Result | success/failure signal | candidate if reusable, validated, or high-impact |

Memory must not:

- mutate RuntimeObjectStore
- change active workflow cursor
- alter Artifact lifecycle statuses
- modify benchmark expectations
- override current user input

## 9. SQLite Logical Architecture

SQLite may be the first physical persistence backend, but logical separation is
required.

Recommended logical stores:

```text
Event Store
  raw ledger events, snapshots, provenance

Candidate Store
  extracted potential memories awaiting policy

Memory Store
  accepted current memories with lifecycle and validity

Archive Store
  superseded, expired, rejected, and historical records
```

All of these may initially live in one SQLite database:

```text
data/memory/uaea_memory.db
```

But the architecture should keep logical separation:

- Event Store answers "what happened?"
- Candidate Store answers "what might matter?"
- Memory Store answers "what is currently remembered?"
- Archive Store answers "what was remembered, rejected, expired, or superseded?"

Do not begin with a `chat_history` table as the Memory foundation.

## 10. Directory / Environment Proposal

Current boundaries remain:

```text
Source:
  D:\UAEA\memory\

Documentation:
  D:\UAEA\docs\phase2b-memory\

Runtime data:
  D:\UAEA\data\memory\

Python environment:
  D:\UAEA\.venv_memory\

SQLite database:
  D:\UAEA\data\memory\uaea_memory.db
```

Dependency rule:

```text
Phase-2B Memory uses an isolated stdlib-only Python environment until a new
architecture decision introduces third-party dependencies.
```

Implementation directories should still be deferred until this lifecycle model
is accepted. The current `memory/README.md` is only a source-boundary marker.

## 11. Architectural Decisions

| ID | Decision | Status |
| --- | --- | --- |
| MBD-001 | Conversation Context is not Memory. | accepted |
| MBD-002 | Memory tiers are driven by relevance, validation, confidence, stability, and reuse value, not age alone. | proposal |
| MBD-003 | Runtime Object, Memory Candidate, and Memory Element are separate layers. | proposal |
| MBD-004 | Supersession must preserve history instead of silently updating old memory. | proposal |
| MBD-005 | SQLite is a persistence mechanism that may host Event/Candidate/Memory/Archive stores but must not define Memory architecture. | proposal |
| MBD-006 | Phase-2 Memory consumes Phase-1 evidence externally and must not modify Phase-1 Runtime semantics. | accepted |
| MBD-007 | Memory is modeled as an object with mutable lifecycle state, not as a static row or raw context archive. | proposal |
| MBD-008 | Episodic, semantic, and procedural/habit forms are representation facets, not mutually exclusive memory types. | proposal |
| MBD-009 | Consolidation is a state transition and evidence aggregation process, not a memory type. | proposal |
| MBD-010 | Dormant is a lifecycle state that lowers retrieval priority without deleting historical evidence. | proposal |

## 12. Unresolved Questions

- What exact minimum fields are required for a Memory Candidate?
- Should candidate extraction run synchronously after each turn or as an
  offline batch over ledger events?
- Should unresolved issues have a separate queue or just a lifecycle/status
  field inside Memory?
- How should confidence decay be represented without overengineering policy?
- Should user preference memory and project architecture memory use separate
  promotion thresholds?
- What is the first retrieval consumer: planner projection, answer generation,
  diagnostics, or architecture review?
- How much raw context can be retained as provenance before privacy and storage
  policy require redaction?
- What minimum relationship model is required before retrieval can be trusted?
- Should short-term / mid-term / long-term remain user-facing vocabulary, or
  should they be internal retrieval tiers only?

## 13. Explicit Non-goals

This document does not authorize:

- Phase-1 Runtime modification
- Phase-1 benchmark modification
- Artifact schema modification
- SQLite schema implementation
- Memory CRUD implementation
- retrieval implementation
- Context Distillation implementation
- Reflection implementation
- Failure Archive implementation
- vector database or embedding dependency
- LLM-based consolidation

## 14. Old Design Notes

This section preserves earlier design language for traceability. It is retained
as old design, not as the preferred current abstraction.

### Old tier-first lifecycle

Earlier drafts used:

```text
Working Context
  -> Candidate Memory
  -> Short-Term Memory
  -> Mid-Term Memory
  -> Long-Term Memory
  -> Archive / Superseded / Expired
```

Current review:

- The direction was useful for separating raw context from durable memory.
- The weakness is that it makes short/mid/long-term sound like the primary
  lifecycle state machine.
- Current design keeps short/mid/long-term as policy or retrieval tiers, while
  using candidate/active/dormant/reactivated/superseded/archive/expired as the
  lifecycle state vocabulary.

### Old type-first memory model

Earlier discussion considered:

```text
Working Context
  -> Memory Candidate
      -> Episodic Memory
      -> Behavioral / Habit Memory
      -> Semantic Memory
      -> Dormant Memory
      -> Reactivation
```

Current review:

- Episodic, semantic, and procedural/habit are not mutually exclusive types.
- Consolidation is not a type; it is a transition process.
- Dormant is not a type; it is a lifecycle state.
- A single Memory Element may have episodic evidence, semantic abstraction,
  procedural relevance, and decision/failure facets at the same time.

### Old storage-first risk

Earlier SQLite discussions risked starting from database tables.

Current review:

- SQLite remains a persistence adapter.
- Schema design must wait until Memory Candidate semantics, lifecycle states,
  representation facets, and evidence relationships are reviewed.
- A `chat_history` table must not become the foundation of UAEA Memory.
