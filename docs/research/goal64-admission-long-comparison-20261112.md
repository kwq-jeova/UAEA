# Goal 64K：短段准入与双组30轮连续对照（2026-11-12）

**总体PARTIAL**。运行/权限/来源身份契约限定PASS；阶段A显式候选形成、保存和实际传输VERIFIED。阶段B两组各30轮独立记录完整，但Goal Shadow零自然提案，**自然形成、自主维护和候选增量价值仍未建立**。不将更少读取、更快完成或空版本表当作Goal Cognition PASS。

本轮已结束，服务清理，等待架构评审；不自动开展新实验、不Commit/Push。

## 1. 实验身份、材料与可比性

新批次：/home/wqkan_wsl/uaea-n1x/research-records/goal64-stageAB-20261112T011601Z

| 阶段/组 | Thread | 轮次 | 原始记录 |
|---|---|---:|---|
| A短验证 | 01a1cd58-f267-72f0-89df-63ced6e11db3 | 7/7 | short/ |
| B Relevant History | 01a1cd0b-7922-77f1-bb00-af9bec7a83c9 | 30/30 | /home/wqkan_wsl/uaea-n1x/research-records/finance-phase1-64k-20261111T235041Z/session |
| B Goal Shadow | 01a1cd62-ef8a-7982-8c2b-489028efe747 | 30/30 | shadow/ |

A不计入B；新Shadow进程/Thread、codex-home、RuntimeObjectStore与候选独立，未注入短段种子。两个长组不拼接；History已经完整，因此无需重新执行，任一组失败也不会取消另一组原始记录。

复用理由：131个冻结执行源码hash、30条用户文本、释放规则、来源/SIM、64K配置、模型、工具权限与采样配置一致；区别是现有Sideband研究通道及非权威Goal投影。新输入锁168项、正式启动/监控/安装策略15项均未改变，原32K默认及64/64入口不变。
基础HEAD125f0d2a8e6b7ac0f6b70baf9913b942be2b1cb2，工作树原已dirty。复现必须采用frozen/source-lock.json的实际副本，不能只checkout HEAD。git-before-docs.json是运行后文档写入前记录，不能冒称干净或最初仓库快照；隔离模型输入在加载前已锁定。

限制：非随机、分时段单次对照；Shadow在同一模型服务运行完A后启动，History是此前独立服务，存在预热、随机轨迹及后台负载差异。没有重新固定每次采样随机状态。不能估计统计显著性、人口平均收益或纯单变量因果效应。

材料沿用已审计金融30轮：前15轮改编自interactive-32768-20261105-053257及071627，后15轮是研究者扩展。逐条出处见frozen/scenario-provenance.json及historical-user-inputs.json，不代表真实用户新Goal或真实持仓。
仅三份研究者摘录与SIM；原HTML/PDF于11-09保存，研究冻结时点11-10、历史估值目标11-04。不能证明11-04原始字节可得性；真实报价、交易日、年度共识、完整电话会议UNKNOWN。本轮没有实时Web或完整财报阅读全文，也未重新在线核验摘录财务真实性。
旧frozen/README中的32K双组/受控20轮不适用；实际driver和本批次预登记使用64K、仅自然Compaction，未事后改脚本追求PASS。

## 2. 最小工程处理与安全

仅隔离研究入口新增ac_gate.py/check-ac.ps1，并加强本批controller启动/周期检查；没有修改正式Runtime/Harness/Goal/Memory或主Guard。

AC准入：最近五条样本稳定在线、同Run、序号递增；Windows QPC计算末样本年龄≤3秒；监控PID及启动Ticks匹配，拒绝PID复用；响应返回额外延迟也不得使样本超过3秒。随后持续检查序号推进，每15秒复核Windows侧存活/单时钟年龄。未依赖两侧UTC同步。
CPU：合法样本PASS，过期首样本、未来时间、死进程、PID复用、跨Run、离线、无效、重复序号、样本不足、频率非法10种反例均拒绝。无模型真实Windows↔WSL检查PASS。
首次UNC -File调用被Windows执行策略拒绝，未启动模型；改用既有Guard的ScriptBlock读取调用方式，未修改执行策略。初次错误日志、初版hash锁和诊断保留。该补丁仅覆盖本隔离研究入口，**不声称所有无人值守入口已同步修复**。

