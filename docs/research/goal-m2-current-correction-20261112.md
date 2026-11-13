# M2 当前纠正与历史依据分离：实际修订、语义边界及 M3 门（2026-11-12）

总体 **PARTIAL**。**VERIFIED**：一次明确反馈后，2次真实revise均通过CURRENT引用与历史依据校验，Host保存2个新版本；后续成功模型请求携带最新head，最终回答准确报告新ID及保存内容。**尚未证明完整语义纠正**：新文本把“不自行添加长期限制”泛化为用户“不需要任何长期限制”。按预登记未放行M3；不能把一次合法提交计作M4自主维护或M5决策增益。

批次：goal-m2-current-feedback-20261112T083318Z。本轮未修改正式Runtime、Goal Schema、SQLite Schema、授权及人工入口；保留原恢复和原失败。Memory Research Reserved；未Commit/Push。

## 1. 先修正上一轮证据表述

上一批 goal-m2-branches-20261112T073526Z 确有6次原生调用与6个Host拒绝回执（ok=false、committed=false）。但模型后续收到的是provider_history转换后的terminal_attempt_fact；它保留Call ID、FAILED、错误文本、execution_succeeded=false、result_available=false，**没有原始committed/ok及head变化字段**。

因此旧失败仅证明该转换反馈条件下的误报；不能表述为“模型在完整committed=false Goal回执下仍误报”。上一报告已追加勘误，原JSON与旧Windows评审包不改。定位见 [prior-feedback-audit.json](../../../research-records/goal-m2-current-feedback-20261112T083318Z/prior-feedback-audit.json)；旧model-http-audit sequence2/行4，对应Call chatcmpl-tool-a78d84a56e8cb702；转换逻辑见 [provider_history.py](../../harness/provider_history.py)。

## 2. 现有接口的表达能力与实际送达

| 用途 | 现有表达 | 能验证的内容 / 不能保证的内容 |
| --- | --- | --- |
| 为什么现在修订 | quote：当前注册原始用户输入的精确子串 | 校验当前触发来源；不要求这一句话重述完整历史目的，也不证明新解释真实 |
| 保留什么历史目的 | input_ids：原用户输入ID | 同Thread注册来源及版本；不是模型摘要，也不是统计独立支持或语义充分性证明 |
| 修正哪个对象 | candidate_id：当前非撤回head | 同Thread当前父版本；不证明操作语义合理 |
| 是否真正提交 | Host receipt、VERSION Journal及实际出站投影 | committed、保存及供给事实；不授予ActiveGoal、Memory或执行权威 |

**VERIFIED**：字段足够，本轮真实模型已合法使用；CURRENT校验、字段集合和Host约束未放宽。API的工具参数经过Harness常规规范化，未携带部分min/max长度描述；与上一批实际出站Schema逐字相同，Host仍独立执行长度/引用等校验。不能以Python字典与API参数序列化不同直接认定新Schema变更。

本轮研究Adapter准备了通用说明，解释“当前触发quote / 历史purpose的input_ids / 当前head / committed反馈”，没有给标准Goal答案、具体操作或参数。**但该说明未实际送达模型**：恢复的Native Thread使用原始rollout保存的动态工具定义；[交互入口](../../scripts/h3_harness_interactive_repl.py)在thread/resume时不重新传dynamicTools。真实出站工具与上一批完全相同。见 [tool-delivery-audit.json](../../../research-records/goal-m2-current-feedback-20261112T083318Z/tool-delivery-audit.json)、[cpu-preflight.json](../../../research-records/goal-m2-current-feedback-20261112T083318Z/cpu-preflight.json)。

这是预登记暴露条件偏差：本地准备/CPU工具描述变化不能冒充实际送达。**不得将本轮合法修订归因于说明改善**；它只证明原有接口在本次输入和抽样下可合法使用。未为此修改历史rollout或正式Harness。

## 3. 独立恢复、一次反馈与停止规则

从 goal-intent-lifecycle-20261112T031832Z/B 的同一冻结原历史恢复，不重新生成种子，不带入上轮纠正回答。保留Thread 01a1cdd9-84df-7030-a240-4ea8f75089ea、Scope、两个原Candidate、父关系、输入版本、4条历史Observation及已处理Call。Native home和Host状态在新副本，原始文件/原Native home未变。这里的历史用户通道内容来自研究者冻结的金融复演脚本，并非独立验证的用户投资心理真值或新交易委托。

