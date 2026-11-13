# Phase 1：56/72 UMA、64K连续金融研究（2026-11-12）

总体 **PARTIAL**。**VERIFIED（限定）**：同一Thread原生完成30轮、42个完整模型请求、最大实际输入49,542 Tokens，一次自然Compaction，无Context Overflow或真实资源停机。任务/SIM持续但语义及执行历史回顾仍有错误。**UNKNOWN**：32K单变量收益、真实决策收益、Goal Cognition收益。

阶段结束后停止，待用户评审；不自动启动Phase2或Goal对照，不Commit/Push。

## 1. 批次与可复现性

原始记录目录：/home/wqkan_wsl/uaea-n1x/research-records/finance-phase1-64k-20261111T235041Z

Thread：01a1cd0b-7922-77f1-bb00-af9bec7a83c9。30个不同Native completed、30份快照，未拼接历史失败批次。Goal Off / projection none，input_actor=test_driver，Shared执行，只有document.read_section；无Shell、Web、写入或交易。本轮没有Goal Shadow。

基础HEAD为125f0d2a8e6b7ac0f6b70baf9913b942be2b1cb2，但工作树原已dirty。冻结131个源码文件，必须以frozen/source-lock.json和实际副本复现，不能只checkout HEAD。session/run-manifest.json中uaea_head/git_dirty为null（隔离副本无.git）；git-before.json及reproducibility-note.json补关联，原Manifest不改写。164项输入锁、131项隔离及工作树对应源码、15项正式启动/守卫/已安装策略运行后全部hash一致。

本轮正式仓库仅新增本报告和研究地图索引。隔离runner、审计及原始记录在仓库外；没有Runtime、Harness、权限、模型依赖或正式启动入口改动，原dirty历史全部保留。

### 场景和时间限定

- 原30条用户输入未改写；前15轮来自interactive-32768-20261105-053257与interactive-32768-20261105-071627的改编，后15轮为研究者扩展。逐条定位见frozen/scenario-provenance.json及historical-user-inputs.json，不冒充真实用户的新Goal。
- 原场景compact_after=20在冻结前移除，本批次仅自然压缩。继承frozen/README.md仍有旧32K双组/受控20轮描述；它不适用于此批次。CURRENT_PROTOCOL.md、预登记、protocol及实际driver明确差异；没有事后改脚本。
- 系统时钟未改；研究冻结时点11-10，历史估值目标11-04。原文档11-09采集、hash校验通过，不能证明11-04已可得的字节版本。交易日、真实收盘价、年度共识、完整电话会议保持UNKNOWN，不宣称严格时点回测。
- 模型实际只读取三份研究者预提取的官方财报短摘录（约708/715/765字节）及SIM卡片；没有读完整HTML/PDF或实时Web。原始文件hash/引用保留，本轮未重新联网核验财务字段，Alphabet沿用已有摘录。字段存在不等于财务真实性；本报告算术检查以冻结字段为输入。
- SIM文件按预定轮次释放、旧版不可变；文件存在不等于读取。纸面现金/仓位不代表真实持仓，无真实交易。此负载比全文网页研究简单，不能把结果扩展为完整Web Research PASS。

## 2. 实际配置与保护

| 项目 | 实测或固定值 |
|---|---|
| UMA | GPU56GiB / Host名义72GiB、Windows可见70.481GiB |
| 模型 / Driver | 现有Nemotron3.5 Bolt74B / 621.14 |
| vLLM / Codex Harness | 0.32.0 / 0.163.0 |
| Context / KV / 并发 | 65,536 / 1,073,741,824字节 / 1 |
| utilization / N1X实际预算 | 隔离入口0.65 / 36GiB（实际budget journal） |
| 引擎报告KV逻辑容量 | 109,817 Tokens，不等于实测满窗口或可以增加并发 |
| Native有效窗口 / 自动压缩阈值 | 62,259 / 49,152 Tokens |
| Host恢复供给上限 | 原24KB不变，不与模型Token窗口混淆 |
| 就绪时间 | 108.07秒，一次加载，无自动重试 |
| 期限 | 每Turn420秒，worker13,200秒，controller15,000秒；与服务/Workflow生命周期分离 |

采样预算2秒、新鲜度3秒、GPU48GiB、Windows Available6GiB、Commit余量max(16GiB,Limit×20%)、WSL Available4GiB、Swap256MiB等阈值不变。启动前GPU48和Windows stale的两项模拟smoke按预期停止，不能当作负载中真实越界。

