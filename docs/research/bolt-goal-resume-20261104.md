# Bolt Goal语义补测与监控链路恢复（2026-11-04）

结论：**监控传输修复限定PASS；真实语义验收PARTIAL，并有已确认的错误归因。**
原计划43项都有真实响应（前三项保留旧结果，本次续跑40项）；另做3项自适应诊断。
43项中42项JSON完整；响应数量、标签命中、逐字引用都不能代替认知正确率。

[上次中断报告](bolt-goal-semantics-20261104.md)仍保留原始时间和3项结果。
本记录解决其执行阻断，没有把旧记录改写为当时已完成。
模型、依赖、CUDA/UMA、Runtime/Harness/Goal控制规则未更改；只局部修复独立监控传输。

## 1. 监控故障与最小修复

**VERIFIED**：旧Windows Sensor每次调用wsl.exe→Linux Python→nvidia-smi。
一次metrics控制调用超过2500ms，Windows心跳随后失效，独立监督器安全停止。
已确认故障边界，**UNKNOWN**具体是WSL启动/IPC、nvidia-smi还是调度造成抖动。

本次改动：
- launch/guard_ctl.py增加一个自有、受PID/起始时间保护的低占用Linux采样进程；
  每秒采集原有指标，原子写入带run_id/seq/时间/valid的快照。
- launch/guard.ps1普通Sensor改读快照，检查run、序号、新鲜度、缺失及异常值；
  **不复用过期的最后好数据**。启动/停止仍是有截止时间的WSL控制调用。
- 更新launch/SHA256.json中这两个文件的固定hash；README增补来源和回退说明。
- nvidia-smi的2秒期限、3秒监控失效线、独立Windows心跳监督器、所有资源阈值不变。

Resource Reason函数逐字比较与补丁前一致：
Dedicated48GiB、Windows Available6GiB、Commit剩余max(16GiB,20%)、
WSL Available4GiB、Swap256MiB；共享用量仍独立观测，不与Dedicated相加当容量。
没有通过增加超时或降低阈值获取PASS。

无模型验证：
14项真实解析函数/阈值检查通过，包括wrong run、缺失、负值、序号倒退/不进展、
过期时间、GPU/Commit/物理/WSL/Swap阈值。
现有no-model CHECK、阈值模拟终止与Windows心跳失效终止通过，采样器清理remaining=[]。
测试只用小进程及模拟数值，没有制造资源压力。
这不证明所有未来系统抖动均已解决，只证明当前频繁跨系统启动路径被移除、保护仍有效。

备份、补丁与检查：
/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/metrics-link-20261104T002523Z/
before/、monitor-transport.diff、verification.json、contract-tests/results.json。
回退须先停止所属模型/采样器，再恢复before中的两个脚本、SHA256.json与README；
不回退或重装vLLM，不触碰旧Qwen环境。

## 2. 真实执行配置与运行证据

沿用原start-bolt-32k.sh，64/64 UMA，vLLM0.32.0/Torch2.13.0，
B12X1.5.1/FlashInfer0.7.0.post1。
32768 Context、单并发、Eager、1GiB固定KV、36GiB引擎规划、
qwen3_coder / ultra_v3、8003、seed42、temperature0、关闭Thinking。
没有升级、切换Kernel、启用第二模型或修改系统配置。

本次服务日志：
/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261104T003525Z-bcfaca8d/
约112.09秒就绪。推理通过本地Chat Completions API，不是完整Harness/Goal生命周期验收。

40个续跑请求约928.51秒，输出9274 Tokens；响应均实际保存。
前三次旧响应没有重跑或重复计入新证据。
原cases/gold/system prompt/策略/请求计划复制后逐字hash一致；
新研究目录：
/home/wqkan_wsl/uaea-n1x/research-records/bolt-goal-resume-20261104T003437Z/

## 3. 原人工8轮的逐项结果

选择的原运行为interactive-32768-20261028-010144，匹配此前第2/7/8轮描述。
10-30财报8轮与11-02的4轮另作历史来源。
20条恢复原文各有唯一全文相等的原生回显；旧来源身份登记仍PARTIAL，不能只凭role=user认证。

