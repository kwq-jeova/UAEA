# UAEA Boundary Integrity Audit（2026-10-02）

> Status: CURRENT
> Role: CURRENT_BASELINE / 边界完整性
> Phase: 2026-10-02
> Still valid: 当前语义/执行/evidence contract；Web 人工验收仍 PARTIAL
> Superseded: 无
> Current reference: [Documentation Guide](../../README.md)
> Governance reviewed: 2026-10-02（文档治理，不等于新实验验证）
> 当前 contract 与历史验证记录分开阅读；本轮仅治理文档，不重新运行模型验收。

本文件是当前 semantic/Web 集成阶段的审计入口；generic Harness Runtime Baseline 已冻结，
不因本轮 UAEA 边界修复重新打开。没有修改 pinned `rust-v0.154.0`、Phase-1 子模块或 frozen `8001`。
Web backend 已可通过 SerpApi 获取 Google 结果；本轮修复后仍需人工确认 search → fetch 的自然行为。
Goal Hypothesis、Memory、Episode、Experience 尚未接入。

## 2026-10-05 阅读指引

本文件的正文、测试计数、PARTIAL 与等待人工段落保留 2026-10-02 时点事实。
后续 failed-attempt recovery、canonical writer 接入人工入口、shadow audit 与 authority 分离
的当前状态统一见 [信息边界 checkpoint](cognition-boundary-checkpoint-20261005.md)。
尤其不要把下表旧“interactive 未接 writer”当成当前缺口，也不要把旧 constraints/application
范围当成最新执行权威：qualified directive 与 retained interpretation 现已分开，最新迭代人工未测。
历史审计仍可用于具体缺陷和原验收证据，但不再独自决定后续阶段状态。

## 证据与判定

审计基于当前代码与真实 run `interactive-32768-20261002-115606`：

- `app-server-events.jsonl` 第 239、1450 行：内部 5 个候选在模型可见响应中只剩 count，没有 `citable_results`。
- 第 1612 行：模型生成 `example.com` 链接；adapter trace 第 6–10 条抓取这些虚构链接，得到 HTTP 404。
- 原始 Google 快照、source history 和内部候选包含真实 URL，没有这些 `example.com` 链接。
- `semantic-state-snapshots.jsonl` 中成功的 raw `function_call_output` 曾被恢复为 failure，且仅保留未解析响应。

第一次候选身份丢失发生在 `HarnessDynamicToolAdapter._bounded_json_text()` / `_fallback_data()`，
不是 Google connectivity 或 SerpApi 返回错误。模型随后编造链接是独立行为风险，不能仅靠修复裁剪保证消失。

## Boundary Matrix

表中“压力”表示转换是否迫使下游猜测；“修复后”不等同于模型自然行为已人工验收。
`CONFIRMED DEFECT → CLOSED` 仅用于已有路径和可复现证据支持的修复。