固定GPU56/Host72、Context65536、KV1GiB、seq1、util0.65、vLLM0.32.0、Codex0.163.0；实际引擎预算36GiB，KV逻辑容量109817。
Native有效窗口62259，自动压缩49152，原Host供给上限24KB不变。
Linux采集2秒、Windows新鲜度3秒及GPU48GiB、Commit余量max(16GiB,Limit×20%)、Windows Available6GiB、WSL Available4GiB、Swap256MiB保护不变。每Turn420秒、短段3500秒、长组13200秒、整批17500秒是有界研究期限，服务保持manual生命周期，未放宽门限。

全服务3142个资源样本；3348条AC均在线有效，205次存活/QPC复核通过，末样本年龄最高1.026637秒，单次probe最长0.945204秒（两项是各自极值，不能相加当作同次）。
原安全smoke按预期拒绝模拟GPU48和Windows stale；正式负载无NVML17、无真实资源/遥测拒绝。
收尾CONTROLLER_STOP为正常owned服务清理，非内存停止；primary_sensor_failure=null、resource_stop=null、remaining=[]。两个Native进程组absent、监控清理完成、AC观察器正常结束；8000/8003无监听。

## 3. 阶段A：契约准入PASS，认知PARTIAL

独立7轮，11个完整响应，最大输入24265 Tokens，0次Compaction，记录用时629.42秒（time.monotonic）。实际5次文档读取，2次Goal调用：1拒绝、1接受。
首轮显式邀请form，错误candidate_id先被拒，模型自行改为null后提交；Host保存goal-candidate:09ece67c23e34ed8e367a19e，原始Call ID chatcmpl-tool-aaaef4a89f685258。同版记录/hash进入请求sequence4–11，共8个完整传输请求；不以publication成功代替真实传输。
候选内容混入冻结日期和缺失资料，语义抽象PARTIAL。取消Apple子任务时保留候选合理。持续目的改变时模型识别旧候选过时，但未修订，且如实说明旧Host状态；无自主修订闭环。

工具Schema核对：类型、required、操作enum和additionalProperties匹配；出站parameters没有Host定义的minLength/maxLength/maxItems（5项约束）。精确等价**PARTIAL**，原false对照保留；Host仍执行所有边界，并未放宽权限。该差异的精确剥离位置未单独定位，不把它归因为首次父ID错误（该规则仍在出站类型/说明中），不为此改Codex Core。
准入JSON验证了Native终止、完整传输、真实form绑定、当前head内容/版本、materialized snapshot、语义与执行Observation分离、正式状态未提升；不是语义正确或价值PASS。
短段REPORT.md、admission.json、goal-audit.json、schema-check.json及resource-window.json单独归档。at-admission-summary是采集时的服务前缀资源快照，最终阶段A资源应按Native区间另行切分，不能用全服务极值混淆阶段。

## 4. 阶段B：独立30轮真实长对照

| 项目 | Relevant History | Goal Shadow |
|---|---:|---:|
| Native开始/不同completed/快照 | 30/30/30 | 30/30/30 |
| 完整模型响应/HTTP | 42/42 | 38/38 |
| 最大实际输入Tokens | 49,542 | 48,826 |
| 累计输入Tokens | 1,204,450 | 1,250,309 |
| 累计输出Tokens | 20,017 | 14,289 |
| 原生会话用时，秒 | 3026.19 | 2463.10 |
| 平均每轮等待，秒 | 100.82 | 82.07 |
| 实际只读调用/Observation | 23/23 | 14/14 |
| 同路径再次读取事件 | 13（10种文件） | 6（8种文件） |
| Compaction | 1，T23自然发生 | 0，自然阈值未触发 |
| Goal工具真实送达 | 未启用 | 38/38请求 |
| 自然Goal调用/版本 | 不适用 | 0/0 |
| ActiveGoal显式null | 30/30 | 30/30 |
| 模型输出非来源证据 | 30/30 | 30/30 |
| Workflow completion显式false | 30/30 | 30/30 |

