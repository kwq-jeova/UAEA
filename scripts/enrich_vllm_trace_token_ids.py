import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def tokenize(base_url: str, model: str, text: str, timeout: int) -> list[int]:
    if not text:
        return []
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/tokenize",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    tokens = data.get("tokens") or []
    return [int(token) for token in tokens]


def enrich_record(record: dict[str, Any], base_url: str, model: str, timeout: int) -> dict[str, Any]:
    enriched = dict(record)
    token_enrichment = {
        "source": f"{base_url.rstrip('/')}/tokenize",
        "model": model,
        "input_token_ids_source": "rendered_prompt",
        "output_token_ids_source": "output_text_excerpt",
    }
    if not enriched.get("input_token_ids"):
        input_ids = tokenize(base_url, model, str(enriched.get("rendered_prompt") or ""), timeout)
        enriched["input_token_ids"] = input_ids
        enriched["input_tokens"] = len(input_ids) or int(enriched.get("input_tokens") or 0)
    if not enriched.get("output_token_ids"):
        output_ids = tokenize(base_url, model, str(enriched.get("output_text_excerpt") or ""), timeout)
        enriched["output_token_ids"] = output_ids
        enriched["output_tokens"] = len(output_ids) or int(enriched.get("output_tokens") or 0)
    enriched["token_enrichment"] = token_enrichment
    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich vLLM inference trace JSONL with token ids via /tokenize.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--model", default="qwen25-14b-awq")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    enriched_count = 0
    with args.input.open("r", encoding="utf-8") as source, args.output.open("w", encoding="utf-8") as sink:
        for line in source:
            if not line.strip():
                continue
            total += 1
            record = json.loads(line)
            try:
                enriched = enrich_record(record, args.base_url, args.model, args.timeout)
                enriched_count += 1
            except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                enriched = dict(record)
                enriched["token_enrichment_error"] = str(exc)
            sink.write(json.dumps(enriched, ensure_ascii=False) + "\n")

    print(json.dumps({"input": str(args.input), "output": str(args.output), "records": total, "enriched": enriched_count}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
