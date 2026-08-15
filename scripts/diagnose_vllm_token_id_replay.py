from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def load_tokenizer(path: str):
    try:
        from transformers import AutoTokenizer
    except Exception as exc:
        raise SystemExit(f"transformers is required: {exc}") from exc
    return AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=True)


def post_completion(
    base_url: str,
    model: str,
    prompt: str | list[int],
    max_tokens: int,
    timeout: int,
) -> tuple[dict[str, Any], float]:
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


def request_completion(
    base_url: str,
    model: str,
    prompt: str | list[int],
    max_tokens: int,
    timeout: int,
) -> dict[str, Any]:
    try:
        data, latency_ms = post_completion(base_url, model, prompt, max_tokens, timeout)
        choice = data["choices"][0]
        text = str(choice.get("text") or "")
        return {
            "ok": True,
            "finish_reason": str(choice.get("finish_reason") or ""),
            "text": text,
            "text_repr": repr(text),
            "starts_with_bang": text.startswith("!"),
            "bang_ratio": round(text.count("!") / max(1, len(text)), 4),
            "latency_ms": round(latency_ms, 3),
            "usage": data.get("usage"),
            "error": None,
        }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "finish_reason": "http_error",
            "text": "",
            "text_repr": "",
            "starts_with_bang": False,
            "bang_ratio": 0.0,
            "latency_ms": 0.0,
            "usage": None,
            "error": f"HTTP {exc.code}: {body[:1000]}",
        }
    except Exception as exc:
        return {
            "ok": False,
            "finish_reason": "error",
            "text": "",
            "text_repr": "",
            "starts_with_bang": False,
            "bang_ratio": 0.0,
            "latency_ms": 0.0,
            "usage": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def encode(tokenizer: Any, text: str) -> list[int]:
    return [int(token_id) for token_id in tokenizer.encode(text, add_special_tokens=False)]


def decode_each(tokenizer: Any, ids: list[int]) -> list[str]:
    return [tokenizer.decode([token_id]) for token_id in ids]


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay vLLM completion prompts as token ids to isolate rendering vs token sequence.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--tokenizer-path", default=r"D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B")
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_token_id_replay.json"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    tokenizer = load_tokenizer(args.tokenizer_path)

    text_prompts = {
        "upper_plain": "You are a local assistant.\n\nRead README section 1 and extract: goals, risks, architecture.",
        "space_upper_plain": " You are a local assistant.\n\nRead README section 1 and extract: goals, risks, architecture.",
        "lower_plain": "you are a local assistant.\n\nRead README section 1 and extract: goals, risks, architecture.",
        "upper_short": "You are a local assistant.",
        "upper_short_with_task": "You are a local assistant. Read README section 1.",
        "just_you": "You",
        "you_are": "You are",
        "you_are_a": "You are a",
        "system_prefix": "System: You are a local assistant.\n\nRead README section 1 and extract: goals, risks, architecture.",
    }

    token_variants: dict[str, list[int]] = {}
    for name, text in text_prompts.items():
        token_variants[f"{name}_ids"] = encode(tokenizer, text)

    upper_ids = token_variants["upper_plain_ids"]
    if upper_ids:
        token_variants["upper_plain_replace_first_with_space_you"] = [1446] + upper_ids[1:]
        token_variants["upper_plain_replace_first_with_lower_you"] = [9330] + upper_ids[1:]
        token_variants["upper_plain_prefix_eos"] = [151643] + upper_ids
        token_variants["upper_plain_prefix_bos"] = [151646] + upper_ids
        token_variants["upper_plain_prefix_newline"] = encode(tokenizer, "\n") + upper_ids

    results: list[dict[str, Any]] = []
    for name, text in text_prompts.items():
        for max_tokens in (1, 16):
            result = request_completion(base_url, args.model, text, max_tokens, args.timeout)
            ids = encode(tokenizer, text)
            result.update(
                {
                    "prompt_name": name,
                    "prompt_kind": "string",
                    "max_tokens": max_tokens,
                    "prompt_text": text,
                    "prompt_token_ids": ids,
                    "prompt_tokens": decode_each(tokenizer, ids),
                }
            )
            results.append(result)

    for name, ids in token_variants.items():
        for max_tokens in (1, 16):
            result = request_completion(base_url, args.model, ids, max_tokens, args.timeout)
            result.update(
                {
                    "prompt_name": name,
                    "prompt_kind": "token_ids",
                    "max_tokens": max_tokens,
                    "prompt_text": tokenizer.decode(ids),
                    "prompt_token_ids": ids,
                    "prompt_tokens": decode_each(tokenizer, ids),
                }
            )
            results.append(result)

    summary: dict[str, Any] = {
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "by_prompt": {},
    }
    for item in results:
        bucket = summary["by_prompt"].setdefault(
            item["prompt_name"],
            {"total": 0, "string": 0, "token_ids": 0, "starts_with_bang": 0},
        )
        bucket["total"] += 1
        bucket[item["prompt_kind"]] += 1
        if item["starts_with_bang"]:
            bucket["starts_with_bang"] += 1

    report = {
        "diagnostic": "vllm_token_id_replay",
        "base_url": base_url,
        "model": args.model,
        "tokenizer_path": args.tokenizer_path,
        "summary": summary,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