所有逐轮用户文本相同。Shadow38份上下游SSE完整且逐字节一致，无采集触限；356次历史工具正文供给hash/完整传输核对通过，原件hash均有效。History324/324供给已在前批复核。
本次没有Context Overflow、响应部分传输或输出上限截断；未见旧121次重复异常，旧根因仍UNKNOWN，不宣称已修复。
Shadow未自然压缩，**本组Goal/候选压缩恢复NOT EXERCISED**；不能用History的无Goal压缩成功代替该验证，也未人为追加压缩。

长组goal-research-state versions=[]、heads=[]，38个请求均实际携带可选Goal工具和空候选投影。没有短段种子串入。空快照结构PASS仅说明“准确保存为空”，不证明候选形成/维护PASS。自然形成未观察，维护及演化UNKNOWN/未执行。
该脚本注明研究者回放、不代表真实用户新Goal；合理不提出与缺少自主工具选择两种解释不能仅凭零调用区分。本轮不把零提案直接归为接口失败，也不强制补发。

### 成本解释

累计输入增加45,859（3.81%），输出减少5728（28.62%），用时少563.09秒（18.61%），读取少9次；描述差异VERIFIED，**原因不能归于Goal候选维护**，因为长组没有任何候选。
首个匹配请求输入10044→10998，差954，含Goal工具/状态及路径、ID、时间等小差异，不是精确纯Goal Token成本。
Goal工具定义每请求1568字符；Goal投影平均2982.24字符、最大3266字符，无Goal回执。字符不是Token或有效bit；单独精确Token归因UNKNOWN。后来两组回答、读取和压缩轨迹不同，不能把总Token差全当静态Goal开销。
更少读取不一定更有效；Shadow从未读取Apple SIM两文件，数值来自用户原文。H与Shadow都可完成这些SIM算术，不能用文件存在或答对数值证明已读取。

## 5. 行为、状态与关键反例

所有语义评注来自原始用户文本、冻结字段和真实Observation；不是被测模型自评，不是通用语义裁判。behavior-findings.json逐条绑定Native Turn、item与回答hash。

| 项目 | 判定/证据级别 | 轮次 | 观察 |
|---|---|---|---|
| short_form | PASS / VERIFIED | short 1 | 显式form先错误父ID被拒，模型自行改为null后保存1版，8个后续完整请求携带同一精确head；不是自然形成。 |
| short_abstraction | PARTIAL / VERIFIED | short 1,3,5 | 候选混入冻结日期/缺失资料限制。Task取消保留候选合理；持续目的改变后识别旧候选过时但未修订，并如实描述旧Host状态。 |
| natural_formation | UNKNOWN / VERIFIED | shadow 全组 | 30轮、38次工具定义真实送达，零Goal调用/版本；未观察到自然形成，不能因空集合的结构完整就判生命周期PASS。 |
| units | FAIL / VERIFIED | shadow 1,11,14,24 | Intel16.5B被写为16.5亿美元，Apple114.5B也出现114.5亿美元。源卡片单位正确，错误发生于压缩之前（本组无压缩）。 |
| unit_correction | PARTIAL / VERIFIED | shadow 19,24,27 | T19正确1145亿美元，优于History该轮11450；T24又写114.5亿美元（=1145亿美元）自相矛盾，T27再用正确1145。不能宣称稳定纠错。 |
| source_period | FAIL / VERIFIED | shadow 19 | Alphabet卡片明确2026Q3且URL文件名2026q3；回答称官方Q4附件PDF。q4cdn域名不是季度标签；错误内部机制UNKNOWN。 |
| company_mismatch | FAIL / VERIFIED | shadow 23 | 把Apple SIM P/E32写成Alphabet SIM，资料无Alphabet SIM版本；并非压缩引入。 |
| version_mismatch | PARTIAL / VERIFIED | shadow 24 | 表格v1=25/v2=40正确，同一回答末尾却称40为Intel v1，版本解释不一致；三个hash前缀与文件真实hash匹配。 |
| sim_calculations | PASS / VERIFIED | shadow 4,11,16,17,22 | 五个预设SIM P/E数值25、40、40、32、50正确；不是实际行情估值或金融Workflow完成。 |
| task_and_purpose | PARTIAL / VERIFIED | shadow 20,26,27 | 取消Apple子任务后继续其他研究，目的变化转为方法核验，并允许Apple作方法样本；未形成Goal对象演化。 |
| read_history | PARTIAL / VERIFIED | shadow 28,29,30 | T28正确说明Apple SIM两文件未读取，且未漏报已读ledger；T29无本轮Tool却用实际调用标题叙述历史读取；T30把Apple SIM同时列在通过read_section已完成和未读取清单，形成事实矛盾。 |
| candidate_feedback | PARTIAL / VERIFIED | shadow 28 | 真实Goal heads为空，但已保存候选表填的是资料缺口/停止事项，没有清楚报告无Goal候选；没有证据显示Host保存了这些文字。 |
| next_action | UNKNOWN / VERIFIED | shadow 29,30 | 选择确认电话会议缺失，实质依据早已读到的资料包说明，没有本轮新IO；将同源旧信息作为新观察。History也重读目录确认已知缺口，未证明真实决策增益。 |
| authority | PASS / VERIFIED | shadow 全组 | 30份快照显式ActiveGoal null，模型输出非来源证据，Workflow completion false；Goal/Memory自动采纳未开放。 |

