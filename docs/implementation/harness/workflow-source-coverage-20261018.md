# 单 Workflow 来源覆盖与续接投影

Status: IMPLEMENTATION_NOTE
日期：2026-10-18
状态：事实覆盖、bounded projection、真实三轮计数核对 PASS；等待人工验收。
整体研究推理质量仍不是本说明的 PASS 范围。

## 范围与 ownership

只处理当前 Workflow 的来源获取事实及请求续接，不实现 Goal/Memory、不修改 Harness Core、
Google backend、proxy、timeout、authorization、semantic ownership/scope 或 frozen 8001。
本轮不修网页正文抽取，也不建立必须逐个 fetch 的执行计划。

沿用 Phase-1 Workflow/Step、现有 call identity、ExecutionObservation、eligible candidates 与 trajectory：

`search candidates / actual fetch outcomes → source_coverage → bounded additionalContext → next turn`

`harness/workflow_continuity.py` 从当前 Workflow 的既有 Step 派生覆盖，不建立平行 Runtime 或数据库。
`harness/semantic_state_adapter.py` 关联真实输入与 Action attempt，组织 snapshot 与 bounded projection。
`harness/io_contract.py` 仍分开 application facts 与 untrusted interpretation。

## 事实 contract

- 来源总体是当前 Workflow 中实际返回、eligible 且 citable 的 discovery URLs，并非解析用户自然语言后
  生成的 authoritative requirement set。`low_relevance` / `uncertain` 结果不会进入此总体。
- `discovered` 按完整 URL 去重，`unit=url`。相同 URL 的多次搜索或读取不增加独立来源数量。
- `fetched`：存在成功执行且 `result_available=true` 的 fetch 观察。
  这只说明取得页面结果，不说明完整阅读、理解、内容相关、来源正确或适用于当前问题。
- `unattempted`：没有对应 fetch attempt；`pending`：尚无可用页面，且存在仍未得到结果的 proposed attempt。
- `failed`：有已终结 attempt，但没有可用页面。可包含执行前 rejection、执行失败或结果不可用，
  不是网络原因分类，也不是授权状态。
- 成功重试后，同一 URL 从失败变为 fetched，旧失败仍留在原始 timeline。
  已留存的成功页面不会因为后续一次失败重试而消失。
- 仅依据 URL 与已有调用/观察身份关联，不把 assistant 声称访问、普通 JSON 文本或猜测链接计为成功。
- 未在 eligible discovery 中出现的 fetch target 保留在 `other_fetches`，不偷偷扩大已发现来源总体。
  其 execution result 仍完整保留，未被丢弃。
- 每个来源保留 discovery call/turn/observation/access identity，以及各次 fetch 的对应身份和结果。

因此 `fetched=2, discovered=6` 不等于任务完成，也不自动要求模型必须读取剩余四个。
已有 `completion_established=false` 边界不变；模型仍根据当前用户请求选择后续行动。

## 请求续接

Step provenance 新增对应的 `user_request` 与 `input_id`。
snapshot 的 `last_action_request` 指向最近一个结构化 Action attempt 所关联的真实用户输入。
它不是推断出的 Active Goal，也不保证该 attempt 已执行或成功。

当最近几个追问不产生 Action 时，bounded continuation 可继续保留该请求摘要，
而不只保留上一句“获得什么结果”。文本仍处于 untrusted surface，不增加权限。
最新用户输入仍完整走原来的 `turn/start.input`，旧请求不能覆盖或授权新动作。
完全没有产生结构化 Action 的请求仍由原 UserInput / task_evolution 保留；
本轮不通过关键词规则推断通用 active-work-request 或任务切换。

## 容量与保真

- semantic budget 保持 2400 字符，计入拆分后实际 additionalContext values 的开销。
- counts 不因为投影裁剪改变；URL 行只能整行省略，不能截短 URL 或伪造可访问地址。
- `omitted_sources` 明确区分“没有投影全部来源”与“来源不存在”。完整列表仍在 snapshot。
- 优先裁减 assistant proposal、重复 observation prose 和重复 candidate，再缩减来源明细。
- 压力下可省略重复的 interpretation effective-state ID、与 outcome status 重复的 attempt state、
  已成功执行时重复的 HTTP 标志、正常 terminal 标签以及固定 URL unit；原始 facts 始终保留。
  compact coverage 中省略的零值 `failed` / `pending` 代表 0；`unit` 缺省仍固定为 URL。
