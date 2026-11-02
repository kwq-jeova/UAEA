"""Local, redacted HTTP-boundary audit. Never edits the forwarded body."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from uuid import uuid4

_SECRET_KEY = re.compile(r"(?:authorization|cookie|password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|(?:^|_)(?:token|credentials?|private_key|client_secret|bearer)(?:$|_))", re.I)
_SECRET_TEXT = re.compile(r"""(?i)(bearer\s+)[^\s"']+|\b(?:sk-|hf_)[A-Za-z0-9_-]{8,}|((?:api[_-]?key|password|access_token)\s*[=:]\s*)[^\s&"']+""")
_SCHEMA = "uaea.model_http_audit.v1"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def redact(value, secrets=()):
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if _SECRET_KEY.search(k)
                    and not (k.lower() == "authorization" and isinstance(v, dict))
                    else redact(v, secrets)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secrets) for v in value]
    if isinstance(value, str):
        try:
            structured = json.loads(value)
        except (ValueError, TypeError):
            structured = None
        if isinstance(structured, (dict, list)):
            return json.dumps(redact(structured, secrets), ensure_ascii=False)
        def tagged(match):
            try:
                data = json.loads(match.group(2))
            except ValueError:
                return match.group(0)
            return "<" + match.group(1) + ">" + json.dumps(redact(data, secrets), ensure_ascii=False) + "</" + match.group(1) + ">"
        value = re.sub(r"<([A-Za-z_][\w.]*)>(.*?)</\1>", tagged, value, flags=re.S)
        # Structured data is often carried inside function outputs and Context tags.
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return _SECRET_TEXT.sub(lambda m: (m.group(1) or m.group(2) or "") + "[REDACTED]", value)
    return value


def message_manifest(request):
    """Describe sequence/identity independently of provider-specific role rendering."""
    rows = []
    for field in ("input", "previous_input_messages"):
        items = request.get(field, [])
        if not isinstance(items, list):
            items = [{"type": "input_text", "text": items}]
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                rows.append({"field": field, "index": index, "type": type(item).__name__})
                continue
            text = json.dumps(item, ensure_ascii=False)
            versions = []
            blocks = []
            texts = [part.get("text", "") for part in item.get("content", [])
                     if isinstance(part, dict)] if isinstance(item.get("content"), list) else []
            for content in texts:
                for match in re.finditer(r"<((?:external_)?uaea\.[\w.]+)>(.*?)</\1>", content, re.S):
                    try:
                        state = json.loads(match.group(2))
                    except ValueError:
                        continue
                    blocks.append({"key": match.group(1),
                                   "chars": len(match.group(2)),
                                   "value_sha256": digest(match.group(2).encode())})
                    if "effective_state_id" in state:
                        versions.append({k: state.get(k) for k in ("task_id", "effective_state_id")})
            rows.append({"field": field, "index": index, "type": item.get("type", "message"),
                         "role": item.get("role"), "call_id": item.get("call_id"),
                         "name": item.get("name"), "context_blocks": blocks, "state_versions": versions,
                         "item_sha256": digest(text.encode())})
    return rows


class RequestAudit:
    def __init__(self, path, *, max_snapshot_bytes=2*1024*1024):
        self.path = Path(path)
        self.max_snapshot_bytes = max_snapshot_bytes
        self._lock = threading.Lock()
        self._secrets = tuple(v for k, v in os.environ.items()
                              if re.search(r"TOKEN|PASSWORD|SECRET|API_KEY|CREDENTIAL", k, re.I) and len(v) >= 6)

    def write(self, event):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # O_NOFOLLOW avoids accidentally following a pre-existing journal symlink.
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        with self._lock:
            fd = os.open(self.path, flags, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as stream:
                os.chmod(self.path, 0o600)
                stream.write(json.dumps(redact(event, self._secrets), ensure_ascii=False) + "\n")
                stream.flush()

    def request(self, original, forwarded, *, path, sequence, decisions):
        identity = str(uuid4())
        payload = json.loads(forwarded)
        clean = redact(payload, self._secrets)
        encoded = json.dumps(clean, ensure_ascii=False).encode()
        covered = len(encoded) <= self.max_snapshot_bytes
        self.write({"schema": _SCHEMA, "event": "request_prepared", "request_id": identity,
                    "utc": time.time(), "sequence": sequence, "path": path.split("?", 1)[0],
                    "boundary": "bridge_http_outbound_not_server_tokenized_input",
                    "original_bytes_sha256": digest(original),
                    "forwarded_bytes_sha256": digest(forwarded),
                    "history_projection_decisions": len(decisions),
                    "snapshot_coverage": "redacted_complete" if covered else "manifest_only_size_limit",
                    "redaction_scope": "credential keys/patterns and known credential environment values; not general PII",
                    "request": clean if covered else None,
                    "snapshot_is_wire_bytes": False,
                    "manifest_hash_basis": "forwarded_original_items_before_redaction",
                    "message_manifest": message_manifest(payload)})
        return identity

    def response(self, identity, *, status=None, bytes_received=0, error=None):
        self.write({"schema": _SCHEMA, "event": "transport_result", "request_id": identity,
                    "utc": time.time(), "http_status": status, "bytes_received": bytes_received,
                    "transport_error": error,
                    "model_understanding": "not_established"})
