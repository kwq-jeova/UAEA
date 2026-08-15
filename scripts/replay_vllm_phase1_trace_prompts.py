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


def text_from_response(endpoint: str, data: dict[str, Any]) -> str:
    choice = data["choices"][0]
    if endpoint == "chat":
        return str(choice.get("message", {}).get("content") or "")
    return str(choice.get("text") or "")


def repetition(text: str) -> dict[str, Any]:
    return {
        "length_chars": len(text),
        "bang_count": text.count("!"),
        "bang_ratio": round(text.count("!") / max(1, len(text)), 4),
        "starts_with_64_bangs": text.startswith("!" * 64),
        "excerpt": text[:1000],
    }


def load_selected_records(path: Path, selected_cases: set[str]) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if str(record.get("case_id")) in selected_cases:
            records.append(record)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay Phase-1 trace prompts directly against vLLM API.")
    parser.add_argument("--trace", type=Path, default=Path("data/inference_traces/vllm/phase1/vllm_phase1_l0_l1_selected.jsonl"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_phase1_prompt_replay.json"))
    args = parser.parse_args()

    selected = {"L0-01", "L0-02", "L1-02"}
    base_url = args.base_url.rstrip("/")
    results: list[dict[str, Any]] = []
    records = load_selected_records(args.trace, selected)
    for record_index, record in enumerate(records, 1):
        rendered_prompt = str(record.get("rendered_prompt") or "")
        messages = parse_canonical_messages(rendered_prompt)
        if not messages:
            continue
        original_max = int((record.get("generation_config") or {}).get("max_tokens") or record.get("output_tokens") or 256)
        original_temperature = float((record.get("generation_config") or {}).get("temperature") or 0.0)
        for endpoint in ("chat", "completion"):
            for max_tokens in (32, 128, original_max):
                for temperature in (0.0, original_temperature, 0.2):
                    if endpoint == "chat":
                        payload = {
                            "model": args.model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "chat_template_kwargs": {"enable_thinking": False},
                        }
                        url = f"{base_url}/chat/completions"
                    else:
                        payload = {
                            "model": args.model,
                            "prompt": rendered_prompt,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        }
                        url = f"{base_url}/completions"
                    try:
                        data, latency_ms = post_json(url, payload, args.timeout)
                        text = text_from_response(endpoint, data)
                        results.append(
                            {
                                "source_record_index": record_index,
                                "case_id": record.get("case_id"),
                                "phase": record.get("phase"),
                                "endpoint": endpoint,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                                "ok": True,
                                "finish_reason": str(data["choices"][0].get("finish_reason") or ""),
                                "latency_ms": round(latency_ms, 3),
                                "usage": data.get("usage"),
                                "repetition": repetition(text),
                                "error": None,
                            }
                        )
                    except Exception as exc:
                        results.append(
                            {
                                "source_record_index": record_index,
                                "case_id": record.get("case_id"),
                                "phase": record.get("phase"),
                                "endpoint": endpoint,
                                "temperature": temperature,
                                "max_tokens": max_tokens,
                                "ok": False,
                                "finish_reason": "error",
                                "latency_ms": 0.0,
                                "usage": None,
                                "repetition": {},
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        )

    summary: dict[str, Any] = {
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "bang_pathology_count": sum(1 for item in results if item.get("repetition", {}).get("bang_ratio", 0) > 0.8),
        "finish_reason_counts": {},
    }
    for item in results:
        reason = str(item.get("finish_reason") or "")
        summary["finish_reason_counts"][reason] = summary["finish_reason_counts"].get(reason, 0) + 1

    report = {
        "diagnostic": "vllm_phase1_trace_prompt_replay",
        "source_trace": str(args.trace),
        "base_url": base_url,
        "model": args.model,
        "summary": summary,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