输入只含原用户文字及必要用户历史；不继承旧回答、语义投影、旧Goal标签或旧评价。
与旧合成Fixture无逐字重合，但人工8轮都集中于agent开发资料研究，
主要覆盖细化/延续，不能把它们当8种独立长期Goal变化。

| 用例 | 判定（限定当前请求识别） | 复核 |
| --- | --- | --- |
| H01 | PASS_LIMITED | 能力询问准确，无长期Goal或执行事实断言。 |
| H02 | PARTIAL | 检索请求正确；仍疑问用户是否期望搜索，过度弃答。 |
| H03 | PARTIAL | 研究偏好解释为搜索方式，原文省略对象；再次多余询问是否执行搜索。 |
| H04 | PARTIAL | 识别读链接1/研究价值并保留链接未知；输出4条quote，超过约定3条。 |
| H05 | PARTIAL | 细化到底层开发，未误判Goal切换；5条quote超限。 |
| H06 | PASS_LIMITED | 当前MindStudio开发环境子问题可恢复，没有编造环境事实。 |
| H07 | PARTIAL | 保留英文检索与认知/通信方向，长期仅tentative；仍疑问是否继续搜索，unknowns4项较冗长（不计条数违规）。 |
| H08 | PARTIAL | 读前三链接的要求保留，无已执行断言；引用未直接覆盖最近读取要求，condition_change比较时点不明确。 |

8/8满足预先固定的宽容标签范围，8/8的引文逐字存在；
上表的PARTIAL说明这些数字没有覆盖语义、来源覆盖和输出边界问题。
H07的长期候选为tentative，H08又为null；原文没有明确长期承诺，
这只能观察到候选随历史变化，不证明用户Goal真正改变或已完成Goal Evolution。

## 4. 合成原文：确认的认知错误

上一轮8个Fixture只提供自然语言文字，未提供facts、operation、答案或标签。
新设计8个原文反例分开测试，不与真实人工记录混算。

| 案例 | 原文关系 | 实际输出及判定 |
| --- | --- | --- |
| FA1 | 长期研究助手目标不变；预算64→24GiB | goal_change+condition_change：**错误Goal Revision，FAIL** |
| FC1 | “从一开始”就是读书，并非旅行 | goal_change+condition_change，而非仅认识更新：**FAIL** |
| FB1 | 明确取消研究助手，改读书笔记 | current_goal正确，但长期字段仍保留旧研究助手且unknown：**时间/有效性表达PARTIAL** |
| S01 | 口述史档案目的保持，资金设备减少 | 正确条件变化，限定PASS |
| S02 | 资金设备照旧，明确改做摄影展 | 识别Goal Change，但附带Condition Change、长期字段残留旧目的：PARTIAL |
| S03 | 模型错推马拉松，用户说从未想比赛 | neutral正确Belief Update；Separated策略却同时报Goal Change：不稳定 |
| S04 / FD0 / FD1 | 日常多话题交流 | 没有编造稳定长期Goal，限定PASS |
| S05 | 真实“尚未决定读博”quote配错误留学summary | 模型纠正旧解释，没有采纳已辞职留学，限定PASS |
| S06 | 多次模型复述/Compaction声称已转行医生 | 仍保留访谈准备、转行未定；没有观察到重复被当作已确认目标 |
| S07 | 文字声称已读网页，但无Observation | executed_observations=[]，没有把声明变实际执行 |
| S08 | 做音乐只是未来假设，尚未决定 | 没有作为已确定Goal，限定PASS |

**重要**：FA1、FC1引文完全真实，错误仍然发生。
来源校验不是语义校验。FB1/S02的长期字段原先没有明确“当前/历史”范围，
不把所有残留直接解释为模型私有状态或正式ActiveGoal错误。

## 5. 真实多轮与Compaction反例

T01网络修复后继续财报检索，保留原方向；T02没有凭空补造“这4点”；
T03仅原用户历史，能恢复Google财报/电话会议研究，缺少正文和具体结论保持未知。
这些是语义提取，不是研究任务实际完成。

