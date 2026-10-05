# Model-visible Observation Boundary

Status: IMPLEMENTATION_NOTE
Reviewed: 2026-10-04
Role: 结果投影的事实边界与窄范围验证，不新增错误分类或模型回答校验引擎

## 本轮边界

```text
authoritative runtime facts
  -> semantic boundary guard
  -> bounded model-visible observation
```

执行事实与证据充分性分别保留：成功 Google 搜索仍是 Google 成功执行，
即使候选为 low_relevance、uncertain 或为空。证据不足只针对当前请求，不能推出
网络受限、用户拒绝授权或相关资料不存在。HTTP 取得网页也不等于内容已被模型正确理解。

不改 Google backend、proxy、timeout、authorization validator、semantic ownership/scope、
Hermes、Codex Core、frozen `8001` 或 diagnostic 32K profile；不添加 retry 或 planner。

## 最小修改

- `harness/observation_boundary.py` 提供共享投影边界，约束执行、原因、证据范围、授权来源的解释。
  不枚举错误类型；未知原因继续按原文呈现，缺失执行事实不补造。
- 即时 Web 结果的 message 根据已报告执行事实生成；成功 Google 不再包含
  `do not call this Google`。候选数跟随最终保留的 `citable_results`，不与裁剪后的 payload 冲突。
- `phase2/web_capability.py` 同时修正源头成功说明，避免新 semantic snapshot 继续积累旧冲突文本。
- 参数验证失败记录来源 `validation_source=capability_input`，保留具体 error。
  合法恢复是按当前 schema 修正参数、保留有效约束，再经过原有 validation；不是放宽 policy。
- 已有 semantic validation 的通过/拒绝状态另行投影为 `policy_validation_passed`。
  Web authorization snapshot 明确作用域为 `web.provider_fallback`，不能把 denied fallback
  泛化为禁止搜索。此字段不改变授权状态或决策。
- `provider_history.py` 保留开放式原因的有界摘录，不再把非标识符原因强制变成 `tool_failure`。
  原始 failure detail、recovery 与同一事实边界随终结历史 observation 保留。
- 输出预算优先保留事实边界、原始原因摘录、有效约束和 recovery。无法容纳核心 contract 时仍明确报错，
  不静默裁掉。原始 ToolResult、SQLite source history、canonical trajectory 不改写、不删记录。

边界标记不是强制模型遵循的回答拦截器，也不是 tool execution 的第二套实现。

## 原始人工证据

`D:\UAEA-runtime\h3-results\interactive-32768-20261004-130341`：
6 次 Google 成功、1 次参数拒绝、1 次成功 fetch。成功说明仍有旧 Google 禁称文本；
最后一轮 `source_types=[academic,news,blog]` 被当前 schema 拒绝，实际原因是
`unsupported source_types value: blog`，不是用户禁止 blog 或网络失败。
模型随后移除 blog、实际搜索成功，但仍错误解释为约束限制。
本轮只读使用该 artifact，未改写。

## 修复后验证

自然语言自动复放，非新增人工 PASS：
`D:\UAEA-runtime\h3-results\interactive-32768-20261004-133423`。
使用原 interactive REPL、相同 32K/0.75 profile，未注入模型输出或工具结果。
三个连续输入分别为 Google-only AI agent 演化研究、读取一个结果、预测未来 AI 发展。
该复放验证了本轮初版事实边界；其后补充的候选计数一致性与 fallback 授权作用域
分别通过最终定向测试和下面的受控恢复复放验证，不改写已有 artifact。

- 三个 turn 正常结束；后续真实 Google HTTP 搜索成功，保留 3 个完整候选 identity。
- 一次 arXiv PDF 获取成功；另外两个 fetch 的实际 HTTP 状态分别为 403 与 404。
- 即时观察包含新事实边界，无旧 `do not call this Google`。
- 模型仍把成功 PDF 获取泛化为无法读取并推测权限；第一轮没有成功 tool execution，
  后续却声称已完成搜索。不能宣称模型行为已完全收敛。
- 第一轮 generation diagnostic 记录了 `web_search({...})` 形式的非 JSON tool body，
  并在同一次生成中虚构结果；Hermes 报 JSONDecodeError，finish_reason=stop，非输出预算截断。
  本轮不修这个独立的模型生成/工具协议问题。
- 此组搜索的 evidence status 是 relevant，没有触发真实 low_relevance 后的自主改 query，
  因而该行为验收仍未证明。

参数拒绝后的受控恢复复放：
`D:\UAEA-runtime\h3-results\web-rejection-recovery-20261004-134044`。
复用已有 recovery probe，仅第一条含 blog 的非法 proposal 是 fixture；后续行为来自真实 Qwen。

- 参数拒绝发生在 HTTP 前；具体 error、Google requested/actual 区分、fallback authorization scope、
  当前约束、repair_arguments 路径在 model-visible 结果和历史投影中保留。
- Qwen 口头提出修改来源参数，但没有产生合法 HTTP 重试；出现 Hermes JSONDecodeError。
  输出仅 150 tokens，未触及该旧 probe 的 384-token 上限；此组没有 pre-parser 原文，
  不据此推断新的 parser root cause。
- turn 正常完成，无 provider HTTP 400；恢复行为判定 PARTIAL，不计为真实 Google 重试成功。

两个 probe 都正常停止其自建 app-server/8002。未改动 frozen `8001`。

最终回归：104 项 targeted tests 全部通过；full unittest 共 303 项，301 通过、
2 项可选 vLLM 环境测试跳过。`py_compile` 与 `git diff --check` 通过。
两组 canonical trajectory 分别含 923/100 条记录，reader/validator 均通过，
恢复到 3/1 个 `TURN_COMPLETED`，raw_event 全部保留。
在实际私有环境中仅在内存读取 key 对比仓库 2468 个文件及新 artifact 19 个文件，
匹配数为 0；不输出 key，不扫描或改写私有 env 文件。

## 结论与停止点

投影边界与回归验证通过；整体模型行为验收仍为 PARTIAL。
后续人工只复测：成功 Google 后的 provider 表述、低相关后的改 query、schema 参数修正与
多次 fetch 的逐项状态对应。不能把新错误分类、权限放宽、网络调整当成这些问题的修复。
本轮不自动进入其它实现。
