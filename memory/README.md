# UAEA Memory Subsystem

This directory is reserved for the Phase-2B Memory subsystem.

Current status:

```text
Candidate domain model implemented
structural validation implemented
evidence references implemented
scope hypothesis implemented
candidate lifecycle implemented
SQLite source ingestion prototype implemented
ChatGPT export graph ingestion implemented
Source -> EvidenceReference bridge implemented
deterministic Web source fixture ingestion implemented
WebAccessEvent -> EvidenceReference bridge implemented
no Memory Policy
no Memory Store
no CRUD API
no retrieval implementation
```

The current Phase-2B documents are:

```text
docs/phase2b-memory-boundary-architecture.md
docs/phase2b-memory-directory-plan.md
docs/phase2b-memory/memory-architecture-boundary-v0.1.md
docs/phase2b-memory/python-environment.md
docs/phase2b-memory/sqlite-source-evidence-closure.md
docs/phase2b-memory/runtime-web-context-kv-feasibility.md
```

Execution boundary:

```text
Python environment: D:\UAEA\.venv_memory
Runtime data:       D:\UAEA\data\memory
SQLite database:    D:\UAEA\data\memory\uaea_memory.db
Source DB:          D:\UAEA\data\memory\source_ingestion.sqlite
```

Current architecture baseline:

```text
Memory Element
  + lifecycle_state
  + representation_facets
  + evidence_references
  + relationship_edges
```

Episodic, semantic, and procedural/habit forms are representation facets.
Consolidation is a transition process. Dormant is a lifecycle state. Current
SQLite work is limited to source/evidence history and Candidate fixture
persistence. It is not the final Memory Store.

Do not place SQLite database files, model weights, inference runtime assets, or
training artifacts in this source directory.
