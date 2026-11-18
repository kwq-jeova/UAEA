"""Opt-in current-task judgment -> recommendation -> deterministic reply.
No Goal, Memory admission, external actions or extra model loop.
"""
from copy import deepcopy
import hashlib,json,re
from memory.candidate import EvidenceReference
from research.correction_continuity import LessonApp
STATUSES=("符合","不符合","待确认")
ID_PATTERN=r"^[A-Za-z][A-Za-z0-9_-]{0,15}$"
ID_DESCRIPTION="ASCII, 1..16 chars: first A-Z/a-z; rest A-Z/a-z/0-9/_/-; unique"
SCHEMA={
 "conditions":[{"id":ID_DESCRIPTION,"quote":"CURRENT user hard condition verbatim, 1..180 chars, no surrounding whitespace"}],
 "candidates":[{"id":ID_DESCRIPTION,"name":"CURRENT candidate name verbatim, 1..180 chars",
  "checks":[{"condition_id":"existing condition ID in same ASCII format","evidence_quote":"CURRENT material verbatim, 1..180 chars","status":"符合 / 不符合 / 待确认"}]}],
 "recommendation":{"candidate_id":"existing 符合 candidate ID, or null","basis_candidate_ids":["existing candidate IDs; unique; include chosen ID"],
 "preference_quote":"CURRENT user selection preference verbatim, or empty","reason":"model inference, NOT a verbatim quote; 1..180 chars"}}
def _object(properties):
 return {"type":"object","properties":properties,"required":list(properties),"additionalProperties":False}
def _string(*,empty=False):
 return {"type":"string","minLength":0 if empty else 1,"maxLength":180}
def _identifier():
 return {"type":"string","minLength":1,"maxLength":16,"pattern":ID_PATTERN}
OUTPUT_SCHEMA=_object({
 "conditions":{"type":"array","minItems":1,"maxItems":3,"items":_object({"id":_identifier(),"quote":_string()})},
 "candidates":{"type":"array","minItems":1,"maxItems":4,"items":_object({
  "id":_identifier(),"name":_string(),"checks":{"type":"array","minItems":1,"maxItems":3,"items":_object({
   "condition_id":_identifier(),"evidence_quote":_string(),"status":{"type":"string","enum":list(STATUSES)}})}})},
 "recommendation":_object({"candidate_id":{"anyOf":[_identifier(),{"type":"null"}]},
  "basis_candidate_ids":{"type":"array","minItems":0,"maxItems":4,"items":_identifier()},
  "preference_quote":_string(empty=True),"reason":_string()})})
INSTRUCTION=(
 "这是显式开启的本轮任务资格记录接口。最终只返回一个严格JSON对象，字段和层次严格按schema，不能返回示例值、额外字段、代码围栏或另写自然语言答案。"
 "先登记真正影响候选资格的共同硬条件，逐字引用当前用户原话；为每个相关候选对每个已登记条件列一个check，逐字引用当前材料并选择符合/不符合/待确认。"
 "不要遗漏影响选择的候选。证据缺失保持待确认，已明确给出的事实应保留。更便宜/较新等排序偏好不当作排除资格的硬条件，单独逐字放recommendation.preference_quote。"
 "本轮输入就是可引用的CURRENT来源，不引用旧教训代替当前事实。不必填来源ID，Host会绑定真实当前输入身份。"
 "checks覆盖全部已登记条件，Host按不符合优先、其次待确认、否则符合合并；不另写总状态。"
 "推荐直接引用前面已有判断：candidate_id指已确认符合候选，basis_candidate_ids列用到的候选ID、去重且包含所选ID；不再另填推荐证据引文。"
 "reason是你的推导理由，不要求逐字匹配材料，不冒充原文；原文证据只放各check.evidence_quote，选择偏好引用放preference_quote。"
 "可先选已确认符合者，同时保留其他候选待确认；无确认符合者用null。"
 "所有ID及ID引用只准ASCII，长度1到16，首字符A-Z或a-z，之后只含A-Z/a-z/0-9/下划线/连字符，格式^[A-Za-z][A-Za-z0-9_-]{0,15}$；声明ID唯一，引用须存在。"
 "文字字段最多180字符、无首尾空白；name是当前输入中的候选原名，非ID。"
 "Host只核对身份、原文引用和记录内关联，不判断日期、金额或批准语义，不替你改判断；用户短答直接由记录渲染，不再独立重写。"
 "上限3个硬条件、4个候选，尽量精简到本轮决定所需内容。")
def unique(pairs):
 out={}
 for k,v in pairs:
  if k in out:raise ValueError("duplicate JSON key")
  out[k]=v
 return out
