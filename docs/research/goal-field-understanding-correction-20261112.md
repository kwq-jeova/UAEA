# Goal 字段理解与受反馈纠正限定验证（2026-11-12）

总体 **PARTIAL**。本轮先更正旧评分，再执行两个独立分支；没有重跑旧实验，没有修改正式 Runtime、SQLite、Goal Schema/CURRENT 规则或 Sideband 生命周期。

批次：goal-field-understanding-correction-20261112T130408Z。

主要结果：

- 旧回答 hypothesis 更正为 **4/6**，两条把 quote 填进正文栏；旧完整字段绑定 PASS 撤销。
- 新 A：hypothesis **6/6**，quote **4/6**，target **6/6**，committed **6/6**；四字段全部正确的 Call 为 **4/6**。整体 PARTIAL。
- B：真实发起一次 revise，但仍选历史目的原句作为 quote，未使用当前输入提供的合法句；Host 正确拒绝，committed=false，无新版本。
- 新 head 后续投影没有可测试对象；M3、30轮、M4/M5、Memory 均未推进。

## 1. 旧评价纠错，不改原模型证据

旧批次 goal-postprojection-readback-repair-20261112T123257Z/P2 的“完整绑定限定 PASS”有误。此前以全文包含关系辅助核验，没有识别同 Call 下字段被错放；这种判断不成立。

| 旧 Call ID 末段 | 原模型正文栏 | 实际 hypothesis | 结论 |
|---|---|---|---|
| b21dfc2c9aa2e545 | 我希望长期跨公司研究AI产业投资机会 | 长期跨公司研究AI产业投资机会 | quote 误当 hypothesis |
| 8b034a9ece344047 | 另一个局部目的，是完成Intel当前财报与估值分析 | 完成Intel当前财报与估值分析 | quote 误当 hypothesis |

其他四条 hypothesis 正确。target、committed 分别 6/6；旧答没有独立 quote 栏，因此 quote 为 UNKNOWN，不能补算通过。前两条真实 hypothesis=quote，字面匹配也不足以证明区分字段的能力。

已更正：

- [上轮阶段报告](goal-postprojection-state-correction-20261112.md)。
- 旧批次 manual-review.json；同目录保留 pre-field-correction 版本。
- 原 Windows 评审包的报告、评价及入口，新增 04_字段绑定评分更正.md。
- 研究地图和阶段进度。

旧评分、原报告、旧 Windows 校验清单先复制到本批次 before/；新评价用 supersedes 指向旧版本。原回答、Native、HTTP、Host Journal 和源 Native home 不变，旧模型实验没有重跑。

[逐 Call 纠错 JSON](../../../research-records/goal-field-understanding-correction-20261112T130408Z/old-evaluation-correction.json) 包含四字段期望值、正文栏实际值、不可观测 quote、错配类型及原行。

## 2. 预登记、同一基线与研究边界

A/B 从同一冻结 Native 历史 goal-m2-branches-20261112T073526Z/B 克隆，源 rollout SHA 相同；历史 Goal Journal 前缀相同。Goal 保存状态来自已核验原始两 head、两 version，与该失败分支一致；身份、Thread/Scope、原 Candidate ID 保留，两个副本不共享新交互。

这仍是隔离的 Goal 状态恢复，不声称恢复失败分支全部旧 Workflow/Input 缓存。当前新用户输入通过原机制登记，历史目的输入 f4 为已恢复的合法原始记录。没有重放历史工具执行，也没有粘贴 ID 伪造版本链。

- A：一次字段核对输入。只要求列出实际四字段，不提供正确值；允许既有只读工具，不允许该分支修改 Goal。
- B：一次显式 revise 邀请。当前输入提供合法纠正句“请修订旧候选中不属于我长期目的的内容。”，并给出已登记的历史目的 Input ID input:f4e32d18-219d-4c3e-83ab-6b89201fee81。不提供候选标准正文或完整工具 JSON。
- B 是带引用用途指导的正控制，不是自然形成或自主维护测试。
- 各分支最多4个模型请求、Turn 420秒；B首次拒绝后停止，无补发、修参或追加提示。
- 实际出站 Goal Schema/说明保持原样，仍明确 CURRENT；六条历史失败实参完整送达。评价真值文件在研究目录，不放入模型可读 sandbox。
- M3代码路径已移除，不因提交成功扩展实验。

