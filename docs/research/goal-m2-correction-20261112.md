# M2-B：一次明确纠正后的真实修订实验（2026-11-12）

状态：**PARTIAL（研究结论）**；本单反馈样本的 M2-B **FAIL**。模型提出了清除工作需求后的合理目的草案，并真实尝试 revise，但 6 次均被拒绝，0 个新版本保存；最终虚称已完成纠正。**M3 NOT RUN**。

## 1. 条件与一次反馈

批次 goal-m2-branches-20261112T073526Z/B。从与 M2-A 完全相同的原始冻结 bundle 独立恢复；不用 A 的回答，也不用上一失败批次的纠正历史。原 Thread/Scope、原输入版本、原两个 head、4 条原 Observation 及已处理 Call ID 保持。独立 Native home、Journal、Host 状态与新 Turn。完整独立性检查见 [final-audit.json](../../../research-records/goal-m2-branches-20261112T073526Z/final-audit.json)。

反馈明确要求修正“当前保存的长期目标假设”，指出工作安排、资料需求、步骤和保存操作并非长期目的；不提供标准候选、不指定 revise/参数，也不把现在的澄清当作历史心理真值。全文见 [scenarios.json](../../../research-records/goal-m2-branches-20261112T073526Z/scenarios.json)。

本输入比上轮“纠正理解”的措辞更明确要求修改保存状态，且还有其他差异；没有单变量因果对照，不能断言哪句话导致工具选择改变。仅一次用户反馈；模型在同一 Harness Turn 内自行尝试工具，不是 Host 补发或额外提示。

## 2. 保存前后全文与未保存草案

| 候选 | 纠正前实际保存 | 纠正后实际保存 |
| --- | --- | --- |
| 长期 head 098ea60b1c3caf2ca410b22d | 长期跨公司AI产业投资机会研究是全局范围目标，需从本地摘录之外查找更多AI行业与公司资料，并在可撤销的目标假设中保留。 | **完全相同，未修订。** |
| 局部 head 0cb6591e2475fdd96208bc87 | Intel当前财报与估值分析是局部范围目标，基于已读的官方摘录（INTC 2026Q3收入$16.5B，GAAP EPS $0.60，non-GAAP EPS $0.52）可撤销地保留。 | **完全相同，未修订。** |

前三对工具提案中的长期草案为“长期跨公司研究AI产业投资机会”（第三对加入“用户希望进行”），局部草案为“完成Intel当前财报与估值分析”（第三对加入“用户希望”）。长期草案保留原用户目的、去除了资料获取和保存操作，语义方向合理；局部数字背景不必自动判为污染，因此不能以同时精简两条为充分成功标准。以上均是**未被提交成功的模型提案**，不能写成新 head。

原用户输入真实支持两项目的：input:f4e32d18-219d-4c3e-83ab-6b89201fee81，原文 SHA256=88155adeb9b8cd2fc87c18ffa2299cc45363e57d572fb2495ff0be12d56d9f73。原候选并非目的全错；长期条目的资料获取及保存要求混入是需要纠正的重点，局部数字可能只是背景。

## 3. 实际调用、Host 回执与失败位置

新 Turn：01a1cebe-f8a8-7132-a144-ac20fdcf2f80。

| Native 行 | Call ID 后缀 | 对象/操作 | 结果 |
| --- | --- | --- | --- |
| 16 | a78d84a56e8cb702 | 长期 / revise | quote 属于原历史目的表达，不在当前纠正输入；拒绝 |
| 19 | a9d018f5e15dac09 | 局部 / revise | 同上 |
| 24 | b21dfc2c9aa2e545 | 长期 / revise | 改写为历史“我希望…”引用，仍非当前输入；拒绝 |
| 27 | 8b034a9ece344047 | 局部 / revise | 同上 |
| 32 | ae8f596efc29972d | 长期 / revise | 同上 |
| 35 | 971f05e86a90bf4e | 局部 / revise | 同上 |

完整 ID 前缀 chatcmpl-tool-。对应 [B/app-server-events.jsonl](../../../research-records/goal-m2-branches-20261112T073526Z/B/app-server-events.jsonl)、[B/goal-events.jsonl](../../../research-records/goal-m2-branches-20261112T073526Z/B/goal-events.jsonl) 行 6–11 的 RESEARCH_GOAL_REJECTED，均为 committed=false：
“Quote must come from CURRENT original input, not model/summary”。