正式服务3,066个资源样本，AC 3,310个均在线有效；无NVML17、遥测拒绝或真实阈值触发。收尾CONTROLLER_STOP是完成后的owned服务清理。monitor-exception虽使用通用“Safety stop”文字，primary_sensor_failure=null、resource_stop=null、remaining=[]，不是安全异常。Native进程组absent、监控清理remaining为空、AC观察器stop_requested/error=null；8000/8003无监听。

## 3. 容量与执行证据：限定PASS / VERIFIED

| 指标 | 结果 |
|---|---:|
| Native完整会话 | 30开始、30不同completed、30快照，同一Thread |
| HTTP完整 / response.completed | 42 / 42，framing、EOF、字节与终端事件交叉验证 |
| 实际输入超过32,768的请求 | 12 |
| 最大输入 / 同请求总Tokens | 49,542 / 49,909，T22 sequence31 |
| 自然压缩 | 1，T23 |
| 超窗 / 部分传输 / 输出上限截断 | 0，未见response.incomplete |
| 真实工具Call / Observation | 23 / 23，均成功，无遗漏拒绝或失败，无重复Call ID |
| 原件与供给正文hash | 23次原件核对有效；324次历史正文供给及完整传输全有效 |
| 流采集 | 42份上下游SSE逐字节相同，结束完整、未触限 |
| 累计输入 / 输出 | 1,204,450 / 20,017 Tokens，含压缩 |

最大请求ID：64514866-1f5e-4e3d-8822-4628edb64fd6。这是实际金融对话，非填充探针；49,542仍小于65,536，结论是“64K配置下真实超过32K负载通过”，不是满64K payload验证。

自然压缩请求sequence32（761773b6-48f9-492e-8d0a-376029dc49dc）41,751输入/1,271输出，随后sequence33输入16,261。Native Turn为01a1cd2b-0e07-7811-b6ab-330902d31e2b，item为01a1cd2b-0e1e-7b80-92d6-651f0e5c0359。压缩时18个历史工具输出共47,347字符仍正常完成；不能保证任意批量大网页正文都不会挤占空间。

10个不同文件、23次读取，13次同路径再次读取。T22/T23核对Intel三版、T29重读目录；重复身份不自动等于无效或统计独立证据。aapl-v2没有真实读取，T17仍用用户新价格计算正确；不能以结果或目录存在证明v2正文已供给。

最大输入的组成另存context-composition.json：18次工具回传正文合计5,322字符（含同源重复），工具完整output为47,347字符；还有系统/Host说明、用户历史和模型回答。49,542 Tokens不等于49,542 Tokens的新金融证据。当前证明了更大的真实工作窗口和完成能力，尚未证明更高的有效证据密度。

未复现历史121次重复输出，旧根因仍UNKNOWN；本轮上下游一致不证明旧异常已修复。

## 4. 连续性与金融行为：PARTIAL

压缩后继续Intel/Alphabet研究，Intel三版、纸面现金条件保留。T20取消Apple子任务并未中断其他公司研究，T26理解目的转向数据核验，T27允许Apple作为方法样本。无旧sandbox路径读取失败。

但T28执行回顾错误、T30继续笼统说Apple完全停止；应区分旧估值子任务与后来的方法样本。正确当前请求已进入出站输入，不等于模型正确采用。Host snapshot Topic仍含初轮摘要，当前请求独立正确供给；历史Topic的因果影响UNKNOWN。本轮未修订它，也不能把模型记得现金条件当作Host已提取全部金融约束。

