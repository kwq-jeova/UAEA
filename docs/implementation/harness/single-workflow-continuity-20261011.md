# 单 Workflow 事实续接验证

Status: IMPLEMENTATION_NOTE
日期：2026-10-11
状态：Runtime 事实组织与传输 PASS；整体模型行为 PARTIAL；可进入人工验收。

## 本轮边界

只改善单个持续 Workflow 的任务、行动、执行观察与下一轮投影，不实现 Memory、
跨 Workflow Goal Hypothesis、完整信息关系模型或新的执行 Runtime。
不修改 Codex Core、Hermes、Google backend、代理、timeout、authorization 或 frozen 8001。
inference 仍使用 Qwen2.5-14B-Instruct-AWQ、单 GPU、8002、32768、GPU utilization 0.75。

## 实际 ownership 与最小改动

- `harness/semantic_state_adapter.py`：相同 task owner 下，局部 relation 的 `new_task`
  提示不再直接覆盖初始 topic；明确任务切换仍沿用已有 owner/scope 规则。
- `harness/workflow_continuity.py`：复用 Phase-1 `WorkflowRunRecord` / `StepRunRecord`，
  按 Workflow、turn、call identity 归并调用及结果，只记事实，不执行工具、不规划步骤。
  `proposed` 不等于执行；validation 拒绝为 `rejected`；真实结果终结为 `completed` 或 `failed`；
  turn 取消且没有结果时为 `cancelled`，正常结束却没有结果时为 `outcome_missing`。
- 同一调用的 dynamic item、`OBSERVATION` 和 `function_call_output` 不生成多份独立执行观察。
  各 representation 的原生 identity、sequence、raw reference 保留在 step provenance 中；
  canonical trajectory 保留全部原始事件，完全不修改。
- assistant 普通文本与伪 tool JSON 不创建 Step、执行观察或已完成工作记录。
  普通 assistant 内容至多作为非权威 `assistant_proposal` 投影。
- `turn/completed` 生成事实 receipt：原生 turn ID、终态、独立 attempt 数、成功数、已观察结果数。
  零调用轮明确记录 0。`completion_established=false` 表示本适配器没有建立 Workflow 完成依据，
  不是新的 Workflow 完成判定器。
- execution success 与 evidence status 独立记录：`low_relevance` / `uncertain` 仍是证据不足，
  执行失败不进入 relevance；保留调用、结果与现有 evidence reference 的关联。
  `unresolved` 是 attempt 范围内尚未成立的结果/证据，不是可重放调用或 Workflow 阻塞依赖。

## Bounded projection

`workflow_continuation` 保存初始请求摘要、前一轮用户细化摘要，以及预算允许时的 assistant proposal。
当前用户输入已经完整经过 `turn/start.input`，不再在这里重复复制。
任务摘要和模型 interpretation 仍处于 `untrusted` surface，不授予执行权威。

`workflow_execution` 在 application surface 提供当前 Workflow 的最近 attempt 和上一轮 receipt。
这只为执行观察提供事实续接，不使工具输出中的文本、搜索摘要或来源声明获得 correctness 保证，
也不授予额外权限。完整 steps / outcomes 仍在 diagnostic snapshot 中。

预算仍为 2400 字符，并核对拆分后的实际 semantic `additionalContext` values 总长度。
runtime facts / capability state 的既有独立预算不计入这项 semantic budget，未借此增加新提示。
依次共享完全相同的 authority metadata 和 basis source identity、压缩 JSON 空白、裁减重复辅助信息。
每条 constraint 的 key/value、独立 basis key/value、owner/scope 与 provenance 可展开还原，
仍使用原来的 `has_execution_authority` 判定，不新增 promotion。
高压预算下可省略重复的 scope header；完整 scope identity 仍在 projection envelope、snapshot 和 binding owner 中。
有效 constraints 不能裁掉，若必要数据依然放不下，继续沿用局部 capacity rejection，不退出 REPL。

没有固定 Search → Fetch → Summary 流程，没有新 planner、关键词指代补丁或更大的 context window。

## 自动与历史 artifact 验证

- targeted regression：WSL 112 项 PASS。
- full unittest：`python -m unittest discover -s tests -t . -q`，359 项，353 PASS、6 skip。
  不带 `-t .` 会把 `tests/backend` / `tests/memory` 当成顶层包导致 discovery import 冲突；
  该错误 invocation 未用于业务回归结论。
- `py_compile` 与 `git diff --check` PASS。
- 私有环境加载后，只在进程内比对真实 credential 字节；扫描仓库及本轮三组 artifacts 共 475 个文件，
  secret matches=0，仅输出 availability/count，不打印 credential。自测结束后 app-server 与 8002 已停止。
- 原 `interactive-32768-20261011-095353` canonical artifact 只读重放：7 个 turn，
  3 个独立 Step、3 个执行观察，receipt attempts 为 `[1, 0, 1, 1, 0, 0, 0]`。
  四条 Google/provider/fallback constraints 完整保留；投影 2270–2342 字符。
  原 events 与 semantic snapshots 的 SHA256 未变。

## 真实 Runtime / Harness 自测

