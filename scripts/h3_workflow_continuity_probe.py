"""Three user inputs through the existing interactive runner; no scripted tool plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import h3_harness_interactive_repl as repl
from harness.trajectory_reader import read_trajectory_jsonl, validate_trajectory_records


TURNS = (
    "Research OpenAI Agents SDK and Anthropic Model Context Protocol using public sources. "
    "Find their official repositories and state what evidence was obtained. "
    "Only use Google. Do not use Bing. Do not use DuckDuckGo. No fallback.",
    "Continue the same research. Select OpenAI Agents SDK for further investigation, "
    "focusing on tools and handoffs. Use its official repository or documentation as sources.",
    "Expand that selected project: which tool and handoff mechanisms are documented? "
    "Separate obtained evidence, unverified claims, and unfinished investigation.",
)

COVERAGE_TURNS = (
    "Search publicly available sources on OpenAI Agents SDK and Model Context Protocol (MCP). "
    "Only use Google. No fallback. Return the sources you found for later review.",
    "Explore the links you just found and work out how they could inform building a local agent runtime. "
    "If some remain unread, keep them explicitly pending rather than claiming completion.",
    "Do not access any more pages in this turn. State precisely how many distinct discovered URLs "
    "were actually fetched successfully and list the remaining ones. Separate retrieved evidence "
    "from unverified conclusions and unfinished work.",
)

BASIS_TURNS = (
    "研究 OpenAI Agents SDK 与 Model Context Protocol（MCP），检索公开资料。仅使用 Google，禁止 fallback。",
    "请探索刚才找到的链接，比较哪些机制能帮助构建本地 agent runtime。区分页面事实和你的设计建议。",
    "继续。",
    "本轮不要访问更多页面。回顾我们要推进的研究、实际搜索了什么、哪些页面确实获取了内容，以及仍未验证的判断。",
)

REQUEST_TURNS = (
    "仅使用 Google，禁止 fallback。搜索三个与 OpenAI Agents SDK 工具执行和 Model Context Protocol 相关的公开来源。",
    "选择刚才找到的一个来源，实际读取该网页，进一步研究它对本地 agent runtime 接口设计的帮助。",
    "继续。",
    "本轮不要再调用工具。总结实际获得的证据和尚未完成的工作，区分仅找到链接与确实获取网页内容。",
)

def summarize(run_dir: Path, *, expected_turns: int = 3) -> dict:
    rows = [json.loads(line) for line in (run_dir / "semantic-state-snapshots.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    snapshots = [row["snapshot"] for row in rows if row["event"] == "TURN_COMPLETED"]
    canonical = [path for path in (run_dir / "normalized-trajectories").glob("*.trajectory.jsonl")
                 if not path.name.endswith(".thread-projection.trajectory.jsonl")]
    # This runner enables only the canonical file, not thread projections.
    if len(canonical) != 1:
        raise RuntimeError("Expected one canonical run trajectory")
    trajectory = read_trajectory_jsonl(canonical[0])
    validation = validate_trajectory_records(trajectory.records)
    requests = []
    seen = set()
    for record in trajectory.records:
        ref = record.raw_event_reference.get("raw_index")
        if ref in seen:
            continue
        seen.add(ref)
        raw = record.raw_event
        message = raw.get("message", raw)
        if raw.get("direction") == "client" and message.get("method") == "turn/start":
            context = message["params"]["additionalContext"]
            requests.append({
                "projection_chars": sum(len(context[key]["value"]) for key in
                                         ("uaea.semantic_state_projection", "uaea.semantic_interpretations")),
                "authority": json.loads(context["uaea.semantic_state_projection"]["value"]),
                "interpretation": json.loads(context["uaea.semantic_interpretations"]["value"]),
            })
    workflow = snapshots[-1]["workflow_continuity"] if snapshots else {}
    return {
        "run_dir": str(run_dir), "canonical_trajectory": str(canonical[0]),
        "trajectory_validation": "PASS" if validation.ok else "FAIL",
        "validation_issues": validation.issues,
        "completed_turns": len(snapshots),
        "same_workflow": len({row["task_id"] for row in snapshots}) == 1,
        "same_root": len({row["workflow_continuity"]["initial_request"] for row in snapshots}) == 1,
        "projections_in_budget": len(requests) == expected_turns and all(row["projection_chars"] <= 2400 for row in requests),
        "pre_turn_projections": requests,
        "turn_receipts": workflow.get("turn_receipts", []),
        "attempts": workflow.get("attempts", []),
        "unresolved": workflow.get("unresolved", []),
        "source_coverage": workflow.get("source_coverage", {}),
        "last_action_request": workflow.get("last_action_request", {}),
        "action_request_origin": workflow.get("action_request_origin", {}),
        "request_continuity": workflow.get("request_continuity", {}),
        "agent_outputs": [row["last_agent_output"] for row in snapshots],
        "behavior_verdict": "REQUIRES_EVIDENCE_REVIEW",
    }


def run_probe(args) -> int:
    scenario = getattr(args, "scenario", "continuity")
    prefix = {"coverage": "workflow-source-coverage", "basis": "workflow-request-basis",
              "request": "workflow-request-continuity"}.get(
        scenario, "workflow-continuity")
    root = args.result_root / f"{prefix}-{repl.utc_stamp()}"
    turns = {"coverage": COVERAGE_TURNS, "basis": BASIS_TURNS, "request": REQUEST_TURNS}.get(scenario, TURNS)
    answers = iter((*turns, "exit"))

    def scripted_input(prompt):
        answer = next(answers)
        print(f"{prompt}{answer}", flush=True)
        return answer

    original = repl.read_user_input
    repl.read_user_input = scripted_input
    try:
        result = repl.run(SimpleNamespace(
            context=32768, result_root=root, codex_bin=repl.DEFAULT_CODEX_BIN,
            codex_home_root=repl.DEFAULT_CODEX_HOME_ROOT, workspace_root=repl.DEFAULT_WORKSPACE_ROOT,
            vllm_root=repl.DEFAULT_VLLM_ROOT, model_root=repl.DEFAULT_MODEL_ROOT,
            gpu_memory_utilization=0.75, health_timeout=repl.DEFAULT_HEALTH_TIMEOUT,
            turn_timeout=args.turn_timeout, generation_diagnostics=False,
        ))
    finally:
        repl.read_user_input = original
    runs = list(root.glob("interactive-*"))
    if len(runs) != 1:
        raise RuntimeError("Expected one isolated interactive run")
    summary = summarize(runs[0], expected_turns=len(turns))
    path = runs[0] / "workflow-continuity-summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[PROBE] summary={path}", flush=True)
    print(json.dumps({key: summary[key] for key in ("completed_turns", "same_workflow", "same_root",
                                                    "projections_in_budget", "trajectory_validation")}), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turn-timeout", type=int, default=420)
    parser.add_argument("--result-root", type=Path, default=repl.DEFAULT_RESULT_ROOT)
    parser.add_argument("--scenario", choices=("continuity", "coverage", "basis", "request"), default="continuity")
    raise SystemExit(run_probe(parser.parse_args()))
