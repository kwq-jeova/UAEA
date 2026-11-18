"""Research-driver gate between Native termination and complete model delivery."""
import hashlib


def _body_key(message):
    if message.get("type") != "message" or message.get("role") != "assistant":
        return None
    body = "".join(part["text"] for part in message.get("content", [])
                   if part.get("type") == "output_text" and isinstance(part.get("text"), str))
    return (message.get("id"), hashlib.sha256(body.encode()).digest())


class UpstreamDelivery:
    def __init__(self):
        self.messages = {}
        self.terminals = {}

    def observe(self, request_id, event):
        kind = event.get("type")
        if kind == "response.output_item.done":
            key = _body_key(event.get("item") or {})
            if key:
                self.messages.setdefault(request_id, set()).add(key)
        if kind in ("response.completed", "response.incomplete", "response.failed"):
            response = event.get("response") or {}
            # Some versions only emit the actual items in output_item.done.
            output = {key for item in response.get("output") or [] if (key := _body_key(item))}
            status = response.get("status")
            details = response.get("incomplete_details") or {}
            self.terminals.setdefault(request_id, set()).add(
                (kind, status, details.get("reason"), frozenset(output)))

    def classify(self, native, request_id):
        if not native["delivery_complete"]:
            return native
        terminals = self.terminals.get(request_id, set())
        updated = dict(native, upstream_request_id=request_id)
        failure = "upstream_terminal_unverified"
        if len(terminals) == 1:
            kind, status, detail, final_messages = next(iter(terminals))
            updated.update(upstream_status=status, upstream_incomplete_reason=detail)
            if status == "incomplete":
                failure = "upstream_incomplete"
            elif kind == "response.completed" and status == "completed":
                expected = (native["item_id"], hashlib.sha256(native["answers"][-1].encode()).digest())
                if expected in (final_messages or self.messages.get(request_id, set())):
                    return updated
                failure = "upstream_final_message_unverified"
        updated.update(delivery_complete=False, partial_answers=native["answers"],
                       answers=[], reason=failure)
        return updated
