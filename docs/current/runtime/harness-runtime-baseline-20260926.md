# UAEA Harness Runtime Baseline

> Status: CURRENT
> Role: CURRENT_BASELINE / Harness freeze
> Phase: 2026-09-26；10-02 收敛
> Still valid: 当前 generic runtime；末尾章节为历史
> Superseded: 历史 Google unsupported 已由 backend/audit 替代
> Current reference: [Documentation Guide](../../README.md)
> Governance reviewed: 2026-10-02（文档治理，不等于新实验验证）
> 当前 contract 与历史验证记录分开阅读；本轮仅治理文档，不重新运行模型验收。

日期：2026-09-26

本文件记录 generic Harness 集成的冻结结论。当前 UAEA semantic/Web 扩展状态以
主 README 和 [Boundary Integrity Audit](../architecture/boundary-integrity-audit-20261002.md) 为准。
阶段性审计、probe 和历史决策保留在 `docs/archive/harness/` 或本文历史章节，不删除。

2026-10-05 状态入口：[信息边界 checkpoint](../architecture/cognition-boundary-checkpoint-20261005.md)。
generic runtime freeze 不变；最新 authority 迭代人工测试未进行，不把后续 UAEA semantic
扩展的自动通过升级为本文件的新模型行为验收结论。

## Baseline Verdict

```text
Harness Runtime Baseline: CLOSED
Harness integration work: STOP
Codex Core fork: NO
```

当前结论是 generic Harness runtime 已经足以作为 UAEA 后续
Goal / Memory / Episode 研究的执行边界。后续问题不再默认通过扩建
Harness 解决。

## 已闭环范围

### Local Runtime And Model Plane

```text
source-owned Codex app-server
  -> local Responses transport
  -> local vLLM
  -> Qwen2.5-14B-Instruct-AWQ
```

Harness 以本地进程运行。H3 diagnostic 路径使用本地 vLLM `8002`；
冻结的 Phase-2 endpoint `8001` 未被修改。当前物理边界仍然是：

```text
Windows 11
WSL2 Ubuntu 24.04.x
NVIDIA RTX 5090 D v2
24 GB VRAM
single GPU
Qwen2.5-14B-Instruct-AWQ
4-bit / AWQ
vLLM
```

### I/O And Lifecycle

已验证的 App Server 外层输入包括：

```text
thread/start
turn/start
turn/start.additionalContext
dynamicTools
model/provider
sandbox / approval policy
```

已验证的事件包括：

```text
thread / turn lifecycle
user message
agent message
dynamic tool call/result
commandExecution
token usage
error / cancellation
contextCompaction occurrence
turn/completed
```

`turn/start.additionalContext` 可作为稳定的 pre-turn application context
入口。`turn/completed` 可作为 UAEA 外层 post-turn trigger。

### Tool And Capability Boundary

动态工具路径已经闭环：

```text
Harness dynamic tool call
  -> HarnessDynamicToolAdapter
  -> UAEA ToolRegistry / Capability
  -> bounded ToolResult
  -> Harness continuation
  -> turn/completed
```

已验证或纳入现有 contract 的 capability 包括：

```text
mock.external_operation
document.read_section
fs.list
web.search
web.fetch
```

Harness-native command/file 路径也已验证。source-owned Codex 使用 bundled
`codex-resources/bwrap` 创建 read-only sandbox，模型可通过
`commandExecution` 读取 `README.md`，获得结果后继续回答并完成 turn。

### Trajectory

当前 trajectory infrastructure 已闭环：

```text
App Server raw events
  -> HarnessEventNormalizer
  -> UAEA TrajectoryEvent
  -> HarnessTrajectoryWriter
  -> canonical run-level JSONL
  -> HarnessTrajectoryReader / validator
  -> per-turn reconstruction / thread projection
```

canonical 文件格式：

```text
<run_id>.trajectory.jsonl
```

thread 文件只是 derived projection，不是第二个权威数据源。事件保留
Harness native identity、UAEA 接收顺序、provenance 和 raw event reference。

基础设施测试及既有 H3 artifact 已验证以下 surface；不代表每个历史 run 都包含 canonical 文件：

```text
JSONL readable: PASS
sequence monotonic: PASS
identity preservation: PASS
turn reconstruction: PASS
thread projection consistency: PASS
native command failure preservation: PASS
```

