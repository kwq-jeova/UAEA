# Goal Hypothesis自主维护：有效种子对照与显式修订正控

日期：2026-11-10。**总体PARTIAL；显式修订/版本反馈限定PASS，自主修订未建立，增量决策价值UNKNOWN。**
本报告只评价WSL升级结束后新批次，旧中断不并入模型统计。
源码检查点：125f0d2a8e6b7ac0f6b70baf9913b942be2b1cb2。
先行研究：[旧有种子未更新](goal-candidate-continuity-20261109.md)、
[30轮零种子的限定结果](goal-wording-contrast-20261110.md)、
[首个显式生命周期](goal-channel-convergence-20261109.md)。

原件：
- 主对照与180秒附加诊断：/home/wqkan_wsl/uaea-n1x/research-records/goal-autonomous-resume-20261110T020213Z
- 独立显式修订正控：/home/wqkan_wsl/uaea-n1x/research-records/goal-maintenance-explicit-control-20261110T022608Z

## 1. 条件与实际完成范围

沿用原Bolt/vLLM0.32.0、32K、1GiB KV、36GiB规划、单并发/Eager、
64/64 UMA、现有Windows/WSL/GPU保护及Fail-Closed，未改依赖、权限或正式Runtime。
WslService运行、安装结束状态0且Installer InProgress不存在后才开始，非升级中自动重载。

| 批次 | 预登记内容 | 实际完成 |
| --- | --- | --- |
| 主对照 | Relevant History / Goal Shadow，同一5轮、同一冻结ledger、读工具与采样默认 | 2会话、10轮原生completed，0 Compaction |
| 附加诊断180 | 主Shadow有种子、T4无更新才运行；独立3轮显式接口正控 | 首轮2次拒绝后form已提交，但180秒时Turn仍未完成；0完成轮，后2轮未发送 |
| 独立正控420 | 保留上述失败，原3轮用户文本不改；隔离bundle单轮等待180→420 | 1会话、3轮completed，真实form→revise，0 Compaction |

合计13个完成轮，另1个未完成原生Turn，不能写成16轮全通过。
主对照首轮显式要求一次种子；其后只取消Task、改变条件、明确更换长期方向并作下一轮探针，
没有要求具体Goal操作。不存在forced tool_choice、Host代填、自动补发或每轮配额。
maintain不要求生成新版本。

样例为非金融合成用户意图，ledger为既有研究者摘录，非真实用户Goal或新GPU观测。
真值来自运行前冻结的明确脚本；语义审查由研究者比对原文，不由Bolt自评，也非独立人类盲评。
单对、固定顺序、会话路径/随机生成不同；实际读取次数不同。不能估计统计效应或长期收益。

## 2. 主Shadow真实轨迹：保持成立，修订未提交

首轮原生Call：chatcmpl-tool-82e7cddc278aa0ad。
Turn：01a1c338-80a8-7132-8695-edb7cfb07b99。
唯一版本：goal-candidate:a8c110f3fea94e52f9283781。
记录SHA256：25e5c4a5eb1240b054468a8e2f16d7c82625572f7e97fcba1b53b2df0b761a6d。

候选正文：
> 研究一个在多轮任务中可追溯来源、能够发现并修正误解的文档助手；不要求产品化或永不出错。

这是有依据的显式种子，不是自然形成证明。
Native arguments、当前原始输入/hash、Journal第1行、保存快照和后续成功请求2–6逐值一致。
工具调用不进入外部Capability Observation，不改变正式ActiveGoal。

| 轮次 | 模型理解/实际动作 | Host及实际出站状态 |
| --- | --- | --- |
| T1 种子 | 真实读取＋form，准确报告提交ID | 保存1个版本；请求2成功携带同内容/hash |
| T2 取消子任务 | 长期方向保持，不新增Goal调用 | 原版本保持；属于本样例中合理不行动 |
| T3 无GPU/外网 | 调整离线路径，保留长期方向，无Goal调用 | 原版本保持；没有把条件改成最终目的 |
| T4 更换长期方向 | 文字转为项目档案；旧候选称历史，但无Goal调用 | 请求5仍是原candidate，无修订/撤回/新根 |
| T5 下一轮 | 仍按档案方向回答、引用旧ID作历史；未实际重读 | 请求6仍携带旧head，五轮头快照完全相同 |

T4 Turn：01a1c33b-0b0c-7171-b445-82f1e7b4db56。
T5 Turn：01a1c33b-a846-77c2-a6c7-64dbc1bf953e。
app-server-events.jsonl第69行为真实form RPC；goal-events.jsonl第1/2行为VERSION/PUBLICATION。
逐Turn调用、完整回答与请求序号见turn-evidence-review.json。

