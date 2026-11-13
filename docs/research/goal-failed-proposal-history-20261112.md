# Goal 失败提案历史投影修复（2026-11-12）

状态：工程限定验收；模型语义及 M2/M3 本轮 NOT RUN。独立审计结论见本报告末节。
批次：goal-failed-history-projection-20261112T115442Z；最终运行在 final/，此前调试记录完整保留。

## 1. 根因与范围

VERIFIED：harness/provider_history.py 的 project_provider_history() 将失败 function_call / function_call_output 合并为 terminal_attempt_fact 时，仅保存 Call ID、终止状态、错误及通用 Observation 白名单。真实 Goal arguments、operation、candidate_id、hypothesis 和当前回执 committed 未进入此事实。

这解释了“提交了什么”在 Provider History 中不可直接读出；不是 Host 丢失 Journal，也不是 Host 接受失败版本。不能据此证明补齐数据后模型必然理解正确。

复核材料：

- 原成功种子：goal-intent-lifecycle-20261112T031832Z/B。
- 原六次拒绝：goal-m2-branches-20261112T073526Z/B。
- P1/P2 缺口及旧模型回答：[上轮 P2 报告](goal-p2-state-report-20261112.md)，批次 goal-p1-p2-m3-20261112T093455Z。
- 当前记录：[最终 CPU 原始绑定与投影](../../../research-records/goal-failed-history-projection-20261112T115442Z/final/cpu-real-history-result.json)。

本轮只改 Provider History 及其直接 Bridge 异常处理、CPU 测试和隔离审计脚本。未改 Goal Schema、CURRENT 规则、候选数据结构、生命周期、SQLite Schema、正式授权或 Agent Loop；未加载 GPU 模型，未重跑 M2，未运行 M3，未 Commit/Push。

## 2. 最小修复与身份规则

失败 Goal fact 新增 goal_attempt：

- operation、target_candidate_id：取当前 Call 的原始参数，未知不借用旧 head。
- submitted_arguments：完整解析后的实参，包含实际 hypothesis、quote、input_ids/evidence_ids；arguments_sha256 对应该 Call 的原始 arguments 字符串。
- arguments_visibility、proposal_text_visibility：complete / missing / omitted_budget / unavailable_invalid_or_missing。
- host_result.accepted、committed：只取同 Call 的真实 goal_hypothesis_receipt；缺少字段、非布尔值或不支持的回执形状均为 UNKNOWN。
- saved_version_id：仅本次明确 committed=true 时可引用回执里的保存 ID；不把目标父版本冒充新保存版本。
- head_effect=not_committed_by_this_call 只表示本次未提交；current_head=UNKNOWN 明确要求从独立 Host 当前状态读取，不能从失败历史推断全局最新 head。
- Host error 保留有界原文并标记 error_complete；不完整错误不能冒充完整错误。
- is_saved_goal_version=false、replayable=false、authorizes_action=false。失败事实是不可执行的历史 message，不会再恢复为 function_call 或创建版本。

成功 form 的原始 function_call / output 保持不变。失败 revise 的 false 不会覆盖旧 form 的 true，旧 form 的 true 也不会传给失败 revise。未知信息不会从相邻成功事件补齐。

history_position 保留 field、call_index、output_index；事实仍在原回执位置出现，不重排事件。独立审计额外复现了“同 Call ID 冲突时字典 last-wins”问题，现增加 Goal 专用歧义拒绝：缺失 Call ID、同 ID 不同工具/参数/Turn metadata 或冲突回执时，Bridge 返回 400、记录 request_blocked、上游不接收。相同 ID 的冲突历史不再被静默合并。

## 3. 修复前后真实反例

| 调用 | 原始实际行为 | 修复前 | 修复后 |
|---|---|---|---|
| chatcmpl-tool-9405f3f580097084 | form 长期候选，committed=true | 成功原记录可见 | 原样保留 |
| chatcmpl-tool-956080bd53bb1609 | form 局部候选，committed=true | 成功原记录可见 | 原样保留 |
| chatcmpl-tool-a78d84a56e8cb702 | revise 长期候选；正文“长期跨公司研究AI产业投资机会”；引用非 CURRENT 被拒 | Call/错误可见，当前正文与 committed 缺失 | 原实参、目标 098ea60b…、正文、accepted=false、committed=false 同 Call 绑定 |
| chatcmpl-tool-a9d018f5e15dac09 | revise 局部候选；正文“完成Intel当前财报与估值分析”；同类拒绝 | 可能将旧 head 正文误认作失败提案 | 实际失败正文与旧保存正文明确不同 |

目标完整 ID 见原始绑定 JSON。随后另外四次失败也逐 Call 独立核对；不合并为一次事件，不按正文相似度替代身份。

[before](../../../research-records/goal-failed-history-projection-20261112T115442Z/final/projection-before.json) /
[after](../../../research-records/goal-failed-history-projection-20261112T115442Z/final/projection-after.json)
是从真实 Native 参数和 Host 回执重建的语义等价 Responses 历史，不宣称其 arguments 编码就是历史原始线缆字节。实际出站另见第 5 节。

## 4. Context 预算与 CPU 回归

复用 Bridge 现有 max_recovery_bytes 数值（默认 24,000 字节），作为本次 raw call/output → fact 转换的 Goal 失败历史上限；两种历史数组合计计费。原 Host 恢复块仍有独立的 24,000 字节上限，未扩大；**两者不是共享总计 24 KB**。未增加 Context/KV，不修改压缩策略。

