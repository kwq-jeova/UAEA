# Phase-2B Memory Boundary Architecture

> Status: architecture draft
> Scope: boundary design only
> Non-goal: SQLite implementation, Memory CRUD, retrieval implementation, or
> Phase-1 Runtime changes

## 1. Motivation

Phase-1 produced a frozen Cognitive Runtime Control Plane. Phase-2A proved that
the Runtime can run through a replaceable inference backend. Phase-2B should
now define how durable memory enters the architecture without turning the
Runtime into a memory database or changing frozen Phase-1 semantics.

The central question is:

```text
Which structured objects produced by Phase-1 may cross a Runtime lifecycle
boundary and become Memory Candidates?
```

The answer is not "save chat history." UAEA Memory must preserve useful
experience, provenance, lifecycle metadata, validity, and retrieval boundaries.
Conversation context can contribute to Memory, but only through distillation
and policy.

## 1A. Architecture Review Result

The reviewed Phase-2B boundary uses four separated concepts:

```text
Memory Object
  + Lifecycle State
  + Representation Facet
  + Evidence Relationship
```

This is now preferred over a type-first or tier-first design.

Key decisions:

- Memory is not raw context and not a passive event dump.
- Memory is an object whose lifecycle state may change over time.
- Evidence and provenance should be append-only references.
- Episodic, semantic, and procedural/habit are representation facets, not
  mutually exclusive memory types.
- Consolidation is a transition process, not a memory type.
- Dormant is a lifecycle state, not a separate storage class.
- Retrieval returns a Memory Projection, not authoritative Runtime state.

Reviewed state machine:

```text
Working Context
  -> Observation / Extraction
  -> Memory Candidate
  -> Active Memory
  -> Dormant Memory
  -> Reactivated Memory
  -> Superseded / Archived / Expired / Rejected
```

Short-term, mid-term, and long-term remain useful as policy/retrieval tiers,
but they should not be treated as the primary lifecycle state machine.

## 2. Phase-1 Freeze Boundary

Phase-1 owns the Runtime lifecycle:

- intent / goal relation
- active goal state
- workflow identity and cursor
- capability execution
- execution observation
- semantic observation
- workflow artifact lifecycle
- failure handling
- ledger event emission
- runtime snapshot semantics

Phase-2B must not move these authorities into Memory. Memory may observe,
index, consolidate, and retrieve, but it must not redefine what a Goal,
Workflow, Artifact, Observation, or failure means inside Phase-1.

The existing Phase-1 object surface is a source, not a persistence contract:

```text
RuntimeObjectStore
  -> in-memory lifecycle state
  -> snapshot / ledger events
  -> Memory Candidate input
```

## 3. Context vs Runtime Object

Conversation context and Runtime objects have different meanings.

| Source | Runtime meaning | Memory meaning |
| --- | --- | --- |
| Ephemeral conversation context | prompt working buffer | not memory by default |
| Complete conversation context | potential evidence | distillation input only |
| IntentRecord / GoalHypothesis | short-lived planning context | candidate if durable, repeated, unresolved, or user-stable |
| ActiveGoalRecord | Runtime-owned task objective | candidate after lifecycle boundary or explicit persistence signal |
| WorkflowRunRecord / WorkflowStepPlanRecord | execution cursor and plan state | mostly not memory; may become experience evidence |
| StepRunRecord / Action | audited execution decision | candidate when it exposes reusable pattern, failure, or constraint |
| ExecutionObservation | factual tool/capability result | evidence source; usually abstract before long-term memory |
| SemanticObservation | structured interpretation | strong candidate input, still subject to policy |
| WorkflowArtifactRecord | reusable Runtime output with lineage | memory should usually store a reference plus summary, not duplicate all content |
| Ledger Event | append-only audit evidence | provenance source for candidates and future SQLite ledger |

The key distinction:

```text
Context helps the next turn.
Runtime objects control the current lifecycle.
Memory preserves selected durable experience beyond the lifecycle.
```

## 4. Runtime Object To Memory Candidate

Runtime objects may become Memory Candidates, but this is a controlled
boundary crossing.