当前 interactive REPL 保存 raw `app-server-events.jsonl`、adapter traces 和 semantic snapshots；
它消费 normalizer，但未接入 writer。canonical 文件规则适用于使用 writer 的路径，
不能将已有 thread-only diagnostic 文件提升为 run canonical。

### Runtime Facts And Web Contract

UAEA 向 Harness 投影最小 runtime facts、effective capability state 和 bounded semantic state：

```text
model/provider
Harness native filesystem/shell policy
shell network restriction
UAEA dynamic web.search/web.fetch availability
effective semantic constraints / ownership / scope
```

Harness 负责承载 context、thread history、token window、compaction 和
generic execution；UAEA 负责 capability-specific semantics。

Web semantic boundary 已冻结到当前研究所需的最小范围：

```text
web.search input:
  provider
  allow_fallback
```

执行结果单独记录：

```text
requested_provider
actual_provider
fallback_occurred
fallback_reason
```

显式 provider 且缺少 `allow_fallback` 时 fail-closed，不静默降级。搜索结果
同时区分 raw provenance、candidate evidence 和 citable evidence。低相关
结果保留在 raw trajectory/source history，但不作为 model-visible citable
evidence。

本轮进一步闭合两项边界：

```text
provider 已指定 + allow_fallback 缺失
  -> semantic validation failure
  -> error_kind=semantic_validation
  -> retryable=true
  -> retry_instruction 明确要求补充 true/false
  -> 不执行搜索
```

dynamic adapter 的 model-visible projection 对 `low_relevance` 做最后一道
bounded gating：

```text
raw_search_results / raw_results_before_filtering
  -> 保留在 ToolResult、SQLite/source history 和 trajectory provenance

Harness/model-visible result
  -> citable_results=[]
  -> candidate_evidence_results=[]
  -> bounded_evidence_block 不含 raw URL
  -> recommended_next_action=revise_query
```

已有真实 App Server artifact：

```text
D:\UAEA-runtime\h3-results\interactive-32768-20260923-124100\app-server-events.jsonl
```

证明 dynamic tool 的 `status=failed` 结果可以进入同一 turn 的 Harness
continuation，并触发模型发起修正后的下一次 tool call。当前 semantic
validation result 使用同一 App Server tool-result channel；本轮没有新增
planner 或 retry subsystem。

## Ownership Freeze

Harness owns：

```text
thread persistence
turn lifecycle
context transport
token window
compaction mechanics
native file/shell/sandbox execution
generic tool protocol
retry / continuation / execution lifecycle
raw event emission
```

UAEA owns：

```text
capability-specific semantic contracts
Runtime Facts / Effective Capability State
Web provider/fallback/evidence semantics
semantic extraction / classification / ownership / scope
effective semantic state / bounded projection / action validation
trajectory normalization and provenance preservation
future Goal Hypothesis / Problem Space / Boundary
future Working Memory / Memory / Episode / Experience / LoRA
```

UAEA -> Harness boundary：

```text
additionalContext
dynamicTools
model/provider selection
sandbox / execution policy inputs
bounded capability results
```

Harness -> UAEA boundary：

```text
ordered App Server events
tool calls/results
native command execution state
token usage
compaction markers
errors/cancellation
turn/completed
canonical raw trajectory
```

## Residual Risks

以下问题已被确认，但不阻止 generic Harness baseline freeze：

```text
full thread history may pollute later turns
compaction internal input/output details are only partially exposed
modelContextWindow may differ from configured 32768
model may overgeneralize shell network restrictions
model may cite URLs outside returned citable_results
Google provider implemented via SerpApi; availability/quota remain external risks
provider/domain/source constraints remain partly best-effort
system PATH may still warn about bubblewrap although bundled bwrap works
```

这些问题分别属于 UAEA future cognition/evidence work、provider capability
limitation 或环境残留风险，不构成 generic Harness lifecycle blocker。

## 后续边界

当前不继续扩展：

```text
Goal Engine
Memory Manager
Working Memory implementation
Web provider redesign
Codex Core fork
新的 generic Runtime subsystem
```

下一阶段应进入 UAEA-owned：

```text
Goal Hypothesis
Problem Boundary
Epistemic Update
Memory / Episode architecture
trajectory evaluation
```

只有出现以下架构级事实时才重新打开 Harness 集成：

```text
缺失稳定的 pre-turn lifecycle hook
关键 tool/result/error/compaction state 无法观察
无法重建 thread/turn/item identity 或事件顺序
tool result 后无法恢复 model continuation
当前 pinned runtime 无法可靠执行 native sandbox
generic runtime capability 确实无法由 App Server 提供
```

