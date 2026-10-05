# Semantic Authority Boundary

Status: IMPLEMENTATION_NOTE
Role: longitudinal cognition 前置边界的第二阶段；不是 Goal/Memory 或新的理解引擎
Human acceptance: NOT TESTED（2026-10-05 整理时尚未人工测试）
Stage verdict: PARTIAL（实现/自动验证 PASS，等待新进程人工 probe）

## 有限目标

把 retained interpretation 与 execution constraint 分开。保留原来的 semantic item、
provenance、scope 和生命周期，但不能仅因 kind、strength、来源存在或投影位置而增加权威。
只保护当前已有 Web directive contract 的执行效力，不实现通用自然语言 directive recognition。

前置人工补验：`D:\UAEA-runtime\h3-results\interactive-32768-20261005-122040`。
实际 8 个 turn completion 对应 8 个 snapshot / POST_TURN，8 PRE_TURN、9 action audit，
identity 完整。Google / 禁止 fallback 指令在 9 次调用中保持；执行事实为 3 success、
4 timeout、2 schema rejection。该补验通过的是诊断边界，不是所有模型行为。

## 最小路径与 ownership

- `semantic_authority.py`：纯 metadata contract 检查；没有模型调用、推理、confidence 或 planner。
- `scoped_semantics.py`：复用 Phase-1 RuntimeObjectRecord，保留全部记录；qualified constraint 与
  interpretation 分开读取。scope/owner 优先级不变；同 key 的两类记录不能相互 supersede 或遮蔽。
- `semantic_state_adapter.py`：沿用现有 extraction，不新增关键词规则。只有现有 user-input Web
  directive 路径创建 promotion basis。pre-turn projection 和 action validation 共用 effective view。
- `io_contract.py`：qualified constraint 走 application context，其余 semantic context 走 untrusted。
  使用同一 authority predicate 校验 binding，不能凭 authority schema 标记增加执行约束。
- `semantic_promotion_audit.py`：只报告记录的 authority、basis 引用和 interpretation transport，不授予权威。

Harness 仍管理 history、turn、tool execution 和 context transport。Phase-1 Agent.handle、
File/Shell/Sandbox、ActiveGoal、Goal Hypothesis、Memory 均未接回或新增。

## 信息与权威含义

semantic item 的 `authority_level` 为 interpretation 或 execution_constraint。
`promotion_basis` 独立于 strength，引用原 user input_id、具体 contract key/value。
获得执行效力需要现有 user-input contract、来源类型和相同 input/key/value 共同匹配。
只有 web.provider、web.fallback、web.exclude_provider 的已有 contract 在本阶段可获执行效力。
model message、tool result、缺少依据的 hard record 或 world/Goal 判断不会因此获得执行授权。

这些是内部受控 producer 的记录边界，不是 cryptographic authentication，也不是任意外部 JSON
可授予权限的公共入口。provenance 的存在仍不证明解释正确。
`existing_web_user_directive` 表示现有有限规则识别的用户执行要求，不能宣称所有自然语言已经
被正确识别；false positive、引用/反问/复杂否定等理解质量仍未闭环。
已有源码中的 source extraction 错误仍保留为 interpretation，例如商业 topic 仍可能产生
exclude:commercial_promotional；本轮不把该结果当成 user directive，也不修其理解算法。

source_preferences 留在 diagnostic snapshot 和低权威 context，不进入 authoritative constraints。
连明确的“只关注论文”等来源措辞，在本阶段也未新增排他性 source directive contract；
它会被保留供模型理解，但不能声称 Runtime 已结构化强制执行此类限制。

## 投影与历史

`uaea.semantic_state_projection` 的 application entry 仅含 qualified constraints、对应 binding
和必要 identity；topic、source preferences、task evolution、references、open questions、
observations 与 interpretation records 在 `uaea.semantic_interpretations` 的 untrusted entry。
untrusted 表示不具备执行授权，不表示内容为假。模型仍可能错误理解它，必须经人工验证。
语义 payload 沿用现有 bounded budget；拆分 transport 会增加有限的 envelope/identity 开销，
没有改变模型 context window 或 vLLM 参数。预算不足时可以减少辅助 interpretation 投影，
完整记录仍在 semantic state / canonical trajectory；qualified constraints 不静默丢弃。

旧 metadata 缺 authority/basis 时不 grandfather 为新的执行授权；原 artifact 仍按历史事实读取，
不迁移、不改写。已有 Harness history 里的 application context 不会被追溯降权，因此本阶段
人工验收必须新进程、新 thread；full-history working-set治理不在本阶段。

## 自动与离线验收

测试覆盖 strength/provenance 非授权、basis 精确绑定、agent source 不授予权限、缺 metadata、
同 key interpretation 不覆盖 directive、directive replacement、共同 projection/validation view、
untrusted transport、projection 不能自造 fallback permission、world/Goal 不属于 Web directive、
local rejection 与 model proposal 不更改 authority，以及 thread isolation。
既有 scope、撤销、native provenance、failed/cancelled terminal 和 dynamic-tool 回归继续保留。

最终自动验证：新增 authority targeted tests 15 项通过；相关 regression 101 项通过；
full unittest 336 项中 330 项通过、6 项按既有条件跳过；WSL authority/state/audit
相关测试 51 项通过。8 个修改或新增的 Python 文件 py_compile 通过，git diff --check
通过。WSL 出现已有 datetime.utcnow deprecation warning，本阶段未扩大范围处理。
实现与自动验证状态为 PASS；新进程下的真实模型行为尚待人工验收，阶段闭环仍为 PARTIAL。

最新真实 run 的离线重放：8 turn / 9 action；Web directive validation 决策不变，来源
interpretation 仍保留但不进入 authoritative constraints。application view 与 validation 相同，
interpretation 走 untrusted，payload 最大 2276 字符；2181 条接收记录仍经过事实记录链路。
原 artifact 哈希不变，没有新增实际 HTTP、模型调用或 inference 进程。

## 最小人工 Probe 与停止点

仍使用既有入口；若 8002 被旧会话占用，先在原 REPL 输入 exit，不开第二个 inference：

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

一组两轮：

1. 请求研究 AI agent 商业落地，商业发布论坛和开发论坛都可以；明确只使用 Google、禁止 fallback，
   检索一个公开案例。换研究主题也可以。观察 source extraction 是否仍保留，但 constraints
   只含有依据的 Web directive；basis 的 input_id 与 native provenance 可对应。
2. 继续同一方向，要求补充一个厂商公开发布中的落地案例。观察 provider/fallback 持续、投影
   与 validation 一致；来源偏好不能被投影成禁止商业案例的执行限制。

在 raw additionalContext 中观察 application / untrusted 两条 entry；在 snapshots/audit 中核对
promotion basis 和 item identity；在真实 tool arguments/result 中核对 requested/actual provider。
若没有 tool call，只完成 state/projection 验证，执行及模型行为仍为 PARTIAL。
若模型仍从 interpretation 中错误生成限制，记录为未闭环的模型行为，不把它冒充 Runtime directive。
网络超时或 schema rejection 不改变本阶段既有授权规则，也不推断资料不存在或 Google 不可用。

实现与自动验证通过后停止等待人工，不继续接 Goal、Memory、独立证据计数、clarification、
continuation divergence、history summarizer 或 truth engine。
