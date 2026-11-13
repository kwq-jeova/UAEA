# 实验B：双范围Goal种子与生命周期准入（2026-11-12）

**PARTIAL；后续生命周期NOT RUN**。两条真实Sideband根候选已保存并进入完整成功请求，但长期种子混入Agent查询需求、候选保存指令，未满足预登记的忠实目的准入。保留原始错误候选，不改写/重试，B2–B10未执行。

[实验A](goal-intent-attribution-experiment-20261112.md)独立完成8轮，不能补作B生命周期。本报告区分来源合法、语义支持、实际保存和正式权威。

## 1. 冻结设计及实际结果

唯一批次：/home/wqkan_wsl/uaea-n1x/research-records/goal-intent-lifecycle-20261112T031832Z。

B Thread：01a1cdd9-84df-7030-a240-4ea8f75089ea；唯一用户Turn：01a1cdd9-84ff-7511-966b-7e2e1e65cbf7。

B-scenarios.json提前冻结10轮；preregistration.json/evaluation-private.json要求两条实际保存、范围清楚且忠实目的的种子及成功请求投影，才继续。独立审查条件未作为答案注入。B1明确邀请形成两个可撤销候选，**不是自然形成实验**。

两个实验各有独立Native进程、Thread、codex-home、sandbox、状态、Journal，只复用同一服务加载。B不依赖A保存状态。来源与真实历史限定见A§1：长期方向是用户授权的实验目的，不证明私人历史心理；Intel局部任务对应真实人工问题。

| 项目 | 实测 |
|---|---|
| 轮次 | 唯一started/completed；1/10，B2–B10 NOT RUN |
| HTTP/响应 | 4/4 framing完整、completed，非仅HTTP200 |
| Tool Call | 4次真实read_section成功，2次goal_hypothesis成功 |
| Goal版本 | 显式form×2，parent均null；没有refine/revise/withdraw |
| 保存/投影 | 保存2、提交2；后续成功请求sequence4携带两条head |
| Token | 累计API输入60117、输出1093，最大18791 |
| 耗时 | B1用户Turn156.07秒；阶段215.77秒含审查等待 |
| Compaction | 0；没有超窗；Goal恢复未测 |

配置与A相同：GPU56/Host72、64K、KV1GiB、seq1、util0.65、Bolt/vLLM0.32.0/Codex0.163.0。4/4请求带Goal工具。A/B提示不同，不以Token差声称接口或Goal开销因果效果。

## 2. 两条真实种子及语义审核

共同原始输入：input:f4e32d18-219d-4c3e-83ab-6b89201fee81；hash 88155adeb9b8cd2fc87c18ffa2299cc45363e57d572fb2495ff0be12d56d9f73。B1明确要求目的概括而非保存操作/工作步骤。

### 宽范围候选

ID：goal-candidate:098ea60b1c3caf2ca410b22d
Call：chatcmpl-tool-9405f3f580097084
原生B/app-server-events.jsonl行60；保存B/goal-events.jsonl行1。

> 长期跨公司AI产业投资机会研究是全局范围目标，需从本地摘录之外查找更多AI行业与公司资料，并在可撤销的目标假设中保留。

quote“长期跨公司研究AI产业投资机会”是真实输入，input_ids及版本绑定合法，但不支持所有附加内容：
- 跨公司AI产业投资机会研究：有明确用户目的依据。
- 需查找更多资料：Agent为研究安排的资料获取手段，用户未将它指定为长期结果。
- 在可撤销假设中保留：本次存储操作/研究约束，不是用户希望实现的长期目的。

因此清洁目的种子准入**FAIL**。判定依据完整上下文，不是关键词禁止查询，也没有新增Runtime规则。

### 局部范围候选

ID：goal-candidate:0cb6591e2475fdd96208bc87
Call：chatcmpl-tool-956080bd53bb1609
原生行66；保存Goal Journal行3。

> Intel当前财报与估值分析是局部范围目标，基于已读的官方摘录（INTC 2026Q3收入$16.5B，GAAP EPS $0.60，non-GAAP EPS $0.52）可撤销地保留。

