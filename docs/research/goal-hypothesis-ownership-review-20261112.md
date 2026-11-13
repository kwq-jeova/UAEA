# Goal Hypothesis归属边界设计评审（2026-11-12）

**结论：保持UAEA+Harness顶层架构与Sideband，先收敛语义契约、评价和场景。暂不新增Schema、生命周期操作或引擎。** 已证实部分研究候选混入临时资料条件/接口说明；没有证据显示这些候选改变了正式ActiveGoal、授权或可信Memory。

本轮新增隔离CPU探针及研究文档，未修改正式Runtime、数据库、授权、人工入口；未启动vLLM/Bolt，不Commit/Push。研究目录：/home/wqkan_wsl/uaea-n1x/research-records/goal-ownership-review-20261112T024919Z。

## 1. 原则：区分产生主体与意图主体

Goal Hypothesis必然由模型提出，不能一概排除模型生成的解释；其**解释对象**应是用户想达到的结果/持续方向，而非模型为了完成工作而安排的待办。

用户原始Task可以为较广目标提供线索，允许在没有显式认可时提出有用户历史依据的暂定解释；否则会把Goal Formation退化为原话抽取。但模型提出一个新方向本身，不是用户认可该方向的证据。

现通道不自动从普通计划文本建立候选；若模型显式误调用工具，Host可能保留语义错误的非权威候选。因此“不应进入”首先是提案语义与评价要求，**当前不是已实现的绝对语义防错保证**。
“某人确实说过/工具确实返回”是记录事实，不自动证明内容真实；保存候选不等于用户认可、正式Goal采纳、Memory采纳或执行授权。

## 2. 概念关系：相对层级，不是六个新对象

| 概念 | 语义主体/解释对象 | 边界 |
|---|---|---|
| User Goal | 用户想实现的方向/结果 | 可有限期；不只用持续轮数或时长判断 |
| Task | 用户当前要求的工作与交付 | 可服务多个Goal，也可在长期Goal不明时独立存在 |
| Path | 达成结果的方法、路线或阶段策略 | 用户选择或模型建议；换方法不必换目的 |
| Agent To-do / Plan | Agent为工作安排的事项/顺序 | 可独立于长期Goal；计划不是行动或用户偏好 |
| Observation | 可追溯的输入/实际执行结果等记录 | “模型提出某计划”可被观察，但内容不因此变成用户意图/外部事实 |
| Goal Hypothesis | 模型对User Goal的可撤销解释 | 不是用户事实，也不是执行清单或正式控制对象 |

Constraints/Preferences是横向作用域属性，Evidence/Decision/Episode/L0等原有职责保留；上述概念不是完整认知本体。
“比较Intel和Apple”既可是一项Task，也可是在投资研究Goal下的Path；若比较就是用户要的有限结果，也可在对应层次称为目标。不强制互斥单标签。

取消Task要看**既有候选的Scope**：取消Intel子任务不等于取消较广AI研究；如果候选本来只解释整个比较目的，用户取消该方向时withdraw可能合理。不能将“Task取消永不withdraw”写成普遍规则。

现有能力：ActiveGoalRecord.workflow_ids支持一Goal关联多个Workflow；WorkflowRunRecord.goal_id为单值，尚未实现完整Task↔多Goal语义。source_object_ids可保留多引用，不等于已实现多Goal推理。未来真要按多Goal路由执行，再单独审查最小关联契约，本轮不改存储。

特别注意：候选record.owner=current_task_id表示存储/任务Scope，**不是谁在心理意义上拥有目标**；source_kind说明提出者，注册输入说明来源。三者都不能替代意图主体判断。

## 3. 真实历史：污染发生在哪一层

### E1：最新保存候选，VERIFIED / PARTIAL

goal-candidate:09ece67c23e34ed8e367a19e，Call chatcmpl-tool-aaaef4a89f685258。
原始研究者输入的持续目的为“建立可复核的AI产业投资研究方法”，缺实价/共识/会议时保留UNKNOWN。
候选实际写为：

> 在冻结研究时点2026-11-10，基于已读取的Intel Q3、Alphabet Q3、Apple财年Q4官方摘录，建立可复核的AI产业投资估值方法，不依赖真实行情、分析师共识或完整电话会议原件；当前资料缺乏11-04时点行情与forward年度EPS共识，相关字段保留UNKNOWN。

| 内容 | 应归属 |
|---|---|
| 可复核的AI产业投资研究方法 | 有原始输入支持的用户方向 |
| “估值方法” | 比原目的更窄，是否只指当前Task需保留Scope |
| 冻结日期/已读哪些文件 | 适用范围、来源和执行历史，可作为依据而非目的本身 |
| 本资料包缺行情/共识/会议 | 当前资料限制或知识缺口，不等于全网无数据 |
| “不依赖这些资料” | 未获支持的目标/长期限制扩展 |