**VERIFIED：有有效种子后，语义上接受新方向，但没有将其提交为候选版本变化。**
原生raw function_call也没有T4/T5 Goal提案；未出现Host授权拒绝或“已提交但投影丢失”。
工具在成功请求中存在，旧head被完整供给，因此不能把这次缺口归为漏注册或漏供给。

同时不能夸大失败：本轮没有明确声称“旧候选已撤回/新候选已保存”，而是把旧ID保留为历史。
“当前状态变更”标题仅为普通回答，不能自动视为Host提交。
候选是非权威解释，保留历史本身合法；**文字历史化不等于已持久化Revision/Supersession**。
尚不能断言模型为何不提交，也不能仅据无工具操作判所有语义理解失败。

## 3. 附加诊断180：拒绝、纠正与未完成分开

独立新会话先按同一首轮建立种子，再显式请求修订；并非自然维护实验。

- chatcmpl-tool-887fc11bda05faf1、chatcmpl-tool-b9ff387d6607c1d1：
  candidate_id实际为字符串“None”，form所需JSON null未满足，Host正确拒绝。
- chatcmpl-tool-911045d868dbbf9c：实际为null，模型在既有Harness循环中自行纠正，
  保存goal-candidate:7d5041f45464057060659bdd；Host没有代填。
- Runner在180秒期限返回pending，未见turn/completed，停止且不发送后续输入。
  这是有限自动研究的等待边界，不是手工服务期限、资源越界或Workflow完成。
- 提交后的请求4虽已准备，transport_result为BrokenPipeError。
  **不能把prepared、部分字节或已保存候选计为成功传输/完整Turn。**
  也不能由中断断言模型绝对未接收过任何片段。

diagnostic-partial-audit.json用独立Host投影manifest、原生user item、实际RPC及保存快照，
验证未完成Turn内的提交确实存在；成功后续供给仍未建立。
没有用缺失的turns.json制造completed，也没有把提交回滚写成拒绝。
两个错误值在Host处可见；缺少Parser前原始生成，模型与Parser的详细归因UNKNOWN，
不能从字符串“None”认定整个nullable schema不受支持。

## 4. 独立显式正控：真实form→revise与下一轮反馈

没有覆盖原诊断，也没有重跑主对照。
仅隔离bundle的longitudinal_dialogue.py中turn_timeout=180改为420；
正式研究Runner/人工入口、模型参数、Context/资源期限均不变。差异保存在runner-timeout-only.diff。

本次3轮实际耗时96.78/79.58/49.44秒，均低于180秒。
因此**不能声称420秒造成修订成功**：新会话与采样不同，正控证明的是接口存在可执行路径。

| 操作 | 原生Call | 版本及实际成功供给 |
| --- | --- | --- |
| 显式form | chatcmpl-tool-afe7d79ab51f586b | goal-candidate:35249146cf38993c0d12e352；请求2、3 |
| 显式revise | chatcmpl-tool-ba5a5dfb345ea189 | goal-candidate:be18a00d3928f299cf461894；父35249146…；请求4、5 |

原始RPC位于该会话app-server-events.jsonl第38和312行。
旧版本未改写，新版本内容、来源、父引用、完整记录hash、快照与出站head一致。
请求5只有新head作为当前版本；原工具回执仍作为历史，不等于旧head重新生效。
第三轮没有新的Goal调用，模型准确引用新ID、父ID、candidate/committed及非权威状态，
并明确“候选不等于项目档案核验结果”。

**限定记录/反馈闭环PASS；自主维护不是本正控测量对象。**
还有关键负面：本正控两个hypothesis直接复制整段用户输入，
把子任务和“请实际调用工具”等操作说明混入候选，未形成干净的长期Goal抽象。
来源及结构正确不等于候选语义质量PASS；当前语义质量PARTIAL。
最终建议对ledger背景与用户新方向的关联仍缺充分理由，未证明实际决策价值。

## 5. Relevant History、成本与Workflow

| 主对照 | 累计输入/输出Token | 成功文件Observation | Goal RPC/版本 | 出站请求 |
| --- | ---: | ---: | ---: | ---: |
| Relevant History | 107862 / 1528 | 3 | 0 / 0 | 8 |
| Goal Shadow | 83569 / 1843 | 1 | 1 / 1 | 6 |