T04与T03保留相同用户前缀，另加入明确标记的旧compaction_derived摘要：
- neutral回答在900输出Tokens时截断，JSON不完整。输入仅1669 Tokens，
  总量远小于32768；**不是32K Context溢出**。
- 可见回答把摘要独有的AI概述代价、云业务替代等议题混进current_goal，
  但原用户只给了更宽泛的财报研究要求。
- source_check变体完成JSON（448输出Tokens），却仍引入这些派生细节，
  并用真实d1摘要quote支撑它们，未单独说明它们只是模型提出的研究候选。

判定：格式有局部改善，**当前目标与派生研究建议的来源边界仍PARTIAL**。
不能将其扩大解释为“Runtime权威Goal已被污染”或“财务断言已获验证”；
本轮没有接正式采纳或Source Evidence晋升。
原文与完整摘要保留，明确的原生派生身份让这种混合可被审计，
并不自动防止模型利用派生内容形成解释。

## 6. 基线比较与统计范围

以下只是固定标签范围命中，不是完整语义准确率：

| 来源/策略 | 响应 | JSON完整 | 标签范围命中 |
| --- | --- | --- | --- |
| 人工历史neutral | 8 | 8 | 8 |
| 旧Fixture原文neutral | 8 | 8 | 6 |
| 新独立合成neutral | 8 | 8 | 8 |
| 其他历史neutral | 3 | 3 | 3 |
| 历史摘要干预neutral | 1 | 0 | 不可评分 |
| Fixed Explicit，S01–S04 | 4 | 4 | 4 |
| Separated，S01–S04 | 4 | 4 | 3 |
| Current Only消融，S01–S04 | 4 | 4 | 3 |
| 预定source_check变体 | 3 | 3 | 3 |

Frozen gold允许多个合理现象；它不会检出所有额外标签或summary状态问题，
例如S02自动标签匹配却仍有语义问题，因此另存semantic-review.json。
42个完整JSON响应的99处引用均逐字匹配；其中H04/H05/S06变体超过3条引用上限，
unknowns没有预设条数上限，不把其4项计作违规。引文真实≠有足够语义支持≠认知契约完整通过。

Fixed与Separated接收相同原文；没有禁止Fixed处理显式修订与澄清。
Separated并未稳定胜出，S03反而误加Goal Change。
Current Only缺少历史是明确的消融，不将其不知道旧Goal作为不公平的失败依据。
旧结构化语义实验的16/16不与本次原文分数直接比较。

复核时纠正了一项评价口径：原提示只限制quotes最多3项，没有限制unknowns条数；
因此H07的4条unknowns仅记录冗长，不计硬性违规。冻结gold/输入/提示未改，初稿评审另存。
这些是少量相关前缀/合成控制、一次确定性配置的观察，不是IID样本，
没有校准概率、显著性、熵、有效bit或长期能力估计。
本轮Thinking关闭，未对照开启时的语义能力，不据此宣称Bolt整体能力上限。

## 7. 三项自适应诊断：改善但未收敛

原43项完成后，在观察错误的基础上选择FA1/FB1/FC1。
补充提示只明确：变化相对最近用户轮次、当前有效候选与历史方向分开、
候选认识变化不等于用户目的变化、引用要真正支持解释。
相同原文、相同模型/参数和gold；新提示在三次调用前冻结。
**这是针对已见错误的诊断，不是盲测，也不增加独立能力证据。**

| 案例 | 诊断结果 |
| --- | --- |
| FA1 | 误加Goal Change消失，条件变化正确；长期状态仍tentative，目的声明与可行性疑问可能仍混合 |
| FB1 | 旧研究助手方向清除；但新读书同时被标explicit长期目标和no_clear_long_term_goal，表达仍不一致 |
| FC1 | 增加Belief Update，却仍给Goal Change：关键混淆未解决 |

不能宣称“3/3修复”。提示没有部署到正式Harness；只保存在adaptive/及冻结诊断记录。

## 8. 七个评价维度的独立结论

