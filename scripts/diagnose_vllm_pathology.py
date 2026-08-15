from __future__ import annotations

import argparse
import json
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DiagnosticCase:
    case_id: str
    endpoint: str
    prompt: str
    temperature: float
    max_tokens: int


def request_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[dict[str, Any], float]:
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


def output_text(endpoint: str, data: dict[str, Any]) -> str:
    choice = data["choices"][0]
    if endpoint == "chat":
        return str(choice.get("message", {}).get("content") or "")
    return str(choice.get("text") or "")


def finish_reason(data: dict[str, Any]) -> str:
    return str(data["choices"][0].get("finish_reason") or "")


def repetition_metrics(text: str) -> dict[str, Any]:
    return {
        "length_chars": len(text),
        "bang_count": text.count("!"),
        "bang_ratio": round(text.count("!") / max(1, len(text)), 4),
        "starts_with_bang_run": text.startswith("!" * min(16, len(text))),
        "max_bang_run": max((len(part) for part in text.replace("\n", " ").split(" ") if set(part) == {"!"}), default=0),
        "excerpt": text[:800],
    }


def build_cases() -> list[DiagnosticCase]:
    prompts = {
        "bootloader_short": "Explain bootloader design.",
        "bootloader_embedded": "Explain bootloader design in embedded systems.",
        "phase1_l0_01": "Explain what UAEA is.",
        "phase1_l1_02": "Read README section 1 and extract goals, risks, and architecture.",
    }
    cases: list[DiagnosticCase] = []
    for prompt_id, prompt in prompts.items():
        for endpoint in ("chat", "completion"):
            for temperature in (0.0, 0.2, 0.7):
                for max_tokens in (32, 128, 512):
                    cases.append(
                        DiagnosticCase(
                            case_id=f"{prompt_id}_{endpoint}_t{temperature}_m{max_tokens}",
                            endpoint=endpoint,
                            prompt=prompt,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                    )
    return cases


def run_case(case: DiagnosticCase, base_url: str, model: str, timeout: int) -> dict[str, Any]:
    if case.endpoint == "chat":
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Answer directly and concisely."},
                {"role": "user", "content": case.prompt},
            ],
            "temperature": case.temperature,
            "max_tokens": case.max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        url = f"{base_url}/chat/completions"
    else:
        payload = {
            "model": model,
            "prompt": case.prompt,
            "temperature": case.temperature,
            "max_tokens": case.max_tokens,
        }
        url = f"{base_url}/completions"

    try:
        data, latency_ms = request_json(url, payload, timeout)
        text = output_text(case.endpoint, data)
        return {
            **asdict(case),
            "ok": True,
            "finish_reason": finish_reason(data),
            "latency_ms": round(latency_ms, 3),
            "usage": data.get("usage"),
            "repetition": repetition_metrics(text),
            "error": None,
            "payload": payload,
        }
    except Exception as exc:
        return {
            **asdict(case),
            "ok": False,
            "finish_reason": "error",
            "latency_ms": 0.0,
            "usage": None,
            "repetition": {},
            "error": f"{type(exc).__name__}: {exc}",
            "payload": payload,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run raw vLLM API pathology diagnostics outside Phase-1 Runtime.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=Path, default=Path("data/diagnostics/vllm_pathology_matrix.json"))
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    results = [run_case(case, base_url, args.model, args.timeout) for case in build_cases()]
    summary = {
        "total": len(results),
        "ok": sum(1 for item in results if item["ok"]),
        "failed": sum(1 for item in results if not item["ok"]),
        "finish_reason_counts": {},
        "bang_pathology_count": sum(1 for item in results if item.get("repetition", {}).get("bang_ratio", 0) > 0.8),
    }
    for item in results:
        reason = str(item.get("finish_reason") or "")
        summary["finish_reason_counts"][reason] = summary["finish_reason_counts"].get(reason, 0) + 1

    report = {
        "diagnostic": "vllm_raw_api_pathology_matrix",
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
