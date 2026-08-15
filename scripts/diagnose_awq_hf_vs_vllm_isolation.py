from __future__ import annotations

import argparse
import json
import os
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


def encode(tokenizer: Any, text: str) -> list[int]:
    return [int(token_id) for token_id in tokenizer.encode(text, add_special_tokens=False)]


def decode_token(tokenizer: Any, token_id: int) -> str:
    return str(tokenizer.decode([int(token_id)]))


def load_tokenizer(path: str):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=True)


def vllm_completion(base_url: str, model: str, prompt: str, timeout: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "temperature": 0.0,
        "max_tokens": 1,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer uaea-local"},
        method="POST",
    )
    started_at = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        choice = data["choices"][0]
        text = str(choice.get("text") or "")
        return {
            "ok": True,
            "finish_reason": str(choice.get("finish_reason") or ""),
            "text": text,
            "text_repr": repr(text),
            "starts_with_bang": text.startswith("!"),
            "latency_ms": round((time.monotonic() - started_at) * 1000, 3),
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


def hf_load_and_generate(model_path: str, tokenizer: Any, prompts: dict[str, str], device: str) -> dict[str, Any]:
    import torch
    from transformers import AutoModelForCausalLM

    started_at = time.monotonic()
    load_result: dict[str, Any] = {
        "ok": False,
        "device": device,
        "load_latency_ms": 0.0,
        "error": None,
        "results": [],
    }
    try:
        kwargs: dict[str, Any] = {
            "local_files_only": True,
            "trust_remote_code": True,
            "torch_dtype": torch.float16,
        }
        if device == "cuda":
            kwargs["device_map"] = {"": "cuda:0"}
        elif device == "auto":
            kwargs["device_map"] = "auto"
        model = AutoModelForCausalLM.from_pretrained(model_path, **kwargs)
        model.eval()
        load_result["ok"] = True
        load_result["load_latency_ms"] = round((time.monotonic() - started_at) * 1000, 3)
    except Exception as exc:
        load_result["load_latency_ms"] = round((time.monotonic() - started_at) * 1000, 3)
        load_result["error"] = f"{type(exc).__name__}: {exc}"
        return load_result

    for prompt_name, prompt in prompts.items():
        row: dict[str, Any] = {"prompt_name": prompt_name, "ok": False, "error": None}
        gen_started_at = time.monotonic()
        try:
            input_ids = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).input_ids
            input_ids = input_ids.to(model.device)
            with torch.no_grad():
                output = model.generate(
                    input_ids=input_ids,
                    max_new_tokens=1,
                    do_sample=False,
                    return_dict_in_generate=True,
                    output_scores=True,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
            new_token_id = int(output.sequences[0, input_ids.shape[-1]].detach().cpu().item())
            score = output.scores[0][0].detach().float().cpu()
            top_values, top_indices = torch.topk(score, k=10)
            row.update(
                {
                    "ok": True,
                    "new_token_id": new_token_id,
                    "new_token_text": decode_token(tokenizer, new_token_id),
                    "starts_with_bang": new_token_id == 0,
                    "top_tokens": [
                        {
                            "token_id": int(token_id),
                            "token": decode_token(tokenizer, int(token_id)),
                            "logit": float(value),
                        }
                        for value, token_id in zip(top_values.tolist(), top_indices.tolist())
                    ],
                    "latency_ms": round((time.monotonic() - gen_started_at) * 1000, 3),
                }
            )
        except Exception as exc:
            row.update(
                {
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "latency_ms": round((time.monotonic() - gen_started_at) * 1000, 3),
                }
            )
        load_result["results"].append(row)
    return load_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Experiment A: same AWQ/compressed-tensors artifact under HF and vLLM.")
    parser.add_argument("--model-path", default="/opt/uaea-models/models/DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4")
    parser.add_argument("--vllm-url", default="http://127.0.0.1:8001/v1")
    parser.add_argument("--vllm-model", default="ds14b-awq")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--hf-device", choices=["cpu", "cuda", "auto"], default="cpu")
    parser.add_argument("--skip-hf", action="store_true")
    parser.add_argument("--skip-vllm", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("/mnt/d/UAEA/data/diagnostics/awq_hf_vs_vllm_isolation.json"))
    args = parser.parse_args()

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    tokenizer = load_tokenizer(args.model_path)
    prompt_metadata = {
        name: {
            "text": prompt,
            "input_token_ids": encode(tokenizer, prompt),
        }
        for name, prompt in PROMPTS.items()
    }
    report: dict[str, Any] = {
        "diagnostic": "awq_hf_vs_vllm_isolation",
        "model_path": args.model_path,
        "tokenizer": {
            "class": type(tokenizer).__name__,
            "bos_token": repr(tokenizer.bos_token),
            "bos_token_id": tokenizer.bos_token_id,
            "eos_token": repr(tokenizer.eos_token),
            "eos_token_id": tokenizer.eos_token_id,
            "pad_token": repr(tokenizer.pad_token),
            "pad_token_id": tokenizer.pad_token_id,
        },
        "prompts": prompt_metadata,
        "hf": None,
        "vllm": None,
    }
    if not args.skip_hf:
        report["hf"] = hf_load_and_generate(args.model_path, tokenizer, PROMPTS, args.hf_device)
    if not args.skip_vllm:
        vllm_rows = []
        for prompt_name, prompt in PROMPTS.items():
            row = vllm_completion(args.vllm_url, args.vllm_model, prompt, args.timeout)
            row["prompt_name"] = prompt_name
            vllm_rows.append(row)
        report["vllm"] = {
            "ok": any(row["ok"] for row in vllm_rows),
            "base_url": args.vllm_url,
            "model": args.vllm_model,
            "results": vllm_rows,
        }

    report["summary"] = {
        "hf_ok": bool(report["hf"] and report["hf"].get("ok")),
        "vllm_ok": bool(report["vllm"] and report["vllm"].get("ok")),
        "hf_bang": sum(1 for row in (report["hf"] or {}).get("results", []) if row.get("starts_with_bang")),
        "vllm_bang": sum(1 for row in (report["vllm"] or {}).get("results", []) if row.get("starts_with_bang")),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
