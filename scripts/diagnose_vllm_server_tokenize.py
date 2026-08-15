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


def post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[int, dict[str, Any] | None, str, float]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer uaea-local"},
        method="POST",
    )
    started_at = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw), raw, (time.monotonic() - started_at) * 1000
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, None, raw, (time.monotonic() - started_at) * 1000


def local_encode(tokenizer: Any, text: str) -> list[int]:
    return [int(token_id) for token_id in tokenizer.encode(text, add_special_tokens=False)]


def normalize_server_tokens(data: dict[str, Any] | None) -> list[int] | None:
    if not isinstance(data, dict):
        return None
    for key in ("tokens", "input_ids", "token_ids"):
        value = data.get(key)
        if isinstance(value, list) and all(isinstance(item, int) for item in value):
            return [int(item) for item in value]
    nested = data.get("data")
    if isinstance(nested, dict):
        return normalize_server_tokens(nested)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare local tokenizer ids with vLLM /tokenize endpoint when available.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--tokenizer-path", default=r"D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B")
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_server_tokenize.json"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    tokenizer = load_tokenizer(args.tokenizer_path)
    prompts = {
        "you_are": "You are",
        "space_you_are": " You are",
        "lower_you_are": "you are",
        "system_you_are": "<|system|>\nYou are",
        "deepseek_user_you_are": "<｜User｜>You are",
        "phase1_upper_plain": "You are a local assistant.\n\nRead README section 1 and extract: goals, risks, architecture.",
    }

    results: list[dict[str, Any]] = []
    for name, prompt in prompts.items():
        for endpoint in ("/tokenize", "/v1/tokenize"):
            payload = {"model": args.model, "prompt": prompt}
            status, data, raw, latency_ms = post_json(f"{base_url}{endpoint}", payload, args.timeout)
            server_ids = normalize_server_tokens(data)
            local_ids = local_encode(tokenizer, prompt)
            results.append(
                {
                    "prompt_name": name,
                    "endpoint": endpoint,
                    "status": status,
                    "ok": 200 <= status < 300,
                    "latency_ms": round(latency_ms, 3),
                    "local_token_ids": local_ids,
                    "local_tokens": [tokenizer.decode([token_id]) for token_id in local_ids],
                    "server_token_ids": server_ids,
                    "server_matches_local": server_ids == local_ids if server_ids is not None else None,
                    "response": data,
                    "raw_response": raw[:2000],
                }
            )

    summary = {
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "server_matches_local": sum(1 for item in results if item["server_matches_local"] is True),
    }
    report = {
        "diagnostic": "vllm_server_tokenize",
        "base_url": base_url,
        "model": args.model,
        "tokenizer_path": args.tokenizer_path,
        "summary": summary,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