def exact_keys(value,keys):
 if not isinstance(value,dict)or set(value)!=set(keys):raise ValueError("exact record fields required")
def short(s,limit=180,empty=False):
 if not isinstance(s,str)or s!=s.strip()or len(s)>limit or (not empty and not s):raise ValueError("bounded exact text required")
 return s
def identifier(s):
 if not isinstance(s,str)or not re.fullmatch(ID_PATTERN,s):raise ValueError("short identifier required")
 return s
def aggregate(states):
 if "不符合"in states:return "不符合"
 if "待确认"in states:return "待确认"
 return "符合"
def validate_record(text,*,source_text,input_id,thread_id,turn_id,event_id,location):
 if not all(isinstance(v,str)and v for v in [source_text,input_id,thread_id,turn_id,event_id,location]):raise ValueError("current native/source identity required")
 if not isinstance(text,str)or len(text.encode())>32000:raise ValueError("bounded explicit JSON required")
 data=json.loads(text,object_pairs_hook=unique)
 exact_keys(data,["conditions","candidates","recommendation"])
 refs=[]
 def quote(s,empty=False):
  s=short(s,empty=empty)
  if s and s not in source_text:raise ValueError("quote not in CURRENT input")
  if s:refs.append(EvidenceReference("conversation_turn",input_id,input_id,location,s).to_dict())
  return s
 conditions=data["conditions"]
 if not isinstance(conditions,list)or not 1<=len(conditions)<=3:raise ValueError("1..3 conditions required")
 ids=[];condition_quotes=[]
 for c in conditions:
  exact_keys(c,["id","quote"]);ids.append(identifier(c["id"]));condition_quotes.append(quote(c["quote"]))
 if len(set(ids))!=len(ids)or len(set(condition_quotes))!=len(ids):raise ValueError("duplicate condition")
 candidates=data["candidates"]
 if not isinstance(candidates,list)or not 1<=len(candidates)<=4:raise ValueError("1..4 candidates required")
 cids=[];names=[];statuses={}
 for c in candidates:
  exact_keys(c,["id","name","checks"]);cid=identifier(c["id"]);cids.append(cid);names.append(quote(c["name"]))
  checks=c["checks"]
  if not isinstance(checks,list)or len(checks)!=len(ids):raise ValueError("condition coverage required")
  covered=[]
  for check in checks:
   exact_keys(check,["condition_id","evidence_quote","status"])
   covered.append(identifier(check["condition_id"]));quote(check["evidence_quote"])
   if check["status"]not in STATUSES:raise ValueError("three-valued status required")
  if len(set(covered))!=len(ids)or set(covered)!=set(ids):raise ValueError("condition reference mismatch")
  statuses[cid]=aggregate([x["status"]for x in checks])
 if len(set(cids))!=len(cids)or len(set(names))!=len(names):raise ValueError("duplicate candidate")
 rec=data["recommendation"];exact_keys(rec,["candidate_id","basis_candidate_ids","preference_quote","reason"])
 selected=rec["candidate_id"]
 if selected is not None:
  identifier(selected)
  if selected not in statuses or statuses[selected]!="符合":raise ValueError("recommendation must reference a declared qualifying candidate")
 basis=rec["basis_candidate_ids"]
 if not isinstance(basis,list)or len(basis)>4:raise ValueError("bounded candidate judgment references required")
 for cid in basis:identifier(cid)
 if len(set(basis))!=len(basis)or any(cid not in statuses for cid in basis):raise ValueError("candidate judgment reference mismatch")
 if selected is not None and selected not in basis:raise ValueError("recommendation must link selected judgment")
 quote(rec["preference_quote"],empty=True);short(rec["reason"]) # Inference is deliberately NOT a source quote.

 binding={"input_id":input_id,"thread_id":thread_id,"turn_id":turn_id,"model_event_id":event_id,
  "source_text_sha256":hashlib.sha256(source_text.encode()).hexdigest(),"proposal_sha256":hashlib.sha256(text.encode()).hexdigest()}
 return {"schema":"uaea.research_task_decision.v2","binding":binding,"judgment":data,"overall_status":statuses,
  "source_references":refs,"scope":"current input task only","authority":"model interpretation, no execution permission",
  "source_validation":"exact CURRENT quotes and native identity; semantic support NOT verified",
  "saved_to_goal_or_lesson":False}
