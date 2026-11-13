# M2-A：恢复历史 Goal 的独立读回实验（2026-11-12）

状态：**PARTIAL**。本单样本的全文、ID、head 和保存状态读回 **VERIFIED / PASS**；表达来源与 Agent To-do 的语义归属 **PARTIAL**。不是反馈纠正或自然形成成功。

## 1. 独立条件与冻结证据

批次 goal-m2-branches-20261112T073526Z/A，独立于 B 的用户反馈、回答和状态修改。从原始 goal-intent-lifecycle-20261112T031832Z/B 复制 Native home 并恢复相同 Host 闭包，未使用上轮失败纠正后的 home。沿用原 Thread 01a1cdd9-84df-7030-a240-4ea8f75089ea、Scope、两个 Candidate ID、Call ID 与幂等状态；这只是隔离研究副本，不是把旧 ID 粘到新 Thread。A 与 B 新 Turn ID 不同；首个请求中互无另一分支新输入或 A 回答，恢复 bundle 完全相同。模型服务顺序共用，不能由此声称统计独立。

用户脚本只要求核对当前两个候选全文、范围、来源/主体/认可、历史与当前状态，不要求修改，也未给标准候选答案。完整脚本见 [scenarios.json](../../../research-records/goal-m2-branches-20261112T073526Z/scenarios.json)；预登记及冻结哈希见 [preregistration.json](../../../research-records/goal-m2-branches-20261112T073526Z/preregistration.json)、[input-lock.json](../../../research-records/goal-m2-branches-20261112T073526Z/input-lock.json)。

真实历史指研究脚本经实际模型、Sideband、Host 执行留下的记录，不代表用户投资心理的独立真值。原种子是显式要求建立的两个候选，不是自然形成。

## 2. 原文及逐项结果

| 当前 head | Host 中完整 hypothesis |
| --- | --- |
| goal-candidate:098ea60b1c3caf2ca410b22d | 长期跨公司AI产业投资机会研究是全局范围目标，需从本地摘录之外查找更多AI行业与公司资料，并在可撤销的目标假设中保留。 |
| goal-candidate:0cb6591e2475fdd96208bc87 | Intel当前财报与估值分析是局部范围目标，基于已读的官方摘录（INTC 2026Q3收入$16.5B，GAAP EPS $0.60，non-GAAP EPS $0.52）可撤销地保留。 |

完整回答保存在 [A/model-answer.md](../../../research-records/goal-m2-branches-20261112T073526Z/A/model-answer.md)，对应 [A/app-server-events.jsonl](../../../research-records/goal-m2-branches-20261112T073526Z/A/app-server-events.jsonl) **行 1187**，新 Turn 01a1cebc-fe24-79f1-8b96-a958ad6f94f5。评价采用完整原文与上下文审读；下面的文本逐字相符检查仅支持读回结论，不代替语义评分。

| 维度 | 证据与判定 |
| --- | --- |
| 两条全文、ID、当前 head | **VERIFIED / PASS**：逐字包含两条全文；ID、form、candidate、共同 basis_input_ids、parent=null、哈希准确。 |
| 保存与历史关系 | **VERIFIED / PASS（当前根版本案例）**：明确本轮没有修改、替换、删除、撤回，也没有 ActiveGoal 采纳。两条均为首次 form；本案例没有非平凡父链，不能外推历史版本选择能力。 |
| 表达来源 | **PARTIAL**：回答以“Host 保存”解释表达来源。存储位置不能代替表达生产者；原候选文字来自模型提案，原目的和操作要求来自用户输入。 |
| 意图主体及范围 | **PARTIAL**：识别全局 AI 投资研究与局部 Intel 分析，但仍把“需查找更多资料”列入 Head 1 适用范围，没有清楚移出 Agent To-do。 |
| 用户认可 | **PARTIAL**：正确限制为研究而非交易/ActiveGoal；却把“在可撤销假设中保留”称作模型自主保留，不准确反映原用户操作要求。操作认可不是长期目的本身。 |
| 数字背景 | 不因含方法/数字机械判无效。局部候选中的数字可属于无害背景，本实验不复核这些财务数字的真实性。 |
| 真实新状态 | **VERIFIED**：0 Tool Call、0 新候选、0 新外部 Observation；两条 head 与 versions 原样保持。该条件下合理不行动。 |

## 3. 请求、资源与限制

实际 1 个用户轮次、1 个模型请求完整结束。API input=20,700、output=1,211 Tokens；Turn 耗时约 124.24 秒；有效窗口 62,259，0 Compaction。真实出站请求含 Goal 工具和两条候选全文；仅有“投影已准备”不足以得出此结论。

HTTP framing、completed 终态与上下游完整字节一致均有原始记录。见 [A/model-http-audit.jsonl](../../../research-records/goal-m2-branches-20261112T073526Z/A/model-http-audit.jsonl)、[A/streams/session.json](../../../research-records/goal-m2-branches-20261112T073526Z/A/streams/session.json)、[evidence-index.json](../../../research-records/goal-m2-branches-20261112T073526Z/evidence-index.json)、[final-audit.json](../../../research-records/goal-m2-branches-20261112T073526Z/final-audit.json)。完整捕获没有触及 16 MiB/层预算。

**UNKNOWN**：其他上下文下的稳定读回、自然 Goal 形成、修订、M3 后续行为、相对 Relevant History 的增量价值。A 不应与 B 合并计算一个“成功率”，也不是与 B 的公平决策质量对照。

结论：已有信息能够在本单样本中被准确读回；归属解释尚不完全准确。不能继续将所有后续错误都归为“看不到原候选”。

关联：[工程与阶段结论](goal-m2-branches-20261112.md)、[M2-B 独立报告](goal-m2-correction-20261112.md)。