quote“完成Intel当前财报与估值分析”合法；局部目的可辨认，数字真实读取，无新行情伪造。但候选混入事实材料和可撤销保留的操作表达，语义抽象**PARTIAL**。即使接受它，宽范围候选也不足以通过双清洁种子准入。

本次用户明确要求实验保留一个有限范围的期望结果，不代表所有Task应自动成为Goal，也不要求新增正式Task对象。

## 3. 保存、真实投影与认知传播

B/goal-audit.json与B/evidence-index.json交叉核对：
- 两条record_binding均true，模型原生Call、submitted_proposal、操作、input_id、payload与内容hash一致。
- goal-research-state保存2条、Journal提交2条；父均null，为两个根，不是版本修订链。
- actual_supplied_sequences均[4]；请求4中两条head均content/version匹配、在提交之后、当时为当前head，且完整HTTP/响应通过。**这是同一用户Turn内的后续模型请求，不是下一用户轮维护证据。**
- Native最终正文行436如实报告两个真实ID、已保留、可撤销及不是正式ActiveGoal。
- 查询/保存指令已进入请求4，并在最终正文重述。可见传播**VERIFIED**；未记录模型内部依赖，不能将相似重述解释成已证明的因果影响，也不能推断跨轮持续性。

metadata仍为interpretation、semantic_correctness=not_established、new_independent_external_evidence=false、adoption_eligible=false。Goal回执不算ExecutionObservation。ActiveGoal始终null，无Memory Admission、可信来源提升或新权限。

**候选内容语义污染已发生；未观察到正式权威提升。非权威不等于不会影响后续认知。** 合法性校验工作正常不能证明主体归属或解释为真。

请求4的Goal块由此前1425字符增至2193字符，历史Goal回执1210字符；每次工具定义1568字符。这些是字符数，非精确Goal Token、有效bit或支持度。重复投影/自产解释不作为新增独立观察。

## 4. 后续覆盖与停止原因

| 冻结轮次 | 研究事件 | 状态 |
|---|---|---|
| B2 | 取消Intel Task、保留宽范围 | NOT RUN |
| B3 | 未来Path变现金流、不恢复已取消Task | NOT RUN |
| B4 | 当前澄清投资方法、纠正旧解释 | NOT RUN |
| B5 | 新方向未明确并行/替代 | NOT RUN |
| B6 | 明确新增财务教学、旧方向保留 | NOT RUN |
| B7 | 原投资方向改为财务数据核验、教学保留 | NOT RUN |
| B8 | 缺资料产生待办、不改用户目的 | NOT RUN |
| B9 | 方法/教学样本核验及下一步条件 | NOT RUN |
| B10 | 候选/Observation状态读回 | NOT RUN |

用户当前澄清与历史心理真值、并行/替代、取消Task与withdraw宽范围、更新后的后续行为，本轮均未获得B证据。不以A7文字纠正或旧form→withdraw实验补齐。

B1后研究者核验真实记录写入seed-review.json pass=false，触发预登记研究准入停止。它不是正式Runtime的候选拒绝/删除/修订器。驱动“Two valid seed scopes not established”和控制器“Study process failed”原文保留；属于研究门禁未通过，不是UAEA崩溃、传输中断或资源失效。没有修改脚本、候选、温度或重复测试追求PASS。

## 5. 安全、版本及复核入口

B对话窗口155条有效样本：NVML峰25.970GiB，Shared0.132GiB，Commit最低余量30.252GiB、距停止线11.955GiB。

完整模型服务1382条、Guard全流程1388条有效采样，加载及运行峰值：
- NVML28.556GiB；PDH Dedicated28.444GiB，Shared0.173GiB。
- CommitLimit91.481GiB，最低剩余27.888GiB，距原20%停止线9.591GiB。
- Windows Available最低35.481GiB；WSL最低17.615GiB；Swap峰0.011719MiB。
- 服务因果样本年龄最大0.119秒；1488条AC样本均有效在线。
- AC准入CPU10反例拒绝；原Guard smoke故障测试是预期保护验证，不是真实资源越界。