先容纳全部身份、操作、目标、Host 结果及完整性标志，再从较新的事实开始容纳完整参数对象。正文不做无标志的局部截断：放不下就 submitted_arguments=null，显式 omitted_budget，仍保留原参数哈希。连身份/结果都放不下时返回 413，并记录 goal_failure_history_over_budget，上游不转发；不默默删 Call ID 或提交结果。

每个原始失败 pair 合并成一个历史事实；再次处理已投影结果不新增事实、不执行调用。上限仅约束本次新生成的 Goal facts；任意已存在的普通 message 不会被识别并重新预算。正常 Native 重建提供原 call/output，本次真实案例属于覆盖范围。不能把本实现称为所有普通历史消息的全局预算器。

最终真实六条失败事实合计 10,856 字节，未省略参数；完整转发请求 88,129 字节（不是 Token 数）。本轮不报告未经 tokenizer/模型测量的 Token 或延迟收益。

64 项 CPU 回归通过：[日志](../../../research-records/goal-failed-history-projection-20261112T115442Z/cpu-regression-postreview.log)。命令：

    python3 -B -m unittest tests.test_goal_failed_history tests.test_harness_provider_history tests.test_context_budget_recovery -q

覆盖：成功 form、失败 revise、成功后失败、多失败/多候选、缺 committed、缺正文、失败事实不可执行及幂等、Unicode 超预算显式省略、元数据超预算拒绝、两数组预算、冲突 ID 拒绝、并行乱序原索引、Bridge 真实 HTTP 200/400/413 与无上游误转发，以及已有 Web/Context 边界回归。原始 Journal/Native 对照由第 5 节补充，不能以纯合成单测替代。

## 5. 无模型的真实 Harness 出站核验

VERIFIED（HTTP 工程范围）：

- 使用已钉选 Codex 0.163.0，真实 app-server / thread/resume / turn/start。
- 克隆真实失败分支 codex-home；原 Thread、两次成功 form 和六次失败 revise 历史来自 Native，未伪造新 Tool Call。
- Host 使用已独立核验的原两 head 恢复基线；确认失败分支没有新增 Goal 版本且 heads/versions 与原基线相同。失败分支额外旧反馈仍属于 Native 历史，不伪装成重新执行的 Host Observation。
- 仅向 loopback CPU HTTP 协议桩发请求；桩返回固定结束标记，既不运行 Bolt，也不评价语义能力。
- 最终 1 个请求完整结束；接收端原始字节 SHA-256 与 model-http-audit.forwarded_bytes_sha256 一致，脱敏后的审计快照与接收 JSON 一致；HTTP framing/response_complete 均 true。
- 两次成功 form 的 true 和六次失败 revise 的 false 正确独立；六次实际实参、目标和正文与原 Native/Host 回执一致。
- 无新增工具执行、无新 Goal 版本/拒绝、两个 head 不变。旧版本保留为历史。

证据：[最终出站结果](../../../research-records/goal-failed-history-projection-20261112T115442Z/final/wire/result.json)、
[实际接收请求](../../../research-records/goal-failed-history-projection-20261112T115442Z/final/wire/captured-wire-1.json)、
[HTTP 审计](../../../research-records/goal-failed-history-projection-20261112T115442Z/final/wire/model-http-audit.jsonl)、
[原始 Native 摘录](../../../research-records/goal-failed-history-projection-20261112T115442Z/final/native-goal-excerpt.jsonl)、
[Host Journal 摘录](../../../research-records/goal-failed-history-projection-20261112T115442Z/final/host-goal-journal-excerpt.jsonl)。

原件 5 件文件及 Native home 哈希一致；副本仅调整其 rollout 路径与 CPU 端点配置，不改 SQLite Schema，不改原件。第一次探针暴露本次新增预算 decision 缺少 Journal 要求的 turn_id，已修并保留 wire-attempt1；第二次实际转发成功但验证误比较脱敏快照与原始 JSON，以及后续验证误读 thread_id 所在文件，日志均保留。最终 final/ 在修复及独立身份审查后完整重跑 CPU 桩，无上述验证错误。不是重复模型测试选优。

## 6. 项目进度与下一步

| 事项 | 当前范围 |
|---|---|
| 历史候选恢复 | 限定 PASS；原结论保留 |
| Step–Observation 绑定 | 已修复；不在本轮扩展 |
| 失败提案历史投影 | 工程限定 PASS，Audit Agent 独立复核通过 |
| M2-A 准确读回 | 既有单样本限定通过；语义 PARTIAL |
| M2-B 受反馈修订 | 已有真实 revise/保存证据；语义忠实性未通过；本轮 NOT RUN |
| 失败状态理解 | 旧试验受投影缺失影响；修复后模型行为 UNKNOWN，必须重新验证 |
| M3 | NOT RUN |
| M4 / M5 | UNKNOWN / UNKNOWN |

候选语义、用户认可、未来决策价值不能由来源保真证明。下一步仅在独立工程审计通过并获下一阶段安排后，重新验证模型对“本次失败提案 / 历史成功版本 / 当前 head”的理解；不在本轮恢复 M2 或 M3。

## 7. 独立审计

Audit Agent 独立只读复核结论：**限定工程 PASS；无当前阻断项，非认知 PASS**。

独立重跑 64 项 CPU；核对最终接收字节及脱敏审计、2 成功 form / 6 失败 revise 与原 Native/Host Journal 的参数摘要、原因和 committed 绑定、原始索引、2 heads / 2 versions 不变及无新工具调用。最初指出的同 Call ID last-wins 歧义已复现并由拒绝转发修复。

审计范围限制：这是正常 Native 原始 call/output 重建路径及明确反例的工程验收；不是任意损坏历史自动修复、所有普通消息全局预算、模型状态理解或候选语义正确性的证明。独立意见完整归档在本批次 independent-audit.md。本轮到此停止。