短段另有反例：A6把Apple FY2026 Q4、截至09-26括注为自然年2026 Q4；这不符合卡片或日历季度，A7又重新强调财政Q4不是自然Q4。候选读回准确不替代财务语义正确。

重要对照：
- 两组T1都有Intel单位错。Shadow T19把Apple换为1145亿美元，History该轮为11450；但Shadow T24又自相矛盾，不能称稳定改进。
- Shadow T23把P/E32错归Alphabet，T24表格归属纠正但正文把40说成Intel v1；源卡片/工具数据仍正确，且本组无Compaction。这是模型使用错误证据，不能据此要求扩容或新建语义层。
- History T28漏报ledger已读；Shadow T28正确回顾ledger及Apple文件未读，却未清晰报告无Goal候选。Shadow T30将Apple SIM既列为“通过read_section已完成”又列为未读取，自我陈述不一致。
- Shadow T29“实际调用已有工具”没有对应本轮新Tool；S-INTC历史上真实读过，不能说该来源从未读取，但也不能把历史读取当本轮新执行。
- 两组T29/T30建议都集中在早已知的缺口，缺少独立后续结果。业务目标原始行情/共识缺失，合理UNKNOWN不等于真实研究已完成。

**独立判断**：两组都能在多轮中理解从投资研究到数据核验的方向变化，但这种理解没有在Shadow转成可观察候选演化；有局部财务/回顾改善，也有新增错配和矛盾。当前没有可归因于Goal Hypothesis的增量研究/决策价值。它是UNKNOWN，不是证明所有Goal Cognition都无价值。也没有足够证据改变UAEA+Harness架构或用Structured/协同机制替换Sideband。

## 6. 资源与时间

| 范围 | NVML峰GiB | Shared峰GiB | Commit最低余量GiB | 距原停止线缓冲GiB |
|---|---:|---:|---:|---:|
| 加载+全服务 | 28.274 | 0.209 | 28.353 | 10.057 |
| A线程区间，不含加载 | 25.838 | 0.209 | 30.468 | 12.172 |
| B Shadow线程区间 | 25.979 | 0.209 | 30.421 | 12.125 |

CommitLimit91.481GiB、原停止余量18.296GiB。全程Windows Available最低35.503GiB、WSL Available最低17.436GiB、Swap峰0.015625MiB、因果新鲜度上界最高0.383776秒、采集最长0.269143秒，均在原限制内。
Shadow首/末100样本Commit余量中位30.646→30.638GiB，无持续下降证据；不证明无泄漏或长期运行普遍稳定。

用时为Driver time.monotonic/单轮等待，原生UTC时间戳及Windows QPC另存，不混称纯Prefill/Decode或精确物理钟差研究。阶段资源窗口以Linux采样开始UTC与Native记录UTC切分，仅用于描述阶段；安全新鲜度仍只由Windows单时钟确认。原始资源CSV/采样/两侧时间均保留。
vLLM周期速率不等于逐轮纯Prefill/Decode；本对照未做精确计算分解或多次性能重复。

## 7. 最小架构建议与停止边界