[预登记](../../../research-records/goal-field-understanding-correction-20261112T130408Z/preregistration.json) /
[完整用户输入](../../../research-records/goal-field-understanding-correction-20261112T130408Z/scenarios.json)。

## 3. A：字段理解 PARTIAL，错误转移不能当成完整成功

[模型完整表格](../../../research-records/goal-field-understanding-correction-20261112T130408Z/A/model-answer.md) /
[逐 Call 四字段评分](../../../research-records/goal-field-understanding-correction-20261112T130408Z/A/field-audit.json)。

| 字段 | 正确 / 总数 | 独立结论 |
|---|---:|---|
| hypothesis | 6/6 | 本样本实际正文读回正确 |
| quote | 4/6 | PARTIAL；前两条原值被扩写 |
| target | 6/6 | 正确对应操作目标 |
| committed | 6/6 | 正确报告全部 false |
| 同 Call 四字段全部正确 | 4/6 | 不是独立样本成功概率 |

新错误：

| Call ID | 实际 quote | 模型 quote |
|---|---|---|
| chatcmpl-tool-a78d84a56e8cb702 | 长期跨公司研究AI产业投资机会 | 我希望长期跨公司研究AI产业投资机会 |
| chatcmpl-tool-a9d018f5e15dac09 | 完成Intel当前财报与估值分析 | 另一个局部目的，是完成Intel当前财报与估值分析 |

较长值确实出现在后续 Call 的 quote 和历史用户原文中，但不属于这两次实际提交的 quote。来源中出现某段文本不等于它属于当前 Call 的字段。不能以“都是用户原话”或“意思相近”判字段复制正确。

需要区分两种现象：

- 旧答：第3、4项把 quote 放到 hypothesis 正文栏。
- 新 A：hypothesis 全部正确；前两项的 quote 原值被补写成后续调用的较长原句。
- 在四个 hypothesis≠quote 的案例（3–6）中，本次四字段均正确。不能笼统说模型完全不懂字段；仍不能说逐 Call 数据保真已通过。

A 的目标是实际参数读取，不评价这些历史 quote 当时是否合法，更不评价 Goal 语义真实。六行来自同一次回答，并非六次独立实验；committed真值均为false，因此6/6不证明成功/失败混合、新提交后的通用状态理解。其1个Native Turn完整结束，0工具调用、0新版本，两个 head 不变。

研究评分器 field_audit.py 只比较同 Call、同字段的带标签单元格；重复 Call ID、缺字段、UNKNOWN 分开处理。CPU反例覆盖旧误判4/6、完美值、目标交换、错误继承true、重复ID、表格字段解析。它不是 Runtime 语义裁判，不从普通回答建立 Goal。

## 4. B：有合法当前句仍选历史 quote，真实纠正 FAIL

原生调用：

    Call ID: chatcmpl-tool-9a22498ac1de5917
    operation: revise
    candidate_id: goal-candidate:098ea60b1c3caf2ca410b22d
    hypothesis: 长期跨公司AI产业投资机会是全局范围目标。
    quote: 我希望长期跨公司研究AI产业投资机会
    input_ids: [input:f4e32d18-219d-4c3e-83ab-6b89201fee81]

| 验收维度 | 判定 | 证据与范围 |
|---|---|---|
| 实际提案/目标绑定 | VERIFIED | 真实 Native revise，目标是当前长期 head；并非文字计划 |
| 当前引用来源合法性 | FAIL | 所选 quote 在历史输入中，不在当前反馈中；长度未超限 |
| 历史目的依据 | VERIFIED（身份范围） | 现有 input_ids 使用正确已登记 f4；不等于完整语义支持证明 |
| 候选语义忠实性 | PARTIAL | 保留长期、跨公司、AI投资机会及全局方向，移出Agent To-do/临时条件；省略“研究”，不机械判扭曲，也不给完整忠实性PASS |
| Host 实际保存 | VERIFIED拒绝；纠正闭环FAIL | ok=false、committed=false；0新版本，仍2 heads/2 versions |
| 新 head 后续投影 | 未开展/无对象 | 未产生新 head，不是投影失败 |
| 拒绝后的模型状态报告 | CENSORED | 按预登记首拒绝停止，无最终报告；不能声称又虚报成功 |

