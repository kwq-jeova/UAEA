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
    prompt: str,
    max_tokens: int,
    timeout: int,
    extra: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], float]:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    payload.update(extra or {})
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
    prompt: str,
    max_tokens: int,
    timeout: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        data, latency_ms = post_completion(base_url, model, prompt, max_tokens, timeout, extra)
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
            "logprobs": choice.get("logprobs"),
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
            "logprobs": None,
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
            "logprobs": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def encode(tokenizer: Any, text: str) -> list[int]:
    return [int(token_id) for token_id in tokenizer.encode(text, add_special_tokens=False)]


def token_summary(tokenizer: Any, prompt: str) -> dict[str, Any]:
    ids = encode(tokenizer, prompt)
    return {
        "token_count": len(ids),
        "head_token_ids": ids[:16],
        "head_tokens": [tokenizer.decode([token_id]) for token_id in ids[:16]],
        "tail_token_ids": ids[-24:],
        "tail_tokens": [tokenizer.decode([token_id]) for token_id in ids[-24:]],
    }


def first_token_logprob_summary(logprobs: Any) -> dict[str, Any]:
    if not isinstance(logprobs, dict):
        return {"available": False}
    tokens = logprobs.get("tokens") or []
    token_logprobs = logprobs.get("token_logprobs") or []
    top_logprobs = logprobs.get("top_logprobs") or []
    return {
        "available": True,
        "tokens": tokens[:3],
        "token_logprobs": token_logprobs[:3],
        "top_logprobs": top_logprobs[:1],
    }


def build_prompts(tokenizer: Any) -> dict[str, str]:
    user_text = "Read README section 1 and extract: goals, risks, architecture."
    system_upper = "You are a local assistant."
    system_lower = "you are a local assistant."
    system_json = "Return one JSON object only. Do not explain."
    bos = str(tokenizer.bos_token or "")
    user = "<｜User｜>"
    assistant = "<｜Assistant｜>"
    think = "<think>\n"
    return {
        "upper_plain": f"{system_upper}\n\n{user_text}",
        "upper_plain_space_prefix": f" {system_upper}\n\n{user_text}",
        "upper_plain_bos": f"{bos}{system_upper}\n\n{user_text}",
        "upper_plain_single_newline": f"{system_upper}\n{user_text}",
        "upper_plain_colon": f"{system_upper}\nUser: {user_text}",
        "lower_plain": f"{system_lower}\n\n{user_text}",
        "json_plain": f"{system_json}\n\n{user_text}",
        "upper_canonical": f"<|system|>\n{system_upper}\n\n<|user|>\n{user_text}",
        "upper_deepseek": f"{system_upper}{user}{user_text}{assistant}{think}",
        "lower_deepseek": f"{system_lower}{user}{user_text}{assistant}{think}",
        "json_deepseek": f"{system_json}{user}{user_text}{assistant}{think}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Localize vLLM token-0 bang first-token attractor.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--tokenizer-path", default=r"D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B")
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_bang_root_layer.json"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    tokenizer = load_tokenizer(args.tokenizer_path)
    prompts = build_prompts(tokenizer)
    bang_token_id = int(encode(tokenizer, "!")[0])

    matrix: list[dict[str, Any]] = []
    profiles = {
        "baseline_1": {"max_tokens": 1, "extra": {}},
        "baseline_16": {"max_tokens": 16, "extra": {}},
        "logprobs_1": {"max_tokens": 1, "extra": {"logprobs": 10}},
        "ban_bang_16": {"max_tokens": 16, "extra": {"logit_bias": {str(bang_token_id): -100}}},
        "stop_bang_16": {"max_tokens": 16, "extra": {"stop": ["!"]}},
    }
    for prompt_name, prompt in prompts.items():
        for profile_name, profile in profiles.items():
            result = request_completion(
                base_url=base_url,
                model=args.model,
                prompt=prompt,
                max_tokens=int(profile["max_tokens"]),
                timeout=args.timeout,
                extra=dict(profile["extra"]),
            )
            result.update(
                {
                    "prompt_name": prompt_name,
                    "profile": profile_name,
                    "request_extra": profile["extra"],
                    "prompt": prompt,
                    "prompt_tokenization": token_summary(tokenizer, prompt),
                    "first_token_logprobs": first_token_logprob_summary(result.get("logprobs")),
                }
            )
            matrix.append(result)

    summary: dict[str, Any] = {
        "total": len(matrix),
        "ok": sum(1 for item in matrix if item["ok"]),
        "failed": sum(1 for item in matrix if not item["ok"]),
        "bang_token_id": bang_token_id,
        "by_prompt": {},
    }
    for item in matrix:
        bucket = summary["by_prompt"].setdefault(
            item["prompt_name"],
            {"total": 0, "starts_with_bang": 0, "ban_bang_ok_nonbang": 0, "stop_bang_empty": 0},
        )
        bucket["total"] += 1
        if item.get("starts_with_bang"):
            bucket["starts_with_bang"] += 1
        if item["profile"] == "ban_bang_16" and item["ok"] and not item.get("starts_with_bang"):
            bucket["ban_bang_ok_nonbang"] += 1
        if item["profile"] == "stop_bang_16" and item["ok"] and item.get("finish_reason") == "stop" and item.get("text") == "":
            bucket["stop_bang_empty"] += 1

    report = {
        "diagnostic": "vllm_bang_root_layer",
        "base_url": base_url,
        "model": args.model,
        "tokenizer_path": args.tokenizer_path,
        "summary": summary,
        "results": matrix,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