1. 64K+56/72+1GiB在本次Goal-enabled负载下具备限定运行条件，保持显式实验入口；不改32K默认、不扩大KV/UMA/并发/权限。
2. 保留现有Sideband。A证明能调用、拒绝、自纠错及传输；B未证明自然候选和增量价值。没有理由新增Goal Engine、自动补提案、第二审查循环或经验维护层。
3. 不继续用相同30轮反复重跑追求首个候选。下一项需评审的是：是否转为有独立语义评价的候选形成/使用实验，或比较可替换提案模型；应先明确何种持续方向值得保留、何时合理不提出。既有自然零调用不能替代该语义判断。
4. 真实用户长期Goal、真实金融决策价值仍UNKNOWN。此轮不需要人工长会话，但不能据研究者脚本宣布真实用户Goal成立。
5. Schema长度/数组边界投影差异保留为限定契约缺口；先审阅其影响，不因此改Core或声称这是自主维护失败根因。
6. Memory数学研究仍Research Reserved，ActiveGoal/Memory Admission关闭；未验证解释不进入可信状态。

## 8. 证据与逐轮索引

- preregistration.json、input-lock.json、baseline-reuse.json、closure-lock-check.json、frozen/source-lock.json、git-before-docs.json。
- short/REPORT.md、admission.json、goal-audit.json、schema-check.json及初次精确比较失败记录；shadow/goal-audit.json及空候选状态。
- comparison.json（两组原文/回答/时间/读取/Native IDs）、behavior-findings.json、analysis各组HTTP/SSE/usage审计、原始app-server事件/Goal Journal/ExecutionObservation/快照。
- AC的ac-health、power-samples、probe前置结果、CPU反例、初次策略拒绝日志；owned Guard资源/挑战/Windows心跳/模型日志。
- 旧History原件仍在/home/wqkan_wsl/uaea-n1x/research-records/finance-phase1-64k-20261111T235041Z，不改写、不过滤失败内容。
- Windows整理包含两个ZIP、可读报告、配对JSON/CSV与Diff及SHA256索引；代码仅隔离研究脚本、文档/索引为本轮仓库增量。

| 轮次 | History秒 | Shadow秒 | History最大输入 | Shadow最大输入 |
|---|---:|---:|---:|---:|
| 1 | 78.34 | 83.03 | 16,387 | 17,279 |
| 2 | 44.84 | 53.00 | 16,932 | 18,083 |
| 3 | 37.02 | 47.80 | 17,633 | 19,061 |
| 4 | 61.66 | 60.52 | 19,513 | 21,218 |
| 5 | 41.05 | 35.20 | 19,956 | 21,751 |
| 6 | 90.41 | 85.23 | 22,102 | 25,088 |
| 7 | 33.60 | 38.57 | 22,779 | 25,795 |
| 8 | 100.52 | 59.42 | 23,236 | 26,411 |
| 9 | 68.96 | 48.00 | 24,092 | 26,877 |
| 10 | 55.26 | 42.87 | 24,719 | 27,246 |
| 11 | 124.99 | 92.59 | 28,124 | 29,008 |
| 12 | 103.78 | 75.54 | 28,719 | 29,338 |
| 13 | 105.95 | 109.27 | 31,158 | 31,471 |
| 14 | 117.39 | 123.40 | 31,478 | 35,051 |
| 15 | 92.28 | 70.02 | 32,524 | 35,585 |
| 16 | 120.19 | 57.15 | 36,287 | 36,310 |
| 17 | 136.96 | 59.60 | 39,706 | 36,641 |
| 18 | 134.86 | 101.56 | 43,104 | 38,542 |
| 19 | 91.84 | 66.72 | 43,431 | 38,695 |
| 20 | 90.48 | 56.97 | 44,137 | 39,183 |
| 21 | 106.84 | 82.88 | 44,713 | 39,460 |
| 22 | 153.49 | 130.62 | 49,542 | 42,781 |
| 23 | 272.78 | 85.32 | 41,751 | 43,177 |
| 24 | 86.51 | 174.56 | 21,808 | 43,889 |
| 25 | 76.10 | 87.00 | 22,838 | 45,434 |
| 26 | 131.32 | 90.96 | 23,695 | 45,908 |
| 27 | 67.55 | 86.02 | 24,961 | 46,513 |
| 28 | 143.92 | 134.11 | 25,635 | 47,122 |
| 29 | 111.19 | 76.47 | 28,859 | 48,336 |
| 30 | 144.66 | 147.68 | 29,310 | 48,826 |
