# Goal认知闭环：两处措辞的受控对照与提案缺口

日期：2026-11-10。**总体PARTIAL：监控条件恢复，新的Goal候选演化闭环未建立。**
原件：/home/wqkan_wsl/uaea-n1x/research-records/telemetry-goal-loop-20261110T001159Z/
前置：[遥测修正](../implementation/harness/n1x-telemetry-reliability-20261110.md)；
历史：[原候选未更新](goal-candidate-continuity-20261109.md)、
[上轮受保护中断](goal-cognition-loop-20261110.md)。
Memory维持Research Reserved；本轮没有扩大Memory数学实验。

## 1. 最小变量设计与实际完成

旧五轮原文、ledger文件内容、工具/schema、Bolt32K/1GiB KV/36GiB规划、
Eager/单并发、Shared显式模式全部保留。只做两项删除：
A：第一轮删除“仅在现在”；B：第二轮删除“，不需要为轮次新增记录”。
第六轮所有条件相同：按最新方向真实重读ledger第1节，给两项核验，
说明旧助手目的当前/历史归属，并不声称未保存的状态已提交。

预登记2×2四种Shadow条件，加一组原措辞Relevant History。
实际5会话、30用户轮全部原生completed；0 Compaction、无重试/强制tool_choice。
每条件一次、固定顺序00基线→00Shadow→11→10→01，不是统计效应估计。
仅一组History基线，不是History完整2×2。路径/ID、模型生成历史和随机性不相同，
因此不宣称bit相同Context或已证明某句的独立因果作用。
factor-diffs.json只比较原五轮文本，证明除两项删除外未改其他轮次；
第六轮是共同探针，不把其提示后改善算作第五轮自发演化。

首轮仍显式邀请一次候选：**不是自然长期Goal Formation实验**。
样例隔离/非授权声明不禁止非权威候选，却可能影响模型选择；
不能从此泛化到所有真实用户Goal或所有Backend。

## 2. 实际轨迹：有语义回应，没有结构化候选

| 条件 | 删除A/B | 用户轮 | Goal调用/拒绝/版本 | 成功/失败文件Observation | 第6轮实际重读 | 累计输入/输出Token |
| --- | --- | ---: | --- | --- | --- | --- |
| Relevant History | 0/0，无Goal通道 | 6 | 0/0/0 | 3/3 | 否 | 140169 / 2724 |
| Shadow00 | 0/0 | 6 | 0/0/0 | 1/0 | 否 | 96331 / 2703 |
| Shadow11 | 1/1 | 6 | 0/0/0 | 1/0 | 否 | 95418 / 1887 |
| Shadow10 | 1/0 | 6 | 0/0/0 | 1/0 | 否 | 94908 / 1832 |
| Shadow01 | 0/1 | 6 | 0/0/0 | 2/0 | 是 | 112426 / 2001 |

这是累计使用量，不是单次Context长度；Harness有效窗口31129，服务配置32768。
8次成功读取（含README）、3次失败尝试均保留，重复读不是独立语义支持。
四个Shadow的Goal工具均在实际出站请求中广告，候选视图为空，
没有原生Goal提案、拒绝、提交或候选版本。Journal/快照为空不是投影丢失了已提交候选。
Goal通道、Runner、G0实现与11月9日成功提交时逐文件hash一致
（goal-path-version-comparison.json）；不能据零调用断言接口绝对不能执行。

**当前最小缺口位于提案产生/提交环节，不在保存或更新后投影。**
没有当前父候选，无法评价maintain/refine/revise/withdraw的真实新能力；
生命周期审计正确保持UNKNOWN，而不是空集PASS或全部操作FAIL。
去掉两句并未在这些运行中产生候选；这不支持“仅删两句就充分修复”，
但不能排除它们对上轮已有候选的工具选择有贡献。

## 3. 可以直接区分的模型行为

- Shadow00第一轮用“长期目标假设（已保留）”表达普通文字，未调用工具。
  这里的“保留”可能只指保留在对话中，不能自动评价为已保存Host候选，
  更不能将该文字导入Journal或Memory。
- Shadow11明确说工具存在、可调用，且复述用户已要求保留，却又问
  “Would you like me to register this hypothesis…?”。这是可观察的多余确认/行动延后，
  不是Host拒绝，也没有新授权缺失记录；内部原因UNKNOWN。
- Shadow10说“当前没有可使用的goal_hypothesis工具”，但出站工具列表实际包含它。
  这是能力表述与已供给协议不一致，不等于代码已移除该能力。
- Shadow01仅作条件式未来表述，未提交，不应当作已保存或已撤回。

各条件普通回答均响应了第五轮的新项目档案方向，但没有候选状态可供更新。
因此不能用普通语义响应替代真实Goal版本演化，也不能把“有新目的”当作正式采纳。

