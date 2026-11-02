"""Host-side collection of observable answers; no permission inference."""
from __future__ import annotations

from typing import Callable


class InputCancelled(Exception):
    pass


def collect_answers(questions: list[dict], read: Callable[[str], str]) -> dict:
    if not isinstance(questions, list) or not 1 <= len(questions) <= 3:
        raise ValueError("Expected one to three native questions")
    if any(not isinstance(item, dict) for item in questions):
        raise ValueError("Invalid question object")
    ids = [item.get("id") for item in questions]
    if any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise ValueError("Question identities must be unique")
    for item in questions:
        if not isinstance(item.get("question"), str) or not item["question"]:
            raise ValueError("Question text is required")
        if item.get("isSecret"):
            raise ValueError("Secret input is not supported by the plain-text REPL")
        if item.get("options") is not None and not isinstance(item["options"], list):
            raise ValueError("Invalid options")
        for option in item.get("options") or []:
            if not isinstance(option, dict) or not isinstance(option.get("label"), str):
                raise ValueError("Invalid question option")
    answers = {}
    for item in questions:
        print(f"\n[QUESTION {item['id']}] {item['question']}", flush=True)
        options = item.get("options") or []
        for index, option in enumerate(options, 1):
            print(f"  {index}. {option['label']} — {option.get('description', '')}", flush=True)
        print("输入选项编号或完整回答；/cancel 取消当前轮次。空输入不会选择任何选项。", flush=True)
        while True:
            value = read(f"[ANSWER {item['id']}] ").strip()
            if value == "/cancel":
                raise InputCancelled
            if not value:
                continue
            if options and value.isdecimal():
                if not 1 <= int(value) <= len(options):
                    continue
                value = options[int(value) - 1]["label"]
            answers[item["id"]] = {"answers": [value]}
            break
    return answers
