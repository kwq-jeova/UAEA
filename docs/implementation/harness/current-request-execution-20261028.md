# 当前用户请求与历史执行事实分离

Status: IMPLEMENTED / MODEL_BEHAVIOR_PARTIAL
日期：2026-10-28

## 根因复核

原 N1X 8 轮人工记录 interactive-32768-20261028-010144 中，第 2、7、8 轮的当前输入都完整进入
turn/start.input，web_search / web_fetch 均在有效动态工具配置中。
第 2 轮实际 Google 搜索成功；第 7、8 轮没有新执行。
原始用户贡献已经通过 workflow_request_input 保存，不依赖 Step；
但投影 last_action_request 从最后一个 Step 取值，仍指向第 2 轮。
这不是请求原文完全丢失，也没有证据支持关闭 Web 或 Compaction 导致了这次失真。

## 最小实现

- workflow_snapshot 在每条既有请求记录的输出副本上附加 execution：
  attempts / outcomes_observed / successful / fulfillment=not_established。
  只匹配该 input_id 发起的真实 Step，不把 request_context_input_ids 的历史引用当作执行完成，
  不以 assistant 输出或 turn completed 生成 Action、Observation 或 fulfillment。
- workflow_continuation.current_request 直接来自当前 retained input；
  unattempted_requests 提供最近一个尚无直接尝试的历史用户贡献。
  这些文本继续以 untrusted 传送，不自动分类成必须执行的任务，也不授予权限。
- 投影中的旧 last_action_request 改名为 historical_action_request；
  snapshot 兼容字段 last_action_request 仍明确表示最后一次真实工具尝试关联的用户请求。
- workflow_execution.current_request 独立提供本次输入的尝试/结果计数。
  这是模型本轮开始时的事实；同一轮后续 Tool Results 优先于该静态计数。
  当前输入的完整文本仍走 turn/start.input，身份和完整请求状态保存在 snapshot / projection provenance。
- 2400 字符预算与 Constraint 优先级不变。压力下压缩可选历史摘要、去除重复的当前文本及冗余零计数；
  当前文本可回指 turn/start.input，完整历史和 identity 始终保留在 snapshot。
- 共用 runtime facts 提示模型区分本轮请求与历史结果；未搜索/未读取时如实说明，
  搜索摘要不是网页正文，普通问答不要求工具。没有强制工具循环、自动执行器、回答改写或 Goal 推断。

## 回归与边界

新增三项定向回归：历史搜索后新的无 Action 搜索请求仍独立保留；
三链接读取只观察到两次真实结果时不自动完成；普通问题不要求工具。
沿用既有取消、替换、跨线程/Workflow、无 Step 保留、权限与高密度预算测试。
既有 source coverage 断言迁移到新历史字段名，仍核对相同历史请求。
provider-history 的进程 test-double 同步 mock 二进制平台验证，修复上轮平台隔离提交后的旧测试夹具。

公共 Harness 回归：210 项，208 PASS / 2 可选 installed-vLLM CPU 测试 SKIP。
平台/入口回归：20 PASS（与前一组有部分重复，不相加为独立总数）。
没有执行完整 Memory 私有语料测试，也没有 5090D GPU 实机复测。

## 一次真实三轮验证：PARTIAL

通过统一 Shell 入口和现有 N1X 32K + Hermes，以原第 2、7、8 轮文本组成最小序列：
1. Google 搜索成功。
2. 新英文研究搜索成功，产生独立真实 web_search。
3. 逐篇阅读没有 web_fetch；模型仍声称访问三个链接并输出总结，事实保真 FAIL。

共 2 次真实搜索、0 次 fetch，无 Compaction，Trajectory 校验 PASS。
第三轮 snapshot 明确 attempts=0 / outcomes_observed=0 / fulfillment=not_established；
没有把模型访问声明计为执行，也没有将 Workflow 标成完成。
这不是完整 8 轮、同采样种子的 A/B，不能声称稳定提高了工具调用率。
运行一次后保留失败证据并停止，没有重试挑选结果。补充投影和提示仍不能保证模型忠实执行阅读要求。

证据目录：
/home/wqkan_wsl/uaea-n1x/audit/continuity-minimal-20261028-074546Z
其中 replay-inputs-2-7-8.json 保存旧输入/工具状态及新投影重放；
live-result.json 保存实际三轮结果，raw events、Trajectory 和语义快照路径完整记录。
后续最小方向是单独核查第三轮未 fetch 的模型行为与回答证据约束；
不据此进入 Goal Hypothesis 或 Memory/Ontology 扩建。
