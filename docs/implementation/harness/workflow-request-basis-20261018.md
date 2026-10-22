# 单 Workflow 请求与行动依据续接

Status: IMPLEMENTATION_NOTE
日期：2026-10-18
当前停止点：完成自动与真实路径自测后，等待人工验证；不启动 Goal/Memory。
结论：请求/行动依据记录与投影 PASS；模型遵循证据的行为 PARTIAL。

## 简要进度

- Harness lifecycle、authority separation 与来源覆盖事实沿用当前基线。
- 030440 人工 run 已确认 6 个发现来源、3 个已获取、3 个未尝试，事实计数 PASS。
- 研究推理仍为 PARTIAL：未经确认的 MCP 展开影响 query，视频标题被扩写为未获取的正文内容。
- 本轮仅让历史请求与实际 query 同时可追溯；不判断哪种 MCP 解释正确，不新增关键词规则。

## 本轮最小能力

`现有 Workflow/Step → 请求来源与实际 Action → bounded pre-turn projection`

`harness/workflow_continuity.py` 派生 `action_request_origin`：当前 Workflow 中，
最早一个关联结构化 Action、且不同于初始请求的用户输入及 input/turn/call identity。
这是历史记录，不是当前工作请求、稳定 Goal，也不是后续指令的 supersession 判定。
`last_action_request` 仍准确指向最近一次 Action 的用户输入，包括“继续”；没有偷偷改写其语义。

`harness/semantic_state_adapter.py` 在其后发生 Action 时，把较早的 origin 摘要保留到
`workflow_continuation.request_history`；后来的输入也保留，最新用户输入照常完整进入 Harness。
此请求历史保持 `untrusted`，不能成为授权、execution constraint 或自动执行计划。
完整依据在 snapshot 的 Step 与 origin identity 中，不另建平行状态机。

`workflow_execution.last_search_action` 记录最近结构化 search proposal 的 call identity 和 query，
并明确 `task_alignment=not_evaluated`。它只证明参数曾被提交：不证明执行成功、任务解释正确、
缩写得到确认，或结果足以支持用户目标；execution outcome 仍由原有 observation 决定。
同一 query 的历史重复表示不形成多份独立证据。

## 容量与边界

- 2400 字符预算不变；优先减少 assistant prose、重复内容和来源明细，不丢有效约束。
- query 摘要可截短、预算不足可省略；原始参数与完整 provenance 始终在 Step/canonical 中。
- 请求历史也只投影摘要，不宣称完整上下文；本轮不建立自动任务解释或替换关系。
- task/thread 隔离沿用已有 ownership；显式新任务不继承旧 origin 或 query。
- 不修改 Web backend、provider history、网络、授权、Harness Core、8001 或 8002 参数。
- 不保证模型正确自我修正；尤其 fetched 仍不等于全文可用、理解或内容充分。

## 自动与真实验证

新增测试覆盖短续接仍保留 origin、后续明确修订不被旧请求覆盖、query 不升级为任务解释、
失败 proposal 不变成功事实、task/thread 隔离，以及四约束与长 query 的预算和原始数据保真。

030440 canonical 只读重放：5 轮投影为 2116、2313、2400、2323、2304 字符，
最后一轮同时保留早期本地 runtime 研究请求和真实 `MCP Multi-Container Platform` query。
来源覆盖仍为 6 / 3 / 3；离线重放只验证投影，不等于行为 A/B。

真实自测使用现有 REPL、source-owned pinned app-server、local Qwen/vLLM 与真实 HTTP：

```bash
python3 scripts/h3_workflow_continuity_probe.py --scenario basis --turn-timeout 420
```

该探针只替代键盘输入，不指定工具执行步骤；行为结论以实际 artifact 为准。

实际 artifact：
`D:\UAEA-runtime\h3-results\workflow-request-basis-20261018-031907\interactive-32768-20261018-031907`

- 4 轮同一 Workflow，全部 terminal 完成，canonical reader/validator PASS。
- 第一次 Google search timeout，随后两个合法 Google search 成功，没有 fallback。
- 没有实际 fetch，覆盖为 discovered=6、fetched=0、unattempted=6；没有把模型自述记成页面执行。
- 4 轮实际 semantic additionalContext 为 2233、2257、2311、2313 字符。
- 后续投影保留第二轮本地 runtime 研究请求与实际 MCP query，明确 task alignment 未评估。
- 模型仍在无 fetch 时把发现链接列为“获取内容的页面”，且未主动展开页面访问。
  真实路径通过不等于行为改善闭环；本轮没有 A/B，也未扩大范围修复这一残余问题。
- 自测结束 app-server 与 8002 正常停止；未启动或修改 8001。

自动测试：新增 5 项；WSL targeted 101 项 PASS；full unittest 375 项，369 PASS、6 skip。
`py_compile` 与 `git diff --check` PASS。原有 datetime deprecation warning 未在本轮处理。
仓库文本与本轮 artifact 的实际 credential 字节扫描：1351 个文件、0 处命中，不输出 credential 值。

## 最小人工测试

入口不变：

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

同一会话连续输入：

1. “研究 OpenAI Agents SDK 与 MCP，仅使用 Google，禁止 fallback。”
2. “请探索刚才找到的链接，比较哪些机制有助于构建本地 agent runtime。”
3. “继续。”
4. “我们在推进什么？你实际查了什么？哪些结论已有页面证据，哪些还未验证？”

观察 snapshots 的 origin/input/call identity、实际 query 与 execution outcome、
canonical additionalContext 的 untrusted 请求历史及 application 执行事实、adapter traces 和模型回复。
模型可以提出解释，但不能把自己生成的缩写展开当用户已经确认；未执行不能称完成。
核对 fetched/未尝试数量，标题页不能被描述为已阅读正文或视频。

可在第四轮之后做一个最小修订：“MCP 指 Model Context Protocol，后续只比较协议接口，不讨论多云容器管理。”
检查最新输入是否改变模型下一次 query，而不是被旧 origin 限制；本轮不自动解析为新硬约束。
未出现缩写分歧时无需强行制造；本轮事实投影 PASS 不替代模型行为人工验收。