- 所有有效 Constraint、authority、scope、promotion basis 和必要 native identity 仍由原有 contract 保留。
  若最小必要投影依然超限，继续局部拒绝，不静默丢约束、不退出线程。

## 验证

- targeted WSL regression：123 项 PASS。
- full unittest：370 项，364 PASS、6 skip。
- `py_compile`、`git diff --check` PASS。
- 覆盖去重、rejection、缺失结果、失败恢复、成功后失败、执行成功但结果不可用、
  low-relevance exclusion、请求来源、跨 thread/task 隔离、URL 原子省略、四约束长身份容量。
- 原 `interactive-32768-20261018-022031` 的七轮 canonical 只读重放：
  5 个独立 attempt/observation；最终 discovered=6、fetched=2、unattempted=4、failed=0。
  已恢复的网络失败仍保留，但不再成为 URL 当前获取失败状态。
  “探索这 6 个链接”的请求能持续进入后面的无 Action 追问投影，且保持非权威。

## 真实 Harness 自测

命令：

```bash
python3 scripts/h3_workflow_continuity_probe.py --scenario coverage --turn-timeout 420
```

探针只替代键盘输入，未 mock inference、HTTP 或工具执行，没有预先指定调用顺序。
复用 source-built pinned Harness、独立 CODEX_HOME、现有 provider-safe history 与动态工具路径。
8002 保持 32768、GPU utilization 0.75、AWQ、Hermes；未触碰 8001。

artifact：
`D:\UAEA-runtime\h3-results\workflow-source-coverage-20261018-023748\interactive-32768-20261018-023748\`

- 第一轮：模型自主搜索，Google 成功，返回 3 个 eligible 来源。
- 第二轮：模型自主进行 3 次 fetch；第一个 network failure，另两个成功。
- 第三轮：没有新调用，准确报告 2 个成功来源及 1 个尚未取得页面的来源，并列对链接。
- 同一 Workflow；全部 3 个 turn 完成；semantic context 为 2170、2396、2386 字符。
- canonical reader/validator PASS；app-server 与 8002 正常停止。

`workflow-continuity-summary.json` 保留实际 pre-turn projection、完整来源映射、调用及结果。
计数核对通过不代表所有研究结论已验证。没有做 A/B，不能把模型行为改善完全归因于新投影。
正文质量、通用指代绑定、长期目标及完整任务完成判断仍未在本阶段实现。

## 人工验收

人工入口不变，不使用探针的 scenario 参数：

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

先连续输入：

1. “研究 Agents SDK 与 MCP，仅使用 Google，禁止 fallback。”
2. “请分别探索刚才找到的链接，找到推进本地 runtime 研究的方法。”
3. “获得了什么结果呢？”
4. “还有哪些没有完成？这些结果怎样帮助实现 runtime？”

不预设 provider 一定返回六个链接。将真实返回的不同 eligible URLs 与成功 fetch 对照，
检查模型报告、source_coverage counts、实际投影一致；没有调用不能声称新访问。
第四轮重点检查 last_action_request 是否继续保留第二轮请求，而非只剩第三轮泛问。

再要求重新访问一个已成功来源，并重新核对不同来源数量：重复访问不得增加 fetched 的 URL 数。
若自然发生失败，不要改代理/timeout 来配合验收；失败必须如实列出，成功重试后只计一个来源。

观察 `semantic-state-snapshots.jsonl`、adapter traces、canonical 的 pre-turn additionalContext 与模型回复。
完成后停止自动推进，由人工 artifact 决定是否收敛本阶段。

## 后续人工验收记录

`interactive-32768-20261018-030440`：5 轮完成、2 次 Google search、3 次 fetch，
最终不同 URL 覆盖为 6 / 3 / 3（discovered / fetched / unattempted）。
canonical 2325 条记录可读取、顺序与 turn reconstruction 验证 PASS；semantic 投影最大 2379 字符。
来源覆盖事实通过人工验收，但模型将未经核实的 MCP 展开用于 query、把视频标题扩写为部署指导、
未续接未访问来源，不能据此宣布整体研究推理 PASS。原文早期待验状态作为历史保留。
下一轮仅补 [请求与行动依据续接](workflow-request-basis-20261018.md)，不扩大 Web 或 Goal/Memory。