Recommended intake sources:

- runtime snapshots
- ledger events
- semantic observations
- workflow artifacts
- failure events
- explicit user preferences or constraints
- distilled conversation context

Do not persist every object by default. Some objects are too operational:

- active workflow cursor
- pending planned step
- retry position
- current prompt projection
- transient context summary

These belong to Runtime state unless they are closed, failed, explicitly saved,
or distilled into a reusable lesson.

Memory Candidate is an intermediate status:

```text
candidate != accepted memory
candidate != long-term memory
candidate != cognition asset
```

A candidate must still pass policy checks for durability, provenance, value,
validity, privacy, and lifecycle target.

## 5. Context Distillation

Conversation context should not be dumped into Memory. The architecture should
support:

```text
Conversation Context
  -> Context Distillation
  -> Memory Candidate
  -> Memory Policy
  -> transient / persistent memory
```

Distillation can extract:

- durable goal
- user intent
- user constraints
- decisions
- preferences
- unresolved issues
- repeated failure patterns
- important project context
- experience summaries

Context Distillation should sit outside Phase-1 Runtime core. It can be part of
the Phase-2B Memory intake pipeline or a nearby Cognitive/Distillation layer.
The Runtime should not need to know whether a conversation message later became
memory.

## 6. Memory Boundary

Recommended boundary:

```text
Conversation / Runtime Evidence
  -> Cognitive Intake / Distillation
  -> Memory Candidate
  -> Memory Policy
  -> Memory Store
  -> Persistence
```

This corresponds most closely to option D:

```text
Conversation / Runtime
  -> Cognitive / Distillation Layer
  -> Memory Candidate
  -> Memory
```

Option D is recommended with one refinement: "Cognitive / Distillation Layer"
should be treated as intake and consolidation, not as autonomous reflection yet.
Reflection and cognition assets are later stages.

### Alternative Review

| Option | Shape | Verdict |
| --- | --- | --- |
| A | Phase-1 Runtime -> Memory | rejected; too invasive and encourages Runtime objects to become persisted state directly |
| B | Phase-1 Runtime -> Memory Candidate -> Memory | viable but incomplete; ignores conversation distillation as a parallel source |
| C | Phase-1 Runtime -> Experience -> Memory Candidate -> Memory | viable if "Experience" is an evidence packet, but risks duplicating ledger concepts |
| D | Conversation / Runtime -> Cognitive / Distillation -> Candidate -> Memory | recommended; separates context, runtime evidence, candidate policy, and persistence |

## 7. Memory Lifecycle

Memory design should use lifecycle states and policy tiers, not only tables.
The current state machine is defined in the review update above and in:

```text
docs/phase2b-memory/memory-architecture-boundary-v0.1.md
```

Earlier drafts used this tier-first vocabulary:

```text
Ephemeral
  -> Session
  -> Short-term
  -> Mid-term
  -> Long-term
  -> Consolidated Cognitive Asset
```

| Lifecycle | Meaning | Example |
| --- | --- | --- |
| Ephemeral | prompt-local working material | current projection, immediate messages |
| Session | useful during current run | recent goal and document context |
| Short-term | useful across turns or nearby sessions | unresolved task, active user preference, pending question |
| Mid-term | useful across a project phase | Phase-2A model selection boundary |
| Long-term | stable memory with provenance | validated project principle or user constraint |
| Consolidated Cognitive Asset | distilled principle with evidence and applicability | artifact compatibility requires representation-level validation |

Current review keeps this vocabulary as policy language, not as the canonical
state machine. For example, a Memory Element may be `active` with a long-term
retrieval tier, or `dormant` while still retaining long-term historical value.

### Goal Lifecycle

A Goal is Runtime state while it is active, unresolved, or controlling the
workflow cursor.

A Goal becomes a Memory Candidate when:

- it is completed and has reusable project value
- it is abandoned but leaves unresolved obligations
- it expresses a durable user objective
- it repeats across sessions
- it constrains future work

A Goal should enter long-term memory only when policy confirms it is durable,
valid, and not merely a transient command.

### Failure Lifecycle

