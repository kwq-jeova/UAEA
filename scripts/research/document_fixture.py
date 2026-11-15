"""Research-only HTML snapshots -> numbered sections, preserving source table cells.

No semantic ranking or question-specific passage selection. Original HTML is
canonical; the manifest records each table/row/cell, span and derived range.
"""
from dataclasses import dataclass, field
from html.parser import HTMLParser
from hashlib import sha256
import json
from pathlib import Path
import re

SKIP = {"script", "style", "nav", "header", "footer", "noscript", "form"}
VOID = {"br", "hr", "img", "meta", "link", "input", "source", "wbr", "area", "base", "embed"}


@dataclass
class Node:
    tag: str
    attrs: dict
    position: tuple
    children: list = field(default_factory=list)


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", {}, (1, 0))
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), self.getpos())
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def nodes(node):
    yield node
    for child in node.children:
        if isinstance(child, Node):
            yield from nodes(child)


def text(node):
    if isinstance(node, str):
        return node
    if node.tag in SKIP:
        return ""
    value = "".join(text(x) for x in node.children)
    return value + (" " if node.tag in {"p", "div", "br", "li"} else "")


def normalized(node):
    return " ".join(text(node).split())


def article_root(root):
    candidates = list(nodes(root))
    # Real structural containers, independent of company, metric or task.
    for node in candidates:
        if node.tag == "article":
            return node
    for node in candidates:
        if "module-news-details" in node.attrs.get("class", "").split():
            return node
    raise ValueError("No auditable article container; do not guess body scope")


def own_rows(table):
    def visit(node):
        for child in node.children:
            if not isinstance(child, Node) or child.tag == "table":
                continue
            if child.tag == "tr":
                yield child
            else:
                yield from visit(child)
    return list(visit(table))


def cells(row):
    result = []
    for child in row.children:
        if isinstance(child, Node):
            if child.tag in {"td", "th"}:
                result.append({"text": normalized(child),
                               "colspan": int(child.attrs.get("colspan", "1")),
                               "rowspan": int(child.attrs.get("rowspan", "1")),
                               "tag": child.tag, "html_position": child.position})
            else:
                result.extend(cells(child))
    return result


def row_text(index, values):
    # Keep original cell order; spans are explicit rather than guessed as new values.
    fields = []
    for cell in values:
        value = cell["text"].replace("|", "\\|")
        span = []
        if cell["colspan"] != 1:
            span.append("colspan=" + str(cell["colspan"]))
        if cell["rowspan"] != 1:
            span.append("rowspan=" + str(cell["rowspan"]))
        fields.append(value + (" [" + ",".join(span) + "]" if span else ""))
    return "r" + str(index) + " | " + " | ".join(fields)


