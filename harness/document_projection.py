"""Budgeted document receipts. Pure projection; source and execution facts stay immutable."""
from copy import deepcopy
from hashlib import sha256
import json


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, default=str)


def _size(text):
    return len(text.encode("utf-8"))


def bounded_document_receipt(payload, budget):
    """Preserve exact line-bounded source text, identity and explicit omissions.

    read_file is also the existing catalogue discovery capability. Its directory
    receives at most half the receipt budget. read_section prioritizes the
    selected body; an oversized directory cannot evict that body.
    The configured character ceiling is also a conservative UTF-8 byte ceiling,
    preventing a later Native byte truncation from invalidating visible hashes.
    """
    original = payload["data"]
    content = original["content"]
    catalog = original.get("section_catalog", [])
    if not isinstance(catalog, list):
        catalog = []
    result = deepcopy(payload)
    data = result["data"]
    data.pop("content", None)
    data.pop("section_catalog", None)
    # The duplicate display string is not source or authority. Raw trace is unchanged.
    result["message"] = str(result.get("message", ""))[:160]
    full_hash = sha256(content.encode("utf-8")).hexdigest()

    def render(end, entries):
        visible = content[:end]
        data["content"] = visible
        data["section_catalog"] = entries
        data["document_projection"] = {
            "schema": "uaea.document_projection.v1",
            "budget_utf8_bytes": budget,
            "scope": "selected_section" if payload["capability"] == "document.read_section" else "full_document",
            "original_content_chars": len(content),
            "original_content_sha256": full_hash,
            "visible_start_char": 0,
            "visible_end_char": end,
            "visible_content_sha256": sha256(visible.encode("utf-8")).hexdigest(),
            "content_complete": end == len(content),
            "omitted_content_chars": len(content) - end,
            "truncation_reason": None if end == len(content) else "tool_result_budget",
            "catalog_total": len(catalog),
            "catalog_supplied": len(entries),
            "catalog_complete": len(entries) == len(catalog),
            "catalog_omitted": len(catalog) - len(entries),
        }
        return _encoded(result)

    # Full source + full catalogue if it fits, including the visibility contract.
    text = render(len(content), catalog)
    if _size(text) <= budget:
        return text
    # Preserve legacy small receipts that fit in full. There is no omission to
    # annotate; original size/content hash still describe exactly the supplied text.
    plain = _encoded(payload)
    if _size(plain) <= budget:
        return plain
    entries = []
    selected = []
    if payload["capability"] == "document.read_file":
        for item in catalog:
            proposed = entries + [item]
            if _size(_encoded(proposed)) > budget // 2 or _size(render(0, proposed)) > budget:
                break
            entries = proposed
    else:
        selected = [item for item in catalog if isinstance(item, dict)
                    and item.get("section_index") == original.get("section_index")][:1]

    # Completeness metadata is shorter than a truncation reason: test the full
    # body explicitly, rather than assuming its encoded size is monotonic.
    text = render(len(content), entries)
    if _size(text) <= budget:
        if selected and _size(render(len(content), selected)) <= budget:
            return render(len(content), selected)
        return text
    if _size(render(0, entries)) > budget:
        raise ValueError("Document result identity/contract exceeds projection budget")

    # Do not split a table row, date, currency, JSON escape, or Unicode character.
    # A line longer than the entire budget remains unavailable rather than
    # pretending an arbitrary prefix is a complete row.
    ends = [0] + [i + 1 for i, char in enumerate(content) if char == "\n"]
    if ends[-1] != len(content):
        ends.append(len(content))
    low, high = 0, max(0, len(ends) - 2)
    while low < high:
        mid = (low + high + 1) // 2
        if _size(render(ends[mid], entries)) <= budget:
            low = mid
        else:
            high = mid - 1
    text = render(ends[low], entries)
    if _size(text) > budget:
        raise ValueError("Document projection exceeds result budget")
    return text
