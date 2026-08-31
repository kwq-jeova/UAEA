# Phase-2B SQLite Source / Evidence Closure

> Status: current implementation closure
> Scope: Source ingestion, source traceability, and EvidenceReference bridge
> Non-goal: Memory Store, Memory Policy, retrieval, embedding, consolidation, or
> Phase-1 Runtime modification

## 1. Closure Position

The current SQLite track is closed as a Source / Evidence history layer.

It is not a final Memory database.

```text
SQLite prototype
  = Source / Experimental Persistence Layer
  != Memory Store
```

The current implementation validates this narrower pipeline:

```text
Raw Source
  -> Source Adapter
  -> Normalized Source Records
  -> SQLite
  -> Inspection / Trace
  -> EvidenceReference bridge
```

It intentionally does not implement:

- automatic Candidate extraction
- Memory Policy
- ACCEPT / REJECT / DEFER logic
- Memory lifecycle
- retrieval
- embedding or vector search
- LLM-based consolidation

## 2. Implemented Boundary

Current source-level objects:

| Object | Meaning |
| --- | --- |
| `source_files` | Raw files and downloaded attachments, with path, size, and hash. |
| `conversations` | ChatGPT export conversation identity and current node pointer. |
| `conversation_nodes` | Normalized graph nodes from ChatGPT `mapping`. |
| `conversation_node_edges` | Parent -> child graph relationships. |
| `attachments` | Attachment metadata and availability state. |
| `source_records` | Simpler source records such as the 100-turn fixture turns. |

Existing Candidate-oriented prototype tables remain separate:

| Object | Meaning |
| --- | --- |
| `evidence_references` | Persisted evidence references used by fixture Candidates. |
| `candidates` | Candidate records from the architecture fixture only. |
| `candidate_evidence` | Candidate -> evidence references. |
| `candidate_scope_dimensions` | Candidate scope hypothesis dimensions. |
| `retrieval_probes` | Future retrieval probe metadata, not retrieval implementation. |

No `memory` or `memory_elements` table is created.

## 3. Real Input Validation

Input corpus:

```text
D:\UAEA\tests\test_resources\chatgpt_personal_selected_2026-08-24
```

Observed import:

```text
conversations: 3
conversation_nodes: 864
conversation_node_edges: 861
current_path nodes: 862
off-path nodes: 2
attachments: 21
available attachments: 16
download_failed attachments: 5
source_files: 19
```

The ChatGPT export is a conversation graph, not a flat message list.
Therefore `ConversationNode` is required at the source layer.

## 4. 100-Turn Fixture Validation

Input fixture:

```text
D:\UAEA\data\memory_test_fixtures\long_context_mixed_100.json
```

Observed import:

```text
source_records: 100
candidates: 11
evidence_references: 17
candidate_evidence: 17
candidate_scope_dimensions: 34
retrieval_probes: 5
```

C006 remains traceable:

```text
candidate_id: C006
scope.backend: vLLM
scope.phase: Phase-2A
scope.decision: production artifact
relation_hint: supersedes
```

This confirms that the source ingestion database can hold both:

- real ChatGPT conversation graph source data
- scenario fixture source/candidate test data

without merging them into accepted Memory.

## 5. EvidenceReference Bridge

The latest closure adds a bridge from normalized source objects to
`EvidenceReference`.

Supported source kinds:

```text
conversation_node
attachment
conversation_turn
exported_conversation_message
```

The bridge is explicit:

```text
selected source object
  -> EvidenceReference
  -> trace back to normalized source
```

It does not:

- scan the conversation for memories
- create Candidates automatically
- write accepted Memory
- calculate evidence strength
- make policy decisions

## 6. Preservation Audit

PRESERVED:

- conversation identity
- source file identity
- node identity
- parent / children graph relationships
- current path / off-path distinction
- role / content type / content text
- timestamps where present
- raw node JSON
- attachment metadata
- attachment availability
- file hash and size for available local attachments

TRANSFORMED:

- ChatGPT `mapping` graph becomes `conversation_nodes` and
  `conversation_node_edges`.
- `current_node` is walked through parent pointers to produce
  `is_current_path` and `current_path_index`.
- Attachment report records become attachment availability states.

AMBIGUOUS:

- Markdown render files duplicate JSON conversation content and are not imported
  as independent conversations.
- Tool messages are preserved as source nodes with role/content metadata, but
  not yet split into a dedicated `ToolEvent` table.
- Failed attachments have provenance metadata but no local content.

LOST:

- No source-ingestion-critical field loss has been observed.

## 7. Architecture Closure

Current closed conclusion:

```text
SQLite is currently justified as Interaction / Source / Evidence history.
It is not yet justified as Memory Store.
```

The "memory weight" problem remains outside this closure. Weight depends on:

- recurrence
- consistency
- cross-context persistence
- external evidence
- user correction
- successful reuse
- time

Those signals require longer-running interaction history. They should be
recorded as source/evidence history before Memory Policy is frozen.

## 8. Validation Commands

Current validation:

```text
python -m unittest discover -s tests -t . -v
.\.venv_memory\Scripts\python.exe -m unittest discover -s tests -t . -v
python scripts\inspect_memory_db.py --db data\memory\source_ingestion.sqlite --counts --conversations --attachments
python scripts\evaluate_memory_fixture.py data\memory_test_fixtures\long_context_mixed_100.json --json
```

Latest observed result:

```text
61/61 PASS
```

## 9. Next Boundary

The next slice should not be Memory Policy.

Recommended next slice:

```text
small manually selected EvidenceReferences
  -> manually constructed MemoryCandidate fixture
  -> structural validation
  -> traceability check
```

The goal is to test whether real source evidence can support Candidate
construction without introducing automatic extraction.
