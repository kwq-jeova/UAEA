from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PROMPTS = {
    "minimal_upper": "You are a local assistant.",
    "minimal_lower": "you are a local assistant.",
    "canonical_upper": "<|system|>\nYou are a local assistant.\n\n<|user|>\nRead README section 1 and extract: goals, risks, architecture.",
    "deepseek_upper": "You are a local assistant.<｜User｜>Read README section 1 and extract: goals, risks, architecture.<｜Assistant｜><think>\n",
}


def post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[bool, dict[str, Any] | None, str | None, float]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer uaea-local"},
        method="POST",
    )
    started_at = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
        return True, json.loads(body), None, (time.monotonic() - started_at) * 1000
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return False, None, f"HTTP {exc.code}: {body[:2000]}", (time.monotonic() - started_at) * 1000
    except Exception as exc:
        return False, None, f"{type(exc).__name__}: {exc}", (time.monotonic() - started_at) * 1000


def summarize_completion(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    choice = data["choices"][0]
    logprobs = choice.get("logprobs") or {}
    tokens = logprobs.get("tokens") or []
    token_logprobs = logprobs.get("token_logprobs") or []
    top_logprobs = logprobs.get("top_logprobs") or []
    text = str(choice.get("text") or "")
    return {
        "text": text,
        "text_repr": repr(text),
        "starts_with_bang": text.startswith("!"),
        "finish_reason": choice.get("finish_reason"),
        "usage": data.get("usage"),
        "first_token": tokens[0] if tokens else None,
        "first_token_logprob": token_logprobs[0] if token_logprobs else None,
        "first_top_logprobs": top_logprobs[0] if top_logprobs else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal vLLM logprobs diagnostic for bang-trigger prompts.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_minimal_logprobs.json"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    results = []
    for name, prompt in PROMPTS.items():
        plain_payload = {
            "model": args.model,
            "prompt": prompt,
            "temperature": 0.0,
            "max_tokens": 1,
        }
        logprobs_payload = {
            **plain_payload,
            "logprobs": 10,
        }
        plain_ok, plain_data, plain_error, plain_latency = post_json(
            f"{base_url}/completions", plain_payload, args.timeout
        )
        log_ok, log_data, log_error, log_latency = post_json(
            f"{base_url}/completions", logprobs_payload, args.timeout
        )
        results.append(
            {
                "prompt_name": name,
                "prompt": prompt,
                "plain": {
                    "ok": plain_ok,
                    "error": plain_error,
                    "latency_ms": round(plain_latency, 3),
                    "response": summarize_completion(plain_data),
                },
                "logprobs": {
                    "ok": log_ok,
                    "error": log_error,
                    "latency_ms": round(log_latency, 3),
                    "response": summarize_completion(log_data),
                },
            }
        )

    report = {
        "diagnostic": "vllm_minimal_logprobs",
        "base_url": base_url,
        "model": args.model,
        "summary": {
            "total": len(results),
            "plain_bang": sum(1 for row in results if row["plain"]["response"].get("starts_with_bang")),
            "logprobs_ok": sum(1 for row in results if row["logprobs"]["ok"]),
            "logprobs_failed": sum(1 for row in results if not row["logprobs"]["ok"]),
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
