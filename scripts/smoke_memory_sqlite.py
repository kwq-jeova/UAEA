import argparse
import json
import sqlite3
import sys
import warnings
from pathlib import Path


def sqlite3_module_version() -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return str(getattr(sqlite3, "version", ""))


def run_smoke(db_path: Path) -> dict[str, object]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    table_name = "__uaea_memory_sqlite_smoke"
    result: dict[str, object] = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "sqlite3_module_version": sqlite3_module_version(),
        "sqlite_engine_version": sqlite3.sqlite_version,
        "database_path": str(db_path.resolve()),
    }
    with sqlite3.connect(db_path) as connection:
        connection.isolation_level = None
        connection.execute("BEGIN")
        try:
            connection.execute(
                f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, label TEXT NOT NULL)"
            )
            connection.execute(f"INSERT INTO {table_name} (label) VALUES (?)", ("phase2b-smoke",))
            selected = connection.execute(f"SELECT label FROM {table_name} WHERE id = 1").fetchone()
            if selected is None or selected[0] != "phase2b-smoke":
                raise RuntimeError("sqlite smoke select did not return inserted value")
            connection.execute(f"DROP TABLE {table_name}")
            connection.execute("COMMIT")
            result.update(
                {
                    "import_sqlite3": "PASS",
                    "create_database": "PASS",
                    "create_table": "PASS",
                    "insert_select": "PASS",
                    "drop_smoke_table": "PASS",
                    "transaction_commit": "PASS",
                }
            )
        except Exception:
            connection.execute("ROLLBACK")
            raise
    result["database_exists"] = db_path.exists()
    result["database_size_bytes"] = db_path.stat().st_size if db_path.exists() else 0
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase-2B Memory sqlite3 environment smoke test.")
    parser.add_argument("--db", type=Path, default=Path("data/memory/uaea_memory.db"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_smoke(args.db)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