| Boundary：输入 → 输出 | 语义身份 | Ownership / scope | Provenance | Actionability | 幻觉压力 | 分类与证据 |
| --- | --- | --- | --- | --- | --- | --- |
| User input → Intent Relation / `TurnRelationRecord` | 保留原输入、关系标签 | task owner 独立于 relation | thread/turn/input/raw reference | 有限 continuation/reference/challenge/new-task 判定 | 隐含任务切换可能误判 | PARTIAL；`semantic_state_adapter._classify_relation()` 为有限启发式，不是通用意图推理 |
| Phase-1 `ActiveGoalRecord` / anchor → 当前 bridge | 代码仍存在，不激活 | 旧 goal/step scope 不冒充 semantic item scope | 保留冻结子模块历史 | 不参与当前投影/执行 | 不声称已推断长期 Goal | FUTURE COGNITION；`ActiveGoal` 不等于 longitudinal Goal Hypothesis |
| Task / `WorkflowRunRecord` → scoped semantic items | topic/constraint/reference/open question 保留 typed record | owner 与 turn/task/cross_task/explicit_until_revoked 明确 | source turn/item + supersession identity | 生效、到期、替换可解释 | 不在 new_task 无条件清空全部对象 | CLOSED；`scoped_semantics.py`，过期记录不删除，不启动旧 workflow 执行 |
| Semantic extraction → `EffectiveSemanticState` | kind/key/value/strength 保留 | 共用 resolver 选取生效项 | 每项保存 Phase-1 object ID 与来源 | projection 与 validation 使用同一状态 | 不以 summary 替代权威约束 | CLOSED；有限自然语言提取覆盖范围仍是 POTENTIAL RISK |
| Effective state → bounded pre-turn `additionalContext` | 有效约束保留 | projected item 保留 owner/scope | `ProjectionRecord` + source IDs | 无法容纳有效约束时显式失败 | 不注入缺失硬约束的残缺上下文 | CLOSED；`prepare_turn()` 先物化当前输入，后投影，不复制完整 planner context |
| `ContextManager` → semantic context summary | summary 是辅助表示 | 权威仍在 typed effective state | snapshot 保留独立记录 | 模型获得小型任务相关上下文 | summary 不授予新权限 | CLOSED；旧 generic runtime 不恢复 |
| Model `allow_fallback=true` → semantic validation | proposal 与 authorization 分离 | policy 来自有效 scope | source item / user turn / decision | unknown/denied 拒绝，granted 才允许 | 不把询问授权升级成授权 | CONFIRMED DEFECT → CLOSED；`validate_tool_action()`，不 silent rewrite、不加 planner |
| Dynamic tool call → `ActionRequest` / registry execution | canonical capability、arguments、request identity | Harness 控制 tool lifecycle，UAEA 校验语义 | thread/turn/call → request/observation ID | 原 registry/capability 执行 | 不混用 Harness-native Web | CLOSED；`codex_dynamic_tools.dispatch()`，ToolRegistry 执行前校验 |
| Raw tool output → `ExecutionObservation` / `SemanticObservation` | 解析 typed JSON result，不仅保存字符串 | observation 属于当前 task | item/raw-response/call/native IDs 保留 | `execution_succeeded`/`ok` 优先于 completed | lifecycle 完成不再冒充执行成功 | CONFIRMED DEFECT → CLOSED；`_tool_result_payload()` 与 `_record_observation()` |
| Native `commandExecution` → observation | start/delta 不产生终态结果 | Harness 原 sandbox ownership 不变 | item/turn/raw reference | terminal `exitCode` 判定成功/失败 | 不由 started 抢占 completed | CONFIRMED DEFECT → CLOSED；command terminal 与 `success=false` 测试 |
| Tool / retryable ERROR → semantic item lifecycle | 错误保留但不伪造 turn completion | 非 terminal 错误不提前到期 turn 项 | 原事件 identity | 同一 turn 继续/修正保持约束 | 不因可重试错误丢约束 | CONFIRMED DEFECT → CLOSED；item error / `willRetry` 与 terminal 区分 |
| Old-task observation → next-task projection | 原 observation 保留 | 只投影当前 task observation | 记录中增加 task/scope，历史仍可审计 | 新任务不读取旧任务“当前结果” | 降低跨任务结果误绑定 | CONFIRMED DEFECT → CLOSED；不实现新 Working Memory engine |
| `RuntimeObjectStore.snapshot()` / `ProjectionRecord` → diagnostic snapshot | 旧 snapshot 非完整 store 序列化 | bridge 另含 semantic_items / last_projection | object IDs + raw provenance 可查 | 可诊断，未承诺完整恢复进程状态 | 不把简化 snapshot 宣称完整持久化 | PARTIAL；Phase-1 store 不变，bridge 补充结构化投影 |
| Provider request → Google/SerpApi execution fact | requested / actual / status 分离 | fallback 受 effective policy 与 contract 控制 | source/access IDs、backend、不含 key 的 URL | strict 失败不执行其它 provider | 不把请求 Google 当作成功 Google | CLOSED；真实 Google 成功；自然语言遵循 execution truth 仍为模型风险 |
| Execution result → Web evidence eligibility | 仅成功且有候选才评估 relevance | 约束过滤沿用 capability contract | raw candidates 留 source history | failure 不建议 revise_query；low_relevance 不可引用 | coarse relevance 不是 Goal relevance | CLOSED（执行/evidence 分离）；PARTIAL（来源/时间/相关度质量，不新增 ranking） |
| Eligible candidates → bounded tool result | retained `title` + `url` 成对完整 | source/access/observation identity 保留 | 最小 `EvidenceReference`、顶层调用 identity | 减 snippet/数量；count 与实际列表一致 | 不再只有 count 而迫使编造 URL | CONFIRMED DEFECT → CLOSED；预算 5000/2000 与真实数据离线重放 |
| File / generic result → bounded result | path/handle/content_ref/hash 不截为无效字符串 | 已有 capability owner 不变 | source/reference/request/native IDs | 最小身份超预算显式失败 | 不拿残缺 URL/path 冒充可执行目标 | CONFIRMED DEFECT → CLOSED；通用身份字段 invariant，不新增 File 实现 |
| Network diagnostics → model-visible observation | 内部诊断完整，模型侧移除 | 仍属于原 access event | trace / SQLite 关联完整 | 保留执行事实与可引用证据 | 不消耗预算复制网络诊断 | CONFIRMED DEFECT → CLOSED；小 payload 同样不暴露诊断 |
| Raw events → normalizer / writer / reader | raw 与 normalized 并存 | run canonical，thread derived projection | native IDs + UAEA receive sequence | reconstruction / terminal 可恢复 | 不把 sequence 称为 Harness 因果号 | CLOSED（基础设施）；PARTIAL（interactive 当前保存 raw/traces/snapshots，未接 writer；老 artifact 不必有 canonical） |
| Full history / compaction → future cognition input | Harness 保留 history，外层先消费 raw | transport/compaction 属 Harness，relevance 属 UAEA | compaction marker 可观察 | 内部压缩输入输出细节部分可见 | 历史污染仍可能影响模型 | PARTIAL / FUTURE COGNITION；不构成现有 Harness freeze blocker |