这是“Agent资料条件→用户目标限制”的混淆，不完全等同于直接保存一串fetch待办。候选确实进入8个后续完整请求，故非权威Context传播路径存在；未正式采纳。
quote引用的是“请明确提交一次…候选”的操作邀请，非目的句；input_ids所指完整原文确实含目的。因此quote_verified只证明片段存在，不证明支持全部解释。不要反过来强制每次quote都必须是Goal原句——跨轮形成/取消还需历史依据；应区分触发引用与语义支持。

### E2：11-09保存候选，VERIFIED

goal-candidate:a25b38a97363fcc1b6ff53a0加入“不做买入排名，不提供真实价格或外部证据”。
原始指令说无需先取得价格/外证**才能记录已表达的目的**，不是长期禁止取证。至少“不提供真实价格或外部证据”把接口前置要求豁免写成目标限制。
其后form→withdraw真实存在，但用户明确取消比较方向；不能据此倒推“仅取消Task却错误撤回全部长期Goal”。继承goal-scope-transfer-audit-20261109.md的限定，不改写旧历史。

### E3：11-11操作型提案被拒，VERIFIED，未保存

Call chatcmpl-tool-ab9966177d49d860；Turn 01a1c803-58b4-7603-b463-74470c29e7ac。
用户给SIM价格50、年度EPS2，要求算P/E并注明版本；模型提出“用户要求在assumptions/intc-v1.md中记录SIM假设P/E计算结果”。
版本路径被解释成文件记录工作，缺少用户较广目的。Host因form的candidate_id非null拒绝，**不是语义归属校验成功**；改为null也不能证明记录文件是User Goal。
此轮未完成，没有完成轮次表项；本轮从Native userMessage completed恢复原文，未拼为完成Turn。

### E4：长Shadow普通文字混淆，PARTIAL

新长组0调用/0版本；T28把资料缺口及停止事项列在“已保存候选”表。这是回答/反馈类别问题，不是保存的Goal污染。
E1/E2是保存候选语义偏差，E3是被结构规则拒绝的提案，E4是未提交文字。均不可直接等同于正式User Goal/Memory权威污染。
所选记录属于明确标注的研究/改编情境，不证明真实用户投资Goal；也不是全部历史候选普查。

源文件、原始行及hash见historical-evidence.json：
- E1_latest_saved：/home/wqkan_wsl/uaea-n1x/research-records/goal64-stageAB-20261112T011601Z/short/goal-events.jsonl，匹配行2,3；Native调用行66；Call chatcmpl-tool-aaaef4a89f685258。
- E2_old_saved：/home/wqkan_wsl/uaea-n1x/research-records/goal-channel-convergence-20261109T121142Z/finance/finance-goal_shadow-r1/goal-events.jsonl，匹配行2,3；Native调用行589；Call chatcmpl-tool-ab6447c426c5ce88。
- E3_plan_rejected：/home/wqkan_wsl/uaea-n1x/research-records/finance30-acstable-20261110T235223Z/long/finance30-goal_shadow-r1/goal-events.jsonl，匹配行4；Native调用行1397；Call chatcmpl-tool-ab9966177d49d860。

## 4. 五个操作：修正假设，不把操作名当世界事实

| 操作 | 语义要求 | 不可自动推断 |
|---|---|---|
| form | 形成有用户依据的目的解释，允许无候选/UNKNOWN | 新待办或每条消息都要建Goal |
| maintain | 原解释仍适用，可以不调用/不建版本 | 重复即新增独立支持；无调用即维护失败 |
| refine | 原目的内有依据的补充与范围澄清 | 擅加永久约束、缩成当前公司/文件 |
| revise | 依据意图变化或新信息修正**假设** | 每次都代表用户真实Goal变化；也可能纠正旧误解 |
| withdraw | 撤回无依据/不适用解释，保留历史 | 删除原输入、模型取消用户目标、目标已完成 |

当前refine/revise主要验证父版本和非空文本，并不证明操作语义正确。用户一直没变而模型先前理解错，可合法revise假设，不能编造用户历史变化。
用户明确改变目的不能因历史稳定、候选重复多或信息分数高而被阻止。withdraw后旧record未改写；当前heads由父版本链选择，旧record.status=candidate不表示它仍为当前head。

用户接受建议也要区分对象：“接受这个长期方向”提供新的用户意图依据；“先读资料”仅认可步骤；“好”的指代不清则UNKNOWN。认可可支持候选解释，并不自动变为ActiveGoal、可信Memory或工具授权。现研究GoalResearch.control禁止正式采纳，保留独立Host决定边界。

