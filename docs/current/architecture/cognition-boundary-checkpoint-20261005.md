# UAEA 信息边界整理 Checkpoint（2026-10-05）

Status: CURRENT_CHECKPOINT
Role: 当前集成状态、证据等级与停止点；不是新的 Goal/Memory baseline
Review date: 2026-10-05
Human acceptance: 最新 semantic authority 迭代 NOT TESTED

## 本次保存什么

保存 Harness Runtime Baseline 之后累积的 provider-safe history、recovery observation、
生成诊断、model-visible observation guard、semantic shadow audit 与 authority boundary，
以及此前未提交的文档分类与兼容入口。今天只整理、复核、提交和上传，不新增执行能力。

本次整理前主分支 HEAD 为 `1993143`；generic Harness freeze commit 为 `211379a`。
Phase-1 子模块仍为 `1f311291df027baceca40779643e5107b9eb6fb3`，不恢复旧执行栈。
上传保存的是待人工验收的集成 checkpoint，不能解释为新 authority 或完整 Web acceptance 已 PASS。

## 当前状态

| 能力 | 已成立的有限结论 | 尚未证明 |
| --- | --- | --- |
| 本地 Harness / inference | source-owned `rust-v0.154.0` app-server + 本地 vLLM；generic runtime baseline CLOSED | 不因此证明 UAEA cognition 已实现 |
| Native execution / sandbox | 已冻结的 File/Shell/sandbox 路径保留 | 不恢复 Phase-1 File/Shell/Sandbox |
| App Server I/O / trajectory | typed pre-turn context、dynamic tools、terminal hooks；raw + canonical run JSONL + reader 可追溯 | compaction 内部细节仍 PARTIAL；不是 memory consolidation |
| Failed-attempt isolation | factual history 保留，provider-facing 副本安全投影；已有同 thread/reload 恢复证据 | 不能把失败调用重新视为待执行 dependency |
| Rejection recovery | 拒绝原因、surviving constraints、授权作用域和合法新 attempt 的恢复信息可投影 | 任意模型输出均能自主正确恢复未证明 |
| Google backend / Web contract | Google 经 SerpApi；provider/fallback、执行/evidence 分离、secret isolation 保留 | Web 整体仍 PARTIAL；不宣称所有 query/fetch/引用质量已验收 |
| Observation guard / parser diagnostics | 真实执行事实与证据充分性分离；可 opt-in 观察 bounded pre-parser 证据 | 自然语言回答仍可能误归因或无证据声称执行完成 |
| Semantic ownership / scope | 复用 Phase-1 对象、有限 relation、生命周期与共同 effective view | 非通用意图识别；不是长期 Goal 稳定性 |
| Shadow promotion audit | 最新人工补验 PASS：8 个真实完成 turn 对应 8 snapshot / POST_TURN | auditor 不判断解释正确性，不授予执行权威 |
| Semantic authority boundary | 实现与自动验证 PASS；retained interpretation 与 qualified constraint 分离 | 新进程下人工测试未进行；阶段整体 PARTIAL |
| Goal / Memory / Episode | 思想与旧资产保留 | 新 cognition engine 未实现，本轮不推进 |

## Ownership 与实际调用链

```text
User input
  -> UAEA semantic extraction / scoped records
  -> qualified execution constraints + retained interpretations
  -> bounded typed additionalContext
  -> local Codex app-server
  -> local provider-history bridge / safe provider projection
  -> local vLLM / Qwen
  -> model action proposal
  -> UAEA semantic validation / capability input validation
  -> ToolRegistry / existing capability
  -> execution fact / evidence eligibility / bounded observation
  -> Harness continuation / terminal event
  -> raw event + canonical trajectory + derived snapshots/audit
```

Harness owns thread persistence、turn/tool lifecycle、model invocation、context transport、
token window、compaction mechanics 和 native generic execution。
UAEA owns capability-specific contract、semantic scope/lifecycle、promotion basis、action validation、
provider-safe context projection、execution/evidence observation 及未来 cognition。
`provider_history.py` 与本地 `responses_bridge.py` 是外层边界，不修改 Codex Core 或 vLLM。

Runtime fact、interpretation、execution authority 和未来 Goal Hypothesis 不互相替代。
本轮整理不增加新的 hook、tool、planner 或第二套 execution lifecycle。

## 已建立的有限信息边界

- 信息保留不等于采纳，支持不等于授权，适用不等于真实，provenance 不等于 correctness。
- `strength=hard`、来源标签或 projection schema 标记本身不能授予执行效力。
- 现有有限 user-input Web directive 使用独立 `promotion_basis`，关联 input identity 与 key/value。
- topic/source preference 和无独立依据的 interpretation 保留，但不进入 authoritative constraints。
- 同 key 的低权威 interpretation 不能 supersede 或遮蔽 qualified directive；原记录不删除。
- pre-turn projection 与 action validation 使用同一 effective view。
- qualified constraints 使用 `application`；其余 semantic context 使用 `untrusted`。
  `untrusted` 表示不具备执行授权，不表示内容为假，也不是模型遵循程度的保证。
- 投影只能保留或减少权威，不能自行制造 fallback permission。

当前 authority 只覆盖既有 `web.provider`、`web.fallback`、`web.exclude_provider:*` contract。
它不是任意外部 JSON 的授权 API，也不是通用 directive correctness 判定。
例如商业 topic 仍可能被现有 extraction 解释成排除项；现在保留为 interpretation，
不能宣称其理解已经修复。新的排他性来源 contract 未实现。

