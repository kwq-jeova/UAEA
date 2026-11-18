"""Research-only integrity checks, no model/tool/API calls."""
from copy import deepcopy
import hashlib,json

def canonical(value):
 return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))

class SSEProgress:
 """Use genuine sequence/id, not a receipt counter; fallback dedups identical payload."""
 def __init__(self,policy,on_event=None):
  self.on_event=on_event;self.policy=policy;self.buffers={};self.seen={}
 def feed(self,request_id,chunk):
  data=self.buffers.get(request_id,b"")+chunk
  # JSON payloads escape newlines; normalize SSE framing only.
  data=data.replace(b"\r\n",b"\n")
  blocks=data.split(b"\n\n");self.buffers[request_id]=blocks.pop()
  for block in blocks:
   payload=b"\n".join(l[5:].lstrip()for l in block.splitlines()if l.startswith(b"data:"))
   if not payload or payload==b"[DONE]":continue
   try:event=json.loads(payload)
   except (ValueError,UnicodeDecodeError):continue
   frame_ids=[l[3:].strip().decode("utf-8")for l in block.splitlines()if l.startswith(b"id:")]
   if type(event.get("sequence_number"))is int:
    identity=(str(request_id),"sequence",str(event["sequence_number"]))
   elif frame_ids:
    identity=(str(request_id),"id",frame_ids[-1])
   elif isinstance(event.get("event_id"),str):
    identity=(str(request_id),"event_id",event["event_id"])
   else:
    # No stable upstream identity: conservative dedup, never poll-time/arrival ordinal.
    identity=(str(request_id),"payload_sha256",hashlib.sha256(canonical(event).encode()).hexdigest())
   fingerprint=hashlib.sha256(canonical(event).encode()).hexdigest()
   if identity in self.seen:
    if self.seen[identity]!=fingerprint:raise ValueError("SSE_EVENT_IDENTITY_CONFLICT")
    continue
   self.seen[identity]=fingerprint;kind=event.get("type","")
   if self.on_event is not None:self.on_event(request_id,event)
   if kind.endswith(".delta")and event.get("delta"):
    self.policy.note_progress("output_delta",canonical(identity),event)
   elif kind=="response.completed":
    self.policy.note_progress("provider_completed",canonical(identity),event)
   elif kind=="response.output_item.done":
    self.policy.note_progress("native_item_completed",canonical(identity),event)

def build_call_cache(native_rows,host_rows):
 """Bind every original Call+receipt independently, including Native-only archives."""
 cached={}
 keys=("threadId","turnId","tool","arguments")
 def put(cid,params=None,result=None):
  if not isinstance(cid,str)or not cid:raise ValueError("CALL_ID_MISSING")
  entry=cached.setdefault(cid,{})
  if params is not None:
   if "params"in entry and any(params.get(k)!=entry["params"].get(k)for k in keys):
    raise ValueError("HISTORICAL_PARAMS_CONFLICT")
   entry["params"]=deepcopy(params)
  if result is not None:
   if "result"in entry and result!=entry["result"]:raise ValueError("HISTORICAL_RESULT_CONFLICT")
   entry["result"]=deepcopy(result)
 for row in native_rows:
  m=row.get("message",{});p=m.get("params",{});item=p.get("item",{})
  if m.get("method")=="item/tool/call":put(p.get("callId"),params=p)
  if m.get("method")=="item/completed"and item.get("type")=="dynamicToolCall":
   cid=item.get("id")
   if cid not in cached or "params"not in cached[cid]:raise ValueError("NATIVE_RECEIPT_WITHOUT_CALL")
   original=cached[cid]["params"]
   if any(p.get(k)!=original.get(k)for k in ("threadId","turnId")):
    raise ValueError("NATIVE_RECEIPT_SCOPE_CONFLICT")
   if item.get("tool") is not None and item.get("tool")!=original.get("tool"):raise ValueError("NATIVE_RECEIPT_TOOL_CONFLICT")
   if "arguments"in item and item["arguments"]!=original.get("arguments"):raise ValueError("NATIVE_RECEIPT_ARGUMENTS_CONFLICT")
   put(cid,result={"success":item["success"],"contentItems":item["contentItems"]})
 for row in host_rows:
  cid=row.get("call_id");params=row.get("params")
  if cid not in cached or not isinstance(params,dict):raise ValueError("HOST_RESULT_WITHOUT_NATIVE_CALL")
  put(cid,params=params,result=row["result"])
 return cached

def started_turn_id(messages,request_id):
 ids={str(m["result"]["turn"]["id"])for m in messages if m.get("id")==request_id and isinstance(m.get("result"),dict)and isinstance(m["result"].get("turn"),dict)and m["result"]["turn"].get("id")}
 if len(ids)!=1:raise ValueError("CURRENT_TURN_START_ACK_UNVERIFIED")
 return ids.pop()

def checked_delivery(messages, thread_id, turn_id):
    """Accept a completed Turn and its user-facing final message, with legacy fallback."""
    result = {"terminal_confirmed": False, "native_status": "unconfirmed",
              "delivery_complete": False, "answers": [], "reason": "current_turn_terminal_missing"}
    if not thread_id or not turn_id:
        return result
    terminals = [(i, m["params"]["turn"]) for i, m in enumerate(messages)
                 if m.get("method") == "turn/completed"
                 and m.get("params", {}).get("threadId") == thread_id
                 and m["params"].get("turn", {}).get("id") == turn_id]
    if not terminals:
        return result
    if len({t.get("status") for _, t in terminals}) != 1:
        raise ValueError("CURRENT_TURN_TERMINAL_CONFLICT")
    end, terminal = terminals[-1]
    result.update(terminal_confirmed=True, native_status=terminal.get("status"))
    if terminal.get("status") != "completed":
        result["reason"] = "current_turn_not_completed"
        return result

    items = [m["params"]["item"] for m in messages[:end]
             if m.get("method") == "item/completed"
             and m.get("params", {}).get("threadId") == thread_id
             and m["params"].get("turnId") == turn_id and "item" in m["params"]]
    snapshot = terminal.get("items") or []
    def user_message(item):
        return item.get("type") == "agentMessage" and item.get("delivery") != "async"

    explicit = [item for item in items + snapshot
                if user_message(item) and item.get("phase") == "final_answer"]
    if explicit:
        item = explicit[-1]
        basis = "explicit_final_answer"
    else:
        candidates = snapshot or items
        item = candidates[-1] if candidates else {}
        if not user_message(item) or item.get("phase") is not None:
            result["reason"] = "current_turn_user_final_missing"
            return result
        basis = "legacy_phase_unknown_terminal_tail"
    # Reconcile copies of the selected item under either phase convention.
    # A repeated terminal snapshot may itself carry a conflicting copy.
    selected_id = item.get("id")
    if selected_id:
        copies = items + [copy for _, t in terminals for copy in (t.get("items") or [])]
        for copy in copies:
            if copy.get("id") != selected_id:
                continue
            if (not user_message(copy) or copy.get("text") != item.get("text")
                    or copy.get("phase") not in (None, "final_answer")):
                result["reason"] = "current_turn_final_item_conflict"
                return result
    answer = item.get("text")
    if not isinstance(answer, str) or not answer.strip():
        result["reason"] = "current_turn_final_body_empty_or_missing"
        return result
    result.update(delivery_complete=True, answers=[answer], reason=basis, item_id=item.get("id"))
    return result
