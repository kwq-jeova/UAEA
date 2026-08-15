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


def request_completion(base_url: str, model: str, prompt: str, timeout: int) -> dict[str, Any]:
    try:
        data, latency_ms = post_completion(base_url, model, prompt, timeout)
        choice = data["choices"][0]
        text = str(choice.get("text") or "")
        return {
            "ok": True,
            "finish_reason": str(choice.get("finish_reason") or ""),
            "text": text,
            "text_repr": repr(text),
            "starts_with_bang": text.startswith("!"),
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
            "latency_ms": 0.0,
            "usage": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def encode(tokenizer: Any, text: str) -> list[int]:
    return [int(token_id) for token_id in tokenizer.encode(text, add_special_tokens=False)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Map vLLM first-token bang behavior over minimal prompt prefixes.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--tokenizer-path", default=r"D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B")
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_prefix_transition.json"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    tokenizer = load_tokenizer(args.tokenizer_path)

    prefixes = [
        "You",
        "You ",
        " You",
        "you",
        "you ",
        "You are",
        "You are ",
        "You are a",
        "You are the",
        "You can",
        "You should",
        "You will",
        "You must",
        "You need",
        "You have",
        "I am",
        "We are",
        "The",
        "The model",
        "Return",
        "System:",
        "System: You are",
        "<|system|>\nYou are",
        "<｜begin▁of▁sentence｜>You are",
        "<｜User｜>You are",
    ]
    suffixes = {
        "none": "",
        "period": ".",
        "task": ".\n\nRead README section 1 and extract: goals, risks, architecture.",
        "short_task": ". Read README.",
    }

    results: list[dict[str, Any]] = []
    for prefix in prefixes:
        for suffix_name, suffix in suffixes.items():
            prompt = prefix + suffix
            result = request_completion(base_url, args.model, prompt, args.timeout)
            ids = encode(tokenizer, prompt)
            result.update(
                {
                    "prefix": prefix,
                    "suffix_name": suffix_name,
                    "prompt": prompt,
                    "prompt_token_ids": ids,
                    "prompt_tokens": [tokenizer.decode([token_id]) for token_id in ids],
                }
            )
            results.append(result)

    summary: dict[str, Any] = {
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "by_prefix": {},
    }
    for item in results:
        bucket = summary["by_prefix"].setdefault(str(item["prefix"]), {"total": 0, "bang": 0, "texts": {}})
        bucket["total"] += 1
        if item["starts_with_bang"]:
            bucket["bang"] += 1
        bucket["texts"][item["suffix_name"]] = item["text_repr"]

    report = {
        "diagnostic": "vllm_prefix_transition",
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
