# Semantic Promotion Shadow Audit

Status: IMPLEMENTATION_NOTE
Role: longitudinal cognition 前置边界的第一阶段诊断；不是新 authority policy

当前状态更新（2026-10-05）：shadow audit / terminal snapshot 已通过最新人工补验，
见文末记录；下面各轮“等待人工”和测试计数保留其历史时点，不再代表当前未验状态。
后续 authority boundary 实现是独立阶段，其人工测试仍未进行。

## 本阶段只证明什么

在不改变 extraction、scope resolution、model context、authorization 或 Web execution
的前提下，观察 semantic item 的保留、生效、constraint surface、模型投影及 validation
snapshot。审计记录不得变成新的权限来源或被注入 additionalContext。

诊断机制通过自动验证不代表原有自然语言提取正确，也不代表 Goal 已实现。
本阶段结束后等待人工 architecture probe，不自动进入下一阶段。

## 实际路径与 ownership

`HarnessSemanticStateAdapter.snapshot()` 补充实际 resolver 已选中的
`effective_semantic_item_ids`、当前 `current_input_id` 和 `last_turn_id`；均为诊断字段，不进入模型投影。
`harness/semantic_promotion_audit.py::build_promotion_audit()` 只读取 snapshot 与已准备的
additionalContext；不调用模型、resolver、validator 或 capability，不修改输入。

人工入口在 PRE_TURN、POST_ACTION_VALIDATION、POST_TURN 将诊断追加到本 run 的
`semantic-promotion-audit.jsonl`。使用原 writer 的 run_id，audit_sequence 只表示审计记录顺序，
不是 canonical trajectory sequence 或 Harness 因果序号。

canonical run-level trajectory 仍是事件事实源；audit 是派生诊断。日志只保留 item/source
identity、scope、声明的 strength、生命周期和各表面 membership，不复制原始用户文本、
semantic value、tool arguments、HTTP URL、credential 或完整 model prompt；内容只保存哈希。
通过 item ID、input ID、projection ID、call ID 回查原有 snapshots/raw trajectory。

PRE_TURN 尚无新 native turn_id，因此 turn_id 留空、旧 turn 放在 prior_turn_id；通过 input_id
和 projection_id 与随后 native input/context 对应。准备过 context 不等于模型已收到它，
delivery 明确为 PREPARED_NOT_CONFIRMED。需要结合实际 turn/start 与后续事件确认。
pre-turn/action 阶段不额外复制完整 snapshot；snapshot_reference 会说明此阶段是否持久化。

## 不能混淆的含义

- `declared_strength=hard` 不证明 interpretation 正确或经过用户确认。
- `promotion_basis=NOT_RECORDED` 表示现有 record 没有独立 promotion 依据，不表示用户未授权。
- `in_current_constraint_surface` 需要实际 effective membership，不能仅比较字符串。
- `in_last_projection_constraint_surface` 是该历史投影的 item membership，不是当前 policy。
- 缺少旧 snapshot 的 effective IDs 时记录未知，不重建或猜测 resolver 的选择。
- `constraint_snapshot_item_ids` 只说明 validator 收到了哪些 item，不证明逐项 enforcement。
- `observed_validation_decisions` 仅记录 semantic action validation；`valid=true` 不表示
  schema validation 已通过，也不表示 HTTP 或其他 capability 已执行。
- Web decision 的 `authorization_state` 描述 fallback permission，不是整个搜索动作是否被授权。
- notices 是结构审计信号，不是自然语言正确性判定或新的 error taxonomy。

源文本保留了 provenance，仍不能证明其解释正确。审计不重新分类 topic/directive、不增加
关键词规则，也不修正已知商业 topic 被提取为排除项的行为。
审计文件打开、构建或写入失败仅输出异常类型，不输出异常内容，不阻断现有 turn/tool loop。

## 最小人工 Probe

使用既有入口，从新进程、新 thread 开始：

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

若原人工会话仍占用 8002，先在原 REPL 输入 exit；不复用旧代码进程，不启动第二个 inference。

一组两轮即可：

1. 自然提出研究方向和非排除性的来源偏好，例如：研究 AI agent 商业化方向，商业发布论坛和
   开发论坛都可以。观察 topic/source item 的来源、soft strength、是否进入 constraints 和
   application projection。当前仍可能出现错误排除项；本阶段要求准确暴露，而不是宣称修复。
2. 在同一任务上补明确执行要求，例如：继续这一方向，只使用 Google，不允许 fallback，
   先找一个公开资料。观察 provider/fallback item 的 hard 标签、source turn、scope、projection，
   若模型产生真实 tool call，比较 action_decisions、tool arguments、requested/actual provider。

可换研究主题、来源偏好或明确 provider，重点是三个表面是否被分开记录，而非某句话必须命中。
若模型没有提出 tool call，只验证 pre/post audit；不能把零 validation decisions 算作执行验证。
最终模型回答是观察对象，不是本阶段审计正确性的权威证明。

## 已验证与未解决

自动测试覆盖 audit 纯读取、topic 不被 auditor 授权、soft promotion 原样暴露、原 validator
接受/拒绝不变、source/native identity、supersession、turn expiration、旧数据未知、transport
区别、原始内容/credential 不复制、per-thread isolation，以及入口 append/noninterference、
审计写入失败隔离、post-turn 与 post-action hooks。

本轮验证：14 项 targeted tests、70 项相关 regression 通过；full unittest 共 317 项，
其中 311 项通过、6 项 skipped。WSL targeted tests 14 项通过；py_compile 和 diff 检查通过。

