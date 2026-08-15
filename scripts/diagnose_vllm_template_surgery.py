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
    except Exception as exc:
        raise SystemExit(f"transformers is required: {exc}") from exc
    return AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=True)


def post_completion(base_url: str, model: str, prompt: str, max_tokens: int, timeout: int) -> tuple[dict[str, Any], float]:
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": 0.0,
        "max_tokens": max_tokens,
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


def repetition(text: str) -> dict[str, Any]:
    bang_count = text.count("!")
    return {
        "length_chars": len(text),
        "bang_count": bang_count,
        "bang_ratio": round(bang_count / max(1, len(text)), 4),
        "starts_with_bang": text.startswith("!"),
        "first_120": text[:120],
    }


def token_tail(tokenizer: Any, text: str, count: int = 32) -> dict[str, Any]:
    ids = [int(token_id) for token_id in tokenizer.encode(text, add_special_tokens=False)]
    tail = ids[-count:]
    return {
        "tokens": len(ids),
        "tail_token_ids": tail,
        "tail_tokens": [tokenizer.decode([token_id]) for token_id in tail],
        "tail_text_repr": repr(text[-300:]),
    }


def build_variants(tokenizer: Any, canonical: str, messages: list[dict[str, str]]) -> dict[str, str]:
    bos = str(tokenizer.bos_token or "")
    user = "<｜User｜>"
    assistant = "<｜Assistant｜>"
    think = "<think>\n"
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    latest_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    deepseek = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    if not isinstance(deepseek, str):
        raise SystemExit("tokenizer.apply_chat_template did not return a string")

    return {
        "canonical": canonical,
        "canonical_plus_assistant_suffix": canonical + "\n" + assistant + think,
        "deepseek_full": deepseek,
        "deepseek_user_newline": deepseek.replace(user, user + "\n"),
        "deepseek_user_and_assistant_newlines": deepseek.replace(user, user + "\n").replace(assistant, "\n" + assistant + "\n"),
        "deepseek_user_to_canonical": deepseek.replace(user, "\n<|user|>\n"),
        "deepseek_user_assistant_to_canonical": deepseek.replace(user, "\n<|user|>\n").replace(assistant, "\n<|assistant|>\n"),
        "deepseek_no_bos": deepseek[len(bos) :] if bos and deepseek.startswith(bos) else deepseek,
        "manual_deepseek_no_bos": system + user + latest_user + assistant + think,
        "manual_deepseek_with_bos": bos + system + user + latest_user + assistant + think,
        "manual_deepseek_with_newlines": bos + system + "\n" + user + "\n" + latest_user + "\n" + assistant + think,
        "manual_canonical_with_bos": bos + canonical,
        "manual_canonical_special_assistant": canonical + "\n" + assistant + think,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Surgically vary DeepSeek chat-template prompt structure.")
    parser.add_argument("--trace", type=Path, default=Path("data/inference_traces/vllm/phase1/vllm_phase1_l0_l1_selected.jsonl"))
    parser.add_argument("--case", default="L1-02")
    parser.add_argument("--phase", default="planner")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--tokenizer-path", default=r"D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B")
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_template_surgery.json"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    tokenizer = load_tokenizer(args.tokenizer_path)
    record = load_first_record(args.trace, args.case, args.phase)
    canonical = str(record.get("rendered_prompt") or "")
    messages = parse_canonical_messages(canonical)
    variants = build_variants(tokenizer, canonical, messages)

    results: list[dict[str, Any]] = []
    for name, prompt in variants.items():
        for max_tokens in (1, 16):
            try:
                data, latency_ms = post_completion(base_url, args.model, prompt, max_tokens, args.timeout)
                text = str(data["choices"][0].get("text") or "")
                result = {
                    "ok": True,
                    "finish_reason": str(data["choices"][0].get("finish_reason") or ""),
                    "latency_ms": round(latency_ms, 3),
                    "usage": data.get("usage"),
                    "repetition": repetition(text),
                    "error": None,
                }
            except Exception as exc:
                result = {
                    "ok": False,
                    "finish_reason": "error",
                    "latency_ms": 0.0,
                    "usage": None,
                    "repetition": {},
                    "error": f"{type(exc).__name__}: {exc}",
                }
            result.update(
                {
                    "variant": name,
                    "max_tokens": max_tokens,
                    "prompt_chars": len(prompt),
                    "prompt_tail": token_tail(tokenizer, prompt),
                }
            )
            results.append(result)

    summary: dict[str, Any] = {
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "bang_first_variants": [],
        "by_variant": {},
    }
    for item in results:
        bucket = summary["by_variant"].setdefault(str(item["variant"]), {"total": 0, "bang_first": 0, "ok": 0})
        bucket["total"] += 1
        if item["ok"]:
            bucket["ok"] += 1
        if item.get("repetition", {}).get("starts_with_bang"):
            bucket["bang_first"] += 1
            if item["variant"] not in summary["bang_first_variants"]:
                summary["bang_first_variants"].append(item["variant"])

    report = {
        "diagnostic": "vllm_template_surgery",
        "source_trace": str(args.trace),
        "case_id": args.case,
        "phase": args.phase,
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