## 历史文档

完整研究过程和旧阶段结论保留在：

```text
docs/archive/harness/harness-feasibility-20260912.md
docs/archive/harness/pre-harness-freeze-20260912.md
```

H3 diagnostic scripts、trajectory implementation 和测试继续保留在当前
源码路径，用于复现和回归，不作为新的 Harness 扩建计划。

## 历史：Scoped Semantic Bridge 边界修正（2026-10-01）

以下保留当时 checkpoint 与测试结果，不是当前 provider 状态。Google 已于 2026-10-02
接入 SerpApi；后续授权、observation 和候选身份修复以当前 Boundary Audit 为准。

本轮修正 extraction 到 state 的绑定边界，保持 Harness 执行路径不变。
`TurnRelation` 只描述关系，不再统一清空语义项。Google 只作为 probe，
scope resolver 不识别 provider 名称，也不改变 WebAdapter provider resolution。

Phase-1 审计与实际复用：

- `RuntimeObjectRecord` 已有 `object_type`、`owner`、`status`、source identity 和
  `metadata`；语义项复用该记录，在 metadata 中补 `kind/key/value/scope/strength/provenance`。
- `RuntimeObjectStore.objects` 保存全部记录，过期与替换只改变 status，保留来源。
  旧 `snapshot()` 未投影通用 objects，因此 bridge diagnostic snapshot 单独包含
  `semantic_items`，同时保留原有 Phase-1 snapshot。
- `WorkflowRunRecord` 只承载 task identity/status；不调用会自动创建 ActiveGoal 的
  `record_workflow_candidate()`，不启动 workflow plan、step 或工具执行。
- `ContextManager`、`TurnRelationRecord`、`ExecutionObservation`、
  `SemanticObservation`、`ProjectionRecord` 继续复用。
- ActiveGoal 与旧 workflow execution lifecycle 有 goal/step 语义，不能直接表达
  session/turn-scoped item；本轮仅审计，不激活。

最小新增 `ScopedSemanticResolver` 与 `EffectiveSemanticState`：现有记录足以保存
数据，但没有通用 scoped-item 到期、替换、生效规则。resolver 是 object store 的
薄扩展，不是新 SemanticState framework，也不是第二套 runtime。

每个跨 turn 项都有 kind、owner、scope、strength、provenance 和 status。
当前支持 topic、capability constraint、reference、open question；执行 observation
仍由现有 observation contract 保留，不推断 Goal/Memory/Episode。

Scope/lifecycle：

- `turn`：owner 为 UAEA input identity，在 terminal boundary 或下一 input 时过期。
- `task`：owner 为 Phase-1 workflow identity，延续/引用/质疑保留；明确切换 owner 后过期。
- `cross_task`：owner 为 semantic scope，在同一会话跨 task 保留。
- `explicit_until_revoked`：显式长期约束，直到同 owner/key 替换或显式撤销。
- 同 owner/scope/key 的新提取 supersedes 旧记录，保留原 provenance 和替换 identity。
  更窄 scope 的显式值优先；其到期后，未撤销的外层值重新生效。

最小自然语言 scope 识别：`本轮/this turn`、`这次`、`本会话/跨任务`、
`以后/所有搜索/直到撤销`。这是有限提取 surface，不是通用 ontology。
任务 owner resolver 仅在初始绑定或明确任务切换（如 `新任务/切换话题/new task`）
时更换 owner。无法确认的 topic/relation 变化保守保留 owner，并记录绑定原因；
尚未声称能自动识别任意隐含任务切换或回到旧 task。

`prepare_turn()` 先提取本轮语义、绑定 owner，再生成 bounded projection。
native turn identity 尚未到达时使用独立 UAEA input identity，不伪造 Harness turn_id；
后续原始 USER_INPUT/turn event 补充真实 identity 与 raw reference，不重复应用输入。

projection 和 action validation 共用唯一 effective-state resolver，记录相同
`effective_state_id` 和有效 constraint。projection 不裁掉有效约束；预算无法容纳时
显式报错，阻止提交不完整上下文。`ProjectionRecord` 保存实际 bounded 内容和来源 object IDs。

模型 proposal 与硬约束冲突时，在 ToolRegistry 执行前拒绝，不 silent rewrite。
validation observation 保留 proposal、decision、semantic owner/scope/source turn，
通过原有 dynamic tool result 允许 Harness continuation/retry。

