"""Read-only inventory of a sealed research checkpoint. Run inside WSL."""
import argparse
import hashlib
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, problem):
    if not condition:
        raise ValueError(problem)


def inspect(root):
    root = root.resolve(strict=True)
    resume = load(root / "resume-manifest.json")
    result = load(root / "result.json")
    require(resume["terminal_confirmed"] is True and resume["resume_eligible"] is True
            and resume["historical_call_cache_complete"] is True, "Missing terminal or resume proof")
    require(load(root / "cleanup.json")["process_group_state"] == "absent", "Source process not sealed")
    latest = load(root / "latest-checkpoint.json")
    gen = Path(resume["host_generation"]).resolve(strict=True)
    require(gen.parent == root / "checkpoints" and str(gen) == latest["generation"], "Host generation mismatch")
    require(digest(gen / "manifest.json") == latest["manifest_sha256"], "Host manifest hash mismatch")
    manifest = load(gen / "manifest.json")
    require(manifest["thread"] == result["thread"] == resume["thread"], "Thread mismatch")
    for name in ("host-state.pickle","normalizer.pickle","semantic-calls.json","after-state.json","goal-journal.jsonl"):
        copy = (root / "profile" if name == "goal-journal.jsonl" else root) / name
        require(digest(copy) == digest(gen / name) == manifest["files"][name], f"Snapshot mismatch: {name}")
    for name, cursor in manifest["event_prefixes"].items():
        require(Path(name).name == name, "Unexpected event path")
        data = (root / name).read_bytes()
        require(len(data) == cursor["bytes"] and hashlib.sha256(data).hexdigest() == cursor["prefix_sha256"],
                f"Sealed event file mismatch: {name}")
    home = Path(resume["native_home"]).resolve(strict=True)
    proof = load(home.parent / "native-copy-proof.json")
    rollout = Path(proof["rollout_copy"]).resolve(strict=True)
    require(rollout.is_relative_to(home / "sessions") and proof["thread_id"] == resume["thread"]
            and digest(rollout) == proof["rollout_sha256"], "Sealed Native rollout mismatch")
    gate = result.get("delivery_validation") or {}
    return {"checkpoint": str(root), "thread":resume["thread"], "turn":result.get("turn"),
            "sealed_files_checked":True, "recorded_resume_eligible": True,
            "upstream_status":gate.get("upstream_status"),
            "complete_response_recorded":gate.get("delivery_complete"), "classification":result["classification"],
            "visible_candidate_ids":[h["candidate_id"] for h in load(root/"after-state.json")["view"]["heads"]]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.checkpoint), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Checkpoint check failed: {error}\n")