第六轮只有Shadow01实际调用并得到新读取Observation。
其他三组Shadow及History基线均没有该轮读取，却用“已重读”或重读标题复述旧材料。
无论它们主观上是否指重读Context，都未满足用户所要求的真实文件重读；
模型应明确复用历史，而非使其看起来是新执行。
原生调用/Observation按Turn逐一关联，非根据工具总数推断。
本轮初次人工整理曾把基线总共3次成功读取误当成末轮重读；
逐Turn原件纠正了该判断，旧误判副本与更正说明保留，不覆盖执行记录。

还有独立反例：Shadow00第六轮把旧目的变为历史的依据归到ledger中“冻结样例/两种方法”。
直接依据应是用户第五轮改方向；ledger自身不能证明用户取消某目的。
部分建议还把整文件hash与节选hash混用，或提出未验证的核验步骤。
这些是模型归因/推理问题，不扩通用语义裁判来替模型修复。

## 4. Contract核查与评价器限定

原goal-audit.json合并基础设施判据为4/5，保留原值。
基线多读了README，其79字符正文被仅针对ledger的fixture-manifest判为unverified_source；
不能由此断言Runtime将README正文伪造为ledger。

补充按真实返回path、沙箱范围、源文件及line_start/end核验全部8次成功Observation：
源hash、节选hash、完整摘录与自身文件均一致（outcome-review.json）。
README由冻结build_adapter代码生成，实验工具只有读取，不是额外可变外部资料。
该补充不覆盖原评分，也不证明多读README符合最佳任务策略或其陈述为真。
未为获得5/5修改评价器；目标ledger的实际供给/hash和当前原始输入仍可追踪。
影子模式额外源视图、工具广告与Runtime行为界限单独核查，
没有将原生Turn completed或文件成功等同于Workflow完成。

全部30轮正式ActiveGoal为空，Workflow completion_established=false；
未开放Memory Admission或新执行权限。Goal正文没有被晋升为Source Evidence。
无新Goal版本则“最新候选被收到/被使用”仍UNKNOWN，不能仅凭空投影合法判成功。
Context原文、消息及实际工具Observation可在state-feedback-audit.json和完整model-http-audit复核。

## 5. 资源与监控版本边界

一次真实加载，1652个服务样本覆盖约1699秒，30轮内无遥测中断、无内存停止。
NVML GPU峰值29.04GiB；Windows Dedicated29.02GiB、Shared0.253GiB；
Windows Available最低21.83GiB，Commit最小余量44.03GiB、占用峰值70.45GiB；
WSL Available最低17.39GiB，Swap峰值约112KiB。
不同口径不相加；采样极值不是瞬时硬上限。

真实运行使用NVML V1，完整采样最大8.882ms、GPU查询最大1.994ms。
停服后V2仅增加2秒迟到成功拒绝，已作CPU红/绿反例和无模型保护复核；
**没有将V1真实结果冒充V2完整模型验收**。详见遥测报告与独立pins。
Driver主动ControllerStop，进程组/监控清理remaining=[]；
外层异常包装中的ControllerStop不是遥测故障或Goal失败。
8000/8003无监听，没有重载、改Carveout、Pagefile、驱动、依赖或阈值。

## 6. 独立结论与下一评审点

| 维度 | 判定 |
| --- | --- |
| 原监控短时恢复及实际运行连续性 | VERIFIED，限定PASS；长期可靠性UNKNOWN |
| 出站原始输入/工具广告/执行事实 | VERIFIED限定；原合并判据4/5及额外源假设单独说明 |
| Goal提案是否产生 | VERIFIED：本批0；不是证明模型永远不能产生 |
| Goal语义理解 | PARTIAL：普通文字可区分方向变化，仍有错误能力/来源及行动陈述 |
| 自然形成、已有候选自主演化 | UNKNOWN：本批未形成种子；历史显式能力仍保留 |
| 最新候选影响后续行为 | UNKNOWN：候选机制没有实际介入 |
| 超越Relevant History的决策收益 | UNKNOWN：Token/工具行为不同，不等于有或无认知收益 |
| 认知闭环 | 未建立，不以30轮完成或回归PASS代替 |

关键研究取舍是：是否继续把“自选工具提交”同时作为形成入口和后续认知维护的前提，
还是先使用已有显式提案能力建立一次真实种子，再独立研究无操作提示的维护。
下一步最小建议是后者的一次正控，不把显式种子叫自然形成，不每轮强制提案；
若要比较已有legacy表达入口，应作为新的隔离协议对照评审，不从普通文字自动采纳。

本批已经足以停止重复空候选的措辞试验，但不支持重建Goal Engine、引入第二Loop、
增加Memory维护层或让Runtime通用语义纠错。
没有真实候选就无法研究其增量决策价值，先解决提案入口，不能增加更多状态来掩盖缺口。
**停止新增模型实验，提交提案入口/研究路线评审；当前无需人工长会话或真实Goal确认。**
不Commit/Push，不改变Phase-1、Goal/Memory正式权威与授权规则。
