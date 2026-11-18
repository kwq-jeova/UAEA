"""Opt-in correction-candidate continuity. Not formal Memory admission or an agent loop."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,re,sqlite3
from uuid import uuid5,NAMESPACE_URL
from memory import sqlite_store as db
from memory.candidate import MemoryCandidate,EvidenceReference,ScopeHypothesis
from research.longitudinal_dialogue import ScenarioApp
from harness.codex_dynamic_tools import HarnessDynamicToolAdapter
TOOL="correction_lesson"
DESCRIPTION=("Propose one narrow, non-authoritative lesson only from the CURRENT explicit user correction. "
 "quote must be an exact substring of current input. Say when relevant and at most one optional low-cost "
 "check using an ALREADY allowed read-only tool. It is not a user preference, Goal, new permission, "
 "mandatory plan or authority to hide/delete candidates. Do not copy current answers into future facts.")
SCHEMA={"type":"object","properties":{k:{"type":"string"}for k in ["claim","when_relevant","one_check","quote"]},
 "required":["claim","when_relevant","one_check","quote"],"additionalProperties":False}
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def grams(s):
 s=re.sub(r"[^\w\u4e00-\u9fff]","",s.lower())
 return {s[i:i+2]for i in range(len(s)-1)}
class LessonStore:
 def __init__(self,path,*,retrieval_basis="scope_only"):
  if retrieval_basis not in ("scope_only","claim_and_scope"):raise ValueError("unknown retrieval basis")
  self.retrieval_basis=retrieval_basis
  self.path=Path(path);self.connection=db.connect(path);db.initialize(self.connection)
 def close(self):self.connection.close()
 def submit(self,*,thread,turn,call,input_id,text,arguments,location):
  if not all(isinstance(x,str)and x for x in [thread,turn,call,input_id,text,location]):raise ValueError("missing native identity")
  if not isinstance(arguments,dict)or set(arguments)!=set(SCHEMA["required"]):raise ValueError("exact proposal fields required")
  if any(not isinstance(v,str)or not v.strip()or len(v)>500 for v in arguments.values()):raise ValueError("bounded nonempty text required")
  if any(v!=v.strip()for v in arguments.values()):raise ValueError("proposal fields must have no outer whitespace")
  if arguments["quote"]not in text:raise ValueError("quote must be CURRENT correction substring")
  cid="LC-"+str(uuid5(NAMESPACE_URL,thread+":"+call))
  binding={"thread":thread,"turn":turn,"call":call,"input_id":input_id,"text_sha256":digest(text),"arguments_sha256":digest(arguments)}
  old=db.get_candidate(self.connection,cid)
  if old:
   if old["raw"].get("native_binding")!=binding:raise ValueError("conflicting duplicate native Call")
   self._verify(old);return {"ok":True,"committed":True,"duplicate":True,"candidate_id":cid,"authorizes_action":False}
  used=self.connection.execute("SELECT 1 FROM candidate_evidence ce JOIN evidence_references e ON ce.evidence_id=e.evidence_id WHERE e.source_kind='conversation_turn' AND e.source_id=? LIMIT 1",(input_id,)).fetchone()
  if used:raise ValueError("one candidate per correction; no overwrite")
  source={"turn_id":input_id,"role":"user","category":"explicit_correction","content":text,"thread_id":thread,"native_turn_id":turn,
          "text_sha256":digest(text),"location":location}
  c=MemoryCandidate(candidate_id=cid,claim=arguments["claim"],source_provenance="derived",
    evidence_references=(EvidenceReference("conversation_turn",input_id,input_id,location,arguments["quote"]),),
    scope_hypothesis=ScopeHypothesis.from_mapping(arguments["when_relevant"],{"owner":"assistant_work_check","not_user_goal":"true"}),
    extraction_confidence=0.0,validation_requirements=(arguments["one_check"],),
    proposed_validity="optional one existing read-only check; not new authority",
    representation_facet_hint="failure lesson",relation_hint=thread+":"+call)
  if not c.is_structurally_valid():raise ValueError("invalid existing candidate structure")
  payload={**c.to_dict(),"native_binding":binding,"confidence_semantics":"legacy required placeholder, NOT calibrated belief"}
  with self.connection:
   prior=self.connection.execute("SELECT raw_json FROM source_records WHERE source_kind='conversation_turn' AND source_id=?",(input_id,)).fetchone()
   if prior and json.loads(prior[0])!=source:raise ValueError("conflicting correction identity")
   db.ingest_source_record(self.connection,source);db.insert_candidate(self.connection,c,raw_mapping=payload)
  return {"ok":True,"committed":True,"candidate_id":cid,"source_input_id":input_id,"candidate_state":"open","authorizes_action":False}
 def _verify(self,c):
  if (c["claim"]!=c["raw"]["claim"]or c["candidate_state"]!="open"or c["scope"]!=c["raw"]["scope_hypothesis"]or c["validation_requirements"]!=c["raw"]["validation_requirements"]or len(c["validation_requirements"])!=1):raise ValueError("candidate changed or hidden")
  trace=db.trace_candidate(self.connection,c["candidate_id"])
  if len(trace["trace"])!=1:raise ValueError("missing correction evidence")
  s=trace["trace"][0]["source_record"]
  if not s or s["role"]!="user"or digest(s["content"])!=s["raw"].get("text_sha256"):raise ValueError("source integrity failure")
  e=trace["trace"][0]["evidence"]
  if e["summary"]not in s["content"]or s["source_id"]!=c["raw"]["native_binding"]["input_id"]:raise ValueError("broken evidence binding")
  binding=c["raw"]["native_binding"]
  args={"claim":c["claim"],"when_relevant":c["scope_summary"],"one_check":c["validation_requirements"][0],"quote":e["summary"]}
  expected="LC-"+str(uuid5(NAMESPACE_URL,binding["thread"]+":"+binding["call"]))
  if (c["candidate_id"]!=expected or digest(args)!=binding["arguments_sha256"]or digest(s["content"])!=binding["text_sha256"]):
   raise ValueError("native binding integrity failure")
  return trace
 def view(self,text):
  values=[]
  for r in self.connection.execute("SELECT candidate_id FROM candidates ORDER BY candidate_id"):
   c=db.get_candidate(self.connection,r[0])
   if c["representation_facet_hint"]!="failure lesson":continue
   trace=self._verify(c)
   match_text=c["scope_summary"]if self.retrieval_basis=="scope_only"else c["claim"]+" "+c["scope_summary"]
   score=len(grams(text)&grams(match_text))
   values.append((score,c,trace))
  ranked=sorted(values,key=lambda x:(-x[0],x[1]["candidate_id"]))
  selected=ranked[:1]if ranked and ranked[0][0]>=2 else[]
  full=[]
  for score,c,t in selected:
   s=t["trace"][0]["source_record"]
   full.append({"candidate_id":c["candidate_id"],"claim":c["claim"],"when_relevant":c["scope_summary"],
    "one_check":c["validation_requirements"][0],"source_input_id":s["source_id"],
    "correction_quote":t["trace"][0]["evidence"]["summary"],"correction_text":s["content"],"source_location":s["raw"]["location"],
    "authority":"non-authoritative work hypothesis; not a Goal or permission","max_optional_checks":1})
  return {"selected":full,"inventory":[{"candidate_id":c["candidate_id"],"state":c["candidate_state"],
     "selected":any(x["candidate_id"]==c["candidate_id"]for x in full),"lexical_overlap":score}for score,c,t in ranked],
    "retrieval_rule":"generic character-bigram overlap, >=2, top1; engineering heuristic not semantic truth",
    "instruction":"仅在本轮材料确实不足且相关时，最多考虑一次已获准的低成本只读核查；材料够则不查。最终结论仍须来自本次材料。不是用户长期偏好，不可据此修改Goal或隐藏候选。"}
 def backup(self,path):
  target=sqlite3.connect(path)
  try:self.connection.backup(target)
  finally:target.close()
def response_basis(receipts,*,input_id):
 """Current-request receipt visibility only, not evidence sufficiency or semantic truth."""
 selected=receipts[-8:]
 return {"scope":"current user request only; not a statement about earlier reading or source absence",
  "input_id":input_id,"recorded_read_attempts":len(receipts),
  "successful_body_receipts":sum(r["body_status"]in ("complete","partial")for r in receipts),
  "recent_receipts":deepcopy(selected),"omitted_earlier_receipts":len(receipts)-len(selected),
  "instruction":"交付时区分用户摘要已给出的信息、工具实际返回的正文和推测。摘要足够时可以直接答，不必为这条说明增加读取或追问。只有成功回执实际供给的内容，才能声称已读取或查证；失败或未读不证明原文没有。关键事实仍缺时，说清本次未核实的具体项，不把它当成已验证事实。这只描述本轮，不否定历史读过的材料。"}
def read_receipt_fact(params,response):
 """Use the same serialized response the existing adapter will send, never file existence."""
 payload=json.loads(response["contentItems"][0]["text"]);d=payload.get("data",{});i=payload.get("identity",{})
 for key,native in [("call_id","callId"),("thread_id","threadId"),("turn_id","turnId")]:
  if i.get(key)!=params.get(native):raise ValueError("receipt/native identity mismatch")
 success=response.get("success")is True and d.get("execution_succeeded")is True
 content=d.get("content")
 projection=d.get("document_projection",{})
 body_status="none"
 if success and isinstance(content,str)and content:
  body_status="complete"if projection.get("content_complete")is True else "partial"if projection.get("content_complete")is False else "unknown"
 return {"call_id":i["call_id"],"thread_id":i["thread_id"],"turn_id":i["turn_id"],
  "path":str(d.get("path",params.get("arguments",{}).get("path","UNKNOWN")))[:512],
  "section_index":d.get("section_index",params.get("arguments",{}).get("section_index")),
  "execution_succeeded":success,"body_status":body_status,
  "visible_content_sha256":projection.get("visible_content_sha256"),
  "omitted_content_chars":projection.get("omitted_content_chars"),
  "failure":None if success else str(d.get("error",payload.get("message","UNKNOWN")))[:256]}

class LessonAdapter(HarnessDynamicToolAdapter):
 def __init__(self,*args,response_basis_view=False,**kwargs):
  super().__init__(*args,**kwargs);self.response_basis_view=response_basis_view;self.read_receipts=[]
 def dispatch(self,params,*args,**kwargs):
  result=super().dispatch(params,*args,**kwargs)
  if self.response_basis_view and params.get("tool")=="read_section":
   fact=read_receipt_fact(params,result.to_app_server_response())
   previous=next((r for r in self.read_receipts if r["call_id"]==fact["call_id"]),None)
   if previous is not None and previous!=fact:raise ValueError("conflicting receipt identity")
   if previous is None:self.read_receipts.append(fact)
  return result
 def dynamic_tools(self):
  return super().dynamic_tools()+[{"type":"function","name":TOOL,"description":DESCRIPTION,"inputSchema":SCHEMA}]
CONCLUSION_DISCIPLINE='先区分材料明确支持、明确排除和仍未确定的内容，再给结论；缺失信息保持未知，不补成确定值，也不自行收紧或放宽用户明确条件。请先简列事实及其支持状态，再写与之相符的结论。'
class LessonApp(ScenarioApp):
 def __init__(self,*,lesson_profile,lesson_view=True,retrieval_basis="scope_only",conclusion_discipline=False,**kwargs):
  if type(conclusion_discipline)is not bool:raise TypeError("conclusion_discipline must be bool")
  self.conclusion_discipline=conclusion_discipline
  self.lesson_store=LessonStore(lesson_profile,retrieval_basis=retrieval_basis);self.lesson_view=lesson_view;self._correction_open=False;self._lesson_text=""
  super().__init__(**kwargs)
 def run_turn(self,text):
  if self._pending_turn is not None:raise ValueError("finish current Harness Turn before a new lesson input")
  self._correction_open=False;self._lesson_text=text
  if getattr(self.adapter,"response_basis_view",False):self.adapter.read_receipts=[]
  return super().run_turn(text)
 def run_correction(self,text):
  if self._pending_turn is not None:raise ValueError("finish current Harness Turn before a correction")
  self._correction_open=True;self._lesson_text=text
  if getattr(self.adapter,"response_basis_view",False):self.adapter.read_receipts=[]
  return super().run_turn(text)
 def _publish_runtime_context_snapshot(self):
  super()._publish_runtime_context_snapshot()
  bridge=self._history_bridge
  if bridge is None or bridge._runtime_context is None:return
  state=deepcopy(bridge._runtime_context);key="uaea.correction_lessons"
  view=self.lesson_store.view(self._lesson_text)if self.lesson_view else {"disabled_for_comparison":True}
  block={"kind":"untrusted","value":json.dumps(view,ensure_ascii=False)}
  state["blocks"][key]=block
  if self._last_turn_context is not None:self._last_turn_context[key]=block
  if getattr(self.adapter,"response_basis_view",False):
   basis=response_basis(self.adapter.read_receipts,input_id=state["input_id"])
   state["blocks"]["uaea.research_response_basis"]={"kind":"application","value":json.dumps(basis,ensure_ascii=False)}
   if self._last_turn_context is not None:self._last_turn_context["uaea.research_response_basis"]=state["blocks"]["uaea.research_response_basis"]
  if self.conclusion_discipline:
   state["blocks"]["uaea.research_conclusion_discipline"]={"kind":"application","value":CONCLUSION_DISCIPLINE}
   if self._last_turn_context is not None:self._last_turn_context["uaea.research_conclusion_discipline"]=state["blocks"]["uaea.research_conclusion_discipline"]
  bridge.set_runtime_context(state["blocks"],thread_id=self.thread_id,input_id=state["input_id"])
  self._lesson_event("retrieval",{"input_id":state["input_id"],"retrieval_basis":self.lesson_store.retrieval_basis,"view":view})
 def _lesson_event(self,kind,value):
  with self.events_path.with_name("lesson-events.jsonl").open("a")as f:
   f.write(json.dumps({"kind":kind,"thread":self.thread_id,**value},ensure_ascii=False)+"\n")
 def _handle_tool_call(self,message):
  p=message.get("params",{})
  if p.get("tool")!=TOOL:return super()._handle_tool_call(message)
  try:
   if not self._correction_open or p.get("threadId")!=self.thread_id:raise ValueError("not CURRENT explicit correction")
   active=self._turn_wait or self._pending_turn
   if not active or p.get("turnId")!=active["turn_id"]:raise ValueError("foreign Turn")
   snap=self.semantic_state.snapshot(self.thread_id)
   current=next((x for x in snap["workflow_continuity"]["request_continuity"]["inputs"]if x["object_id"]==snap["current_input_id"]),None)
   if current is None or current["metadata"]["text"]!=self._lesson_text:raise ValueError("CURRENT input text/identity mismatch")
   receipt=self.lesson_store.submit(thread=self.thread_id,turn=p.get("turnId",""),call=p.get("callId",""),
    input_id=snap["current_input_id"],text=self._lesson_text,arguments=p.get("arguments"),location=str(self.events_path))
  except(ValueError,KeyError,TypeError)as exc:
   receipt={"ok":False,"committed":False,"error":str(exc),"authorizes_action":False}
  self._lesson_event("proposal",{"call_id":p.get("callId"),"arguments":p.get("arguments"),"receipt":receipt})
  self._send({"jsonrpc":"2.0","id":message.get("id"),"result":{"success":receipt["ok"],
   "contentItems":[{"type":"inputText","text":json.dumps(receipt,ensure_ascii=False)}]}})
  if receipt["ok"]:self._publish_runtime_context()

 def close(self):
  try:return super().close()
  finally:self.lesson_store.close()

def app_for(profile,out,workspace,*,lesson_view=True,retrieval_basis="scope_only",response_basis_view=False,conclusion_discipline=False,task_decision_view=False,base_url="http://127.0.0.1:8003",timeout=420):
 """Project entry: persistence/retrieval are owned by this App, never by a test injector."""
 from h3_context_characterization import ToolRegistry,Sandbox,LedgerStub,write_config
 from harness.codex_dynamic_tools import DynamicToolBinding
 from h3_harness_interactive_repl import DEFAULT_CODEX_BIN
 out=Path(out);out.mkdir(parents=True,exist_ok=True);workspace=Path(workspace).resolve()
 registry=ToolRegistry(Sandbox(workspace.parent,workspace),LedgerStub(out/"tool-traces"))
 binding=DynamicToolBinding.from_registry(registry,"document.read_section",
  description="Read one positive 1-based Markdown section ordinal. Completeness describes actual visible content.",
  input_schema={"type":"object","properties":{"path":{"type":"string"},"section_index":{"type":"integer","minimum":1}},
   "required":["path","section_index"],"additionalProperties":False})
 adapter=LessonAdapter(registry,[binding],max_output_chars=12000,response_basis_view=response_basis_view)
 write_config(out/"codex-home",base_url,65536,model="nemotron-bolt-n1x",n1x=True)
 if type(task_decision_view)is not bool:raise TypeError("task_decision_view must be bool")
 app_type=LessonApp
 if task_decision_view:
  from research.task_decision import TaskDecisionApp
  app_type=TaskDecisionApp
 app=app_type(lesson_profile=profile,lesson_view=lesson_view,retrieval_basis=retrieval_basis,conclusion_discipline=conclusion_discipline,codex=DEFAULT_CODEX_BIN,codex_home=out/"codex-home",
  workspace=workspace,base_url=base_url,adapter=adapter,events_path=out/"app-server-events.jsonl",
  stderr_path=out/"stderr.log",turn_timeout=timeout,model="nemotron-bolt-n1x",reasoning_effort="none",
  execution_contract="shared",goal_mode="off",goal_projection="optional",input_actor="test_driver")
 app.research_fixture_files=[{"path":str(f),"title":f.read_text().splitlines()[0].lstrip("# ").strip(),
   "scope":"available file, not read evidence"}for f in sorted(workspace.glob("*.md"))]
 return app
