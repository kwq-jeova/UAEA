"""Pinned runtime selection; no downloading, upgrading or implicit fallback."""

from __future__ import annotations

import json
import hashlib
import os
import platform
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
    host = current_platform()
    record = _platform_record(tag, manifest["versions"][tag], host)
    expected = {"linux-aarch64": "aarch64-unknown-linux-gnu",
                "linux-x86_64": "x86_64-unknown-linux-gnu"}.get(host)
    if expected is None or record.get("build_target") != expected:
        raise ValueError(f"No compatible Harness build for {tag} on {host}; no fallback performed")
    return record


def current_platform() -> str:
    machine = platform.machine().lower()
    machine = {"arm64": "aarch64", "amd64": "x86_64"}.get(machine, machine)
    return f"{platform.system().lower()}-{machine}"


def _platform_record(tag: str, record: dict[str, Any], platform_key: str | None) -> dict[str, Any]:
    result = {key: value for key, value in record.items() if key != "platforms"}
    override = record.get("platforms", {}).get(platform_key, {})
    if any(key in override for key in ("commit", "tag")):
        raise ValueError("Platform records cannot change the pinned source identity")
    result.update(override)
    return {"tag": tag, **result, **({"platform": platform_key} if override else {})}


def identify_harness(binary: Path) -> dict[str, Any]:
    for tag, record in load_manifest()["versions"].items():
        for platform_key in (None, *record.get("platforms", {})):
            candidate = _platform_record(tag, record, platform_key)
            if binary == Path(candidate["binary"]):
                return candidate
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

    expected_bwrap = record.get("bwrap_sha256")
    if expected_bwrap:
        bwrap = binary.parent / "codex-resources" / "bwrap"
        digest = hashlib.sha256(bwrap.read_bytes()).hexdigest()
        if digest != expected_bwrap:
            raise RuntimeError("Bundled bwrap checksum does not match the pinned manifest")
        record["bwrap_digest_verified"] = True

def verify_binary_platform(binary: Path, record: dict[str, Any]) -> None:
    """Reject incompatible registered or explicitly overridden executables before launch."""
    host = current_platform()
    targets = {"linux-aarch64": ("aarch64-unknown-linux-gnu", 183),
               "linux-x86_64": ("x86_64-unknown-linux-gnu", 62)}
    if host not in targets:
        raise RuntimeError(f"Unsupported Harness execution platform: {host}")
    target, machine = targets[host]
    if record.get("build_target") not in (None, target):
        raise RuntimeError(f"Harness platform mismatch: {record['build_target']} on {host}")
    with binary.open("rb") as stream:
        header = stream.read(20)
    if (len(header) < 20 or header[:4] != b"\x7fELF"
            or header[4:6] != bytes((2, 1))
            or int.from_bytes(header[18:20], "little") != machine):
        raise RuntimeError(f"Harness binary must be a native 64-bit ELF for {host}: {binary}")
    record["binary_platform_verified"] = True
