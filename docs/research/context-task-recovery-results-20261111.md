# 长任务 Context 恢复、HTTP framing 与金融 Goal 实验（2026-11-11）

**总体 PARTIAL。** A确定性修复限定PASS；B当前Apple任务短恢复限定PASS、一般稳健性PARTIAL；
C新金融History首轮流式输出退化，0/30完成，Goal长组NOT RUN。Goal成熟度不提高。

## 1. 本轮范围与原始版本

原始总目录：
/home/wqkan_wsl/uaea-n1x/research-records/context-resume-20261111T023249Z（下称B）。

保留三个独立执行目录，不拼接：
- B：初始回放构造pilot，0轮，错误把历史放进Host恢复块导致413，不作为有效语义对照。
- B/accepted-run：改正回放放置后的旧说明条件，首轮420秒未完成；澄清条件尚未执行。
- B/remaining-run：只执行尚未运行的澄清条件（2轮完成），通过审查后启动全新金融长批次。
  没有重跑有效旧条件，也没有重跑失败的金融首轮。

每批独立一次受控模型加载；全部16个模型/守卫配置pin在结束时匹配。
pilot/accepted/remaining分别307/308/307个冻结输入hash匹配。
HEAD保持125f0d2a8e6b7ac0f6b70baf9913b942be2b1cb2。
模型环境、Guard、Goal/Memory采纳与权限未改，不Commit/Push。
旧13、14、20轮及之前History30批次均独立，不计为本轮完成。

新长批次scenarios.json与上轮冻结金融脚本逐字节相同，原来源、SIM版本及释放时点相同。
只读工具、32K服务/31129原生有效窗、24576压缩线、1GiB固定KV、36GiB规划、
Eager、单并发、64/64 UMA和Provider Policy保持。Memory仍Research Reserved。
没有第二套Agent Loop，研究脚本仅调度固定输入；Harness继续执行模型/工具循环。

## 2. A1：HTTP提前EOF修复 — VERIFIED（限定PASS）

根因：HTTPResponse.read1()在固定Content-Length正文不完整时可能返回空字节而不抛异常。
此前把这一物理EOF与“收发字节相等”组合为完整成功，没有核对声明长度。

最小改动：
- harness/responses_bridge.py在头部取得response.length，并在read1循环结束后核对实际正文长度。
  不足时记录IncompleteRead；保留实际收到和下游写入字节、原始HTTP200和物理EOF状态。
- harness/request_audit.py增加expected_body_bytes、http_framing_complete，
  response_complete要求固定长度相符；transport_state对已知长度不符不能返回完整成功。
- 由标准HTTP解析器处理chunked终止；合法close-delimited EOF仍可完成。
  未新增SSE语义、模型理解或Workflow完成裁判。

真实loopback反例见B/early-eof-observation.json：
request_id=9acff0d8-02c0-4745-9f91-7dd6d40f63df，
HTTP200，声明100，收到3/转发3，物理EOF=true，
transport_error=IncompleteRead，http_framing_complete=false，response_complete=false。
没有将HTTP200更名为请求成功，也没有丢失原状态。

负例/正例覆盖：100/3、精确3/3、合法close-delimited、缺chunk终止、正确chunk终止、
伪造complete及长度不符。旧日志没有保存声明长度/framing证据时，
不能用本次代码追认其framing已完整；原件及既有结论保留，适用证据范围另列。

## 3. A2：实验Turn时限一致性 — VERIFIED（限定PASS）

- prepare的--turn-timeout（本轮420）写入冻结protocol.json。
- Runner从该协议读取；不再构造时硬编码180，也不再为受控Compaction另写180。
- --check-only在无模型情况下验证冻结配置和源码；缺值、非正数、非有限值、
  CLI与冻结值不一致均拒绝。
- 控制器在加载前核对预登记、protocol与Runner预检；构造App后再次核对实际值。
- Manifest由真实App配置记录；wait_timeout事件也记录实际值。
  三批实测pre-registration=protocol=precheck=manifest=420秒。