本次一次反馈原文在 [scenarios.json](../../../research-records/goal-m2-current-feedback-20261112T083318Z/scenarios.json)，要求去除模型待办与资料获取/保存操作、保留用户目的、不自行添加长期限制，如实报告Host状态。没有给完整候选或指定revise。旧反馈和新反馈措辞也不同，且无重复采样；不能用前后两批声称单变量因果改善。

[study_driver.py](../../../research-records/goal-m2-current-feedback-20261112T083318Z/study_driver.py)复用原Harness循环。研究停止钩子仅限制首次拒绝后新的模型请求，既不补发工具，也不改参数；CPU故障对照证明拒绝标记后0次上游请求。**本批B没有拒绝，该停止钩子未触发**。M3另受语义证据门控制。预登记见 [preregistration.json](../../../research-records/goal-m2-current-feedback-20261112T083318Z/preregistration.json)。

## 4. 纠正前后完整候选

| 分支 | 原head | 新head及父版本 |
| --- | --- | --- |
| 长期 | goal-candidate:098ea60b1c3caf2ca410b22d | goal-candidate:63a3dfa892d9d1a952d61d0f → metadata.previous_candidate_id=goal-candidate:098ea60b1c3caf2ca410b22d |
| 局部 | goal-candidate:0cb6591e2475fdd96208bc87 | goal-candidate:7a2044e25371a290c3bd2287 → metadata.previous_candidate_id=goal-candidate:0cb6591e2475fdd96208bc87 |

长期原文：
> 长期跨公司AI产业投资机会研究是全局范围目标，需从本地摘录之外查找更多AI行业与公司资料，并在可撤销的目标假设中保留。

长期新文：
> 基于本地冻结摘录的长期跨公司AI产业投资机会研究是全局范围目标，依据S-INTC/S-AAPL/S-GOOGL三份已读官方摘录为可撤销目标假设；未要求从本地之外获取资料，也不需要任何长期限制。

局部原文：
> Intel当前财报与估值分析是局部范围目标，基于已读的官方摘录（INTC 2026Q3收入$16.5B，GAAP EPS $0.60，non-GAAP EPS $0.52）可撤销地保留。

局部新文：
> 基于本地冻结摘录的Intel当前财报与估值分析是局部范围目标，依据已读S-INTC（2026Q3收入$16.5B，GAAP EPS $0.60，non-GAAP EPS $0.52；Q4 non-GAAP EPS指引$0.25不是forward年度EPS；无分析师共识，不能据此认定miss）为可撤销目标假设；11-04真实报价、共识和完整电话会议缺失，保留未知。不需要任何长期限制。

**版本关系在metadata.previous_candidate_id，不是通用object.parent_id。** 旧两条记录仍作为不可变历史保留，已不在当前head；历史文字继续出现在旧对话中并不构成旧head复活。

### 实际来源与执行证据

- 新Native Turn：01a1ceeb-3d44-7ad3-8e47-5475e5169695。
- [B/app-server-events.jsonl](../../../research-records/goal-m2-current-feedback-20261112T083318Z/B/app-server-events.jsonl) 行16：chatcmpl-tool-9074d2d9ed4c6c43，长期revise；行19：chatcmpl-tool-9fb3813039f794ea，局部revise。
- [B/goal-events.jsonl](../../../research-records/goal-m2-current-feedback-20261112T083318Z/B/goal-events.jsonl) 行6、8：真实VERSION及committed=true；行7、9：提交后的publication记录。两条parent分别指向原真实head。
- 两次quote都来自本次反馈：“依据原始用户输入重新理解我真正希望实现的方向，并修正当前保存的长期意图解释；保留仍有依据的目的，不自行添加长期限制。”
- 两次input_ids都显式包含本次 input:279d30c0-70af-41e5-a654-06aeda0be5a1 与历史 input:f4e32d18-219d-4c3e-83ab-6b89201fee81。当前/历史文本SHA与注册版本一致。
- [B/model-http-audit.jsonl](../../../research-records/goal-m2-current-feedback-20261112T083318Z/B/model-http-audit.jsonl) sequence1含原head，sequence2含两个新head全文及接受回执，均完整completed。sequence2是**同一用户Turn内**的后续请求，不是M3下一用户轮。
- [B/model-answer.md](../../../research-records/goal-m2-current-feedback-20261112T083318Z/B/model-answer.md) / Native行759：最终准确报告新ID及Host实际保存的条款。保存状态报告已不同于上轮虚称更新；不能因此证明语义条款受原文支持。
- 精确关联与哈希见 [final-audit.json](../../../research-records/goal-m2-current-feedback-20261112T083318Z/final-audit.json)、[branch-evidence.json](../../../research-records/goal-m2-current-feedback-20261112T083318Z/branch-evidence.json)、[B/goal-wire-receipts.jsonl](../../../research-records/goal-m2-current-feedback-20261112T083318Z/B/goal-wire-receipts.jsonl)。

