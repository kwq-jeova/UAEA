"""Opt-in local research Goal continuity. Journal is the sole candidate authority.
Not a Runtime/Workflow checkpoint, Memory store, adoption path or Agent Loop.
Linux/WSL single-writer lease; incomplete/corrupt journals fail closed.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import fcntl, hashlib, json, os, time
from harness.goal_integration import digest
from runtime.runtime_objects import RuntimeObjectRecord
from research.goal_hypothesis import GoalResearch, candidate_head
from research.goal_hypothesis_audit import record_binding

def need(ok, message):
    if not ok: raise ValueError(message)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def lines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]

def verified_observations(trajectory, native, steps):
    """Exact historical Observation/Step/Call/receipt identity, never just self-hashes."""
    calls = {}
    receipts = {}
    for row in native:
        m = row.get("message", {})
        if m.get("method") == "item/tool/call":
            c = m["params"]; cid = c["callId"]
            need(cid not in calls or calls[cid] == c, "Conflicting execution Call ID")
            calls[cid] = c
        if m.get("method") == "item/completed":
            p = m["params"]; it = p.get("item", {})
            if it.get("type") == "dynamicToolCall":
                receipts[(p["threadId"], p["turnId"], it["id"])] = it
    decisions = {}
    observed = {}
    for row in trajectory:
        if row["event_type"] == "EXECUTION_DECISION":
            key = row["identity"]["item_id"]
            need(key not in decisions or decisions[key] == row, "Conflicting decision")
            decisions[key] = row
        elif row["event_type"] == "OBSERVATION":
            oid = row["payload"]["execution_observation"]["observation_id"]
            need(oid not in observed or observed[oid] == row, "Conflicting Observation")
            observed[oid] = row
    step_map = {x["execution_observation_id"]: x for x in steps if x["execution_observation_id"]}
    need(len(step_map) == sum(bool(x["execution_observation_id"]) for x in steps),
         "Duplicate Step/Observation binding")
    need(set(step_map) == set(observed), "Unbound historical Step/Observation")
    result = {}
    for oid, row in observed.items():
        identity = row["identity"]; cid = identity["item_id"]
        o = row["payload"]["execution_observation"]; d = row["payload"]["decision"]
        need(cid in decisions and decisions[cid]["payload"] == d and cid in calls,
             "Observation not bound to actual decision/Call")
        c = calls[cid]; st = step_map[oid]; h = st["action"]["harness"]
        need(c["threadId"] == identity["thread_id"] == decisions[cid]["identity"]["thread_id"]
             and c["turnId"] == identity["turn_id"] == decisions[cid]["identity"]["turn_id"] == h["turn_id"]
             and h["call_id"] == cid == d["action_id"]
             and st["workflow_id"] == d["workflow_id"] and h["input_id"] == d["input_id"]
             and st["action"]["execution_contract"] == d
             and st["action"]["arguments"] == c["arguments"] == d["proposed_parameters"],
             "Step/Observation execution ownership mismatch")
        it = receipts.get((c["threadId"], c["turnId"], cid))
        need(it and it["status"] in ("completed", "failed"), "Native execution receipt absent")
        raw_receipt = it["contentItems"][0]["text"]
        receipt = json.loads(raw_receipt)
        need(receipt["identity"] == {"thread_id": c["threadId"], "turn_id": c["turnId"],
             "call_id": cid, "observation_id": oid}, "Native execution identity mismatch")
        host = st["action"]["host_execution_receipt"]
        need(host["execution_observation"] == o, "Step/trajectory Observation differs")
        from runtime.semantic_observation import ExecutionObservation as RecordedObservation
        full_data = host["result"]["data"]
        reconstructed = RecordedObservation(o["observation_id"], o["capability"], o["tool_name"],
            o["status"], o["message"], deepcopy(full_data)).to_event_metadata()
        need(reconstructed == o, "Canonical excerpt differs from original Host result")
        if isinstance(full_data.get("content"), str) and "content_hash" in full_data:
            need(hashlib.sha256(full_data["content"].encode()).hexdigest() == full_data["content_hash"],
                 "Full Host result body hash mismatch")
        # Reuse actual serializer, including truthful errors and explicit budget truncation.
        # This is deterministic receipt validation, not tool execution/replay.
        from harness.codex_dynamic_tools import HarnessToolDispatch, ActionRequest, ToolResult, ExecutionObservation
        dispatch = HarnessToolDispatch(c["threadId"], c["turnId"], cid, c["tool"],
            ActionRequest(o["capability"], deepcopy(c["arguments"]), request_id=cid),
            ToolResult(**{k: deepcopy(host["result"][k]) for k in ("ok", "message", "data")}), ExecutionObservation(**deepcopy(o)),
            semantic_validation=deepcopy(st["action"].get("validation")),
            max_output_chars=len(raw_receipt), execution_decision=deepcopy(d))
        expected = dispatch.to_app_server_response()
        need(json.loads(expected["contentItems"][0]["text"]) == receipt,
             "Observation/Native original result projection mismatch")
        result[oid] = deepcopy(o)
    return result

class ContinuityJournal:
    """One local profile, no independently editable state snapshot."""
    def __init__(self, root, *, create=False):
        self.root = Path(root).resolve()
        if create: self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        need(self.root.is_dir(), "Continuity directory missing")
        self.path = self.root / "goal-journal.jsonl"
        self.lock = (self.root / "writer.lock").open("a+b")
        try: fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.lock.close()
            raise ValueError("Continuity writer already active")
        try:
            if not self.path.exists():
                need(create, "Continuity journal missing; no empty-state fallback")
                self._write_initial()
            self.reload()
        except BaseException:
            self.close()
            raise

    def __enter__(self): return self
    def __exit__(self, *args): self.close()
    def close(self):
        if not self.lock.closed:
            fcntl.flock(self.lock.fileno(), fcntl.LOCK_UN); self.lock.close()

    def _write_initial(self):
        data = self._envelope("INIT", {"profile": self.root.name}, 1, "")
        with self.path.open("xb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        self._sync_dir()

    def _sync_dir(self):
        fd = os.open(self.root, os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)

    @staticmethod
    def _envelope(kind, payload, seq, previous):
        row = {"schema": "uaea.research_goal_continuity.v1", "seq": seq,
               "previous_sha256": previous, "kind": kind, "payload": payload}
        row["sha256"] = digest(row)
        return (json.dumps(row, ensure_ascii=False) + "\n").encode()

    def reload(self):
        self.valid = False
        raw = self.path.read_bytes()
        need(raw and raw.endswith(b"\n") and len(raw) <= 16 * 2**20,
             "Incomplete/oversized continuity journal; refuse recovery")
        self.entries = []
        previous = ""
        for i, line in enumerate(raw.splitlines(), 1):
            row = json.loads(line)
            expected = row.pop("sha256")
            need(row["schema"] == "uaea.research_goal_continuity.v1" and row["seq"] == i
                 and row["previous_sha256"] == previous and digest(row) == expected,
                 "Continuity sequence/hash mismatch")
            row["sha256"] = expected; self.entries.append(row); previous = expected
        need(self.entries[0]["kind"] == "INIT", "Continuity INIT absent")
        self._reduce()
        self.valid = True

    def _reduce(self):
        self.inputs = {}; self.observations = {}; self.observation_bindings = {}; self.versions = {}
        self.families = {}; self.bindings = {}; self.handled = {}; self.failures = {}
        self.imports = set(); self.events = []; self.origins = {}
        for row in self.entries[1:]:
            p = row["payload"]; kind = row["kind"]
            if kind == "IMPORT":
                need(p["bundle_sha256"] not in self.imports, "Duplicate import entry")
                self.imports.add(p["bundle_sha256"])
                self._sources(p)
                for item in p["events"]: self._event(item["event"], item.get("call"))
                for root, binding in p["bindings"].items():
                    need(root in self.versions and self.families[root] == root
                         and binding["kind"] in ("global", "local")
                         and binding["origin_thread"] == self.versions[root]["metadata"]["thread_id"],
                         "Invalid explicit family scope")
                    self.bindings[root] = binding
            elif kind == "EVENT":
                self._sources(p); self._event(p["event"], p.get("call"))
            elif kind == "BIND":
                root = p["family"]
                need(root in self.bindings and self.families[root] == root
                     and p["kind"] in ("global", "local") and p["basis"],
                     "Invalid explicit scope binding")
                self.bindings[root] = {"kind": p["kind"],
                    "origin_thread": self.versions[root]["metadata"]["thread_id"],
                    "basis": p["basis"]}
            elif kind == "ANNOTATION":
                need(p["failure_class"] in ("none", "store", "projection", "semantics",
                     "reference", "conceptual", "unknown"), "Invalid research failure category")
            else: raise ValueError("Unsupported continuity entry")
        need(all(root in self.bindings for root in set(self.families.values())),
             "Family scope missing")

    def _sources(self, p):
        for record in p.get("inputs", []):
            key = record["object_id"]; m = record["metadata"]
            need(record["object_type"] == "workflow_request_input"
                 and m["input_id"] == key and m["raw_text_sha256"] == hashlib.sha256(m["text"].encode()).hexdigest()
                 and m["host_input_origin"] == {"channel": "registered_user_entry", "input_id": key,
                                               "raw_text_sha256": m["raw_text_sha256"]},
                 "Original input identity/hash mismatch")
            need(key not in self.inputs or self.inputs[key] == record, "Input identity reused")
            self.inputs[key] = deepcopy(record)
        for oid, observation in p.get("observations", {}).items():
            need(observation["observation_id"] == oid, "Observation identity mismatch")
            data = observation["data"]
            if "content_excerpt" in data:
                excerpt = data["content_excerpt"]
                need(isinstance(excerpt, str) and type(data["content_length"]) is int
                     and data["content_length"] >= len(excerpt), "Observation excerpt extent mismatch")
                if data["content_length"] == len(excerpt):
                    need(hashlib.sha256(excerpt.encode()).hexdigest() == data["content_hash"],
                         "Complete Observation body mismatch")
            need(oid not in self.observations or self.observations[oid] == observation,
                 "Observation identity reused")
            self.observations[oid] = deepcopy(observation)
        for oid, binding in p.get("observation_bindings", {}).items():
            need(oid in self.observations and (oid not in self.observation_bindings
                 or self.observation_bindings[oid] == binding), "Observation binding conflict")
            self.observation_bindings[oid] = deepcopy(binding)
        for k, origin in p.get("origins", {}).items():
            if k in self.origins:
                need(self.origins[k]["path"] == origin["path"], "Origin identity reused")
            else: self.origins[k] = origin

    def _event(self, event, call):
        need(event["mode"] == "shadow" and event["changes_tool_authorization"] is False
             and event["completes_workflow"] is False and event["writes_memory"] is False,
             "Authority-bearing event forbidden")
        p = event["payload"]; name = event["event"]
        need(name in ("RESEARCH_GOAL_VERSION", "RESEARCH_GOAL_REJECTED",
             "RESEARCH_GOAL_TURN", "RESEARCH_GOAL_PUBLICATION", "RESEARCH_GOAL_SNAPSHOT_FAILED"),
             "Unsupported Goal event type")
        if name == "RESEARCH_GOAL_VERSION":
            record = p["record"]; cid = record["object_id"]
            source = self.inputs.get(record["metadata"]["input_id"])
            need(source and call and source["metadata"]["provenance"]["thread_id"] == call["threadId"],
                 "Current input belongs to another Thread")
            originals = {k: {"text": r["metadata"]["text"], "sha256": r["metadata"]["raw_text_sha256"],
                            "owner": r["owner"], "native_turn_id": r["metadata"]["provenance"]["turn_id"]}
                         for k, r in self.inputs.items()}
            need(call and call["callId"] == p["call_id"] and call["threadId"] == event["thread_id"]
                 and record_binding(p, call, originals, self.versions, set(self.observations)),
                 "Accepted version/Native/input/parent binding invalid")
            parent_id = record["metadata"]["previous_candidate_id"]
            if parent_id:
                binding = self.bindings[self.families[parent_id]]
                need(binding["kind"] == "global" or binding["origin_thread"] == call["threadId"],
                     "Local family cannot cross Thread")
            key = (call["threadId"], call["turnId"], call["callId"])
            need(key not in self.handled and key not in self.failures, "Call identity already terminal")
            parent = record["metadata"]["previous_candidate_id"]
            family = self.families[parent] if parent else cid
            self.families[cid] = family
            self.versions[cid] = deepcopy(record); self.handled[key] = deepcopy(p["receipt"])
            if not parent and family not in self.bindings:
                self.bindings[family] = {"kind": "local", "origin_thread": call["threadId"],
                                         "basis": "new proposals default to originating session; not inferred long-term scope"}
        elif name == "RESEARCH_GOAL_REJECTED":
            need(call and p["call_id"] == call["callId"]
                 and p["turn_id"] == call["turnId"] and event["thread_id"] == call["threadId"]
                 and p["payload_sha256"] == digest(call["arguments"]), "Rejected Call binding invalid")
            key = (call["threadId"], call["turnId"], call["callId"])
            need(key not in self.handled, "Accepted call cannot become rejected")
            need(key not in self.failures or self.failures[key] == event, "Conflicting failed Call ID")
            self.failures[key] = deepcopy(event)
        self.events.append(deepcopy(event))

    def append(self, kind, payload):
        self.reload()
        data = self._envelope(kind, payload, len(self.entries) + 1, self.entries[-1]["sha256"])
        need(len(data) <= 2 * 2**20 and self.path.stat().st_size + len(data) <= 16 * 2**20,
             "Continuity journal research budget exhausted")
        # Validate the proposed entire reduction before writing any bytes.
        row = json.loads(data); old = self.entries
        try:
            self.entries = old + [row]; self._reduce()
        finally: self.entries = old; self._reduce()
        with self.path.open("ab") as f:
            n = f.write(data); need(n == len(data), "Short journal write")
            f.flush(); os.fsync(f.fileno())
        self.reload()
        return self.entries[-1]["sha256"]

    def visible(self, thread):
        need(self.valid, "Continuity recovery invalid; no partial view")
        return [deepcopy(r) for cid, r in self.versions.items()
                if self.bindings[self.families[cid]]["kind"] == "global"
                or self.bindings[self.families[cid]]["origin_thread"] == thread]

    def heads(self, thread):
        records = self.visible(thread)
        old = {r["metadata"]["previous_candidate_id"] for r in records}
        return [r for r in records if r["object_id"] not in old]

    def source_status(self, input_id):
        origin = self.origins.get(input_id)
        if not origin: return "original_native_record_unavailable"
        p = Path(origin["path"])
        try: raw = p.read_bytes()
        except OSError: return "original_native_record_unavailable"
        prefix = raw[:origin["bytes"]]
        return ("original_native_prefix_verified" if len(prefix) == origin["bytes"]
                and hashlib.sha256(prefix).hexdigest() == origin["sha256"]
                else "original_native_prefix_mismatch")

    def view(self, thread, budget=4200):
        heads = self.heads(thread)
        dossier = {"interpretations_only": True, "semantic_correctness": "not_established",
                   "is_source_evidence": False, "versions_immutable": True,
                   "active_goal_adoption_disabled": True, "restored_history_is_not_new_observation": True,
                   "current_thread_id": thread, "heads": [], "history": [], "sources": [],
                   "omitted_heads": 0, "omitted_history": 0, "omitted_sources": 0}
        chosen = list(reversed(heads))  # latest first; no semantic preference inferred
        for r in chosen[:3]:
            h = candidate_head(r); root = self.families[r["object_id"]]
            h.update(origin_thread=r["metadata"]["thread_id"], scope_binding=self.bindings[root],
                     current_interpretation_applicable=r["status"] != "withdrawn")
            dossier["heads"].append(h)
        dossier["omitted_heads"] = len(heads) - len(dossier["heads"])
        selected = {h["candidate_id"] for h in dossier["heads"]}
        required = []
        for cid in sorted(selected):
            chain = cid
            while chain:
                r = self.versions[chain]; m = r["metadata"]
                for iid in [m["input_id"]] + m["asserted_support_input_ids"]:
                    if iid not in required: required.append(iid)
                if chain != cid:
                    dossier["history"].append({"candidate_id": chain, "current": False,
                                              "candidate_sha256": digest(r), "hypothesis": m["hypothesis"]["hypothesis"]})
                chain = m["previous_candidate_id"]
        for iid in required:
            r = self.inputs[iid]; text = r["metadata"]["text"]
            dossier["sources"].append({"input_id": iid, "origin_thread": r["metadata"]["provenance"]["thread_id"],
                "text": text[:600], "text_complete": len(text) <= 600,
                "sha256": r["metadata"]["raw_text_sha256"], "source_status": self.source_status(iid),
                "CURRENT_requires_current_registered_request": True})
        while len(json.dumps(dossier, ensure_ascii=False)) > budget:
            if dossier["history"]:
                dossier["history"].pop(); dossier["omitted_history"] += 1
            elif dossier["sources"]:
                dossier["sources"].pop(); dossier["omitted_sources"] += 1
            elif dossier["heads"]:
                dossier["heads"].pop(); dossier["omitted_heads"] += 1
            else: raise ValueError("Continuity view cannot fit mandatory identity budget")
        return dossier

    def bind_scope(self, family, kind, basis):
        """Explicit local operator selection; never model inference or adoption."""
        return self.append("BIND", {"family": family, "kind": kind, "basis": basis})

    def annotate(self, text, *, failure_class="unknown", references=()):
        need(isinstance(text, str) and 0 < len(text) <= 4000, "Invalid annotation text")
        return self.append("ANNOTATION", {"text": text, "failure_class": failure_class,
            "references": list(references), "utc": time.time(), "is_Goal_or_authority": False})

def import_bundle(store, bundle_path, *, global_families=()):
    """Import only a previously audited evidence-closed bundle; recheck its raw records."""
    bundle_path = Path(bundle_path)
    bundle = json.loads(bundle_path.read_text())
    locks = bundle.get("all_source_hashes", {str(Path(bundle["source_root"])/k): v
                                            for k, v in bundle["source_hashes"].items()})
    need(locks and all(Path(k).is_file() and sha(k) == v for k, v in locks.items()),
         "Import original history missing/changed")
    native = []; journals = []
    roots = bundle.get("history_roots", [bundle["source_root"]])
    for root in roots:
        native += lines(Path(root)/"app-server-events.jsonl")
        journals += lines(Path(root)/"goal-events.jsonl")
    calls = {}
    for row in native:
        m = row.get("message", {})
        if m.get("method") == "item/tool/call":
            call = m["params"]; key = call["callId"]
            need(key not in calls or calls[key] == call, "Native Call ID conflict")
            calls[key] = call
    trajectory = []
    for path in locks:
        if Path(path).name == "execution-contract.trajectory.jsonl":
            trajectory += lines(path)
    observations = verified_observations(trajectory, native,
        bundle["snapshot"]["workflow_continuity"]["attempts"])
    need(observations == bundle["observations"], "Bundle Observation differs from raw execution history")
    observation_bindings = {}
    for st in bundle["snapshot"]["workflow_continuity"]["attempts"]:
        oid = st["execution_observation_id"]
        if oid:
            h = st["action"]["harness"]
            observation_bindings[oid] = {"call_id": h["call_id"], "turn_id": h["turn_id"],
                "thread_id": calls[h["call_id"]]["threadId"], "workflow_id": st["workflow_id"],
                "input_id": h["input_id"], "decision": st["action"]["execution_contract"]}
    need(observation_bindings == bundle.get("observation_bindings", observation_bindings), "Bundle Observation provenance differs")
    origins = {}
    for record in bundle["inputs"]:
        m = record["metadata"]; matches = []
        for root in roots:
            p = Path(root)/"app-server-events.jsonl"
            for row in lines(p):
                msg = row.get("message", {}); it = msg.get("params", {}).get("item", {})
                if msg.get("method") == "item/completed" and it.get("type") == "userMessage":
                    par = msg["params"]; text = "".join(c.get("text", "") for c in it["content"] if c.get("type") == "text")
                    if par["turnId"] == m["provenance"]["turn_id"] and par["threadId"] == m["provenance"]["thread_id"] and text == m["text"]:
                        matches.append(p)
        need(matches, "Original input absent from Native record")
        p = matches[0]; origins[record["object_id"]] = {"path": str(p), "bytes": p.stat().st_size, "sha256": sha(p)}
    for path in locks:
        if Path(path).name == "execution-contract.trajectory.jsonl":
            for row in lines(path):
                if row["event_type"] == "OBSERVATION":
                    oid = row["payload"]["execution_observation"]["observation_id"]
                    origins[oid] = {"path": path, "bytes": Path(path).stat().st_size, "sha256": sha(path)}
    events = []; seen = {}
    for event in journals:
        if event["event"] not in ("RESEARCH_GOAL_VERSION", "RESEARCH_GOAL_REJECTED"): continue
        p = event["payload"]; key = (event["event"], event["thread_id"], p["turn_id"], p["call_id"])
        if key in seen:
            need(seen[key] == event, "Conflicting duplicate historical Goal event")
            continue
        seen[key] = event; call = calls.get(p["call_id"])
        if event["event"] == "RESEARCH_GOAL_VERSION":
            need(p["record"] in bundle["versions"], "Bundle missing recorded version")
            completed = [x["message"]["params"]["item"] for x in native
                         if x.get("message", {}).get("method") == "item/completed"
                         and x["message"]["params"].get("item", {}).get("id") == p["call_id"]]
            need(completed, "Native accepted receipt missing")
            receipt = json.loads(completed[-1]["contentItems"][0]["text"])
            need(all(receipt.get(k) == p["receipt"][k] for k in
                     ("candidate_id","operation","committed","candidate_sha256","payload_sha256","ok")),
                 "Journal/Native receipt mismatch")
        events.append({"event": event, "call": call})
    need([x["event"]["payload"]["record"] for x in events
          if x["event"]["event"] == "RESEARCH_GOAL_VERSION"] == bundle["versions"],
         "Bundle contains versions not in original commit journal")
    roots_set = {r["object_id"] for r in bundle["versions"] if r["metadata"]["previous_candidate_id"] is None}
    need(set(global_families) <= roots_set, "Global scope must name explicit original family roots")
    bindings = {r["object_id"]: {"kind": "global" if r["object_id"] in global_families else "local",
        "origin_thread": r["metadata"]["thread_id"], "basis": "explicit research operator binding, not adoption or model inference"}
        for r in bundle["versions"] if r["object_id"] in roots_set}
    payload = {"bundle_sha256": sha(bundle_path), "inputs": bundle["inputs"],
               "observations": bundle["observations"], "observation_bindings": observation_bindings,
               "events": events,
               "origins": origins, "bindings": bindings, "import_is_not_new_model_behavior": True}
    if payload["bundle_sha256"] in store.imports:
        old = next(x["payload"] for x in store.entries if x["kind"] == "IMPORT"
                   and x["payload"]["bundle_sha256"] == payload["bundle_sha256"])
        need(old == payload, "Same import identity changed bindings/content")
        return False
    need(not store.imports and not store.versions, "Use one verified bootstrap; do not merge unrelated histories")
    store.append("IMPORT", payload)
    need(list(store.versions.values()) == bundle["versions"], "Imported version order differs")
    return True

class PersistentGoals(GoalResearch):
    """Research adapter; Native origin identities stay immutable across Threads."""
    def __init__(self, semantic, path, store):
        super().__init__(semantic, path)
        self.store = store; self.native_call = None
        self.handled = deepcopy(store.handled)

    def records(self, state):
        return [RuntimeObjectRecord(**r) for r in self.store.visible(state.thread_id)]

    def original_inputs(self, state):
        current = super().original_inputs(state)
        ids = {x.object_id for x in current}
        visible = self.store.visible(state.thread_id)
        required = {i for r in visible for i in [r["metadata"]["input_id"]] + r["metadata"]["asserted_support_input_ids"]}
        return [RuntimeObjectRecord(**deepcopy(self.store.inputs[i])) for i in required if i not in ids] + current

    def _event(self, thread_id, event, payload):
        row = {"schema": "uaea.goal_integration.v1", "event": event, "thread_id": thread_id,
               "mode": "shadow", "projection": "optional", "payload": deepcopy(payload),
               "changes_tool_authorization": False, "completes_workflow": False, "writes_memory": False}
        state = self._state(thread_id)
        records = super().original_inputs(state)
        inputs = [r.to_dict() for r in records if r.object_id not in self.store.inputs]
        origins = {}
        for r in inputs:
            p = self.path.with_name("app-server-events.jsonl")
            if p.exists(): origins[r["object_id"]] = {"path": str(p), "bytes": p.stat().st_size, "sha256": sha(p)}
        observations = {}
        p = self.path.with_name("execution-contract.trajectory.jsonl")
        if p.exists():
            observations = verified_observations(lines(p),
                lines(self.path.with_name("app-server-events.jsonl")),
                [x.to_dict() for x in state.runtime_objects.step_runs])
        bindings = {}
        for st in state.runtime_objects.step_runs:
            oid = st.execution_observation_id
            if oid in observations:
                h = st.action["harness"]
                bindings[oid] = {"call_id": h["call_id"], "turn_id": h["turn_id"],
                    "thread_id": thread_id, "workflow_id": st.workflow_id, "input_id": h["input_id"],
                    "decision": deepcopy(st.action["execution_contract"])}
                origins[oid] = {"path": str(p), "bytes": p.stat().st_size, "sha256": sha(p)}
        self.store.append("EVENT", {"event": row, "call": deepcopy(self.native_call),
                    "inputs": inputs, "observations": observations,
                    "observation_bindings": bindings, "origins": origins})
        return row

    def save(self, thread_id):
        # Derived output only; never loaded as recovery authority.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        value = {"derived_from": str(self.store.path), "journal_sha256": sha(self.store.path),
                 "heads": self.store.heads(thread_id), "versions": self.store.visible(thread_id),
                 "active_goal_id": "", "not_recovery_authority": True}
        path = self.path.with_name("goal-research-state.json"); tmp = path.with_suffix(".tmp")
        with tmp.open("w") as f:
            json.dump(value, f, ensure_ascii=False, indent=2); f.flush(); os.fsync(f.fileno())
        tmp.replace(path)

    def context(self, thread_id):
        # Reuse existing authority envelope. Only the research hypothesis view is persistent.
        from research.goal_hypothesis import DESCRIPTION, TOOL
        return {"uaea.goal_state": {"kind": "application", "value": json.dumps({
            "schema": "uaea.goal_integration.v1", "mode": "shadow",
            "state_sha256": digest(self._goal_state(self._state(thread_id))),
            "active_goal_id": "", "decision_id": None,
            "goal_completion_established": False, "goal_is_not_authorization": True,
            "research_channel": TOOL, "instruction": DESCRIPTION}, ensure_ascii=False)},
            "uaea.goal_hypotheses": {"kind": "untrusted",
                "value": json.dumps(self.store.view(thread_id), ensure_ascii=False)}}
