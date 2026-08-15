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
        raise SystemExit(f"transformers is required for this diagnostic: {exc}") from exc
    return AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=True)


def token_snapshot(tokenizer: Any, text: str, tail: int = 48) -> dict[str, Any]:
    token_ids = [int(token_id) for token_id in tokenizer.encode(text, add_special_tokens=False)]
    tail_ids = token_ids[-tail:]
    return {
        "chars": len(text),
        "tokens": len(token_ids),
        "tail_token_ids": tail_ids,
        "tail_tokens": [tokenizer.decode([token_id]) for token_id in tail_ids],
        "tail_text_repr": repr(text[-500:]),
    }


def post_completion(base_url: str, model: str, prompt: str, timeout: int) -> tuple[dict[str, Any], float]:
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": 0.0,
        "max_tokens": 1,
        "logprobs": 10,
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


def completion_summary(data: dict[str, Any], latency_ms: float) -> dict[str, Any]:
    choice = data["choices"][0]
    logprobs = choice.get("logprobs") or {}
    tokens = logprobs.get("tokens") or []
    token_logprobs = logprobs.get("token_logprobs") or []
    top_logprobs = logprobs.get("top_logprobs") or []
    text = str(choice.get("text") or "")
    return {
        "text": text,
        "text_repr": repr(text),
        "finish_reason": str(choice.get("finish_reason") or ""),
        "stop_reason": choice.get("stop_reason"),
        "latency_ms": round(latency_ms, 3),
        "usage": data.get("usage"),
        "first_token": tokens[0] if tokens else "",
        "first_token_logprob": token_logprobs[0] if token_logprobs else None,
        "first_top_logprobs": top_logprobs[0] if top_logprobs else {},
    }


def exact_specials(tokenizer: Any) -> dict[str, str]:
    return {
        "bos": str(tokenizer.bos_token or ""),
        "eos": str(tokenizer.eos_token or ""),
        "pad": str(tokenizer.pad_token or ""),
        "assistant": "<｜Assistant｜>",
        "user": "<｜User｜>",
        "think": "<think>\n",
    }


def build_variants(tokenizer: Any, canonical_prompt: str, messages: list[dict[str, str]]) -> dict[str, str]:
    specials = exact_specials(tokenizer)
    deepseek_full = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    deepseek_no_generation = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    if not isinstance(deepseek_full, str) or not isinstance(deepseek_no_generation, str):
        raise SystemExit("tokenizer.apply_chat_template did not return strings")

    no_bos = deepseek_full
    if specials["bos"] and no_bos.startswith(specials["bos"]):
        no_bos = no_bos[len(specials["bos"]) :]

    no_assistant_suffix = deepseek_full
    suffix = specials["assistant"] + specials["think"]
    if no_assistant_suffix.endswith(suffix):
        no_assistant_suffix = no_assistant_suffix[: -len(suffix)]

    assistant_only_suffix = canonical_prompt + "\n" + suffix
    canonical_plus_bos = specials["bos"] + canonical_prompt

    return {
        "canonical": canonical_prompt,
        "canonical_plus_bos": canonical_plus_bos,
        "canonical_plus_deepseek_assistant_suffix": assistant_only_suffix,
        "deepseek_full": deepseek_full,
        "deepseek_no_bos": no_bos,
        "deepseek_no_generation_prompt": deepseek_no_generation,
        "deepseek_without_assistant_suffix": no_assistant_suffix,
        "deepseek_without_think_marker": deepseek_full.replace("<think>\n", ""),
        "deepseek_without_assistant_marker": deepseek_full.replace(specials["assistant"], ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture vLLM first-token logprobs for canonical vs chat-template prompts.")
    parser.add_argument("--trace", type=Path, default=Path("data/inference_traces/vllm/phase1/vllm_phase1_l0_l1_selected.jsonl"))
    parser.add_argument("--case", default="L1-02")
    parser.add_argument("--phase", default="planner")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--tokenizer-path", default=r"D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B")
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_first_token_logprobs.json"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    tokenizer = load_tokenizer(args.tokenizer_path)
    record = load_first_record(args.trace, args.case, args.phase)
    canonical_prompt = str(record.get("rendered_prompt") or "")
    messages = parse_canonical_messages(canonical_prompt)
    variants = build_variants(tokenizer, canonical_prompt, messages)

    results: list[dict[str, Any]] = []
    for name, prompt in variants.items():
        try:
            data, latency_ms = post_completion(base_url, args.model, prompt, args.timeout)
            response = completion_summary(data, latency_ms)
            error = None
        except Exception as exc:
            response = {}
            error = f"{type(exc).__name__}: {exc}"
        snapshot = token_snapshot(tokenizer, prompt)
        results.append(
            {
                "variant": name,
                "ok": error is None,
                "error": error,
                "prompt_snapshot": snapshot,
                "response": response,
            }
        )

    special_token_strings = exact_specials(tokenizer)
    special_token_ids = {
        key: tokenizer.encode(value, add_special_tokens=False) if value else []
        for key, value in special_token_strings.items()
    }
    summary = {
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "first_token_counts": {},
        "bang_first_variants": [],
    }
    for item in results:
        token = str((item.get("response") or {}).get("first_token") or "")
        summary["first_token_counts"][token] = summary["first_token_counts"].get(token, 0) + 1
        if token == "!":
            summary["bang_first_variants"].append(item["variant"])

    report = {
        "diagnostic": "vllm_first_token_logprobs",
        "source_trace": str(args.trace),
        "case_id": args.case,
        "phase": args.phase,
        "base_url": base_url,
        "model": args.model,
        "tokenizer_path": args.tokenizer_path,
        "special_token_strings": special_token_strings,
        "special_token_ids": special_token_ids,
        "summary": summary,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