Failures can be more valuable than ordinary context because they expose hidden
constraints, invalid assumptions, model/backend incompatibility, or boundary
collisions.

Failure should not be persisted only as an error string. A useful failure memory
needs:

- trigger
- expected behavior
- observed behavior
- failed layer
- evidence references
- final decision
- validity window
- confidence

### Artifact Lifecycle

Artifact content is not automatically Memory. Memory should usually store:

- artifact id / path / hash reference
- summary
- status
- provenance
- applicability
- lifecycle decision

Full artifact duplication should be reserved for cases where the artifact is
itself the durable asset and cannot be recovered from its source.

### Observation Lifecycle

ExecutionObservation is factual evidence. It is usually too raw for long-term
memory, but it is valuable provenance.

SemanticObservation is closer to a Memory Candidate because it already extracts
facts, boundaries, risks, decisions, and open questions. It still requires
policy and consolidation because a single semantic observation can be wrong,
over-specific, or temporary.

### Decision Lifecycle

Decision memory should store both:

- conclusion
- decision context

The conclusion without context becomes unsafe over time. At minimum a Decision
memory needs source references, constraints, confidence, validity period, and
supersession metadata.

## 8. Memory Policy

Memory Policy decides whether a candidate is discarded, held temporarily, or
persisted.

Minimum policy dimensions:

- durability: will this matter beyond the current turn?
- provenance: what evidence supports it?
- source type: runtime object, semantic observation, artifact, distilled context
- validity: current, stale, superseded, disputed
- confidence: low, medium, high
- scope: user, project, model, backend, environment, benchmark
- sensitivity: safe to persist or needs redaction
- lifecycle target: transient, short-term, mid-term, long-term, cognitive asset candidate

Policy must preserve the distinction between:

```text
raw event
candidate
accepted memory
retrieved memory
consolidated cognitive asset
```

## 9. Retrieval Boundary

Retrieval should not mutate Phase-1 Runtime semantics. Retrieved memory should
enter Runtime through an explicit projection boundary, similar to context
projection:

```text
Memory Store
  -> Retrieval Policy
  -> Memory Projection
  -> Runtime prompt/context input
```

The Runtime may use retrieved memory as context, but it must continue to obey
Phase-1 authority order:

```text
Current User Input
  > Intent Relation
  > Active Goal
  > Active Workflow
  > Workflow Artifact
  > Semantic Observation
  > Conversation Context
  > Retrieved Memory
```

Retrieved Memory should not override active workflow cursor, fabricate
artifacts, or change failure recovery rules.

## 10. Persistence Boundary

SQLite should be treated as a persistence mechanism, not the Memory
architecture itself.

Recommended layering:

```text
Memory Policy
  -> Memory Store Interface
  -> Persistence Adapter
  -> SQLite
```

SQLite can be the first durable backend because it is local, auditable, and
transactional enough for early UAEA. It should not force premature schema
commitment for cognition, reflection, or training data.

Phase-2B should first define record semantics and lifecycle metadata. Database
schema can follow after the boundary is stable.

## 11. Architecture Debate

This section records adversarial review points that should remain visible.

### Challenge: Why should Goal enter Memory?

Goal should not enter Memory just because it existed. ActiveGoalRecord is a
Runtime control object. It becomes a Memory Candidate only when it represents a
durable user/project objective, unresolved obligation, or reusable task
pattern.

### Challenge: Why is Observation not just Context?

Observation is evidence. Context is prompt material. The same observation may
be projected into context, logged to ledger, or distilled into memory. Treating
Observation as Context loses provenance and factual/semantic separation.

### Challenge: Is Memory Candidate a necessary layer?

Yes. Without Candidate, either Runtime writes directly to Memory or Memory
becomes a passive event dump. Candidate allows policy, confidence, lifecycle,
and redaction before persistence.

### Challenge: Does Experience duplicate Memory?

"Experience" should not be an additional durable store in Phase-2B. If used,
it should mean an evidence packet assembled from ledger/runtime/context
sources. Otherwise it duplicates ledger and Memory Candidate.

### Challenge: Should Context Distillation live inside Memory?