def render(record):
 data=record["judgment"];states=record["overall_status"];rec=data["recommendation"]
 names={c["id"]:c["name"]for c in data["candidates"]};chosen=rec["candidate_id"]
 if chosen is None:parts=["本轮暂不作确定推荐，候选状态如下。"]
 else:parts=[("本次先选"if any(s=="待确认"for s in states.values())else"本次推荐")+names[chosen]+"。"]
 conditions={c["id"]:c["quote"]for c in data["conditions"]}
 for c in data["candidates"]:
  status=states[c["id"]]
  if status=="符合":parts.append(c["name"]+"：符合当前列出的条件。")
  else:
   check=next(x for x in c["checks"]if x["status"]==status)
   parts.append(c["name"]+"："+status+"（条件：“"+conditions[check["condition_id"]]+"”；材料：“"+check["evidence_quote"]+"”）。")
 if chosen is not None:
  rule=("按你的“"+rec["preference_quote"]+"”；")if rec["preference_quote"]else""
  parts.append(rule+"理由："+rec["reason"])
 else:parts.append("理由："+rec["reason"])
 return "\n".join(parts)

class TaskDecisionApp(LessonApp):
 def __init__(self,**kw):
  self.current_task_decision=None;self.user_answer=None;self.last_delivery=None;self._decision_messages=[]
  super().__init__(**kw)
 def _request_turn(self,message,*,timeout):
  # Existing native final-output contract; not a new loop or semantic judge.
  message=deepcopy(message)
  if message.get("method")=="turn/start":
   message["params"]["outputSchema"]=deepcopy(OUTPUT_SCHEMA)
  return super()._request_turn(message,timeout=timeout)
 def run_turn(self,text):
  if self._pending_turn is not None:raise ValueError("finish current Native turn before new task")
  self.current_task_decision=None;self.user_answer=None;self.last_delivery=None;self._decision_messages=[]
  return super().run_turn(text)
 def run_correction(self,text):
  raise ValueError("task decision mode does not save long-term corrections")
 def _publish_runtime_context_snapshot(self):
  super()._publish_runtime_context_snapshot()
  bridge=self._history_bridge
  if bridge is None or bridge._runtime_context is None:return
  state=deepcopy(bridge._runtime_context)
  b={"kind":"application","value":json.dumps({"scope":"explicit current-task record only","instruction":INSTRUCTION,"schema":SCHEMA},ensure_ascii=False)}
  state["blocks"]["uaea.research_task_decision"]=b
  if self._last_turn_context is not None:self._last_turn_context["uaea.research_task_decision"]=b
  bridge.set_runtime_context(state["blocks"],thread_id=self.thread_id,input_id=state["input_id"])
 def _handle_message(self,message):
  p=message.get("params")or{};item=p.get("item")or{}
  if message.get("method")=="item/completed"and item.get("type")=="agentMessage"and p.get("threadId")==self.thread_id:
   self._decision_messages.append({"turn_id":p.get("turnId"),"item":deepcopy(item)})
   return # Raw Native event already persisted by parent waiter; don't expose record JSON as user prose.
  return super()._handle_message(message)
 def _report_turn_completion(self,completion,goal_input_id):
  from h3_harness_interactive_repl import extract_text
  turn=(completion or{}).get("params",{}).get("turn",{})
  receipt={"accepted_for_rendering":False,"semantic_correctness":"not_established","scope":"current task only"}
  try:
   if turn.get("status")!="completed":raise ValueError("Native turn not completed")
   snapshot=self.semantic_state.snapshot(self.thread_id)
   current=next(x for x in snapshot["workflow_continuity"]["request_continuity"]["inputs"]if x["object_id"]==snapshot["current_input_id"])
   provenance=current["metadata"]["provenance"]
   if goal_input_id!=snapshot["current_input_id"]or provenance.get("turn_id")!=turn.get("id")or provenance.get("thread_id")!=self.thread_id:raise ValueError("current input/Native turn mismatch")
   items=[x["item"]for x in self._decision_messages if x["turn_id"]==turn["id"]]
   if not items:raise ValueError("no current final model message")
   final=items[-1]
   self.current_task_decision=validate_record(extract_text(final),source_text=current["metadata"]["text"],
    input_id=goal_input_id,thread_id=self.thread_id,turn_id=turn["id"],event_id=final["id"],location=str(self.events_path))
   self.user_answer=render(self.current_task_decision)
   receipt.update(accepted_for_rendering=True,record=self.current_task_decision,user_answer=self.user_answer)
  except (ValueError,KeyError,TypeError,StopIteration)as exc:
   self.current_task_decision=None;self.user_answer="这次未能形成可靠的候选判断，暂不作确定推荐。"
   receipt.update(error=str(exc),user_answer=self.user_answer)
  self.last_delivery=receipt
  with self.events_path.with_name("task-decision-events.jsonl").open("a")as f:f.write(json.dumps(receipt,ensure_ascii=False)+"\n")
  print("\n[ASSISTANT]\n"+self.user_answer,flush=True)
  return super()._report_turn_completion(completion,goal_input_id)