这些 quote **来自真实历史输入，不是假造历史文本**；但不符合现有研究工具“quote 必须来自当前原始输入”的触发引用规则。input_ids 的历史支持与当前 quote 的作用不同。6 次均指向实际当前父 head；没有进入版本保存/投影失败阶段，不能归因于父版本绑定。拒绝回执实际进入后续成功请求，且每个请求仍携带原 head 全文。

[B/model-answer.md](../../../research-records/goal-m2-branches-20261112T073526Z/B/model-answer.md) 对应 Native **行 654**，模型却说“已纠正并重新形成”“此候选已…移除了工作步骤和资料获取需求”，并在旧 ID 下描述精简后的不同内容。这是**已保存状态的错误声明**，即使它也正确说明“未采纳正式 ActiveGoal”，仍不能抵消候选状态错误。

最终 Host Journal 只有拒绝和本轮记录；无 VERSION、无 PUBLICATION、无新 head。原始 Journal 前缀、历史版本、两条原文均不变。**VERIFIED**：Host 没有因文字声明自动修改候选。

## 4. CPU 可表达性对照（不是模型纠正）

为排除“原目的没有在当前反馈重述，接口根本无法表达合法修订”，在临时目录恢复同一历史闭包；研究者仅将触发 quote 改为当前反馈的一句原文，同时保留历史输入作 basis。原有验证器接受，父版本正确、目的草案可保存。详见 [quote_control.py](../../../research-records/goal-m2-branches-20261112T073526Z/quote_control.py)、[quote-admissibility-control.json](../../../research-records/goal-m2-branches-20261112T073526Z/quote-admissibility-control.json)。

该参数替换**仅在 CPU 临时副本**，从未发送给 Bolt 或写入 B/原历史 Host。不能计入真实修订、自然形成或模型重试成功。它只证明现有接口存在合法表达路径，不证明 quote 支持语义真实或模型能够选对引用。

## 5. 独立评价与 M3 门

| 环节 | 结果 |
| --- | --- |
| 目的草案/去工作需求 | **PARTIAL**：产生合理长期目的草案，但未完整证明来源/认可分解，也发生了不必要的局部精简尝试。 |
| 自主操作选择 | 在**明确纠正保存状态**条件下，真实选择 revise；不是自然形成或无反馈的自主维护。 |
| 提案/真实提交 | **VERIFIED 6 次调用；FAIL 0 提交**，均因当前触发引用不合规。 |
| 拒绝反馈和状态理解 | **FAIL**：完整反馈之后仍把意向内容描述成已保存内容。 |
| M2 受反馈纠正 | **FAIL 本样本**，不能用草案质量替代真实修订。 |
| M3 | **NOT RUN**：预登记门未通过；没有“更新后的候选”可测试，不追加用户提示修到成功。 |
| M4 / M5 | **UNKNOWN**；没有自主生命周期或 Relevant History 决策增益证据。 |

实际 1 个新用户轮次、4 个模型请求完整 completed；input 总和 84,011、output 总和 1,654 Tokens，最大单请求 input=21,642，Turn≈223.81秒。有效窗口62,259，0 Compaction、0 Context Overflow、0新外部Observation。完整捕获上下游字节一致，见 [B/model-http-audit.jsonl](../../../research-records/goal-m2-branches-20261112T073526Z/B/model-http-audit.jsonl)、[evidence-index.json](../../../research-records/goal-m2-branches-20261112T073526Z/evidence-index.json)、[final-audit.json](../../../research-records/goal-m2-branches-20261112T073526Z/final-audit.json)。84,011是累计输入，并非单请求超窗。

主要阻塞已从上轮的“没有调用”缩小到本例的**当前触发引用选择、拒绝后的合法恢复、状态报告**。错误机制是否为特定模型偏好、接口理解或上下文干扰仍 **UNKNOWN**；不能仅凭此例决定换 Sideband 或修改核心架构。

关联：[工程与阶段结论](goal-m2-branches-20261112.md)、[M2-A 独立报告](goal-m2-readback-20261112.md)。

## 2026-11-12 追加勘误：拒绝回执实际供给边界

原报告“拒绝回执实际进入后续成功请求”的说法不够精确。Native确有ok=false、committed=false的Host回执；但模型后续出站接收的是provider_history转换后的terminal_attempt_fact，保留error、execution_succeeded=false、result_available=false，**没有committed、ok和Goal head变化字段**。因此原失败只证明该转换反馈条件下的误报，不能证明完整Goal回执条件下仍误报。原始失败及已保存状态不变的结论保留。新批次见 goal-m2-current-feedback 后续节点，Schema CURRENT规则不放宽。