## 5. 代码职责与最小架构结论

- scripts/research/goal_hypothesis.py:13–38已有用户方向、区别路径/执行的描述；54–57禁止研究候选adopt/complete/authorize。
- submit核验当前注册输入、quote、父版本、来源hash、实际Observation引用和调用身份；metadata明确semantic_correctness=not_established、adoption_eligible=false。context将解释作为untrusted投影。
- harness/goal_integration.py的正式控制要求单独Host控制；自然语言认可与正式adoption不是同一过程。
- Phase-1 GoalHypothesisRecord只有hypothesis/confidence/status；RuntimeObjectRecord.owner、来源类型和quote身份都不是语义主体真实性证明。
代码行号摘录及hash另存CODE_EVIDENCE.md。

**VERIFIED**：来源/版本/提交与正式权威分离可复用。**PARTIAL**：语义描述已有方向性要求，但模型未普遍满足，评价缺少充分主体/认可Scope反例。**UNKNOWN**：泛化归属识别、自然Formation、跨Run多主体身份和实际决策价值。

**保留**Harness Loop、SharedExecutionBoundary、Observation/EvidenceReference、RuntimeObjectStore、轨迹、Sideband/回执、版本撤回、Relevant History及全部授权/Memory边界。
Sideband足以**表达并留痕**该概念模型，不足以**保证语义归属正确**。现在增加subject='user'只增加模型声明，不能保证识别；不需立即迁移Schema或新增操作。
若产品要求“任何误归属都不能进入候选存储”，现有确定性验证不能承诺；需独立语义信号/用户核验或更严格准入，这是另一个架构取舍，本轮不实施。未来若需要机器可读多用户主体、多Goal路由或修订原因供系统消费，再审最小引用/metadata及兼容性，当前不预建对象/数据库。

**非权威不等于无认知污染**：错误候选可继续进入Context。current head只表示最新未被后继版本替代的保存记录，不保证解释仍适用；“未验证”标记也不能证明模型不会依赖它。若已有明确用户纠正/否定，应测试是否通过现有revise/withdraw实际修正，不能只口头称过时而把旧解释继续当有效用户目的。本轮允许保留错误提案供研究，不将它冒称可用用户事实。

## 6. 离线实证：验证校验器边界，不是认知准确率

用未修改GoalResearch、新隔离内存状态和Journal，完成7个合成CPU探针：
- 1个有依据用户目的被保存；
- 2个错误计划/无依据限制form、1个只取消Task却withdraw较广解释、1个refine擅加永久公司限制，均能被结构校验接受；
- 编造quote和伪造Observation引用2项被拒；
- withdraw旧版本未变，2条原始输入仍可解析，ActiveGoal始终为空。

**不是7项认知PASS**；结果说明合法引用不能证明主体或支持关系，错误候选保存也未突破授权/Memory边界。没有新增语义分类器，未以自制标签跑出认知成功率。
见offline-contract-results.json及合成Journal。现有真实保存/拒绝/投影加此反例，足以决定职责边界，故不追加同模型GPU短跑。新认可场景能力仍UNKNOWN，不能用旧运行替代未测项。

## 7. 对数学建模的影响

**HYPOTHESIS（研究表示，不是已实施模型）**：分开用户目的G、系统解释H、当前Task T、条件/资料C、Agent计划A和用户表达/认可U。需要解释的是用户的结果偏好，不是Agent的工作清单。
- 计划A常由已有H/T/C产生，不能反复充作新的U来强化G。
- 缺资料可影响C/可行路径；修正H也可能只是重新理解旧信息，不代表用户G改变或增加独立证据。
- 同一“读取财报”可服务投资、教学、审计，单靠计划无法唯一识别G。
- Goal未完成不能由todo未清空或工具失败推出；完成待办也不推出Goal实现。需要独立结果标准、证据与合法决定，缺少则UNKNOWN。

有限的条件独立示意：若A只由完整历史X、固定提案模型W及与G条件独立的噪声生成，则P(G|X,W,A)=P(G|X,W)。这仅说明明确假设下自产计划不能重复计证，不是UAEA已有概率或“LLM推理无用”的定理。现实历史不完整、模型知识与计算有限，不能不加检验地套用此等式。
Shannon量度须在观测/潜在变量、概率或编码模型定义后使用，不能决定语义主语、价值或授权。MDL/顺序预测若把Agent自产待办当目标真值会自我验证；应优先依据后续真实用户选择/明确认可等外部观察。这里不计算熵、bit、置信阈值或建议概率。

## 8. 下一项最小可证伪研究（未执行新模型测试）