- API命令握手期限、自动研究Turn等待、实验作业期限、模型服务生命周期和Workflow仍分开。
  人工入口无新增固定期限，资源保护也不受Turn期限代替。
- 此次没有为了成功延长登记420秒，未覆盖旧180秒失配记录。

B/target-tests.log：104项全PASS。
B/scoped-regression.json：738项中736 PASS、2 SKIP、0 FAIL/ERROR。
10项旧Memory个人语料/附件前提缺失，沿用上轮明确排除名单，没有修补或伪造资料；
因此这不是全项目无条件PASS。Memory源码未改、Phase-1子模块干净，git diff --check通过。

## 4. B：错误历史路径与当前Apple任务

### 4.1 原始错误的第一处可观察来源

旧轨迹：
/home/wqkan_wsl/uaea-n1x/research-records/capability-finance-20261111T010429Z/long/finance30-relevant_history-r1。

B/first-path-appearance.json定位：
- 原生app-server-events.jsonl第5116行，rawResponseItem/completed，
  turn=01a1c84a-3dfc-7d72-8135-97300e1519d3。
- 模型Compaction摘要首次可见地给出相对sandbox/sources/official-intc.md、
  sandbox/sources/official-googl.md和sandbox/ledger.md。
- 同一摘要还有“create/verify SIM”和旧Intel/Alphabet待办及日期错误。
  它们不是新的原始用户指令或真实执行事实。
- 压缩后原始Apple请求、current_user_request、正确Host绝对路径和来源仍在P0。
  不能归为“当前任务完全没传入”，也不能据此证明模型正确使用了它们。

相对路径基于sandbox_root解析，多出sandbox前缀会指向sandbox/sandbox/...。
本轮没有去掉前缀、增加alias或扩大允许路径。
可观察行为与“把派生摘要的待办/路径当当前依据”一致，
但隐藏推理依赖无法恢复；没有证据证明Host的权威Goal/Evidence被摘要修改。

### 4.2 最小冲突表达

harness/io_contract.py原有current request/历史topic边界增加通用说明：
Compaction/handoff的路径、TODO、完成声明属于未经验证的模型派生历史；
与当前原始请求或最新Host位置事实冲突时，保留当前请求、采用当前Host引用；
旧路径失败不产生逐个读完旧来源的义务。
filesystem说明同步区分摘要引用与可验证位置。
没有Apple/股票专属规则，没有Source自动选择、自动提案或新控制器。

这是一项可回滚的输入契约澄清，不能将说明本身称为语义正确性保证。

### 4.3 有判别力的短回放

两个条件使用同一真实旧摘要、6条历史失败、原金融第14/15轮Apple输入、
截至原14轮已释放的ledger和6份不可变资料。
研究Driver通过原生untrusted AdditionalContext一次性放入历史，
不当作新用户观察、Host receipt或反复恢复的权威块。
这不是自然Compaction重演，而是隔离的受控回放；
实际新Tool Observation与旧回放记录分开。

初始pilot放置错误造成413，已单独保留并排除对照。
修正只改变实验材料所在通道，原摘要/历史失败正文保持；
未提高24KB Host预算。replay-placement-check.json验证不会重复把历史当必需Host状态。

| 条件 | 实际完成 | 真读取 | 压缩 | 结果 |
| --- | ---: | ---: | ---: | --- |
| 有效旧说明 | 0/2，首轮420秒未终止 | 20次，Apple3次，反复读旧资料 | 1自然 | 无当前任务最终回答 |
| 澄清说明 | 2/2 | 6次，Apple1次；第二轮无新读取 | 0 | 回到Apple并延续 |

旧组的实际P0包含完整Tool Results和Apple114.5数据，不能将重复读取简单解释成从未供给。
澄清组第1轮150.583秒、第2轮78.502秒，4个HTTP请求均有framing/转发完成证据。
它报告FY2026财政Q4、114.5 billion USD、季度EPS2.10及0.05影响，
区分季度与年度forward口径；对历史真实价格和40倍PE保留UNKNOWN。
第二轮继续引用实际Apple原件与时间缺口，没有返回旧Intel任务。
Host workflow_completion仍false。