## 真实证据与自动验证不能混用

最新真实人工 run：`D:\UAEA-runtime\h3-results\interactive-32768-20261005-122040`。
它产生 8 PRE_TURN、9 POST_ACTION_VALIDATION、8 POST_TURN、8 semantic snapshot，
并有 canonical run-level trajectory。9 次 Web attempt 均保持 Google / no fallback；
执行结果为 3 success、4 timeout、2 schema rejection。拒绝不等于 HTTP 已执行。
该 run 验证的是 authority 迭代之前的诊断和已有 directive 行为，不是新 authority 人工验收。

前一次 `interactive-32768-20261005-120237` 的 observation 曾被错误标成 POST_TURN；
原 artifact 保留。读取该记录必须核对 snapshot schema、native identity 与实际 terminal event，
不能按伪标签把重复表达计为新的 turn/evidence。详见 [shadow audit](../../implementation/harness/semantic-promotion-shadow-audit-20261005.md)。

上一轮对最新 run 的只读离线重放：8 turn / 9 action，directive 决策不变；来源解释保留但
不进入 authoritative constraints；application view 与 validation 一致。payload 最大 2276 字符，
2181 条接收记录保留，原 artifact 哈希不变，没有新增 HTTP 或 model turn。
这属于结构验证，不是新上下文下真实模型行为验证。

本次提交前重新运行的测试结果在末尾记录；历史文档的测试数量仅对应各自 checkpoint。

## 尚未解决与明确停止点

仍未解决：任意自然语言 directive correctness、旧 application history 的追溯降权、
模型误用 interpretation、同一 call 的多份记录独立性、local action failure 到 world conclusion
的无依据升级、稳定 Goal 与 materially different continuation 的判定。
这些不是本轮新增实现，也不因自动测试通过而视为解决。

未来认知研究遵循 high bar for promotion、low bar for retention；Goal cognition 与执行授权分离。
稳定 Goal + 新 evidence + continuation divergence 仍是待验证方向，不是已冻结算法或 schema。
不提前引入 ontology、confidence 阈值、完整 branch tree、error taxonomy、Episode/Memory schema
或 truth engine，不用新 keyword patch 替代架构验证。

当前只等 semantic authority 阶段人工结果；未通过前不自动推进下一阶段。

## 物理边界与人工入口

```text
RTX 5090 D v2 / 24GB VRAM / single GPU
Qwen2.5-14B-Instruct-AWQ / 4-bit AWQ / vLLM
frozen 8001: 原配置不变
diagnostic 8002: max_model_len=32768 / gpu_memory_utilization=0.75
Codex model_context_window=32768
--enable-auto-tool-choice --tool-call-parser hermes
```

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

使用仓库外 `~/.config/uaea/web.env`，权限 `600`；secret 不入仓库或 artifact。
authority 人工验收需新进程、新 thread；旧会话占用 8002 时先在原 REPL 输入 exit。
两轮 probe 与观察点见 [authority 阶段说明](../../implementation/harness/semantic-authority-boundary-20261005.md#最小人工-probe-与停止点)。
本次整理不启动 inference，不做网络或新的人工测试。

## 文档阅读与历史保留

本文件决定当前阶段状态和停止点；[2026-10-02 audit](boundary-integrity-audit-20261002.md)
保留原修复证据和仍有效的边界，涉及后续状态时以本 checkpoint 为准。
[Harness baseline](../runtime/harness-runtime-baseline-20260926.md) 决定 generic execution freeze；
[implementation notes](../../implementation/README.md) 保存逐轮实现和当时验证结果；
[research map](../../research/research-foundation-map.md) 保留思想血缘与未决问题。

先前文档治理的分类正文和 REDIRECT 一并提交，旧路径继续存在；本次不删除或搬移文件。
旧等待人工的段落作为当时事实保留，通过后续有日期的结果说明更新，不覆写历史为最新 PASS。

## 提交前验证

- full unittest：336 项，330 项通过、6 项按既有条件跳过。
- WSL authority/state/audit 相关测试：51 项通过；25 个待提交 Python 文件 py_compile 通过。
- 主 README 与 docs：74 份 Markdown，260 条本地文件/章节链接全部可解析。
- 24 对兼容路径 / 分类正文均存在；忽略相对链接目标与行尾空白后，原非空正文行按顺序完整保留。
  新注释和 header 不改写旧实验结论；本轮没有文件删除。
- 仓库、Phase-1 tracked/untracked 内容、最近三个真实 interactive run 及 working/staged diff
  的真实 SerpApi credential / URL 编码值仅在内存比对：517 个文件，匹配 0；不输出 secret。
- working/staged `git diff --check` 通过；最终清单为 99 个文件，仅含 Markdown/Python，
  54 个新增、45 个修改、0 个文件删除；staged diff 的真实 credential 检查同样零命中。
- 本次未重跑 Phase-1 benchmark、真实 Web HTTP 或模型人工验收；历史 benchmark 计数仍只属原 checkpoint。
- 已有 datetime.utcnow deprecation warning 保留，不为文档整理扩展实现。

最新 authority 人工测试状态固定为 NOT TESTED，不得由任何自动/离线结果替代。