| 检查 | 判定/级别 | 轮次 | 实际观察 |
|---|---|---|---|
| unit_intel | FAIL / VERIFIED | 1 | 供给16.5 billion USD，回答写16.5亿美元；应165亿美元，压缩前即出现。 |
| assumption_scope | PARTIAL / VERIFIED | 14 | Apple讨论出现50÷(2.10×4)示例；50此前为Intel SIM价，未交代Apple假设。回答同时拒绝把它当真实forward估值，不能升级为已冒充实际Apple报价。 |
| miss_reasoning | PARTIAL / VERIFIED | 2,6,14 | 季度miss结果UNKNOWN合理，但混用年度forward EPS共识作为缺口；同期间、同GAAP/non-GAAP口径的预期不能由年度估值共识替代。 |
| sim_arithmetic | PASS / VERIFIED | 4,11,16,17,22 | 五个SIM P/E检查分别25、40、40、32、50。给定假设计算正确不证明真实市场估值。 |
| version_read_scope | PARTIAL / VERIFIED | 17 | aapl-v2文件未被工具读取；80来自当轮用户输入，实际读v1和官方摘录。算对不证明v2正文供给。 |
| unit_apple | FAIL / VERIFIED | 19 | 114.5 billion USD换为11450亿美元，应1145亿美元；转换系数用了100而非10，原始数及来源正确。 |
| eps_change | PASS / VERIFIED | 19 | 按冻结字段2.12-2.87=-0.75，变化约-26.1%；非在线财务真实性验证。 |
| task_cancel | PASS / VERIFIED | 20,21,22 | 取消Apple子任务后继续Intel/Alphabet；Goal Off，不能评价正式Goal维持能力。 |
| compaction_continue | PARTIAL / VERIFIED | 23,24,25 | 自然压缩后继续回答及真实重读，Intel三版与现金约束保持；后续执行回顾及旧Apple暂停范围仍有错。 |
| purpose_change | PARTIAL / VERIFIED | 26,27,30 | 理解目的转为数据核验，T27允许Apple作样本；T28/T30仍笼统说Apple完全停止，旧任务与新样本范围未彻底区分。 |
| read_history | FAIL / VERIFIED | 28 | 称ledger存在但未读取；T1 contract:2证明已读。官方摘录此前也真实读过，不能仅称来自摘要。T29重读目录后T30才列为已读。 |
| new_observation | PARTIAL / VERIFIED | 29,30 | missing共识时合理UNKNOWN，但把旧目录重读称为改变建议的新观察；不能证明新外部信息或最有价值决策。 |
| unknown_missing | PASS / VERIFIED | 2,5,7,9,10,24,25,29,30 | 所选回答对缺失历史实价、共识、完整电话会议和政策原件保持UNKNOWN，并区别冻结无Web与网络故障；非逐断言无幻觉保证。 |
| authority | PASS / VERIFIED | 全批次 | 30快照ActiveGoal null、模型输出非来源证据，没有Workflow completion建立；不评价Goal维护。 |
| decision_value | UNKNOWN / UNKNOWN | 全批次 | 无Goal组、实际投资执行或独立后续结果，不支持Goal增量价值。 |

可复核反例：
- T19原文“114.5 billion USD = 114.5 × 100 = 11450 亿美元”，应乘10。来源原数正确，错误在回答单位转换。T1单位错误也发生于压缩前。
- T28原文“ledger.md … 存在，未读取”；真实T1 contract:2 / chatcmpl-tool-9222488ab3bbc661已读取，T29 contract:46才再次读取。不能根据模型自述推断实际执行历史。
- T27称Alphabet资料“在intc-v3的handoff summary中记录”，不是原始来源ID；来源可恢复不等于语义来源绑定正确。
- T29/T30将旧目录重读作为改变建议的新观察。一次新读取可返回旧信息，不能重复计为独立支持。
- T30已有SIM计算却泛称“所有…P/E计算均UNKNOWN”，缺真实估值与可计算SIM的范围不清。

T15给出卡片中的Apple官方URL，但没有实际联网Fetch；Host仍保留unresolved URL标记。引用地址不等于读取该地址。

没有把这些错误自动转为Runtime缺陷。哈希和传输完整未被破坏，模型回答也未升级为正式Goal、Memory或Workflow完成。Goal Off，不能据此宣称自主维护已通过。

## 5. 资源与性能

| 指标 | 实测 |
|---|---:|
| 原生会话总时长 | 3026.19秒（50.44分钟） |
| 累计轮等待 / 平均 / 中位 | 3024.73 / 100.82 / 96.40秒 |
| 最慢单轮 | 272.78秒，T23含压缩及重读 |
| 控制器阶段总时长 | 3146.59秒 |
| NVML / PDH Dedicated峰值 | 28.173 / 28.170GiB |
| Shared峰值 | 0.185GiB |
| Commit Limit / 使用峰值 | 91.481 / 63.234GiB |
| Commit最低余量 / 停止线 / 最低缓冲 | 28.247 / 18.296 / 9.951GiB |
| Windows Available最低 | 34.170GiB |
| WSL Available最低 / Swap峰值 | 17.382GiB / 0.148MiB |
| 样本新鲜度 / Linux采集最长 | 0.138719秒 / 3.189毫秒 |

就绪后首/末5分钟Commit余量中位数30.799→30.803GiB、Shared中位数0.1228→0.1215GiB。此窗口无单调恶化，不证明无泄漏或长期稳定。resource-series.csv保存全曲线，不能仅看NVML。