## 修复边界与通用 invariant

**可减少数量和辅助文本，不能破坏保留对象的最小语义身份、ownership、provenance 与 actionability。**

- Search 先移除诊断、重复元数据、长 snippet，再减少候选数量；retained title/url 不截断。
- `eligible_result_count` 表示投影前 eligible 数量；`citable_result_count` 表示当前投影列表数量。
- 没有完整候选能装入预算时明确 `identity_exceeds_budget`、空列表、`report_projection_limit`；不指示 fetch 猜测链接。
- 最小执行/来源 envelope 也无法容纳时抛出显式预算错误，不输出超预算或残缺身份。
- `requested_provider`、`actual_provider`、`execution_succeeded` 同时保留；网络诊断只在内部。
- 模型 proposal 不是 user authorization；unknown/pending 不因模型提出 true 而变 granted。
- typed result 解析、command terminal 与任务相关 observation 投影均为薄 adapter 修复；不启动第二套 Agent lifecycle。

## 未扩大实现的风险

有限输入提取长度/规则、隐含 task arbitration、任意“第一个方向”的对象绑定仍不等于通用 semantic understanding。
raw/native 两种表达可能产生不同 event identity；不能把接收顺序或 snapshot 误称内部因果或完整持久化。
模型仍可能违反返回事实、编造或引用未提供的 URL；用户明确给定的 URL 仍可 fetch，未新增全局 URL allowlist/truth engine。
SerpApi/代理可用性、配额、source/language/freshness best-effort 以及 coarse relevance 属 capability/model 残余风险。
不为这些潜在风险新增 provider、Meta Requirement DSL、Goal/Memory 或 Core fork。

## 当前状态与停止点

- Harness Runtime Baseline：CLOSED；Core fork：NOT REQUIRED。
- 当前可执行证据投影与语义授权/result 边界：自动验证通过后可交人工复测。
- Web Capability Baseline：PARTIAL，等待本次修复后连续 search → fetch 的人工确认，不把离线重放当 model-mediated acceptance。
- Phase-1 semantic architecture：通过 bridge 复用；旧 generic runtime/File/Shell/Sandbox 仅 legacy baseline。
- 历史文档保留并标记 superseded；当前架构入口为主 README、本审计和 Harness baseline。

仅在缺失关键 hook、身份不可观察、
无法投影必需上下文或 native runtime 确实不足等架构级证据出现时重开 Harness；不因未来优化重开。
本轮完成提交后停止，不自动进入 Goal/Memory/Episode 实现。

## 本轮验证

- 定向 boundary / semantic / Web / Harness regression：133/133；全量 unittest：253/253。
- 冻结 Phase-1 scripted benchmark `--mode scripted --level all`：24/24，子模块仍干净。
- 21 个修改/新增 Python 文件 `py_compile`，9 个 shell scripts `bash -n`，Windows Git `diff --check`：PASS。
- 原人工 artifact 只读重放：trace 第 2、5 条 eligible 搜索在 5000/2000 字符预算下均保留 3 个完整 title/url；
  第 3、4 条 low_relevance 继续保留空 citable 列表。来源 identity 完整，未修改原 artifact。
- 原 App Server raw output 重放：4 个成功、6 个失败均恢复成正确 typed observation，原 result 保留。
- 真实 credential 仅在内存比较原值/URL 编码值：仓库、Phase-1 tracked 文件、最近 3 个 interactive 和 2 个 backend
  run、diff/cached diff 共 454 个文件，匹配数 0；私有 env 权限 `600`，未入仓库。
- 没有启动新的 inference/model turn、扩大 workload、提高 timeout 或增加 retry。
- 这些结果验证结构 contract，不宣称已完成修复后的模型自然引用、搜索质量或跨站点 fetch 人工验收。