这是累计usage，不是单次Context长度；Harness有效31129、服务32768。
源文件版本相同，读取节段及调用次数不同，不是bit相同的实际模型输入。
基线也正确接受长期方向变化，并在T5真正重读；Shadow未执行T5明确要求的真实重读。
因此Shadow较低输入成本不能称为认知效率收益；至少部分伴随少做必要操作。
两臂建议仍主要为离线核验/来源整理，没有真实后续决策结果，增量价值UNKNOWN。

独立显式正控输入67923、输出1645，仅报自身成本，不混入主对照。
中断诊断的部分usage不当成完整会话成本。
成功Observation的真实source/excerpt/hash供给核查通过；
外部文件观察与语义控制调用分别统计，Tool Success和Turn completed不等于Workflow completed。
所有完成轮快照的ActiveGoal为空，Workflow completion_established=false，
model_output_is_source_evidence=false。Memory全局未采纳未作独立审计，不以声明字段代替观测。

## 6. 资源、清理与影响范围

| 新批次 | service样本 | NVML峰值 | Win Dedicated/Shared峰值 | Win Available最低 | Commit最小余量 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 主对照＋中断诊断 | 786 | 29.27GiB | 29.27 / 0.243GiB | 22.27GiB | 43.69GiB |
| 独立显式正控 | 331 | 28.95GiB | 28.95 / 0.233GiB | 22.46GiB | 43.76GiB |

WSL Available最低分别17.51/17.51GiB，Swap峰值12/16KiB。
完整Linux采样最长分别5.93/1.59ms。不同内存域不相加，极值不是瞬时硬上限。
没有实际资源阈值或遥测失效停止；原GPU阈值/失效CPU烟测依旧按预期触发。
两个服务由本研究Controller主动STOP，模型remaining=[]、采样器remaining=[]，
共4个Harness进程组均absent；8000/8003无监听。
外层monitor-exception的CONTROLLER_STOP是主动收尾包装，不能错判为内存保护触发。

正式源码、Goal通道、依赖与启动资产pins保持一致。
两种bundle只有隔离Runner等待那一处源码hash不同，均执行前冻结、执行后核对。
正式修改仅本研究文档和地图；脚本、模型请求/原生事件及失败原件位于独立research-records。
未改Phase-1、Harness执行循环、Provider Policy、自动Goal/Memory采纳或资源边界，不Commit/Push。

## 7. 判定与架构评审点

| 维度 | 判定 |
| --- | --- |
| Runtime/来源、版本、提交与成功投影 | VERIFIED，限定PASS |
| 有种子后的Task/Path保持 | VERIFIED，清楚脚本条件下限定PASS |
| 无操作提示的候选修订 | PARTIAL/未建立：主T4/T5没有提交；普遍能力UNKNOWN |
| 显式form→revise→下一轮真实状态反馈 | VERIFIED，限定PASS |
| Goal语义抽象及建议质量 | PARTIAL：正文混入指令，建议价值未证 |
| 自然根形成、Compaction/跨Run恢复、长期增益 | UNKNOWN，本批不覆盖 |

结合[此前有效种子未更新](goal-candidate-continuity-20261109.md)，
新的有效对照仍出现“理解方向变化但没有版本提交”；最新30轮的空种子结果不混作维护失败。
本次显式修订又证明保存、版本、投影和权限通路能执行。当前实际断点是
**如何从语义判断进入可选提案提交**，不是缺少版本Engine或应由Host解析普通文字自动更新。

HYPOTHESIS：模型工具选择与交互约定构成自主维护的实际门槛。
精确内部原因UNKNOWN；不能把“可选”、不改文件措辞、schema或某模型单独定为原因。
没有证据证明工具接口代码本身必然错误；也不能从接口能执行推导模型会自主维护。

**建议保留当前通道为显式、非权威、可撤销的研究正控，不把自主维护切为默认。**
到达有种子负面结果＋真实显式修订版本链的路线评审节点，停止重复措辞实验。
若继续，先评审一个有限的可替换提案生产者/既有结构化研究入口对照，
保留相同种子脚本与Host验证，避免再把工具自选和语义能力混在一起。
不新增自动补发、第二Loop、Goal维护Engine、Memory层或语义裁判。
当前无需人工长会话或真实用户Goal确认。

复核入口：combined-evidence-summary.json、turn-evidence-review.json、interface-review.json、
goal-audit.json、diagnostic-partial-audit.json、source-index.json、resource-review.json；
原始Goal Journal、model-http-audit及app-server-events均保留。
回退只需停止使用opt-in研究入口；没有正式默认模式、依赖或安全配置需要回退。