实际 Host 回执：

    Quote must come from CURRENT original input, not model/summary

CURRENT 纠正句及历史 Input ID 已进入真实 HTTP 请求，不是只在本地 Adapter 准备。工具描述也明确 CURRENT，未改引用规则。没有发现信息供给、版本绑定或 Host 拒绝逻辑的新缺陷。

这次将“支持目的含义的历史原句”用于“当前纠正触发引用”，其来源选择不合法。为什么仍选择历史句——忽略指令、复制旧模式、证据用途混淆或其他模型行为——内部机制仍 UNKNOWN。不能据此宣布现有 Schema 无法表达。

草案是名词式方向概括，未明显增加收益目标、交易行为或新限制。省略“研究”使活动/结果范围表达不够明确，故保留 PARTIAL；不因一个词缺失机械FAIL，也不由 Host 状态决定语义评分。

[Native 调用/Host 回执](../../../research-records/goal-field-understanding-correction-20261112T130408Z/B/goal-wire-receipts.jsonl) /
[引用与保存核验](../../../research-records/goal-field-understanding-correction-20261112T130408Z/B/binding-audit.json)。

## 5. 传输、成本和安全独立记录

A/B 各有1个完整模型响应，HTTP framing、response.completed、上下游 SSE 字节一致均通过；B这个完整响应是工具提案，不是完整用户Turn或任务完成。B在Host拒绝后研究停止，最终状态陈述为CENSORED，不能与HTTP截断混淆。

| 项目 | A | B |
|---|---:|---:|
| API input tokens | 26,012 | 25,866 |
| API output tokens | 530 | 163 |
| API total tokens | 26,542 | 26,029 |
| 分支耗时秒（含恢复/清理） | 79.707 | 43.218 |
| 完成用户Turn | 1 | 0（首拒绝停止） |
| Goal调用/新版本 | 0/0 | 1/0 |

一轮模型加载，整体243.744秒。有效service资源样本217条，NVML峰值28.764 GiB，Windows Commit最低余量23.742 GiB、最低原停止线缓冲5.446 GiB。64K、1 GiB KV、seq1、util0.65不变，实际KV容量109,817 tokens；无Compaction、无超窗或输出截断。

原单时钟采样、AC身份/新鲜度及内存门限保持；服务最终为计划CONTROLLER_STOP、remaining=[]，Native进程组退出，没有资源或遥测失效触发停止。资源完整指标见 [resource-summary.json](../../../research-records/goal-field-understanding-correction-20261112T130408Z/resource-summary.json)。

正式可执行源码、原安全/模型pins、源Native home和旧原始回答/HTTP/Journal哈希均复核。只有隔离研究脚本、评价说明、报告和索引增量；未 Commit/Push。

[执行事实审计](../../../research-records/goal-field-understanding-correction-20261112T130408Z/execution-fact-audit.json) /
[原件与源码核验](../../../research-records/goal-field-understanding-correction-20261112T130408Z/source-safety-immutability.json)。

## 6. 进度与下一步

- 历史恢复/失败投影：保持工程限定PASS；本轮真实请求中信息完整，不代替认知评分。
- 字段理解：PARTIAL；不能再使用全文包含关系证明正确绑定。
- M2受反馈纠正：本次显式正控制FAIL；已有历史合法保存通道证据保留，但尚无本轮合法、语义充分忠实、已保存并实际供给的新 head。
- M3：按本轮边界不开展；M4/M5 UNKNOWN；Memory Research Reserved。

当前没有证据支持改正式Schema、放宽CURRENT、自动修quote或新增语义裁判。应保留错误提案，避免将失败自动“修好”后误报模型能力。若继续研究，优先用固定冻结材料区分“字段原值保真”与“生成提案时证据用途选择”，必要时评估可替换模型；不把本项目变成不断追加提示直到调用成功的循环。

## 7. 独立审计

Audit Agent 已独立解析原Native/Host回执，确认旧4/6及新A各字段计数，复核同一冻结基线、实际CURRENT供给、真实拒绝、完整HTTP与无新head。最终书面意见归档 independent-audit.md；整体仍PARTIAL，B纠正FAIL，CENSORED和UNKNOWN不得提升为PASS。报告完成后停止，不启动追加实验。
