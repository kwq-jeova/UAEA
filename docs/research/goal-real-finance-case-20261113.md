# 真实金融资料案例：Goal View ON/OFF（2026-11-13）

总体 **PARTIAL**；金融答案/决策比较 **CENSORED**。本批一次冻结配对结束，未重跑模型或扩大请求预算。独立审计以原始Native/HTTP/SSE和实际供给内容为准。

## 任务与来源

用户选择“金融板块分析或者股票分析”为后续研究对象。研究者据此选NVIDIA/AMD，要求自行选一项最值得检验的差异并完成比较/计算，不指定结论/具体指标。领域选择不等于用户确认个人投资目的、风险、仓位或交易权限；任务文本的具体公司/措辞是研究者编写。

从未受M4治理脚本影响的真实A55,275B checkpoint独立建立两个Thread，原global76fe/四版本/20条普通历史均相同。OFF只删除当前专用Goal视图，仍保留普通修订历史、工具回执、Sideband和Host状态。OFF f0→ON f1，首CPU wire规范化仅差View，实际模型首请求也由独立审计核对。单次顺序配对不能证明稳定因果收益。

本次新来源与旧研究者摘录分开：实际HTTPS抓取两份官方发布全文，原HTML、URL/UTC/headers/字节SHA、可复现提取器和派生正文均归档。
- [NVIDIA FY2027 Q2发布](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Second-Quarter-Fiscal-2027/default.aspx)：8月26日发布，截至7月26日。
- [AMD 2026 Q3发布](https://ir.amd.com/news-events/press-releases/detail/1303/amd-reports-third-quarter-2026-financial-results)：11月3日发布，截至9月26日。

这是11-13新任务可见资料，不提前用于此前11-04历史估值；不声称仅凭抓取证明公司每项陈述/市场真值。模型配置、来源/工具权限、420秒Turn/600秒分支、4次请求和2048输出上限相同。

## 重要供给限制

**文件正确、读取成功，不等于财务正文已经送达模型。**

新文件只有一个整体Markdown section。read_section实际读取完整30K/38K字符，Adapter在12,000字符回执总预算内采用既有通用fallback：data.content只有800字符并明确标记[field truncated]，基本止于长来源头/标题。Native Tool回执与成功Provider请求都没有包含本次关键日期或财务数字；recovery_sources为空。ON请求section2时正确返回section_not_found。

首次截断发生于现有HarnessDynamicToolAdapter.to_app_server_response→_bounded_json_text（codex_dynamic_tools.py 144/475–484）；不是HTTP损坏、64K超窗或Compaction。原始ToolResult/Observation与原文件可追溯，Provider再转发未恢复缺失正文。不得把本次错误记成“正确日期已提供而模型仍混用”，也不能由源文件哈希正确证明语义支持已供给。

## 实际行为与状态

| 条件 | 真实行为 | 状态 / 成本 |
|---|---|---|
| OFF f0 | 5次read成功，包含一次短旧Intel卡；重复读两新文件仍只获800字符。主动form97cc→revise668c，CURRENT/父版本合法，Host保存2个local新版本；候选写出无已供证据的7-31/9-30和“期间不重叠”，并混写研究优先项/未验证事实 |4请求，输入122,553/输出1,392，287.21秒；Native失败、无最终答案|
| ON f1 | 8次read尝试：6成功但正文截断、2次section2不存在；尝试获取后续段，没有Goal提案/新版本；没有交付最终比较 |4请求，输入126,402/输出810，233.42秒；Native失败、无最终答案|

两组均在第5次恢复时触发ResearchBudgetStop（limit4），实际仅各4次上游请求；first-exception.json保留classification=budget_exhausted、stage=bridge_research_budget、原始原因/时间/计数。Native对外显示本地Bridge502，是预算停止的下游表现，不是已证明公网错误、vLLM停服或Harness恢复机制故障。原有日志问题在本例获得真实验证；不扩大请求数救援。两组实际各有34次restore_started：前4次对应4个成功上游请求，第5–34次为30次被预算挡住的本地Harness自动重连/恢复尝试。没有人工追加提示、重跑模型或突破上游cap，不等于没有本地自动重试；34不能计成模型请求或认知行动。

8个实际上游响应传输/生成均完整，但都是过程/工具响应，不能代替用户任务完成。ON最后2个读取回执发生后没有第5个成功Provider请求，不宣称这些内容已被模型消费。

### OFF 候选细节

- form Call chatcmpl-tool-965bc297c22de78d → goal-candidate:97cc2712cb746f920452ce3b。
- revise Call chatcmpl-tool-995b631c523be1cf → goal-candidate:668c58ea375f560a9dc896ea，父97cc。
- 两次committed=true、参数/原文/hash对应；原global76fe保持，新增仅当前Thread local family，未自动全局绑定、正式采纳或授权。
- form回执进入第4个实际模型请求；最终revise已由Host保存，但其后第5请求被预算阻止，**没有成功的后续模型送达/行为**。prepared/publication不等于delivered。
- 没有显式Goal操作邀请，故是自然工具选择存在性证据；但不是合格的长期Goal形成/M4/M5成功。
- 用户确实委托选择比较问题，选择AI基础设施供给可以是合理的局部研究方向；不能仅因模型选定或出现方法词就判整个候选归属错误。应单独评价候选以研究结论/优先项为主体的抽象质量，以及无已供证据的日期、“不重叠”、旧11-04/资料缺口等混写。归属/抽象PARTIAL，具体精确事实不受所供正文支持。
- 原件日期实际不同且季度存在重叠，但这些正确日期当时未进入模型请求。可记录“信息缺失时仍编造精确断言”，不能定位成读到正确日期后的误算/错配。

同一组无依据的精确日期在form→revise中持续出现，后版还称其为“正式期间”。这是可观察的候选内错误保持；不能进一步断言Host接受回执造成了强化，内部因果仍UNKNOWN。原本只是不完整的证据，不应因候选被保存而自动变成可靠事实。

## 无模型最小修正：源文件机械分段

本批原文件/Journal/Native/请求均未改。独立source-section-reachability副本将完整parsed正文按原序、最多500字符机械切片，不选择答案、不增加事实；139段均带原sha和字符offset，原文逐字无损覆盖。正式Tool/Schema、回执12,000预算、Context/24KB恢复预算全部不变。

- 139段经真实现有adapter序列化，正文最大654字符、总回执最大9,174字符，正文不再被800 fallback截去。
- CPU真实Harness→Bridge→HTTP协议桩3请求，实际read NVDA第2段、AMD第16段，下一请求逐Call包含正确日期片段；原4 Goal版本/Scope不变。
- 测试定位器选择这两段只用于CPU验收，未作为真实模型输入或自动检索算法。首次漏复制live_capture_v2 helper的CPU导入失败保留；补齐后通过，无GPU重试。
- 只证明既有接口下相关正文可达。模型能否自主选段、在4请求内完成任务、正确理解表格及是否改善Goal行为 **NOT RUN/UNKNOWN**。机械切片可能切断表格语境，跨段聚合和目录成本仍需之后有限研究，不宣称已解决长金融资料阅读。

## 安全、判断与下一步

固定56/72、64K、1GiBKV、并发1、util0.65，原准入/停止线/AC/Fail-Closed未改。586条服务采样有效，820条AC在线；NVML峰28.869GiB，Shared峰0.220GiB，Commit最低余21.708GiB、距原18.296GiB停止线3.412GiB。服务正常CONTROLLER_STOP、无owned残留；原5618输入/136源码/15安全pins无变化。不是长时稳定性证明。

- **VERIFIED（限定）**：真实来源字节/解析、实际首请求公平性、CURRENT/真实local form→revise保存、原global/正式边界、预算原因日志及CPU正文可达性。
- **PARTIAL**：自然表达为局部研究候选的归属/抽象、来源不足时的UNKNOWN处理；OFF存在精确猜造，不能以Host接受洗白语义。
- **CENSORED**：两组最终金融答案、任务完成、实际决策增量比较。
- **UNKNOWN**：当前结构化View净收益、M4普遍自主维护、M5真实用户决策价值、自动分段选择及聚合能力。
- **NOT RUN**：分段资料下的真实模型复验；本轮不通过更换资料后立即重跑追PASS。

下一项最有判别力的工作是将这139段作为独立资料可达性协议，在下一金融任务中观察模型能否自主定位/聚合并保持UNKNOWN，而不是继续调整Goal Prompt或增加Runtime语义规则。保留原CENSORED批次作为对照，不与后续协议结果混合。现有Sideband/Journal仍足以记录合法候选；800 fallback是本次fixture与既有接口粒度不适配，不构成增加Goal Engine、改Schema或开放权限的证据。

M3先前三批的连续性正例和反例独立保留，本例不倒改为认知PASS或抹去旧结果。全部原始材料位于 goal-finance-realcase-20261113T071403Z；Audit Agent独立逐请求审阅。未Commit/Push。
