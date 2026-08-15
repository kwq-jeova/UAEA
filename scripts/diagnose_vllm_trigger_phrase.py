from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path
from typing import Any


def load_tokenizer(path: str):
    try:
        from transformers import AutoTokenizer
    except Exception as exc:
        raise SystemExit(f"transformers is required: {exc}") from exc
    return AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=True)


def post_completion(base_url: str, model: str, prompt: str, timeout: int) -> tuple[dict[str, Any], float]:
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": 0.0,
        "max_tokens": 1,
    }
    request = urllib.request.Request(
        f"{base_url}/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer uaea-local"},
        method="POST",
    )
    started_at = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8")), (time.monotonic() - started_at) * 1000


def token_tail(tokenizer: Any, text: str) -> dict[str, Any]:
    ids = [int(token_id) for token_id in tokenizer.encode(text, add_special_tokens=False)]
    tail = ids[-20:]
    return {
        "tokens": len(ids),
        "tail_token_ids": tail,
        "tail_tokens": [tokenizer.decode([token_id]) for token_id in tail],
    }


def build_prompt(system: str, user_text: str, style: str, tokenizer: Any) -> str:
    if style == "plain":
        return f"{system}\n\n{user_text}"
    if style == "canonical":
        return f"<|system|>\n{system}\n\n<|user|>\n{user_text}"
    if style == "deepseek":
        return f"{system}<｜User｜>{user_text}<｜Assistant｜><think>\n"
    if style == "deepseek_bos":
        return f"{tokenizer.bos_token}{system}<｜User｜>{user_text}<｜Assistant｜><think>\n"
    raise ValueError(style)


def main() -> int:
    parser = argparse.ArgumentParser(description="Isolate vLLM bang trigger phrase vs role-token style.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--tokenizer-path", default=r"D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B")
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_trigger_phrase.json"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    tokenizer = load_tokenizer(args.tokenizer_path)
    user_text = "Read README section 1 and extract: goals, risks, architecture."
    systems = {
        "planner_exact": "You are the semantic action planner for a local runtime.",
        "planner_no_semantic": "You are the action planner for a local runtime.",
        "planner_no_planner": "You are the semantic action selector for a local runtime.",
        "planner_no_runtime": "You are the semantic action planner.",
        "planner_lowercase": "you are the semantic action planner for a local runtime.",
        "json_only": "Return one JSON object only. Do not explain.",
        "assistant_short": "You are a local assistant.",
        "planner_with_json": "You are the semantic action planner for a local runtime. Return one JSON object only.",
    }
    styles = ["plain", "canonical", "deepseek", "deepseek_bos"]

    results: list[dict[str, Any]] = []
    for system_name, system in systems.items():
        for style in styles:
            prompt = build_prompt(system, user_text, style, tokenizer)
            try:
                data, latency_ms = post_completion(base_url, args.model, prompt, args.timeout)
                text = str(data["choices"][0].get("text") or "")
                result = {
                    "ok": True,
                    "finish_reason": str(data["choices"][0].get("finish_reason") or ""),
                    "latency_ms": round(latency_ms, 3),
                    "usage": data.get("usage"),
                    "text": text,
                    "text_repr": repr(text),
                    "starts_with_bang": text.startswith("!"),
                    "error": None,
                }
            except Exception as exc:
                result = {
                    "ok": False,
                    "finish_reason": "error",
                    "latency_ms": 0.0,
                    "usage": None,
                    "text": "",
                    "text_repr": "",
                    "starts_with_bang": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            result.update(
                {
                    "system_name": system_name,
                    "system": system,
                    "style": style,
                    "prompt_chars": len(prompt),
                    "prompt_tail": token_tail(tokenizer, prompt),
                }
            )
            results.append(result)

    summary: dict[str, Any] = {
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "bang_cases": [
            {"system_name": item["system_name"], "style": item["style"]}
            for item in results
            if item.get("starts_with_bang")
        ],
        "by_system": {},
    }
    for item in results:
        bucket = summary["by_system"].setdefault(str(item["system_name"]), {"total": 0, "bang": 0})
        bucket["total"] += 1
        if item.get("starts_with_bang"):
            bucket["bang"] += 1

    report = {
        "diagnostic": "vllm_trigger_phrase",
        "base_url": base_url,
        "model": args.model,
        "tokenizer_path": args.tokenizer_path,
        "summary": summary,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