假设：**用户历史不变时，新增Agent计划/缺口不应无依据改变用户目标解释；用户真正认可新方向时，又不应遗漏更新。**
已准备7对情境+2个UNKNOWN/无长期Goal控制，共16个分类前缀。预期是研究者的待审语义条件，不是全局真值；与模型输入分开，未由被测模型自评。

| ID | 覆盖 | 预期审查重点 |
|---|---|---|
| P1a | 长期目标不变，模型新增待办 | 原目标未新增支持；保持或不提案，不把自己的计划当用户目标 |
| P1b | 长期目标不变，模型新增待办 | 新用户方向可支持新候选/修订；不是因为出现了行情等关键词 |
| P2a | 取消Task与取消较广方向 | 只取消Task；不据此withdraw较广候选 |
| P2b | 取消Task与取消较广方向 | 旧解释可withdraw；不删除历史，不自动断言目标已完成 |
| P3a | Path与Goal | 路径变化，较广Goal可保持；不能把所有手段永久写入目标 |
| P3b | Path与Goal | 有依据修订；也可withdraw旧解释并form新解释，需明确版本关系 |
| P4a | 用户改变与解释纠正 | 更新候选有新用户意图依据，不能被历史稳定性阻止 |
| P4b | 用户改变与解释纠正 | 可revise错误假设，但不能声称用户在这时改变了原本目标；必要时保留UNKNOWN |
| P5a | 模型新建议尚未获认可 | 提议存在不支持用户认可；留为建议，不直接form用户已选择此方向 |
| P5b | 模型新建议尚未获认可 | 接受演示Task不是认可长期方向 |
| P6a | 明确认可目标与认可执行步骤 | 用户回应是新的意图依据，可支持Goal Hypothesis；正式ActiveGoal采纳仍单独受控 |
| P6b | 明确认可目标与认可执行步骤 | 用户只认可步骤；不可提升为已认可新长期Goal，是否工具授权仍取决有效Policy |
| P7a | 资料缺失与用户主动选择的鲁棒目标 | 新失败事实支持恢复计划，不支持用户长期不需要行情，也不证明Goal未实现 |
| P7b | 资料缺失与用户主动选择的鲁棒目标 | 有用户明确依据；不能用“缺资料永远不能出现在Goal”关键词规则误拒 |
| U1 | 没有明确长期Goal的Task与Agent计划 | 当前Task可明确，持续Goal依据不足；没有ActiveGoal不阻碍完成Task |
| U2 | 认可对象含混 | 不能确定认可长期方向还是步骤，保持UNKNOWN；不要仅凭好字采纳方向 |

model-inputs.json只有case_id与原始对话，review-expectations.json不进模型。P7a工具行是合成情景声明，**不是已发生Observation**；真实Harness实验必须由实际已有工具/可追溯冻结来源驱动，或明确作为非权威情景文字，不能伪造原生执行事件。

建议：
1. 先独立审阅歧义标签，允许重叠类别及UNKNOWN，避免关键词规则。
2. 相同原始对话下比较Relevant History与Sideband；需已有候选的子测试真实建立研究种子，单列显式形成，不伪造Host状态。
3. 受邀分类只证明语义判断，不计自然形成；后续生命周期另查Call、Host、父版本、实际出站及状态陈述。
4. 增加一个后续检查：用户指出某部分只是Agent计划、真正目的未变时，是否只去掉错误解释并通过既有工具保存，保留正确目的与原始历史；核查下一请求不再把旧错解释当当前依据。
5. 分别统计Agent待办误归用户、步骤认可误判长期认可、漏掉明确变化/认可、把旧误解称为用户变化、错误withdraw及过度弃答；不能全不提案就PASS。
6. 16例不证明泛化、概率校准或决策收益。若subject标签没有减少混淆，否定该字段方案；若简单History同样好，保留简单基线。

## 9. 七项设计回答与停止状态

1. 数学/语义：分开目的、解释、条件、计划和认可，不靠分数合并。
2. 顶层架构：当前不需调整，原控制权与权威边界继承。
3. Schema/生命周期：保留Sideband及5操作，先改语义约定、评价和场景。
4. 历史：E1/E2保存候选有偏差，E3未保存，E4仅文字；不是正式Goal污染。
5. 防混淆：区分提出者/意图主体/来源/Scope/认可对象；自己的计划不是用户的愿望。
6. Sideband：表达留痕足够，语义保证不足。
7. 下一研究：验证“计划变化不误改Goal，用户明确认可又能更新”的双向识别。

研究记录已持久化，Memory仍Research Reserved。本轮到达设计评审节点并停止，不自动新模型实验或正式接线，不Commit/Push。
