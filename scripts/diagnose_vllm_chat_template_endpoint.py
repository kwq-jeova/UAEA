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


def post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[dict[str, Any], float]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer uaea-local"},
        method="POST",
    )
    started_at = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data, (time.monotonic() - started_at) * 1000


def response_text(endpoint: str, data: dict[str, Any]) -> str:
    choice = data["choices"][0]
    if endpoint == "chat":
        return str(choice.get("message", {}).get("content") or "")
    return str(choice.get("text") or "")


def repetition(text: str) -> dict[str, Any]:
    bang_count = text.count("!")
    return {
        "length_chars": len(text),
        "bang_count": bang_count,
        "bang_ratio": round(bang_count / max(1, len(text)), 4),
        "starts_with_32_bangs": text.startswith("!" * min(32, len(text))),
        "excerpt": text[:1200],
    }


def load_records(path: Path, selected: set[tuple[str, str]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        key = (str(record.get("case_id") or ""), str(record.get("phase") or ""))
        if key in selected and key not in seen:
            records.append(record)
            seen.add(key)
    return records


def load_tokenizer(tokenizer_path: str):
    try:
        from transformers import AutoTokenizer
    except Exception:
        return None
    try:
        return AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True, trust_remote_code=True)
    except Exception:
        return None


def render_with_tokenizer(tokenizer: Any, messages: list[dict[str, str]], add_generation_prompt: bool = True) -> str:
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


def l0_system_variants(messages: list[dict[str, str]]) -> list[tuple[str, list[dict[str, str]]]]:
    if not messages or messages[0].get("role") != "system":
        return []
    system = messages[0]["content"]
    user_messages = [message for message in messages if message.get("role") == "user"]
    variants: list[tuple[str, str]] = [
        ("l0_simple_system", "Answer directly and concisely."),
        ("l0_phase1_system_full", system),
        (
            "l0_phase1_without_think_instruction",
            system.replace("Do not output <think> tags or hidden chain-of-thought.\n", ""),
        ),
        (
            "l0_phase1_without_context_policy",
            system.split("\n\nContext policy:", 1)[0],
        ),
        (
            "l0_phase1_minimal_core",
            "\n".join(
                line
                for line in system.splitlines()
                if line.startswith("Answer ordinary questions")
                or line.startswith("Keep the answer")
                or line.startswith("Provide the final answer")
            ),
        ),
    ]
    return [(name, [{"role": "system", "content": text}, *user_messages]) for name, text in variants]


def run_variant(
    name: str,
    endpoint: str,
    base_url: str,
    model: str,
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    url = f"{base_url}/chat/completions" if endpoint == "chat" else f"{base_url}/completions"
    try:
        data, latency_ms = post_json(url, payload, timeout)
        text = response_text(endpoint, data)
        return {
            "variant": name,
            "endpoint": endpoint,
            "ok": True,
            "finish_reason": str(data["choices"][0].get("finish_reason") or ""),
            "latency_ms": round(latency_ms, 3),
            "usage": data.get("usage"),
            "repetition": repetition(text),
            "payload_keys": sorted(payload.keys()),
            "temperature": payload.get("temperature"),
            "max_tokens": payload.get("max_tokens"),
            "chat_template_kwargs": payload.get("chat_template_kwargs"),
            "error": None,
        }
    except Exception as exc:
        return {
            "variant": name,
            "endpoint": endpoint,
            "ok": False,
            "finish_reason": "error",
            "latency_ms": 0.0,
            "usage": None,
            "repetition": {},
            "payload_keys": sorted(payload.keys()),
            "temperature": payload.get("temperature"),
            "max_tokens": payload.get("max_tokens"),
            "chat_template_kwargs": payload.get("chat_template_kwargs"),
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose vLLM chat endpoint vs rendered prompt behavior.")
    parser.add_argument("--trace", type=Path, default=Path("data/inference_traces/vllm/phase1/vllm_phase1_l0_l1_selected.jsonl"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--tokenizer-path", default=r"D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B")
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_chat_template_endpoint_matrix.json"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    tokenizer = load_tokenizer(args.tokenizer_path)
    selected = {("L0-01", "chat_answer"), ("L0-02", "planner"), ("L1-02", "planner")}
    records = load_records(args.trace, selected)
    results: list[dict[str, Any]] = []

    for record in records:
        canonical_prompt = str(record.get("rendered_prompt") or "")
        messages = parse_canonical_messages(canonical_prompt)
        rendered_ds = render_with_tokenizer(tokenizer, messages, add_generation_prompt=True)
        rendered_ds_no_generation_prompt = render_with_tokenizer(tokenizer, messages, add_generation_prompt=False)
        variants: list[tuple[str, str, dict[str, Any]]] = [
            (
                "chat_messages_enable_false",
                "chat",
                {
                    "model": args.model,
                    "messages": messages,
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            ),
            (
                "chat_messages_no_kwargs",
                "chat",
                {
                    "model": args.model,
                    "messages": messages,
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                },
            ),
            (
                "completion_canonical_prompt",
                "completion",
                {
                    "model": args.model,
                    "prompt": canonical_prompt,
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                },
            ),
        ]
        if rendered_ds:
            variants.append(
                (
                    "completion_deepseek_template_prompt",
                    "completion",
                    {
                        "model": args.model,
                        "prompt": rendered_ds,
                        "temperature": args.temperature,
                        "max_tokens": args.max_tokens,
                    },
                )
            )
        if rendered_ds_no_generation_prompt:
            variants.append(
                (
                    "completion_deepseek_template_no_generation_prompt",
                    "completion",
                    {
                        "model": args.model,
                        "prompt": rendered_ds_no_generation_prompt,
                        "temperature": args.temperature,
                        "max_tokens": args.max_tokens,
                    },
                )
            )

        if record.get("case_id") == "L0-01" and record.get("phase") == "chat_answer":
            for variant_name, variant_messages in l0_system_variants(messages):
                variants.append(
                    (
                        variant_name,
                        "chat",
                        {
                            "model": args.model,
                            "messages": variant_messages,
                            "temperature": args.temperature,
                            "max_tokens": args.max_tokens,
                            "chat_template_kwargs": {"enable_thinking": False},
                        },
                    )
                )

        for variant_name, endpoint, payload in variants:
            item = run_variant(variant_name, endpoint, base_url, args.model, payload, args.timeout)
            item.update(
                {
                    "case_id": record.get("case_id"),
                    "phase": record.get("phase"),
                    "source_input_tokens": record.get("input_tokens"),
                    "canonical_prompt_chars": len(canonical_prompt),
                    "deepseek_prompt_chars": len(rendered_ds),
                    "tokenizer_path": args.tokenizer_path if tokenizer is not None else "",
                }
            )
            results.append(item)

    summary: dict[str, Any] = {
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "bang_pathology_count": sum(1 for item in results if item.get("repetition", {}).get("bang_ratio", 0) > 0.8),
        "finish_reason_counts": {},
        "by_variant": {},
    }
    for item in results:
        reason = str(item.get("finish_reason") or "")
        summary["finish_reason_counts"][reason] = summary["finish_reason_counts"].get(reason, 0) + 1
        variant = str(item.get("variant") or "")
        bucket = summary["by_variant"].setdefault(variant, {"total": 0, "bang": 0, "finish_reason_counts": {}})
        bucket["total"] += 1
        if item.get("repetition", {}).get("bang_ratio", 0) > 0.8:
            bucket["bang"] += 1
        bucket["finish_reason_counts"][reason] = bucket["finish_reason_counts"].get(reason, 0) + 1

    report = {
        "diagnostic": "vllm_chat_template_endpoint_matrix",
        "source_trace": str(args.trace),
        "base_url": base_url,
        "model": args.model,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "summary": summary,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