It should live at the Memory intake boundary. It is not Phase-1 Runtime. It is
also not final Memory. Later it may become part of a broader Cognitive layer,
but Phase-2B should keep it as a bounded intake function.

### Challenge: Will SQLite prematurely freeze schema?

It can, if introduced too early. Phase-2B should document semantic record
types first, then implement SQLite behind an adapter after candidate/policy
boundaries are stable.

### Challenge: Should Retrieval belong to Runtime or Memory?

Retrieval belongs to Memory. Runtime should only receive a bounded Memory
Projection. Runtime must not know query strategy, ranking, or persistence
details.

### Challenge: Can Memory pollute Phase-1 semantics?

Yes, if retrieved memory outranks current user input or active workflow state.
The architecture must keep retrieved memory below frozen Runtime authorities
and label it as retrieved context, not lifecycle state.

## 12. Recommended Boundary

Recommended architecture:

```text
Phase-1 Runtime (frozen)
  -> Ledger Events / Snapshot / Runtime Objects
      -> Memory Intake Boundary
          -> Context Distillation
          -> Runtime Object Candidate Extraction
          -> Memory Candidate
              -> Memory Policy
                  -> transient memory
                  -> persistent memory
                      -> SQLite adapter

Memory Store
  -> Retrieval Policy
  -> Memory Projection
  -> Phase-1 Runtime context input
```

Important constraints:

- Runtime emits evidence; Memory decides persistence.
- Context distillation is outside Runtime core.
- Memory Candidate is distinct from accepted memory.
- SQLite is below Memory Store, not above it.
- Retrieval returns projections, not authoritative Runtime state.

## 13. Phase-2B Scope

Phase-2B should define and then implement only the first Memory boundary:

- Memory Candidate semantics
- candidate intake from runtime snapshots and ledger events
- context distillation boundary, not full distillation implementation
- memory policy criteria
- retrieval projection boundary
- persistence adapter boundary
- initial SQLite storage after schema is justified

Phase-2B should not yet implement reflection, cognition asset synthesis,
training corpus generation, or LoRA evolution.

## 14. Open Architectural Questions

- Should there be a separate "Experience Packet" object, or should candidate
  provenance reference ledger events directly?
- What is the minimum metadata needed before a candidate can be persisted?
- Should user preference memory and project architecture memory share one
  policy engine or separate policies?
- How are memories invalidated or superseded?
- What is the first retrieval consumer: planner context, answer generation, or
  diagnostics?
- Should semantic observations be persisted verbatim, abstracted, or both?
- How much raw conversation evidence is allowed in provenance before privacy or
  token cost becomes unacceptable?
- Should Memory support confidence decay over time?
- How should benchmark traces and inference traces relate to cognitive memory?
- What is the minimum evidence relationship model needed before retrieval is
  allowed to influence prompts?
- Should short/mid/long-term remain internal retrieval tiers rather than
  persisted lifecycle states?

Temporal lifecycle extension:

```text
docs/phase2b-memory/memory-architecture-boundary-v0.1.md
```

## 15. Explicit Non-goals

This phase does not:

- modify `runtime/phase1-runtime`
- modify Phase-1 benchmark expectations
- modify Artifact schema
- implement SQLite
- implement Memory CRUD
- implement Memory retrieval
- implement Context Distillation
- implement Reflection
- implement Failure Archive
- implement Cognition Assets
- implement LoRA training or dataset selection
- make retrieved memory authoritative over current Runtime state

## 16. Old Design Notes

The following concepts are retained as old design references, not current
preferred architecture:

- `short-term -> mid-term -> long-term` as the primary lifecycle state machine
- `episodic / semantic / habit` as mutually exclusive memory types
- `consolidation` as a memory type
- `dormant memory` as a memory type or storage area
- SQLite tables as the starting point for architecture

Current replacement:

```text
Memory Element
  + lifecycle_state
  + representation_facets
  + confidence
  + validity_boundary
  + evidence_references
  + relationship_edges
```

Old concepts may still appear in historical notes and discussions, but they
should be interpreted through the reviewed object-state-facet model.