保留模型反例：
- 读了多份不必要的旧资料。
- 声称“已读完所有可用资料”，但paper-cash文件没有本次读取Observation。
  此声明未成为Host读取事实。
- 财务表述仍有局部不精确；没有通用语义裁判替模型修正。

成本：澄清组原生累计76425 Token（输入74739、输出1686）。
旧组最后已报告累计77777（75527/2250），但首轮未完成，缺最后未结束推理用量。
不能据二者算完整成本节省率。

**判定：当前任务恢复限定PASS，一般稳健性PARTIAL。**
只有各一次、不同Thread/模型冷启动/路径名、默认采样；不是统计稳定性或某句话的因果证明。
两组是旧/新通用说明对照，不是Goal机制价值对照。
澄清组通过预先登记的限定门后，继续真实金融长实验，没有要求人工输入“继续”。

## 5. C：独立新金融长实验与新增阻塞

位置：B/remaining-run/long。
History已发第1轮，完成0/30；Goal Shadow长组 **NOT RUN**。
没有拼接旧完成轮次，没有修改脚本后重试本轮。

| 观察 | 真实结果 |
| --- | --- |
| 原生Thread | 01a1c896-4f87-7b63-ae1a-01642ac9a573 |
| 原生Turn | 01a1c896-4fb5-7e52-94dd-6db260ebfaaa |
| 真实工具 | ledger、Intel、Apple、Alphabet共4次成功只读 |
| Compaction | 0；原定第20轮受控压缩NOT RUN |
| HTTP | 前2完整；第3为200后部分传输 |
| 终止 | 实际420秒原生Turn未结束，控制器停止并清理 |
| Goal候选/版本/后续价值 | 本轮未获可评价长对照，UNKNOWN |

### 5.1 持续生成重复片段，而非无响应

B/long-repetition-case.json定位原生消息msg_9b807aab44f9de7e，
app-server-events.jsonl第57至3241行：
03:12:12.865至03:18:11.052（原记录未带时区，来自本批UTC记录）。
部分文本3311字符；同一短句“11:23 12:07 开盘，上涨 17 94 95”重复121次。
该短句不在第3次出站请求体中。开头“已读取所有三份官方摘录”之后持续退化，
没有最终研究回答。重复计数仅描述文本现象，不是Goal熵、认知波动或质量概率。

vLLM日志同时显示Running1/Waiting0、持续约10.2–10.4 tokens/s生成、
KV使用约26.2%，随后接收控制器SIGTERM。
没有原生Compaction、ContextBudgetError/413、遥测拒绝或资源超限证据。
最近已完成请求的input usage为12420，有效窗31129；
**最后未结束请求没有最终Usage，不能写成其输入恰好12.4K或总成本22919。**
22919（输入22533/输出386）只是前两个已完成推理的累计，未包含退化流的最终用量。

### 5.2 HTTP200并未被计完整成功

第3请求：sequence3，request_id=9eaa2c64-46d1-4cc7-a482-16cf89f8d5d1。
最终transport_result记录：
HTTP200，received631886、forwarded631690、BrokenPipeError、
upstream_eof=false、http_framing_complete=false、response_complete=false。
这与首轮等待结束/客户端清理相邻，不能把下游BrokenPipe倒推为先前重复生成的原因。

四次读取的执行及内容hash可核验；但部分传输不能计完整供给PASS。
“请求体含来源”与“模型语义采用来源”继续分开。
本次也没有把输出片段中的不存在行情提升为可信Evidence或正式完成事实。

### 5.3 根因分级

- **VERIFIED**：原生输出流重复、Turn未完成；发生在首轮，尚未压缩；Guard正常；
  真实HTTP完整/部分判据区分正确。
- **HYPOTHESIS**：生成通道退化是本轮未完成的直接表现，不能归为原错误sandbox前缀。
- **UNKNOWN**：底层模型采样、vLLM/模型parser与原生流处理之间的确切归因。
  未保存原始upstream SSE/token IDs，不能用原生delta代替底层token证明。
  新说明对生成分布是否有影响未做消融；既不能判完全无关，也不能因一次失败直接归因于它。
