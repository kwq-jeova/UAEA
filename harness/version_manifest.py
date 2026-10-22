"""Pinned runtime selection; no downloading, upgrading or implicit fallback."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
from typing import Any


MANIFEST_PATH = Path(__file__).with_name("versions.json")


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def selected_harness(version: str | None = None) -> dict[str, Any]:
    manifest = load_manifest()
    tag = version or os.environ.get("UAEA_CODEX_VERSION") or manifest["active_version"]
    if tag not in manifest["versions"]:
        raise ValueError(f"Unknown Harness version: {tag}; no fallback performed")
    return {"tag": tag, **manifest["versions"][tag]}


def identify_harness(binary: Path) -> dict[str, Any]:
    for tag, record in load_manifest()["versions"].items():
        if binary == Path(record["binary"]):
            return {"tag": tag, **record}
    return {"tag": "explicit_binary_override", "commit": "unknown", "binary": str(binary)}


def codex_process_environment(home: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if home is not None:
        env["CODEX_HOME"] = str(home)
    for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_API_KEY", "CHATGPT_API_KEY", "SERPAPI_KEY"):
        env.pop(name, None)
    return env


def verify_binary_digest(binary: Path, record: dict[str, Any]) -> None:
    expected = record.get("binary_sha256")
    if expected:
        digest = hashlib.sha256()
        with binary.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise RuntimeError("Harness binary checksum does not match the pinned manifest")
        record["binary_digest_verified"] = True