原守卫目录：/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261112T032134Z-963f0032。两侧UTC、单钟确认、序号/nonce、NVML/PDH与停止原因保留。模型服务由本轮控制器正常清理：primary_sensor_failure=null、remaining=[]；Native两进程组、模型、遥测和AC观察器退出，8000/8003无监听。

final-audit.json证明220输入锁、131冻结/当前执行源码、15正式启动/安全原件未变。正式Runtime/数据库/Schema/权限、人工入口没有本轮修改，原工作树保留；仅隔离研究驱动/审计/证据及文档新增，不Commit/Push。

审计优先：
1. B-scenarios.json、scenario-provenance.json、preregistration.json。
2. B/evidence-index.json：B1原生行10–443，调用60/66，最终正文436。
3. B/goal-events.jsonl行1/3及goal-research-state.json。
4. B/model-http-audit.jsonl、streams：请求4和完整响应。
5. B/goal-audit.json、seed-review.json：结构事实与语义审查分开。
6. analysis/B/answers.json、final-audit.json：真实回报/正式边界/资源。

## 6. 六项架构回答

| 问题 | 独立判断 |
|---|---|
| 定义是否足够准确 | DESIGN INTENT清楚：用户希望实现的结果/方向；模型落实PARTIAL。本次目的与工作/操作混合，不等于定义必须换架构 |
| User Goal/Agent To-do要独立正式对象吗 | 语义身份必须分开；当前无证据要求新增正式对象。来源、版本、Observation可复用。subject=user字段也不能保证识别正确 |
| Task/Path/Goal关系要调整吗 | 不宜强制同生命周期/一对一；有限范围结果可作为实验解释。取消Task不能机械撤回宽Goal，但本轮维护NOT RUN，不宣称能力验证 |
| Sideband足够吗 | VERIFIED可表达宽/窄Scope、提交及投影；忠实语义与演化闭环PARTIAL/UNKNOWN。没有无法表达目的的结构证据，不支持替换接口或第二Loop |
| 进入数学建模吗 | 可研究可观察变量、Scope与解释修订的形式化；暂不建熵/bit/概率阈值或复杂动态模型。当前最小缺口是忠实种子与可审查维护行为，不是缺方程 |
| 相比Relevant History有增量价值吗 | UNKNOWN。未运行匹配新对照，旧30轮输入不同；有Context/状态维护成本，无真实新增收益证据。错误记录的研究价值不等于正式机制价值 |

## 7. 下一项最小研究建议与停止边界

本次取得完整可追溯的负面路径：用户目的→真实quote→附加Agent工作/操作→保存→成功Context→回答重述。**没有取得正确的生命周期闭环。**

保留现有Sideband、Relevant History及全部权威边界。建议评审后开展一个预登记、至多一次反馈机会的语义纠正实验：把本次真实错误候选反馈原模型，指出查询/保存属于工作或操作，观察模型是否通过现有revise保存忠实目的，并在下一用户轮正确使用。它是受反馈纠错，不叫自主发现/自然形成，不由Runtime删词或研究者伪造种子；失败保留，不反复调提示。

先取得两条语义合格、真实模型提交的种子，再继续本次冻结的生命周期。无需用户确认私人投资Goal。若仍失败，保留模型提案质量负面证据，不新增Goal引擎/通用语义裁判。不同Backend后续可独立比较，不为Bolt固化协议。

本轮停在语义准入与阶段评审节点，不安排人工长会话、不自动新批次。Memory继续Research Reserved；Retention不等于Adoption。


## 后续评价澄清（2026-11-12，v2；不改写原运行）

此前清洁种子准入是本次研究的严格方法选择，原停止、调用、保存和NOT RUN事实保留。
不将“包含额外文字”自动等同整个候选无效：目的/范围扭曲、手段混入与无害背景冗余分别评价。
旧长期候选保留了有依据的AI投资目的，同时混入Agent查询/保存操作；不直接断言核心目的已被替换。
局部候选中的真实财务背景不因出现数字或方法就自动有害。
新研究以三个独立标注维度及真实当前种子检验一次受反馈纠正，不能用孤立对话指定生命周期。
用户当前澄清支持更新解释，但不是对所有过去心理状态的客观证明。
