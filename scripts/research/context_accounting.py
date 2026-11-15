"""Read-only prompt accounting from actual vLLM /render token IDs.

API usage remains the primary execution ledger. Component attribution is a
disjoint character-span convention over the rendered prompt, reconciled to
actual token IDs; it is not a semantic relevance or quality score.
"""
import json
import re
from collections import Counter
from hashlib import sha256
from pathlib import Path
import http.client
from urllib.parse import urlsplit


def render_request(request, url="http://127.0.0.1:8003"):
    # Rendering tokenizes only: it does not submit a generation/Tool Call.
    payload = dict(request)
    payload["return_token_offsets"] = True
    body = json.dumps(payload, ensure_ascii=False).encode()
    target = urlsplit(url)
    if target.scheme != "http" or target.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Accounting renderer is loopback-only")
    connection = http.client.HTTPConnection(target.hostname, target.port, timeout=15)
    try:
        connection.request("POST", "/v1/responses/render", body=body,
                           headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        raw = response.read(2 * 1024 * 1024 + 1)
        if response.status != 200:
            raise ValueError("Local render HTTP " + str(response.status) + ": " + raw[:300].decode(errors="replace"))
    finally:
        connection.close()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("Render observation budget exceeded")
    return json.loads(raw)


def prompt_components(rendered, request, tokenizer, *, current_task=""):
    ids = rendered["token_ids"]
    text = tokenizer.decode(ids, skip_special_tokens=False)
    encoded = tokenizer.encode(text, add_special_tokens=False)
    if encoded.ids != ids:
        return {"status": "UNKNOWN", "render_tokens": len(ids),
                "reason": "decoded prompt did not re-encode to exact server IDs",
                "component_counts_not_reported_as_exact": True}
    length = len(text)
    roles = ["template"] * length
    labels = ["template"] * length
    priority = [0] * length
    def mark(start, end, label, rank):
        for i in range(max(0, start), min(length, end)):
            if rank >= priority[i]:
                labels[i] = label; priority[i] = rank
    role_matches = list(re.finditer(r"<\|im_start\|>([a-z_]+)\n", text))
    for item in role_matches:
        end = text.find("<|im_end|>", item.end())
        end = length if end < 0 else end
        role = item.group(1)
        for i in range(item.end(), end):
            roles[i] = role
        mark(item.end(), end,
             "system_developer" if role in {"system", "developer"} else
             "assistant_history" if role == "assistant" else "ordinary_user_history", 1)
    for match in re.finditer(r"<external_uaea\.[^>]+>.*?</external_uaea\.[^>]+>", text, re.S):
        mark(match.start(), match.end(), "runtime_context", 10)
    if current_task:
        for literal in [current_task, json.dumps(current_task, ensure_ascii=False)[1:-1]]:
            start = 0
            while literal and (start := text.find(literal, start)) >= 0:
                mark(start, start + len(literal), "current_task", 15);start += len(literal)
    for match in re.finditer(r"<tools>.*?</tools>", text, re.S):
        mark(match.start(), match.end(), "tool_definitions", 90)
    for match in re.finditer(r"<external_uaea\.goal_hypotheses>.*?</external_uaea\.goal_hypotheses>", text, re.S):
        mark(match.start(), match.end(), "Goal_view", 80)
    for block in re.finditer(r"<external_uaea\.relevant_history>(.*?)</external_uaea\.relevant_history>", text, re.S):
        mark(block.start(), block.end(), "relevant_history_metadata", 30)
        value = json.loads(block.group(1))
        cursor = block.start(1)
        for entry in value.get("entries", []):
            literal = json.dumps(entry, ensure_ascii=False)
            start = text.find(literal, cursor, block.end(1))
            if start < 0:
                continue
            end = start + len(literal);cursor = end
            content = entry.get("content", {})
            tool = content.get("tool") if isinstance(content, dict) else None
            role = entry.get("role")
            label = ("Goal_history" if tool == "goal_hypothesis" else
                     "tool_call_history" if role == "historical_model_tool_call" else
                     "tool_receipt_metadata" if role == "historical_Host_tool_receipt" else
                     "historical_user" if role == "historical_user" else "assistant_history")
            mark(start, end, label, 40)
            # Original body may be JSON-encoded twice inside a historical receipt.
            if role == "historical_Host_tool_receipt" and tool != "goal_hypothesis":
                for part in content.get("contentItems", []):
                    try: receipt = json.loads(part.get("text", ""))
                    except (ValueError, TypeError): continue
                    body = receipt.get("data", {}).get("content")
                    if isinstance(body, str) and len(body) > 20:
                        for _ in range(3):
                            body = json.dumps(body, ensure_ascii=False)[1:-1]
                            at = text.find(body, start, end)
                            if at >= 0:
                                mark(at, at + len(body), "evidence_body", 100);break
    for match in re.finditer(r"<tool_call>.*?</tool_call>", text, re.S):
        if roles[match.start()] != "assistant":
            continue
        label = "Goal_history" if "<function=goal_hypothesis>" in match.group() else "tool_call_history"
        mark(match.start(), match.end(), label, 60)
    for match in re.finditer(r"<tool_response>\n(.*?)\n</tool_response>", text, re.S):
        raw = match.group(1)
        try: value = json.loads(raw)
        except ValueError: continue
        goal = value.get("kind") == "goal_hypothesis_receipt"
        mark(match.start(), match.end(), "Goal_history" if goal else "tool_receipt_metadata", 60)
        if goal or value.get("capability") not in {"document.read_section", "document.read_file"}:
            continue
        for field in re.finditer(r'"content"\s*:\s*("(?:[^"\\]|\\.)*")', raw):
            at = match.start(1) + field.start(1) + 1
            end = match.start(1) + field.end(1) - 1
            mark(at, end, "evidence_body", 100)
        for field in re.finditer(r'"section_catalog"\s*:\s*\[', raw):
            # Exact catalogue text is a JSON array; count it independently of body.
            try: array, used = json.JSONDecoder().raw_decode(raw[field.end()-1:])
            except ValueError: continue
            at = match.start(1) + field.end() - 1
            mark(at, at + used, "document_catalogue", 100)

    semantic = Counter(); model_roles = Counter()
    for start, end in encoded.offsets:
        if end <= start:
            semantic["zero_width_special"] += 1;model_roles["zero_width_special"] += 1;continue
        categories = set(labels[start:end]); actual_roles = set(roles[start:end])
        semantic[next(iter(categories)) if len(categories) == 1 else "boundary_mixed"] += 1
        model_roles[next(iter(actual_roles)) if len(actual_roles) == 1 else "boundary_mixed"] += 1
    assert sum(semantic.values()) == sum(model_roles.values()) == len(ids)
    return {"status": "VERIFIED token partition, not semantic truth", "render_tokens": len(ids),
            "exact_ID_roundtrip": True, "prompt_sha256": sha256(text.encode()).hexdigest(),
            "component_tokens": dict(semantic), "rendered_role_tokens": dict(model_roles),
            "axes_not_additive_to_each_other": True,
            "boundaries_assigned_separately": True,
            "tool_output_may_render_as_user_role": True,
            "character_span_convention_not_causal_Goal_use": True}