engine-rate-log.json有263次周期吞吐，非零prompt中位2637.2 Tokens/s、generation中位10.5 Tokens/s；混合活动窗口，不是逐轮纯Prefill/Decode。per-turn-audit中的首次可见文本等待也含工具、多请求耗时。精确分离与32K性能因果改善UNKNOWN。平均约101秒/轮，受控研究可用但非低延迟互动。

## 6. 与32K历史的比较及建议

旧32K goal-flow-v2-20261111T064226Z第21轮压缩HTTP400，服务器只报告“至少32769”（非精确长度）；10回执47,068字符、完整决定29,950字符。当前64K一次自然压缩完成30轮，12次输入超过32K，这些分别VERIFIED。

但回执精简、UMA、util、驱动和压缩计划均有差异，不能称严格A/B或把全部收益归于64K。当前仅小摘录，尚未完整评估高密度网页正文研究。单位错误在压缩前已出现，扩容并未解决它们。

建议保留32K原默认，允许64K显式用于长研究；56/72、1GiB KV、单并发及安全边界不变，无证据要求更大KV/Context。**Phase1限定收敛，整体PARTIAL，停止提交评审**；获批后才开展Goal Shadow独立长对照。此轮无人工长会话需求，不新增语义裁判、强制重试、Goal Engine或Memory维护层。

真实投资/长期决策价值UNKNOWN；Goal对照NOT RUN，Memory仍Research Reserved。

## 7. 证据索引与逐轮数据

批次中：
- preregistration.json、protocol.json、CURRENT_PROTOCOL.md、input-lock.json、git-before.json及frozen/source-lock.json。
- phase1-summary.json、final-integrity.json、behavior-findings.json、per-turn-audit.json、requests-audit.json、resource-series.csv。
- session/app-server-events.jsonl、execution-contract.trajectory.jsonl、model-http-audit.jsonl；streams下原始SSE、capture；turn快照、fixture-release-events及result。
- 监控原件 /home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261111T235521Z-80a0c761，包括resource-samples、guard-outcomes、metrics-cleanup及service日志；批次另有power-samples及power-observer-end。
- behavior-findings中逐条列Native Turn、item与回答hash；不是模型自评。Windows整理包有SHA256索引，原始JSON不覆盖。

以下是执行与usage，不是逐轮认知PASS：

| 轮 | 秒 | 最大实际输入Tokens | 请求数 | 自然压缩 |
|---|---:|---:|---:|---:|
| 1 | 78.34 | 16,387 | 2 | 0 |
| 2 | 44.84 | 16,932 | 1 | 0 |
| 3 | 37.02 | 17,633 | 1 | 0 |
| 4 | 61.66 | 19,513 | 2 | 0 |
| 5 | 41.05 | 19,956 | 1 | 0 |
| 6 | 90.41 | 22,102 | 2 | 0 |
| 7 | 33.60 | 22,779 | 1 | 0 |
| 8 | 100.52 | 23,236 | 1 | 0 |
| 9 | 68.96 | 24,092 | 1 | 0 |
| 10 | 55.26 | 24,719 | 1 | 0 |
| 11 | 124.99 | 28,124 | 2 | 0 |
| 12 | 103.78 | 28,719 | 1 | 0 |
| 13 | 105.95 | 31,158 | 2 | 0 |
| 14 | 117.39 | 31,478 | 1 | 0 |
| 15 | 92.28 | 32,524 | 1 | 0 |
| 16 | 120.19 | 36,287 | 2 | 0 |
| 17 | 136.96 | 39,706 | 2 | 0 |
| 18 | 134.86 | 43,104 | 2 | 0 |
| 19 | 91.84 | 43,431 | 1 | 0 |
| 20 | 90.48 | 44,137 | 1 | 0 |
| 21 | 106.84 | 44,713 | 1 | 0 |
| 22 | 153.49 | 49,542 | 2 | 0 |
| 23 | 272.78 | 41,751 | 3 | 1 |
| 24 | 86.51 | 21,808 | 1 | 0 |
| 25 | 76.10 | 22,838 | 1 | 0 |
| 26 | 131.32 | 23,695 | 1 | 0 |
| 27 | 67.55 | 24,961 | 1 | 0 |
| 28 | 143.92 | 25,635 | 1 | 0 |
| 29 | 111.19 | 28,859 | 2 | 0 |
| 30 | 144.66 | 29,310 | 1 | 0 |