## 5. 语义审读与 M3 不放行的原因

**已改善**：长期研究AI产业投资机会的核心目的保留，肯定式“需从本地之外获取更多资料”的工作需求被移除；原始目的输入与当前纠正用途实际分离。

**尚未闭环**：用户“不自行添加长期限制”是约束模型解释的要求；它不支持用户在所有相关情境下“不需要任何长期限制”这一新泛化。两条新候选都保存了后一句。该语义外推是M2未完整通过的主要原因。

按审计标准区分，不因文字不够纯粹机械判失败：

- 数字、来源名和已读事实可为无害背景，不能仅因存在方法/事实词判整个候选无效。
- “基于本地冻结摘录”可能只是当前研究背景，也可能被当作长期范围，现有样本不能确定后续影响。
- “未要求外部获取”**不等于禁止外部获取**，本评审不把二者混同。
- 主要风险是把不新增未经确认的限制，反向变成用户永远无须限制的偏好；该条未被用户确认。
- Host接受结构合法的非权威解释符合契约；不能要求Runtime变成通用语义真值裁判。候选仍semantic_correctness=not_established，未改权限或正式状态。

[B/gate-1-review.json](../../../research-records/goal-m2-current-feedback-20261112T083318Z/B/gate-1-review.json)保留了上述独立语义判断。预登记要求“实际语义纠正并保存”才进入M3，因此Apple后续Task **NOT RUN**。这是研究准入停止，不是模型服务失败、模型无法执行Apple任务或Context超窗。未追加提示修到PASS；没有因数据库出现新版本宣称认知闭环。

## 6. 运行事实、成本和边界

1个新用户Turn、2个成功模型请求、2个原生Goal调用、2个接受、0拒绝、0新外部Observation。API input累计42,375 / 最大21,710，output累计1,431；0Compaction、有效窗口62,259。相加的Token不是单请求Context长度。

保持56/72 UMA、64K、KV1GiB、单并发、util0.65及全部监控。资源与清理证据见 [final-audit.json](../../../research-records/goal-m2-current-feedback-20261112T083318Z/final-audit.json)。本运行还包含单独的C1诊断；资源统计覆盖整个服务生命周期，不能当作仅Goal调用的成本。C1数据构造错误和修正后的独立C2，见[反馈对照独立报告](goal-m2-failure-feedback-20261112.md)。

当前里程碑：M1 PARTIAL；M2-A沿用先前限定PASS不重复；M2-B **PARTIAL（合规提交与真实保存报告VERIFIED，语义纠正未完整通过）**；M3 NOT RUN；M4/M5 UNKNOWN。没有Relevant History决策对照，不能宣称新增Goal有决策收益。

## 7. 下一步建议

本轮已跨过“当前引用必然错误/没有真实提交”这一阻塞，但没有跨过“正确抽象用户目的”。优先研究一个小问题：**用户纠正模型不应推断某偏好时，模型能否避免反向推断成相反的永久偏好**。沿用可撤销候选与原始Evidence，采用固定、可证伪的范围/否定/不确定性案例，不新增语义裁判或强制提交。

真实M3应在候选语义边界达标后验证实际新Task与读取行为；若仅证明新head进入模型请求，应单独记作状态供给成功。不要通过增加Prompt、修订轮数或Runtime规则追求PASS。当前没有正式Schema/Goal Engine/Memory层变更依据，暂停提交本轮评审。
