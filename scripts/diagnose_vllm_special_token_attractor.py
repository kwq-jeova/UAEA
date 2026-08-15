from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any


ROLE_PATTERN = re.compile(r"<\|(?P<role>system|user|assistant)\|>\n")


def parse_canonical_messages(rendered_prompt: str) -> list[dict[str, str]]:
    matches = list(ROLE_PATTERN.finditer(rendered_prompt))
    messages: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(rendered_prompt)
        messages.append({"role": match.group("role"), "content": rendered_prompt[start:end].strip()})
    return messages


def load_first_record(path: Path, case_id: str, phase: str) -> dict[str, Any]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("case_id") == case_id and record.get("phase") == phase:
            return record
    raise SystemExit(f"No record found for {case_id}/{phase}")


def load_tokenizer(path: str):
    try:
        from transformers import AutoTokenizer
    except Exception:
        return None
    try:
        return AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=True)
    except Exception:
        return None


def render_deepseek(tokenizer: Any, messages: list[dict[str, str]], add_generation_prompt: bool) -> str:
    if tokenizer is None:
        return ""
    try:
        rendered = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=add_generation_prompt,
        )
    except Exception:
        return ""
    return rendered if isinstance(rendered, str) else ""


def post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[dict[str, Any], float]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer uaea-local"},
        method="POST",
    )
    started_at = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8")), (time.monotonic() - started_at) * 1000


def repetition(text: str) -> dict[str, Any]:
    bang_count = text.count("!")
    return {
        "length_chars": len(text),
        "bang_count": bang_count,
        "bang_ratio": round(bang_count / max(1, len(text)), 4),
        "starts_with_bang": text.startswith("!"),
        "starts_with_16_bangs": text.startswith("!" * min(16, len(text))),
        "first_80": text[:80],
        "excerpt": text[:600],
    }


def run_completion(base_url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    try:
        data, latency_ms = post_json(f"{base_url}/completions", payload, timeout)
        text = str(data["choices"][0].get("text") or "")
        return {
            "ok": True,
            "finish_reason": str(data["choices"][0].get("finish_reason") or ""),
            "latency_ms": round(latency_ms, 3),
            "usage": data.get("usage"),
            "repetition": repetition(text),
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "finish_reason": "error",
            "latency_ms": 0.0,
            "usage": None,
            "repetition": {},
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Test whether DeepSeek special-token rendering creates a bang attractor.")
    parser.add_argument("--trace", type=Path, default=Path("data/inference_traces/vllm/phase1/vllm_phase1_l0_l1_selected.jsonl"))
    parser.add_argument("--case", default="L1-02")
    parser.add_argument("--phase", default="planner")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--tokenizer-path", default=r"D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B")
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_special_token_attractor.json"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    record = load_first_record(args.trace, args.case, args.phase)
    canonical_prompt = str(record.get("rendered_prompt") or "")
    messages = parse_canonical_messages(canonical_prompt)
    tokenizer = load_tokenizer(args.tokenizer_path)
    deepseek_prompt = render_deepseek(tokenizer, messages, add_generation_prompt=True)
    deepseek_no_gen = render_deepseek(tokenizer, messages, add_generation_prompt=False)

    prompts = {
        "canonical": canonical_prompt,
        "deepseek_template": deepseek_prompt,
        "deepseek_template_no_generation_prompt": deepseek_no_gen,
        "deepseek_template_without_think_marker": deepseek_prompt.replace("<think>\n", ""),
    }
    temperatures = [0.0, 0.2]
    max_tokens_values = [1, 8, 32]
    stop_variants: list[tuple[str, dict[str, Any]]] = [
        ("no_stop", {}),
        ("stop_eos_literal", {"stop": ["<｜end▁of▁sentence｜>"]}),
        ("stop_bang", {"stop": ["!"]}),
    ]

    results: list[dict[str, Any]] = []
    for prompt_name, prompt in prompts.items():
        if not prompt:
            continue
        for temperature in temperatures:
            for max_tokens in max_tokens_values:
                for stop_name, stop_payload in stop_variants:
                    payload = {
                        "model": args.model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                    payload.update(stop_payload)
                    item = run_completion(base_url, payload, args.timeout)
                    item.update(
                        {
                            "case_id": args.case,
                            "phase": args.phase,
                            "prompt_name": prompt_name,
                            "prompt_chars": len(prompt),
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "stop_name": stop_name,
                            "stop": stop_payload.get("stop"),
                        }
                    )
                    results.append(item)

    summary: dict[str, Any] = {
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "bang_pathology_count": sum(1 for item in results if item.get("repetition", {}).get("bang_ratio", 0) > 0.8),
        "starts_with_bang_count": sum(1 for item in results if item.get("repetition", {}).get("starts_with_bang")),
        "by_prompt": {},
    }
    for item in results:
        bucket = summary["by_prompt"].setdefault(
            str(item.get("prompt_name")),
            {"total": 0, "bang_pathology": 0, "starts_with_bang": 0, "finish_reason_counts": {}},
        )
        bucket["total"] += 1
        if item.get("repetition", {}).get("bang_ratio", 0) > 0.8:
            bucket["bang_pathology"] += 1
        if item.get("repetition", {}).get("starts_with_bang"):
            bucket["starts_with_bang"] += 1
        reason = str(item.get("finish_reason") or "")
        bucket["finish_reason_counts"][reason] = bucket["finish_reason_counts"].get(reason, 0) + 1

    report = {
        "diagnostic": "vllm_special_token_attractor",
        "source_trace": str(args.trace),
        "base_url": base_url,
        "model": args.model,
        "tokenizer_path": args.tokenizer_path if tokenizer is not None else "",
        "summary": summary,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