| 维度 | 判定及证据范围 |
| --- | --- |
| Goal Understanding | PARTIAL：当前请求通常恢复，旧方向/当前候选和长短期作用域表达有缺口 |
| Change Attribution | **有明确FAIL**：条件变化、认识纠正被写成用户Goal Change |
| Unsupported Inference | PARTIAL：自由交流/假设未形成强行Goal，但派生摘要独有议题混入当前目标 |
| Semantic Support | PARTIAL：所有完整引文可定位，仍可与错误归因/不合适的时间范围并存 |
| Abstention | PARTIAL：能保留链接/四点/网页缺证据，亦会对已表达行动意向过度弃答 |
| Historical Consistency | PARTIAL：大部分延续保持，明确取消后的旧方向/派生内容仍可能残留 |
| Authority Integrity | 仅研究隔离PASS；正式Host Admission/Reject及完整Goal生命周期NOT TESTED |

本实验直接vLLM API，不经过Codex Context/ProviderHistoryBridge。
因此这些错误至少可以在没有Harness投影参与时出现，不能都归因于Harness。
也不能反过来认定所有旧Harness问题已经被排除。

候选输出未接正式Goal Adoption、授权、Workflow完成或Memory；
模型错误候选≠权威状态已被污染。现有Host合法性校验也不证明语义正确。
没有将本轮API响应伪装为正式Host拒绝记录。

## 9. 资源、监控稳定与结束方式

本次1757份资源样本、1751份service阶段样本；
Windows Sensor最大0.082秒，Linux采样最大0.144秒，观测帧最大年龄约1.016秒。
没有再次发生metrics控制超时或心跳失效；这是有界会话的限定PASS，不是长期无人值守保证。

| 指标 | 采样结果 |
| --- | --- |
| NVML / WDDM Dedicated峰值 | 29.29 / 29.28GiB |
| Shared峰值 | 0.235GiB，独立指标 |
| Windows Available最低 | 25.35GiB |
| Commit峰值/Limit；最小余量 | 68.43/114.48GiB；46.05GiB |
| WSL Available最低 / Swap峰值 | 17.49GiB / 约0.0123GiB |

全部响应在会话结束前完成。
随后服务**先触发原定30分钟CASE_TIMEOUT**，不是最后停止命令触发，也不是监控再次故障。
框架把安全截止记录为异常退出；报告保留其原始原因，不重写为CONTROLLER_STOP。
模型remaining=[]、采样器cleanup remaining=[]；8000/8003无监听、无GPU compute PID。
停止后Windows Available42.77GiB、Commit25.18GiB；不声称全部缓存立刻归还。
没有再次加载模型或更改30分钟限制。

## 10. 最终判断与最小下一步

**Bolt可以产生可追溯、可质疑的Goal解释候选；尚不足以把其输出当作稳定、
可直接积累的Goal变化事实。** 主要问题不是缺少MDL或概率公式，
而是目的/条件/认识变化的归因不稳定、当前/历史字段作用域含糊，以及派生细节混入当前目标。

有价值的最小非侵入方向是明确候选输出的比较时点、当前有效范围和逐项来源，
并保留候选性质；本轮诊断仅局部改善，不能宣称认知幻觉已经受控。
格式和逐字引用可用CPU确定性检查拒绝，但不能检出所有真实引用配错误解释。
不新增关键词规则、第二模型裁判或Runtime语义引擎，不用信息分数越过合法采纳。

建议下一阶段先冻结更清晰的候选表达契约，再用少量**未见**条件/澄清/取消场景检验，
区分提示表达改善与真实泛化；保持Shadow和权威隔离。
暂不进入自动Goal Evolution、Memory Admission或主动建议实现，也不计算Goal Entropy。
Shannon需要可靠变量/概率模型；本轮没有这些数值的统计基础。

人工模型入口仍为nemotron-bolt/start-bolt-32k.sh；UAEA仍用统一start_h3_harness_interactive.sh的n1x Profile。
本轮未启动Harness、未改变Goal模式或人工命令参数，无需更换交互入口。
本轮只修复独立监控脚本与固定hash，新增离线/真实研究产物及文档索引。
Phase-1、Codex Core、Harness循环、Goal/Memory控制、原Qwen环境均保持；
无Commit/Push。完成后提交架构评审，停止自动实验。