def render_snapshot(html, *, url, captured_utc, title, max_part_chars=6000):
    tree = Tree(); tree.feed(html)
    root = article_root(tree.root)
    raw_hash = sha256(html.encode()).hexdigest()
    blocks = []
    def walk(node):
        if node.tag in SKIP:
            return
        if node.tag == "table":
            rows = [{"index": i, "cells": cells(row)} for i, row in enumerate(own_rows(node), 1)]
            rows = [row for row in rows if any(c["text"] for c in row["cells"])]
            if rows:
                blocks.append(("table", rows, node.position))
            return
        if node.tag in {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            value = normalized(node)
            if value:
                blocks.append(("text", value, node.position))
            return
        for child in node.children:
            if isinstance(child, Node):
                walk(child)
    walk(root)
    sections = []
    tables = []
    paragraphs = []
    last_text = ""
    recent_texts = []
    def add(name, body, provenance):
        suffix = re.search(r" / part \d+$", name)
        shown = name if len(name) <= 180 else (name[:180] if not suffix else name[:160] + suffix.group(0))
        sections.append({"name": shown, "body": body, "provenance": provenance})
    def flush():
        if paragraphs:
            first = paragraphs[0][0]
            add("Text — " + first[:100], "\n\n".join(x[0] for x in paragraphs),
                {"kind": "original_paragraphs", "html_positions": [x[1] for x in paragraphs]})
            paragraphs.clear()
    for kind, value, position in blocks:
        if kind == "text":
            if sum(len(x[0]) + 2 for x in paragraphs) + len(value) > max_part_chars:
                flush()
            # A long single original paragraph remains explicitly one section.
            paragraphs.append((value, position)); last_text = value
            recent_texts.append(value)
            continue
        flush()
        ordinal = len(tables) + 1
        rows = value
        tables.append({"table": ordinal, "html_position": position, "rows": rows})
        context = rows[:min(12, len(rows))]
        nearby = recent_texts[-1:] if recent_texts and len(recent_texts[-1]) < 200 else []
        if nearby and nearby[0].startswith("("):
            for value in reversed(recent_texts[:-1]):
                if not value.isupper() or len(nearby) == 3:
                    break
                nearby.insert(0, value)
        table_titles = []
        for row in rows[:6]:
            nonempty = [c["text"] for c in row["cells"] if c["text"]]
            if len(nonempty) != 1 or not any(char.isalpha() for char in nonempty[0]):
                break
            table_titles.extend(nonempty)
        heading = " / ".join(nearby + [x for x in table_titles if x not in nearby]) or "original source table"
        recent_texts.clear()
        prefix = ("Original table " + str(ordinal) +
                  "; rN is original HTML row index; cells/spans remain in source order.\n")
        # Splitting preserves leading context, including units and multirow headers.
        context_text = "\n".join(row_text(row["index"], row["cells"]) for row in context)
        remaining = rows
        part = 1
        while remaining:
            lead = prefix + (("Repeated original context rows:\n" + context_text + "\n") if part > 1 else "")
            chosen = []
            while remaining:
                candidate = row_text(remaining[0]["index"], remaining[0]["cells"])
                if chosen and len(lead) + sum(len(x[1]) + 1 for x in chosen) + len(candidate) > max_part_chars:
                    break
                row = remaining[0]; remaining = remaining[1:]
                chosen.append((row["index"], candidate))
            add("Table " + str(ordinal) + " — " + heading + " / part " + str(part),
                lead + "\n".join(x[1] for x in chosen),
                {"kind": "original_table_rows", "table": ordinal, "rows": [x[0] for x in chosen],
                 "repeated_context_rows": [x["index"] for x in context] if part > 1 else [],
                 "html_position": position})
            part += 1
    flush()
    guide = ("This is a directory, not evidence that any financial body was read.\n"
             "Use the returned section_catalog to choose original text/table sections.\n"
             "Table parts repeat original leading rows for unit/period/column context; repeats are labelled.\n"
             "An incomplete document_projection does not establish missing facts.\n"
             "Source URL: " + url + "\nCaptured UTC: " + captured_utc + "\nRaw HTML SHA256: " + raw_hash)
    sections.insert(0, {"name": "Directory and provenance", "body": guide, "provenance": {"kind": "derived_directory"}})
    output = "# 1. " + title + "\n\n"
    for i, section in enumerate(sections, 1):
        section["section_index"] = i + 1
        section["line_start"] = output.count("\n") + 1
        output += "## " + str(i + 1) + ". " + section["name"] + "\n\n" + section["body"] + "\n\n"
        section["body_sha256"] = sha256(section["body"].encode()).hexdigest()
    return output, {"raw_html_sha256": raw_hash, "root_position": root.position,
                    "root_tag": root.tag, "sections": sections, "tables": tables,
                    "semantic_interpretation": False}


def prepare(source_html, capture_json, output, manifest):
    html = Path(source_html).read_bytes().decode("utf-8")
    capture = json.loads(Path(capture_json).read_text())
    if sha256(html.encode()).hexdigest() != capture["sha256"]:
        raise ValueError("Raw source capture hash mismatch")
    body, mapping = render_snapshot(html, url=capture["url"], captured_utc=capture["captured_UTC"],
                                    title=Path(source_html).stem + " official release")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(body)
    Path(manifest).write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n")