命令：`python3 scripts/h3_workflow_continuity_probe.py --turn-timeout 420`。
探针仅替代交互 REPL 的三次键盘输入；启动、provider-safe bridge、模型、dynamic dispatch、HTTP、
canonical trajectory 与 teardown 均复用真实人工入口，没有 mock inference 或预定义工具执行计划。

最终 artifact：
`D:\UAEA-runtime\h3-results\workflow-continuity-20261011-103831\interactive-32768-20261011-103831\`

- `app-server-events.jsonl`：原生事件与最终回复。
- `adapter/traces/`：真实 ActionRequest / execution observation。
- `semantic-state-snapshots.jsonl`：完整 Workflow facts 与 turn receipt。
- `normalized-trajectories/`：canonical run trajectory，reader/validator PASS。
- `workflow-continuity-summary.json`：实际 pre-turn projection、attempt、结果、receipt 与诊断摘要。

同一 Workflow ID：`cd8d20be-a7b1-48b1-ae40-716130c1657f`。
三个 turn 均完成，三个 semantic context values 长度为 2223、2398、2386，均 <= 2400。
四条约束持续有效，Google searches 均为 `allow_fallback=false`、actual provider `google`。

| Turn | 实际调用 | 执行与证据 | 后续状态 |
| --- | --- | --- | --- |
| 1 | `call_84c7fd39c0bccd94`、`call_a5ab9c240e32a16b`，2 次 search | Google success；各 3 个 model-visible citable candidates，仅搜索摘要 | Workflow active，不宣称研究完成 |
| 2 | 3 次 fetch | npm URL 两次 403；模型提出的 GitHub README URL 404；全部无可用页面证据 | failure 被完整记录，不终止线程 |
| 3 | 0 次调用 | 模型延续 OpenAI Agents SDK 对象；没有新的执行或页面结果 | receipt=0，Workflow 仍 active |

第三轮 pre-turn 保留了 `Select OpenAI Agents SDK` 请求摘要、上一轮 3 个 attempt、
最近 fetch 的 `http_failure` / `execution_succeeded=false` / `result_available=false`。
模型原生终态不再被当成 Workflow 完成。

中间两次 probe 分别在第三轮出现 2424 / 2457 字符的安全 capacity rejection，artifacts 保留：
`workflow-continuity-20261011-102948`、`workflow-continuity-20261011-103445`。
发现后消除重复当前输入、不适用的 fetch search 字段、冗余 scope header，未增大预算。
第一组还观察到一次真实成功 fetch；最终组三轮完整，但 fetch 没成功，不冒充完整页面研究 PASS。

## 仍未闭环

- 模型会重复 fetch 相同失败 URL、猜测一个未返回过的 repository URL；Runtime 如实记录失败。
- 模型仍可能把搜索摘要称为已核实文档/官方来源，或给出超出所得内容的解释；
  可引用 URL / provenance 不等于页面内容已验证或来源宣称正确。
- authority separation 没有让 assistant 普通历史中的错误叙述消失。
- 高压预算下只保护最近行动事实和短请求摘要；完整候选及更旧结果不保证都进入 projection，
  仍可从原生历史和完整 snapshot 追溯。本轮不建立选定对象的通用指代解析器或复杂 working set。
- 没有实现 semantic state 的跨进程恢复、Goal 完成判定、自动结论校验或 confidence scoring。

因此 Runtime 事实续接验证 PASS；模型基于证据持续修正行为只到 PARTIAL，不能以流畅接话作为整体 PASS。

## 最小人工验收

保持现有入口：`bash scripts/start_h3_harness_interactive.sh --turn-timeout 420`。
先确认之前会话已正常退出，8002 空闲；不要复用未知 runtime、改 8001 或放开 shell network。

1. 连续三个输入：
   - “研究 OpenAI Agents SDK 与 MCP 的公开资料，仅使用 Google，不要 Bing，不要 DuckDuckGo，禁止 fallback。”
   - “继续同一研究，选择 OpenAI Agents SDK，重点查工具与 handoff 的资料。”
   - “展开刚才选中的项目，分开列出真实取得的证据、未验证判断与未完成事项。”
   检查 task ID 不变、原任务摘要与 prior request 保留、tool arguments 随对象细化、
   call/outcome/source identity 对应；不能把无工具轮的承诺算成实际检索。
2. 失败后续接：要求 fetch `https://example.com/uaea-continuity-probe-nonexistent`，
   再问“继续原研究。先说明刚才访问实际取得了什么，然后自行选择一个合理后续行动。”
   HTTP 结果以实际记录为准，不预先假定 404；局部失败不得变成全局无权限或 Workflow 完成。
3. 证据不足：在同一研究中要求查一个不存在的项目，如
   “继续查 UAEA-probe-no-such-agent-project-20261011 的公开资料”，
   再问“基于刚才实际取得的资料，哪些判断有依据，哪些仍待核实？”
   不保证 provider 必然返回 `low_relevance`；若出现该状态，citable=0 不应被模型升级为已验证事实。

每组检查 events、adapter traces、`workflow_continuity`、下一轮实际 additionalContext 和最终模型回复。
停止自动扩展，待人工 artifact 决定后续阶段；不据此关闭 Authority Separation 整体或启动 Goal / Memory。
