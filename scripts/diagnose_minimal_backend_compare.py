from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def post_chat(
    base_url: str,
    model: str,
    system: str,
    user: str,
    timeout: int,
) -> tuple[dict[str, Any], float]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.0,
        "max_tokens": 16,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer uaea-local"},
        method="POST",
    )
    started_at = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8")), (time.monotonic() - started_at) * 1000


def call_backend(name: str, base_url: str, model: str, system: str, user: str, timeout: int) -> dict[str, Any]:
    try:
        data, latency_ms = post_chat(base_url, model, system, user, timeout)
        choice = data["choices"][0]
        message = choice.get("message") or {}
        text = str(message.get("content") or "")
        return {
            "backend": name,
            "base_url": base_url,
            "model": model,
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
            "backend": name,
            "base_url": base_url,
            "model": model,
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
            "backend": name,
            "base_url": base_url,
            "model": model,
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare minimal chat prompts across LMF and vLLM APIs.")
    parser.add_argument("--lmf-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--lmf-model", default="DeepSeek-R1-Distill-Qwen-14B")
    parser.add_argument("--vllm-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--vllm-model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/minimal_backend_compare.json"))
    args = parser.parse_args()

    prompts = [
        {
            "case_id": "upper_you_are",
            "system": "You are a local assistant.",
            "user": "Read README section 1 and extract: goals, risks, architecture.",
        },
        {
            "case_id": "lower_you_are",
            "system": "you are a local assistant.",
            "user": "Read README section 1 and extract: goals, risks, architecture.",
        },
        {
            "case_id": "json_only",
            "system": "Return one JSON object only. Do not explain.",
            "user": "Read README section 1 and extract: goals, risks, architecture.",
        },
    ]
    backends = [
        ("lmf", args.lmf_url, args.lmf_model),
        ("vllm", args.vllm_url, args.vllm_model),
    ]
    results: list[dict[str, Any]] = []
    for prompt in prompts:
        for backend_name, base_url, model in backends:
            result = call_backend(
                name=backend_name,
                base_url=base_url,
                model=model,
                system=prompt["system"],
                user=prompt["user"],
                timeout=args.timeout,
            )
            result.update(prompt)
            results.append(result)

    summary = {
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "by_backend": {},
    }
    for item in results:
        bucket = summary["by_backend"].setdefault(item["backend"], {"total": 0, "ok": 0, "bang": 0})
        bucket["total"] += 1
        if item["ok"]:
            bucket["ok"] += 1
        if item["starts_with_bang"]:
            bucket["bang"] += 1

    report = {
        "diagnostic": "minimal_backend_compare",
        "summary": summary,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
