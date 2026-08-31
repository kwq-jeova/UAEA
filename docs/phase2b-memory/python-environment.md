# Phase-2B Memory Python Environment

> Status: environment boundary
> Scope: Python venv and SQLite smoke only
> Non-goal: Memory implementation, schema design, CRUD API, retrieval, ORM, or
> integration with Phase-1 Runtime

## 1. Environment Inventory

Current UAEA-related Python environments observed on this machine:

| Environment | Path | Python | Role | Boundary |
| --- | --- | --- | --- | --- |
| Phase-1 Runtime | `D:\AI_Agent_FW\.venv` | 3.13.12 | frozen Runtime execution | do not modify for Memory |
| LMF / HF inference | `D:\AI_Agent_FW\.venv_lmf_api` | 3.13.12 | LLaMA-Factory / HuggingFace 4-bit serving | do not modify for Memory |
| vLLM inference | `/opt/uaea/vllm_env` | 3.12.3 | vLLM 0.26.0 serving under WSL2 | do not modify for Memory |
| Repository default Python | `D:\Miniconda3\python.exe` | 3.13.12 | local tests and tooling | source for Memory venv creation |
| Phase-2B Memory | `D:\UAEA\.venv_memory` | 3.13.12 | SQLite persistence boundary smoke | isolated, stdlib-only |

No `requirements.txt`, `pyproject.toml`, `setup.py`, or `environment.yml` file
is currently present in `D:\UAEA`.

## 2. Recommended Memory Environment

Use a dedicated lightweight environment:

```text
D:\UAEA\.venv_memory
```

Rationale:

- keeps Memory / SQLite separate from Phase-1 Runtime
- keeps Memory / SQLite separate from LMF and vLLM inference stacks
- avoids pulling ML dependencies into persistence code
- uses the same Windows-side Python major/minor already used by Phase-1 and LMF

## 3. Python Version Boundary

Recommended version:

```text
Python 3.13.12
```

This matches the observed Windows-side Runtime and LMF environments. vLLM remains
isolated in WSL with Python 3.12.3 and should not be reused for Memory.

Observed Memory venv after creation:

```text
Python: 3.13.12
pip: 25.3
sqlite3 Python module: 2.6.0
SQLite engine: 3.51.1
```

The `sqlite3` Python module is a standard-library wrapper. The SQLite engine is
the underlying SQLite library that actually executes SQL and manages the
database file. They have separate version numbers and must both be recorded.

## 4. Dependency Policy

Phase-2B Memory dependencies must remain isolated from Phase-1 Runtime and
Phase-2A inference dependencies.

Initial policy:

```text
ZERO third-party dependencies.
Use Python standard library sqlite3 only.
```

Do not install these for Phase-2B Memory until a separate architecture decision
requires them:

- SQLAlchemy
- vector database packages
- embedding frameworks
- torch
- transformers
- vLLM
- LLaMA-Factory
- AutoAWQ
- model-serving clients beyond stdlib HTTP tooling

## 5. Path Boundary

| Purpose | Path |
| --- | --- |
| Source code | `D:\UAEA\memory\` |
| Documentation | `D:\UAEA\docs\phase2b-memory\` |
| Runtime data | `D:\UAEA\data\memory\` |
| Python environment | `D:\UAEA\.venv_memory\` |
| SQLite database | `D:\UAEA\data\memory\uaea_memory.db` |

The SQLite database must not live under:

- `runtime/phase1-runtime/`
- `backend/`
- `docs/`
- `memory/`
- `.venv_memory/`

## 6. Create / Activate

Create:

```powershell
cd D:\UAEA
python -m venv .venv_memory
```

Activate:

```powershell
.\.venv_memory\Scripts\Activate.ps1
```

Inspect:

```powershell
python --version
python -m pip --version
python -c "import sqlite3, sys; print(sys.version); print(sqlite3.version); print(sqlite3.sqlite_version)"
```

## 7. SQLite Smoke Test

Run from repository root:

```powershell
.\.venv_memory\Scripts\python.exe scripts\smoke_memory_sqlite.py --db data\memory\uaea_memory.db --json
```

The smoke test verifies:

- Python environment starts
- `sqlite3` imports
- SQLite database file can be created under `data\memory\`
- a minimal smoke table can be created inside a transaction
- insert/select works
- drop table and commit work

The smoke table is created, used, dropped, and committed inside one transaction.
This verifies SQLite runtime behavior without leaving a Phase-2B Memory schema.

## 8. Current Smoke Result

```text
import_sqlite3: PASS
create_database: PASS
create_table: PASS
insert_select: PASS
drop_smoke_table: PASS
transaction_commit: PASS
database_path: D:\UAEA\data\memory\uaea_memory.db
database_size_bytes: 8192
```

The smoke table is dropped before commit. A post-smoke schema inspection
returned no persistent tables.

## 9. Boundary Rules

- Memory environment is not an inference environment.
- Memory environment is not a training environment.
- Memory environment must not import vLLM, LLaMA-Factory, torch, transformers,
  or model artifacts.
- SQLite persistence must remain below Memory Store / Persistence Adapter.
- A successful SQLite smoke test does not authorize Memory schema or Runtime
  integration work.