对 `D:\UAEA-runtime\h3-results\interactive-32768-20261005-104236` 只读重放：两个 soft
capability constraint 出现在已准备的 application projection；旧 snapshot 未保留当前
effective membership IDs，因此该字段明确未知。两个 attempt 均未进行 HTTP；一个在 semantic
validation 被拒绝，另一个通过该层后被 schema validation 拒绝。审计不将后者记为执行成功。
没有改写原 artifact，也没有新增实际模型或网络请求。

实现与自动验证 PASS；本阶段人工验收仍待新的真实 run，不因此进入后续阶段。

仍未实现：promotion gate、directive correctness、evidence 独立性计证、Goal、continuation
divergence、clarification policy、world conclusion validation。它们不是本阶段 PASS 的内容。
无需新数据库、ontology、confidence 算法、另一套 Runtime 或 Codex Core 修改。

## 人工验收后的最小补闭环

依据：`D:\UAEA-runtime\h3-results\interactive-32768-20261005-120237`。
canonical trajectory 可读且 sequence 验证通过；实际有 7 个 turn terminal boundary、8 个
Web attempt。明确的 Google / 禁止 fallback 指令出现在实际 tool arguments 中，且已有
真实 Google 执行成功。商业 topic 和来源偏好仍出现 soft constraint promotion，本阶段没有修正。

上一版人工入口把 `consume_raw_event()` 返回的所有 dict 都当成 terminal snapshot。
该接口既返回 observation record，也返回完整 state snapshot，导致 16 条 observation
被误写成 TURN_COMPLETED / POST_TURN，总计 23 条；这些伪 post-turn audit 缺少 thread identity。
这属于 UAEA 诊断消费者边界错误，不是 Harness 多结束了 16 个 turn。

本轮只在入口使用现有 `SEMANTIC_STATE_SCHEMA` 区分完整 snapshot 与 observation，
并防止 observation 被直接传入 shadow journal 冒充 snapshot。没有改 adapter 的状态更新、
projection、scope、授权或执行；没有新增 ontology、错误分类或另一套事件 hierarchy。
observation 仍由 adapter 消费并保留在 semantic state 中，其原始事实仍进入 raw event log 和
canonical trajectory；它不再触发 terminal snapshot / POST_TURN 诊断。

旧 artifact 不修改、不删除。分析旧 snapshot 文件时不能仅凭外层 event 标签识别 turn completion，
必须核对 snapshot schema、native identity 和实际 turn/completed。旧 audit 中无 identity 的
伪 POST_TURN 是诊断缺陷，不是额外 evidence 或真实 terminal boundary。

同一真实 run 经修复后的入口离线重放：7 PRE_TURN、8 POST_ACTION_VALIDATION、7 POST_TURN；
无空 thread identity。2561 条接收记录均经过原始事实记录路径，每轮 constraints 与原 run
相同；四个输入 artifact 的哈希未变，没有新增 HTTP、模型调用或 inference 进程。

本轮验证：18 项 targeted tests、83 项相关 regression、WSL 18 项 targeted tests 通过。
full unittest 共 321 项，315 项通过、6 项 skipped；py_compile 和 diff 检查通过。
新增回归覆盖 tool rejection observation、native command failure observation、实际 terminal
snapshot、直接误传 observation、failed/cancelled terminal identity 和事实记录保留。

当前状态：实现与自动/离线验证 PASS；新的人工补验待完成。不要据此宣称 promotion authority
或 Goal 已闭环，也不自动进入 promotion gate 实现。

最小补验只需新 run 两轮：

1. 请求检索一份公开资料，明确 Google / 禁止 fallback，并给出非排除性来源偏好。
   至少出现一个真实 tool call。核对每个 tool result 在 raw/canonical 中保留，但只有实际
   turn/completed 产生完整 snapshot 和一条 POST_TURN；timeout/rejection 也不能冒充 turn completion。
2. 继续同一方向。核对下一轮 PRE_TURN 的 constraints 与既有 projection 一致，native
   thread/turn identity 完整，每个实际完成的 turn 对应一条 POST_TURN，而不是按 tool result 数量增加。

若第一轮没有 tool call，此补验只能算 PARTIAL。不要为了制造失败调整网络或授权规则。
偏好错误 promotion、多个原始 surface 对应同一 call 的独立性问题、最终回答的无证据结论仍未解决。
这些必须与本轮只修正诊断分类的范围分开。

## 最新人工补验与阶段结论（2026-10-05）

真实 run：`D:\UAEA-runtime\h3-results\interactive-32768-20261005-122040`。
实际 8 个完成 turn 对应 8 个完整 snapshot / POST_TURN，8 PRE_TURN、9 POST_ACTION_VALIDATION，
identity 完整，canonical run-level trajectory 存在；tool observation 不再伪造 terminal snapshot。
9 次调用保持 Google / no fallback；3 success、4 timeout、2 schema rejection。
通过的是 audit/terminal 诊断边界与既有 directive 保持，不把 semantic validation accepted
等同于 schema accepted 或 HTTP executed。

shadow audit 阶段及 terminal 补闭环：PASS。来源 soft interpretation 曾进入 constraint surface
的现象已准确暴露；后续 [authority boundary](semantic-authority-boundary-20261005.md) 处理
retention/authority 分离，不能用本次旧上下文下人工 PASS 替代其新上下文人工测试。
最新整体状态和停止点见 [checkpoint](../../current/architecture/cognition-boundary-checkpoint-20261005.md)。