- **NOT RUN**：Goal长组、30轮决策对照、跨轮Goal修订与收益评价。

本轮未调temperature、重复惩罚、Parser、模型权重/依赖或Kernel，也未延长420秒重试。
这是一项生成稳定性阻塞，不能充当Goal Proposal接口或Goal架构优劣证据。

## 6. 资源保护与清理

三批受控模型分别使用：
- manual-20261111T024446Z-a49278e8（pilot）
- manual-20261111T025123Z-80a71504（旧说明）
- manual-20261111T030145Z-f28de805（澄清及新长批次）

原Guard单时钟、一次性标记、2秒采集、3秒新鲜度、48GiB GPU、
6GiB Windows、Commit独立保护、WSL/Swap门限均未改。
每次加载均经原配置/版本检查和资源/心跳失效smoke。
三批1594条服务资源样本、1864条被动AC样本（258+599+1007）均无NVML17/遥测拒绝，
AC均有效且在线。有限区间不等于长期可靠性已证明。

跨三批范围：
Dedicated峰值29.577GiB；Shared峰值0.175GiB（独立计数）；
Windows Available最低22.929GiB；Commit剩余最低42.629GiB；
WSL Available最低17.501GiB；Swap峰值96KiB。这些域不相加。

最终service/state及metrics-cleanup remaining=[]，Harness进程组absent，
Windows/WSL的8000/8003无监听，被动observer已退出。
monitor-exception包装虽含Safety stop，实际均CONTROLLER_STOP且primary_sensor_failure=null；
资源保护不是本次中断的第一原因。没有关闭外部模型服务。

## 7. 修改范围与回退

代码：
- harness/responses_bridge.py、harness/request_audit.py：HTTP framing完整性。
- scripts/research/longitudinal_prepare.py、longitudinal_dialogue.py：单一冻结时限与启动前检查。
- harness/io_contract.py：通用的当前输入/派生摘要/Host路径冲突表达。
- tests/test_transport_framing_and_research_config.py：9个针对性测试。

研究Driver、故障pilot、独立批次、证据Reducer仅在研究记录目录。
本报告及research-foundation-map追加索引，不覆盖冻结历史。
本轮精确Diff/前后hash保存在B/current-turn.patch、changed-files.json，
依据B/before区分此前用户未提交变更；不能用整个HEAD差异归属本轮。
回退只核对本轮hunks，保留用户先前修改和全部原始失败记录；不reset/clean。

## 8. 判定与下一步

| 维度 | 判定 | 边界 |
| --- | --- | --- |
| HTTP提前EOF、Turn配置 | PASS / VERIFIED | 确定性反例、实机配置及738项限定回归 |
| Context信息供给/来源 | VERIFIED（限定） | 原始输入/Host路径与派生历史分开，实际观察可追溯 |
| Apple任务恢复 | PARTIAL；短场景限定PASS | 两轮真实恢复，有过度读取/声明反例，无稳健性证明 |
| 金融长Workflow | FAIL（本批未完成） | History0/30；Goal长组NOT RUN |
| Goal形成、版本演化与价值 | UNKNOWN | 无有效新长配对，不上调成熟度 |
| 新Goal架构需求 | 未获支持 | 当前证据指向生成/Context使用限制，不是权威机制缺失 |

保留Sideband、Relevant History对照、32K默认/64K实验和全部资源边界。
不新增Goal Engine/控制循环/自动修订，也不把工具成功当任务完成。
HTTP与时限修复可独立评审；Context文字澄清保留可回滚性，不宣称普适认知修复。

最小下一步建议：冻结本次第3请求及模型/配置，先做一项受控的生成端/流式转发隔离，
保存upstream原始SSE、token/finish_reason，再用相同输出做无GPU的下游回放。
区分模型生成与parser/流处理后，再决定是否值得重启30×2。
这不是要求改Goal架构或立即换Backend，也不需要新的人工长会话。
本轮不自动重跑、不以扩展Runtime复杂度追求PASS，提交阶段评审。