人工复测：同 task 延续与引用、明确新 task 释放 task scope、长期约束跨 task 保留、
显式替换/撤销、projection 与 validation 一致。Google provider 未实现，严格 Google
应 fail-closed；本轮不以 Google 搜索成功为验收条件。

`Goal Hypothesis implemented: NO`；`Memory/Episode implemented: NO`；
`Codex Core changes: NO`；frozen `8001` 未修改。

本轮验证：semantic adapter/dynamic tool targeted tests 27/27；full unittest
192/192；Phase-1 scripted regression 24/24；`py_compile` 与
`git diff --check` 通过。真实模型人工复测尚待用户执行；以上结果证明 contract、
状态生命周期和执行前拒绝，不代表模型自然语言行为已完成复测。

## 历史：Web 执行结果与 Evidence 边界（2026-10-01）

以下 unsupported Google 示例仅记录当时未实现 provider 的行为，已被 Google backend 接入替代。
执行/evidence 分离原则仍有效；真实失败须使用实际 execution status，不能再默认解释为 provider 未实现。

Semantic Ownership / Scope / Effective State 保持阶段性 PASS，本轮不修改该层。
Web 结果增加独立 `execution_status`、`execution_succeeded`、`http_attempted`
与 `reason`。`access_status` 继续保留原有 ledger 的 `fetched/failed/unsupported`
语义；capability/model-visible `status` 表达执行分类。

- 执行分类：`success`、`unsupported`、`network_failure`、`timeout`、
  `http_failure`、`validation_failed`。
- Evidence 分类只在成功取得候选结果后进行；失败或无候选时
  `evidence_status=null`、`evidence_evaluation.performed=false`。
- 严格 Google：`unsupported`、`reason=provider_not_implemented`、
  `requested_provider=google`、`actual_provider=null`、`fallback_occurred=false`、
  `http_attempted=false`。observation 明确 provider 未实现，不推断 Google 网络不可达。
- 执行失败不生成 relevance metadata、`low_relevance` 或 `revise_query`。
  model-visible failure projection 优先执行事实，不把历史/raw candidate 数据暴露为 evidence。
- HTTP 成功但没有过滤后的候选结果，不进行 relevance evaluation。过滤前 raw results
  继续留在原 SQLite/source history；不能绕过过滤重新投影成候选。
- 成功且存在候选时，原有 relevant/uncertain/low_relevance 规则和 evidence gating 继续使用。

Requested provider 表示用户要求；actual provider 表示实际选择/请求的 endpoint provider；
两者都不能单独证明执行成功。网络失败可以有 actual provider，但
`execution_succeeded=false`，不得当作成功搜索。模型应使用执行结果中的
`reason/failure_explanation` 解释失败，而不是把用户请求或先前承诺当成事实。

工具响应即使被 bounded truncation 压缩，也保留失败分类、reason、requested/actual
provider 和 execution success。原始 observation/source history/trajectory 保留诊断来源。
Google provider 未新增，provider/fallback resolution 与 Codex Core 均未修改。
模型自然语言是否准确解释失败，仍需人工复测严格 Google case。

本轮验证：Web/dynamic adapter targeted tests 52/52，context/I/O/semantic bridge
regression 32/32，full unittest 199/199，`py_compile` 与 `git diff --check` 通过。
严格 Google model-visible observation 在 4000/1000 字符预算下保留 unsupported
原因和 requested/actual 区分，且不产生 `low_relevance` 或 `revise_query`。

## Failed Attempt Recovery 修正（2026-10-03）

人工 Web acceptance 发现 malformed FunctionCall 在 Harness 拒绝后仍作为 structured history
被下一请求重放，导致本地 vLLM 历史 JSON preprocessing 持续 HTTP 400。新增 UAEA provider-facing
history 投影仅改发送副本：明确 `REJECTED/FAILED/CANCELLED` attempt 转为不可执行历史 observation；
原始 rollout/trajectory 不删除、不覆盖。真实 Harness、真实 Qwen 普通对话及同 thread
磁盘恢复已通过；现有人工入口自动使用 loopback bridge，无需 fork Core。

ownership 仍由 Harness 承担 persistence/reconstruction/execution lifecycle，UAEA 承担安全投影。
不改 frozen `8001`、8002 inference profile、Web provider/proxy/timeout 或 semantic state。
范围、证据和未覆盖的 native/custom failure/compaction 见
[维护说明](../../implementation/harness/failed-attempt-recovery-20261003.md)。Web end-to-end 人工验收仍待继续。
