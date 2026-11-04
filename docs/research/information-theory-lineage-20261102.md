# Information Theory / Information Lineage 基础研究（2026-11-02）

Status: RESEARCH / NOT AN ARCHITECTURE DECISION  
Review: **Research Baseline PASS**（用户顶层架构审计，2026-11-02）；**正式架构实施暂缓**。  
此PASS仅确认研究基线及边界整理，不提升理论假设或Runtime能力的证据等级。
范围：源码、历史与既有轨迹只读核查，理论资料研究及文档整理。未实施算法、未启动模型或新增实验。  
主仓库：`122040dde1bf75b9d9eabd3ed00236cf8a1375e0`；冻结 Runtime：`1f311291df027baceca40779643e5107b9eb6fb3`。  
P3.5/G0/G1依据当前**未提交工作树**，不能声称上述Commit已包含它们。本轮源码哈希和Diff另存审查记录。

## 1. 研究起源、结论及分级

用户提出：Goal、Intent、Context、Evidence、Memory、Workflow可以分别采用信息论模型，
共享可追溯身份、来源及依赖。“1000 bit / x bit”表达长期结构稳定而可修订的直觉，
不是实测信息量、证据强度、目标重要性或正式采纳阈值。

结论分级针对 **UAEA能力与应用判断**，不是将成熟数学定义当猜想：
**VERIFIED**=代码/旧运行记录支持的限定事实；**DESIGN INTENT**=历史设计意图；
**HYPOTHESIS**=待检验设想；**UNKNOWN**=缺少模型/数据；**CONFLICT**=某种应用违反边界，
不等于断言现有代码已有该缺陷。

| 判断 | 分级 | 取舍 |
| --- | --- | --- |
| Goal作为解释多轮交互的稳定潜在结构 | HYPOTHESIS | 值得研究，但目的、世界事实及合法状态不同 |
| 六个方向共享一个bit总分/阈值 | CONFLICT | 不同变量、编码模型、效用不能直接相加 |
| 现有对象承载了多数来源引用 | VERIFIED | 具备局部来源、调用、Observation、候选、决定和内容哈希 |
| 已有全局完整血缘、独立证据计数 | UNKNOWN | 未见跨全部对象的统一身份/版本/关系约束 |
| 暂不建Information Pool，先研究引用约束 | HYPOTHESIS / 建议 | 现有存储可复用；没有新增中心状态的收益证据 |
| 信息论得分自动采纳Goal/Memory或授予权限 | CONFLICT | 数值只能辅助候选比较，不能替代合法决定 |

“共享依据，不共享结论”需要限定：**可以引用其他模块的解释及已采纳状态，
但不因引用而继承其采纳权或改变其语义类型**。Context需要读取ActiveGoal，
不因此获得修改Goal的权力。禁止共享解释本身会重复推理，也与当前投影冲突。
共享引用须保留所有者、来源、作用域与可见性；不是全模块无条件读取原文。

## 2. 理论候选与数学边界

以下公式是研究定义候选，不是当前UAEA已有算法。外部资料见§10；
对UAEA的适用性取舍是本轮独立评估。

### 2.1 Shannon、证据与Surprise

对明确随机变量/概率分布，`H(X)=-Σ_x p(x)log₂p(x)`；单次surprisal为`-log₂p(x)`。
文本长度、Token数、JSON大小、文件压缩率均不自动等于语义信息量。
复杂度、对某解释的支持、目标重要性、正式采纳权威必须分开。[T1]

比较H₁/H₀时，后验log odds增量是条件log likelihood ratio：
`log₂[p(o|H₁,D)/p(o|H₀,D)]`，而不是旧1000bit减新xbit。
简短信息可能高度区分解释；大量重复可能没有独立增益。
这需要先验、似然、观察单位及依赖模型，不能用模型confidence替代。

Bayesian surprise常为`KL(p(H|o,D)||p(H|D))`；它不等于事件surprisal，
也不等于每次都非负的“先验熵减后验熵”。某次观察可能增加不确定性。[T5]
条件互信息`I(H;E|D)`对可能观察取期望；单条网页不能直接给出可靠有效bit。
高surprise可能来自噪声、攻击或错误模型，不是来源可靠性证明。

**反例**：长期Goal后一句“取消这个目标”，不应因“信息不足”被挡住。
合法显式修订仍走现有控制边界；可以校验过期、来源和scope，但不应按累计分数否决。
环境证据推翻实施方案，也不自动取消用户愿望。

### 2.2 MDL / Prequential MDL / Zero State

静态两部编码可研究`L(G)+L(O|G)`。[T2]
最短Goal文本不等于最正确、重要或被授权的目标；“帮助用户”过于宽泛，
必须在指定预测问题中优于无Goal基准，不能只比字符串长度。

顺序策略C的示意分数为`L_pre(C)=-Σ_t log₂ q_C(o_t|o_<t)`。
C要预先规定初始化、更新、候选生成及模型/切换成本；观察o_t后产生的Goal
不能免费回填成对过去的预测。两部编码开销与已包含先验成本的混合编码也不能重复计入。[T2,T3]

Zero State必须区分运行状态、候选状态和实验对照模型，不能混用（见§2.2.1）；
无论哪种状态，都不等于“无先验/编码语言/模型族”。
LLM有先验及提示条件；G0/G1的low/medium/high不是q_C。
现有记录没有Goal条件校准似然、候选先验或编码器，因此真实MDL分数为**UNKNOWN**。
即便获取Token logprobs，也不自动等于用户意图/Goal后验。

避免闭环自证：用自己的回答、注入后复述及自己选择的搜索结果来生成并验证Goal，
可能只压缩模型自身行为。可先研究后续真实用户输入/任务关系等外部可观察项；
工具结果选择依赖策略，必须声明条件，不能假定IID。
“稳定且有解释力”是有价值的候选假设，不是长期Goal Formation已成立。

### 2.2.1 Goal Zero State：三个独立语义

以下是概念区分，不规定形成阈值、保留分数或采纳算法：

| 名称 | 含义及当前能力 | 不得推断 |
| --- | --- | --- |
| No ActiveGoal | 指定运行作用域没有正式采纳的活动Goal。**VERIFIED**：Phase-1 snapshot可为`active_goal=null`，G1对应`active_goal_id=""`；历史或候选记录仍可能存在 | 不等于没有用户任务、没有候选，或实验采用Null Goal Model |
| No Goal Hypothesis | 尚未形成值得保留的候选解释。**DESIGN INTENT**：描述候选层的缺席；**VERIFIED（更窄）**：当前只能查询指定scope是否有保留候选 | 零候选不能证明模型内部没有理解/潜在目的；Goal Off、未输出结构化提议、提议被拒或未保留，都可能造成记录缺席 |
| Null Goal Model | **HYPOTHESIS**：信息论实验中不使用长期Goal结构的对照模型/预测策略，必须预先定义其输入、历史范围及编码/概率规则 | 不是`active_goal=null`的别名，也不能仅以Goal Off或没有候选日志证明它成立 |

三者不是阶段顺序，也不能相互替代：没有ActiveGoal时可保留多个候选；
已有ActiveGoal时本轮可以没有新候选，但不能据此声称历史上从无Hypothesis；
某运行未采纳Goal，其实验仍可使用长期Goal候选特征，
所以不必是Null Model。反之，已有运行Goal的历史也可被用于Null对照，
前提是实验按预先声明的规则不使用长期Goal结构；这不要求删除/修改Host状态。

**用户明确提出的当前任务**是原始输入及其作用域内的行动要求，不须先变成长期Goal候选
才能被保留或依法执行。**推断形成的长期Goal**是跨交互目的的候选解释，
需要独立采纳依据，不能把当前任务自动升级为长期承诺。
Null对照仍须保留约定的当前任务、约束、授权边界及必要执行事实；
是否可使用其他历史需预先声明，不能把删光请求或删除安全约束造成的失败当成Goal收益。

**UNKNOWN**：当前尚无正式Null预测策略、校准概率或完整长期候选形成机制；
本节不是宣称已有MDL实验。以任一运行空值替代实验模型定义属于**CONFLICT**。

### 2.3 Intent Relation / Change Detection

可以研究`P(z_t|o_≤t)`作为延续/修订/切换的候选，不能与权威Goal状态等同。
变点检测需要似然、hazard/持续时间等假设。[T4]
临时离题后恢复、并行Goal、嵌套任务不等于单序列一次参数变点。
词面话题变化也不是Intent切换真值；当前规则式TurnRelation不是Bayesian State实现。

### 2.4 Context / Information Bottleneck / Rate-Distortion

IB研究压缩X为Z，同时保留关于任务变量Y的信息，例如`min I(X;Z)-βI(Z;Y)`。[T6]
Rate-Distortion还需失真函数、分布及成本约束。Y是什么、丢失一个来源/当前要求的损失怎样定义，
目前**UNKNOWN**。Token预算是工程成本，不是互信息；短摘要不必然更好。

可先在固定Token预算下测任务状态/来源保留和任务错误，无须估高维MI。
权限、合法Host决定及真实执行事实应独立保护，不能为降低平均失真而允许摘要创造权限。
原始依据留在Host、投影有界，不要求全部原文重复注入。

### 2.5 Evidence / Memory / Workflow

Evidence：条件信息提醒我们处理相关性；URL数量、Fetch次数、引用次数或confidence
都不能直接当信息增益。血缘帮助识别已知复用，不能给出未知依赖的联合分布。

Memory：MDL/信息价值可研究候选保留与检索收益；大量一致幻觉也很易压缩。
一次关键纠正、用户限制可能罕见而重要。压缩收益不是Admission，
不能绕过来源、适用性、隐私、有效期及撤回。

Workflow：PSR是动作条件未来观察的预测表示，不是JSON状态列表的别名。[T7]
没有充分统计/预测分布，不能声称现有Workflow具备PSR。
VOI比较获取信息前后的期望最优效用，再减行动成本；需结果概率、效用及合法行动集合。[T8]
无成本理想VPI的非负性不适用于有费用/失败/延迟的真实搜索。
高VOI不授予权限，也不决定任务已经完成。

## 3. 现有信息血缘能力与缺口

本节VERIFIED表示已读代码/已有记录支持，不等于本轮新增实验通过。
链接行号仅定位本次快照，未来以符号/版本为准。

| 对象 | 已有证据 | 缺口及范围 | 分级 |
| --- | --- | --- | --- |
| Canonical Trajectory | [TrajectoryEvent](../../harness/event_normalizer.py#L25)有thread/turn/item/event、provenance、raw引用；[writer](../../harness/trajectory_writer.py)保留事件 | 默认event_id=uaea-event-N（约L530），仅normalizer内递增，非全局身份；事件顺序不等于语义依赖 | VERIFIED；全局完备UNKNOWN |
| RuntimeObjectStore | [对象/投影](../../runtime/phase1-runtime/runtime/runtime_objects.py#L22)有owner/parent/source_object_ids/source_event_ids；Step关联Observation，Artifact有hash/来源 | 可变内存表面，非全局持久权威库；ID列表没有统一关系类型/版本约束，parent不能承担全部血缘语义 | VERIFIED |
| Execution/Semantic Observation | [两个类型](../../runtime/phase1-runtime/runtime/semantic_observation.py#L40)分离；SemanticObservation有source_observation_ids/source_artifact_ids/evidence_refs | frozen SemanticObservation无独立observation_id字段；understood_facts名称不证明事实；H3的semantic_observations列表不等于完整Phase-1语义推理 | VERIFIED |
| H3回执/重复回显 | [Host receipt优先](../../harness/semantic_state_adapter.py#L813)、[同call去重](../../harness/semantic_state_adapter.py#L907)、[Shared边界](../../harness/semantic_execution_contract.py#L209)保存决定/Observation | 调用身份去重不证明不同调用独立；进程内回执非崩溃安全exactly-once | VERIFIED |
| Evidence/Model Claim | [source_inventory/ground_claim](../../harness/evidence_provenance.py#L16)区分发现/获取/摘录/来源关联；[Claim](../../harness/evidence_provenance.py#L129)标为unverified/interpretation，可标compaction_derived | execution-grounded、source-linked、content-supported分开，内容支持不自动评估；可见不等于使用，历史claim依赖列表未全路径自动填充 | VERIFIED |
| Projection/Compaction | [来源列表](../../harness/semantic_state_adapter.py#L1180)、[Bridge快照与恢复](../../harness/responses_bridge.py#L180)、[请求审计](../../harness/request_audit.py)有块/消息hash | 块级部分有界来源，不是逐句完整依赖；脱敏审计非原始wire bytes；摘要断言血缘未完整 | VERIFIED；完整语义恢复UNKNOWN |
| G0/G1 | [GoalIntegration](../../harness/goal_integration.py#L102)包装Phase-1候选，关联注册输入、模型事件、请求hash；[控制](../../harness/goal_integration.py#L183)独立保留控制/决定 | [ActiveGoalRecord](../../runtime/phase1-runtime/runtime/runtime_objects.py#L99)的source_goal_hypothesis是文本，精确候选ID关联靠G1 sidecar决定；长期自动演化未实现 | VERIFIED |
| Phase-2B Candidate/SQLite | [EvidenceReference/MemoryCandidate](../../memory/candidate.py#L54)；[Source SQLite](../../memory/sqlite_store.py#L117)有会话节点、Web access、内容引用/hash、候选→来源trace | 结构校验只检字段，不证明支持；有限source_kind，未知trace返回None；未见H3/G1接入自动Memory Admission | VERIFIED |
| 时间/版本/权威 | 多处有created/updated/accessed_at，content/excerpt/request hash；G1决定有before/after hash，执行契约有policy/input/workflow引用 | 无覆盖全对象的统一版本/有效期/authority-ref；记录/访问时间≠发布时间/content_period，owner字符串≠ACL | 局部VERIFIED；统一约束UNKNOWN |
| 独立证据/同源转述 | 同call和部分内容复用可识别；历史地图要求不重复计权 | 无全局依赖闭包/相关性模型/统一信息权重，不能把未知依赖当独立 | DESIGN INTENT / UNKNOWN |

冻结Phase-1的ensure_active_goal等不是G1权威校验器。
当前保护在Host接入边界，不能由对象字段存在推断全部旧路径具相同契约。
本轮不改冻结API，不恢复Agent Loop。

SQLite已经是Source/Evidence历史层，不能忽略它或直接改名为Information Pool/最终Memory Store。
[原闭环文档](../current/evidence/sqlite-source-evidence-closure.md#1-closure-position)
区分来源存储、fixture Candidate与未实施Memory Policy。当前代码已有web_access_event引用，
历史文档较早的source_kind列表不是现状全集。

## 4. Information Lineage候选共享约束

**HYPOTHESIS，供评审；不是冻结schema/API，也不是本轮实施任务。**
先采用已有对象间的可解析引用及明确关系；原文、Observation、解释、决定留在各自所有者处。
不另设全局truth/importance/active-goal中心，不预设新数据库/图谱/Runtime Layer。

| 概念 | 候选约束 | 复用及限制 |
| --- | --- | --- |
| Identity | 生产者/运行命名空间+对象种类+ID；可变对象还需版本/状态指纹 | run manifest、thread/turn/object；不能跨run只用uaea-event-N或裸URL |
| Provenance | 谁产生/观察、Host入口/模型输出、经哪项活动、原始记录位置 | source_event_ids、raw引用、Host input origin；role=user不是人类来源证明 |
| Dependency | 区分derived_from、observed_by、available_in_context、asserted_supports、adopted_by_decision | 已有ID列表/metadata可承载，但这些边并非都已实现；可见不能写成模型实际使用 |
| Derivation | 输入引用、摘录/截断/压缩/推断类型、已知变换/范围及输出版本/hash | 模型添加的新推断标为解释，不能假装纯复制 |
| Scope/Time | 原始任务/输入、生成/访问/来源声明时间及适用期分别保留，未知不填造 | owner/workflow/time；摘要不能扩大scope；跨系统时间不自动证明因果顺序 |
| Content Reference/Hash | 区分原始字节、文本、规范化文本、脱敏视图、供给片段，注明encoding/范围 | 各类hash不可互换；一致性不证明真实性、理解或授权 |
| Authority Reference | 引用既有采纳/执行决定，消费方校验类型、主体、scope、状态及允许的效果 | G1控制/决定、policy引用；候选自填ID或字段存在不产生权利 |

身份不等于内容hash：同文档可有多次有意义访问/版本观察；同字节不同事件不能全抹掉。
同一事件的Raw、Canonical、回显及摘要也不可算四份独立证据。
可变对象只解析到“最新状态”会让历史推论静默指向未来版本，必须区分引用时版本。

**不新增通用权威传播规则**：已采纳Goal是任务目的，不是世界Evidence；
Evidence可支持Memory Candidate，不因此完成Admission。各权威领域没有单一可信度总阶。
派生视图不能自行增权；新权威只能来自独立合法决定，不复制“最高父节点权威”。

### 4.1 去重与依赖能证明什么

1. 同调用/Observation的副本保留各自记录，关联同一活动，不能重复当独立观察。
2. 转述/摘要/Compaction保留派生链；新record_id不增加独立支持，历史模型claim仍为解释。
3. 同URL/hash只提示复用/版本，不证明独立或完全等价；多站可转载同一公告，
   重访也可能有“来源仍未变化”的时效价值。
4. “已识别重复后的来源族数”不是独立样本数/有效bit。没有记录依赖≠独立，未知保持UNKNOWN。
5. 血缘可证明记录可追溯、执行发生、版本匹配或显式冲突记录；
   不证明语义支持、真伪、因果、理解、授权或完成。发现URL、完整页面、供给摘录、理解须分开。

数据处理不等式可作启发：在`H→E→Z`成立时，纯派生Z不增加关于H的互信息。
但模型摘要若使用其他上下文/额外先验，未必满足此Markov条件；
不能把它当任意摘要的真伪定理，也不能把模型新推断升级为来源证据。

### 4.2 Information Dependency 与 Semantic Support

这里只澄清§4已有关系名称，不新增关系类型、支持度计算或验证引擎：

| 关系 | 可以表达 | 不能由此证明 |
| --- | --- | --- |
| `derived_from` | 某记录经摘录、压缩、变换或推断来源于另一记录；注明已知变换及版本 | 派生保真、结论被原文支持、真实性或新操作权限 |
| `available_in_context` | 某版本/片段位于实际模型请求供给中；仅准备投影不足，脱敏或传输证据缺失须注明范围/未知 | 模型实际关注、理解、采用，或其结论获得支持 |
| `asserted_supports` | 某可识别主体声称材料支持某结论；应可追溯声称者、材料及结论版本 | Host已独立确认支持，更不等于内容真实；模型重复自评不能自动升格 |
| `adopted_by_decision` | 合法主体在有效scope内经独立决定完成特定状态采纳 | 世界事实因此为真、其他状态同步采纳，或工具权限自动扩大；边本身不取代决定合法性校验 |

**来源关联不等于语义支持；语义支持不等于真实性；真实性也不自动授予操作权威。**
例如准确引用一篇含错误信息的文章，首先只能证明文字匹配；即使另经独立核验确认
该文支持所引用结论，也不能仅凭支持关系证明文章或结论真实。
即使事实为真，操作仍须合法授权。
采纳Goal确认的是任务目的/状态，不是采纳其涉及的所有世界断言。

- **已知依赖**：有可核查的活动/记录版本证明派生或供给，例如Host实际摘录及出站审计。
  现有局部能力为**VERIFIED**；它不自动成为support边，也不保证穷尽所有依赖。
- **未知依赖**：缺父来源、供给证据或版本关系；维持**UNKNOWN**，不是独立、无关或不支持的证明。
- **经过独立验证的支持关系**：作为**DESIGN INTENT**，须能追溯独立于原声称的核验依据、
  核验主体/方法、材料与结论版本、范围及限制。它不是新边类型，也不要求新增第二模型。
  只有已完成的特定核验可在其范围内标为**VERIFIED**；不能泛化为全部语义/事实验证通过。
  精确字符串匹配仅验证匹配，不自动验证整体语义支持；同一模型重复原结论不自动算独立核验。

现有`ground_claim`明确保留`content_supported=not_assessed_requires_semantic_judgment`；
因此全自动支持判断仍为**UNKNOWN**。不能把字段关联、hash一致或决定存在升级为已验证支持。

### 4.3 跨运行 Identity、Version 与 Validity

本节是语义要求及能力缺口，**DESIGN INTENT**，不规定统一ID、字段Schema或新存储。
必须分别回答“哪个对象”“当时哪一状态”“何时观察/记录”“当前是否仍适用”；
同一ID、内容未变、仍可读取，都不能单独回答有效性。

| 维度 | 现有证据与能力 | 仍缺什么 |
| --- | --- | --- |
| 跨Run/Session身份 | **VERIFIED**：对象UUID、run manifest、thread/turn及raw引用提供局部定位；默认Canonical事件ID仍可能在另一个normalizer重复 | **UNKNOWN**：跨run统一解析、导入后的同一性及可见范围；不能把Session路径或重复裸ID当稳定对象身份 |
| 可变对象版本 | **VERIFIED**：G1 revise更新同一`goal_id`对象，决定有before hash/after snapshot及控制/候选引用；`updated_at`只标更新时间 | 无通用按历史版本读取API；裸`goal_id`只找到当前对象，hash也不是完整历史内容或认证签名 |
| 观察/记录/适用时间 | **VERIFIED（局部）**：raw observed_at/emitted_at、Web accessed_at、对象created_at/updated_at分属不同阶段 | 原始观察时间与Host记录时间须分开；适用期未知就未知，不能拿访问/记录时间代替。源发布时间与内容所属期也各自保留 |
| Revision/Supersession | **VERIFIED（限定）**：G1决定记录revise/switch，修订保留ID，切换创建新Goal并suspend旧Goal | suspend不等于永久superseded；没有通用、跨会话的revision/supersession历史关系契约，不能据此宣称完整演化 |
| 旧引用的稳定解析/有效性 | **VERIFIED（更窄）**：已有决定日志可保留部分历史状态依据，checkpoint恢复还要求原始Host请求/控制/决定已存在 | **UNKNOWN**：跨会话任意旧版本的稳定读取/冷恢复；当前有效、曾经有效、失效/撤回和历史可追溯性须分开 |

代码依据：[G1 revise/switch](../../harness/goal_integration.py#L219)、
[决定与原始控制](../../harness/goal_integration.py#L260)、
[受原始账本约束的恢复](../../harness/goal_integration.py#L319)及
[ActiveGoal字段](../../runtime/phase1-runtime/runtime/runtime_objects.py#L99)。
不可从created_at/updated_at自动推导valid-from/valid-until，或由状态hash单独重建丢失历史。

**三会话示例（HYPOTHESIS，说明所需语义，不是当前跨会话功能验收）**：
G1/G2在此只是两个目标历史状态的标签，不是G1研发阶段，也不规定必须使用两个`goal_id`。

| 时点 | 事件与引用含义 | 必须区分 |
| --- | --- | --- |
| 会话一 t1 | 候选经合法决定D1采纳为状态G1；原始请求、候选和D1可追溯 | 当时G1为已采纳目的，非世界事实/工具授权 |
| 会话二 t2 | 合法修订D2产生状态G2；同一Goal修订可保留逻辑ID，替代目标也可能另有身份，均需明确历史关系 | G2为当前状态；D2确定哪些G1内容被修订/替代，不能默认G1全部为假或全部仍适用 |
| 会话三 t3 | 请求引用“会话一的G1” | 应解析到t1对应内容及D1依据，同时告知当前为G2；不得静默返回G2冒充旧G1 |

旧G1可作为“曾被采纳”的历史依据，不得直接当当前行动目的或新权限。
其当前适用性依D2范围判断；未能确定则为**UNKNOWN**。
若旧版本/决定无法找回，应明确不可解析，不根据最新对象或模型摘要拼造旧G1。
历史可追溯性、现在是否active、信息适用期与内容真实性是独立问题。

## 5. 六方向：职责、共享输入及依赖

理论映射均为**HYPOTHESIS**；代码载体存在不等于理论已运行。
六项是本轮信息论研究分类，不代表UAEA全部认知能力；Episode、L0等既有研究
保留原有职责/边界，不被此表替代、合并或重新授权。

| 方向 | 共享引用 | 独立输出/权威边界 | 测量前提 |
| --- | --- | --- | --- |
| Goal | 注册请求、历史候选、独立Evidence、采纳/修订决定 | 模型提候选，Host维护采纳；不是事实或权限 | null基准、候选族、预先规定编码/预测任务；当前MDL分数UNKNOWN |
| Intent Relation | 当前输入、历史任务/Goal身份、交互事件 | 延续/修订/切换建议，不凭分数改owner/scope/Goal | 标签、观测/变点模型；话题相似度不是后验 |
| Context | 当前Host状态、请求、回执、来源版本、解释 | 有界working set/投影，不修改上游状态 | 明确目标/失真、固定Token成本、事实/出处保留指标 |
| Evidence | Observation、source/access/内容版本、摘录、claim | 来源/候选支持关联，不把claim变truth | 已知重复与未知依赖分开，语义支持另行判断 |
| Memory | 上述来源、纠正/冲突/复用及显式控制 | Candidate与Admission分开，目前不接长期Admission | 有效性/撤回/隐私/成本/未来收益；可压缩性不准入 |
| Workflow | 请求、Action/Decision/Observation、来源、Goal目的 | 待办/执行/阻塞状态，不改Harness循环或自动完成 | 执行事实先行，VOI/PSR需概率、效用、合法行动模型 |

依赖顺序：可靠身份/来源/版本→候选与决定分离→可观察供给/结果→明确评价任务→比较理论。
不是先造完整血缘图或六个模块。同一来源对不同问题的相关性不同，
不能共享一个未经校准的Evidence权重作为全部认知模块的结论。

## 6. Phase-1、5090D与N1X连续性

- **DESIGN INTENT**：[5090D ownership](../archive/harness/harness-feasibility-20260912.md#ownership-matrix)
  和[Context职责](../archive/harness/harness-feasibility-20260912.md#harness-context-runtime-vs-uaea-context-semantics)
  分开Harness执行循环/窗口/Compaction与UAEA认知状态；不能为算信息分数恢复旧Agent/Planner。
- **VERIFIED**：冻结Phase-1有GoalHypothesisRecord、ActiveGoal、Workflow、RuntimeObject及Observation；
  这些不是完整长期形成算法。
- **DESIGN INTENT**：[Memory v0.1关系](memory/memory-architecture-boundary-v0.1.md#1d-memory-relationship-model)
  已提出derived_from/supported_by/supersedes/conflicts_with。accepted/proposal是设计评审用语，
  不代表当前H3已实现Memory生命周期。
- **DESIGN INTENT/部分VERIFIED**：[2026-10-05 checkpoint](../current/architecture/cognition-boundary-checkpoint-20261005.md)
  保留provenance≠correctness、support≠authorization、retention≠adoption及同call不重复算证据；
  不是独立证据计数已实现。
- **VERIFIED（限定）**：[黑盒契约](../implementation/harness/black-box-semantic-execution-contract-20261029.md)
  区分Proposal/参数来源/授权/Observation；该文当时明确离线、未接正式入口。
  不能用后续接线倒写“当时已通过”。
- **VERIFIED（限定）**：[G0/G1](../implementation/harness/goal-integration-g0-g1-20261102.md)
  及[兼容性记录](../implementation/harness/goal-compatibility-20261102.md)
  有真实候选、test_driver显式采纳及采纳后工具调用。其范围PARTIAL，
  候选不自动升级，不等于完整长期Formation/Evolution。

**CONFLICT**用法：按熵下降/编码收益自动增权或改Goal，把Compaction当真实用户，
合并为新全局权威，或增加第二执行控制器。
仅用于非权威候选评估并保留现有合法状态转换，未发现必须重构Phase-1/Harness的实质矛盾。

## 7. 既有真实证据与反例

本轮只读取旧文件，不重跑；限定运行结论不外推：

1. `interactive-32768-20261102-065220`：原始事件有2次Compaction开始/完成，
   4份Host语义快照均无ActiveGoal，Workflow完成未成立。
   模型摘要将推断写成“确认”，不能直接证明权威Goal已污染；
   没有ActiveGoal时更不能声称已验证Goal演化。
2. `goal-compat-live-20261102T123059Z`：四模式12轮。Off/不注入无Goal块，
   可选投影每块仅一次；普通问答无新增候选/Revision。
   不注入组用文档文字填当前用户quote而被拒；其读取失败≠没有Tool Call。
3. `goal-compat-active-20261102T124823Z`：先有候选、test_driver显式控制/采纳，
   再有真实read_section和821字符摘录，hash为
   `a6b85b87eb56f805d9955a263cf4b8716fff964d51f2b06adc84dd374a2ba335`。
   模型把原文放Goal quote而漏掉回答引用，候选被拒，已有Goal与Observation保留。
   这证明限定来源合法性校验生效，不证明语义理解、完整回答或完全无干扰。
4. 此前506项回归（504 PASS/2 SKIP）是兼容性任务结果；本轮未重跑/新增测试。
   Host恢复等覆盖不代表MDL、PSR、独立证据计权或长时Memory已实现。

源记录在§11列出的本机证据索引；不把运行原文复制到公开研究地图。
本轮没有读取隐藏推理或以模型自述作为执行证据。

## 8. 最小研究路线、反例与否定条件

以下不构成本轮实施授权，也不预先决定下一阶段开发。

| 优先级 | 问题 | 最小验证材料/指标 | 否定或止损条件 |
| --- | --- | --- | --- |
| R0，优先 | 现有引用是否足以恢复关键来源链 | 少量历史case手工对照输入/调用/Observation/摘录/Claim/Goal决定，记录可解析、版本匹配、UNKNOWN；与现有trace比较 | 字段已足够就不加公共对象；若要统一全部旧对象才能用，缩小case，不造Pool |
| R1，优先 | 复述/压缩是否重复算支持或越权 | 同call多回显、同文多摘要、同源转载、未知来源、跨scope/撤销、错误Compaction等反例；核查不增权、不新增独立观测、不丢决定 | 不能溯源就未知；不靠关键词/模型自评填成真实依赖 |
| R2，可研究 | Goal候选是否比null基准解释未来输入更好 | 先离线定义有限观测、编码/概率规则、无Goal与简单关系基准，按时间只预测未来一次；累计log loss/复杂度/错误切换；固定proposer版本 | q不归一或未定义不报bit；收益只来自自生成文本、极依赖编码选择或不优于简单基准则否定/暂缓MDL用途 |
| R3，可研究 | 固定预算Context是否保留必要语义/来源 | 既有轨迹对比请求/约束/事实/来源版本可恢复率及任务错误，明确失真，不先估高维MI | 摘要更短却增权/丢关键来源即失败；普通优先级投影足够则不做IB优化 |
| R4，后置 | Intent变点、Memory价值、Workflow VOI/PSR是否有收益 | 先有关系标签、长期反馈、有效时间/效用及合法行动模型，各方向分开评价 | 缺概率/效用/外部评价时只作启发，不追加六套模块 |

建议先评审R0/R1和一个明确的Goal/null预测问题。R0/R1只限代表性case，可与候选研究并行；
不把全项目血缘迁移作为全局前置，直接涉及来源/授权缺失时仅阻断相关case。
未来实验仍由Coding AI设计并自动执行，
不把新一轮人工交互作为本轮交付前提。

**暂缓**：全局熵管理、跨模块bit总分、长期Memory Admission、学习型Workflow控制器、
高维MI估计和完整Goal Evolution。
**放弃作为方案依据**：文本长度=支持强度、重复次数=独立支持、hash/URL=真实、
最小描述=合法采纳，以及累计分数抵消用户显式修订。

### 8.1 后续验收不变量

- 候选评分再高，不自行改变ActiveGoal、授权、Workflow完成或Memory状态。
- 原始用户身份不取自协议role；摘要/模型claim不能变原始输入。
- 同一活动的复制/投影不增加独立支持，未知同源不默认独立。
- 引用版本/范围/hash和用途明确，旧决定不随对象更新指向新版本。
- 来源正文、模型推断及已采纳目的可以关联，但不可互换权威。
- Compaction不能改写Host决定/回执；模型可见不等于理解/采用。
- 同源信息供给不同认知研究时，结论及状态仍由各自合法边界决定。
- 不同Harness包装不得改变规范化来源/合法决定；不要求模型逐字输出一致。
- 引用契约、候选行为、生命周期及任务结果分别报告，不互相替代。

## 9. 风险与外部设计取舍

W3C PROV的Entity/Activity/Agent及派生、使用、归属关系可帮助命名。[S1]
其中Agent指负责/产生的主体，不要求新增UAEA多Agent架构。
PROV约束验证历史结构一致性，不证明内容真实或授权。[S2]
OpenLineage区分运行观察与静态依赖声明，可借鉴“声明有依赖≠执行已发生”，
但数据管道模型不能直接替代Goal/Evidence。[S3]
Event Sourcing可启发独立决定日志与派生视图；当前可变Store、局部JSONL和回执缓存
不能因此宣称全系统可重放、事务一致或崩溃安全。[S4]

主要风险：
- 血缘不完整、跨run身份碰撞、版本漂移、虚假边、撤销传播不明。
  不可变派生版本可检查时间顺序；认知相互影响不意味着所有关系都必须组成DAG。
- 已知父节点不证明穷尽真实来源；模型内部依赖保持黑盒，不补造真实推理图。
- 数值优化制造假精确、旧Goal惯性、同源重复计权或自我实现预测。
- 错误材料也可高压缩，摘要可漏约束；高信息增益不等于有用/真实/合法。
- 血缘传播敏感原文有成本；引用不是新读取权限，hash不是认证签名。
- 集中全部状态引入新的迁移/一致性负担，目前没有充分收益证据。

## 10. 外部原始资料与设计参考

查阅日期2026-11-02，仅借用思想，不引入框架/依赖；不能据此宣称UAEA或N1X已实现理论。

- T1 — Shannon (1948), [A Mathematical Theory of Communication](https://people.math.harvard.edu/~ctm/home/text/others/shannon/entropy/entropy.pdf)：§6等概率/熵定义，非语义价值。
- T2 — Grünwald (2004), [MDL tutorial](https://arxiv.org/html/math/0406077v1)：§1.4/§2.4编码选择，§2.6.4/§2.9.3 prequential解释。
- T3 — Grünwald & Roos (2020), [Minimum description length revisited](https://ir.cwi.nl/pub/29246/29246.pdf)：§2.4顺序预测/累积log loss，需指定编码模型。
- T4 — Adams & MacKay (2007), [Bayesian Online Changepoint Detection](https://arxiv.org/abs/0710.3742)：run length、生成模型、变点假设。
- T5 — Itti & Baldi (2005), [Bayesian Surprise Attracts Human Attention](https://papers.neurips.cc/paper/2822-bayesian-surprise-attracts-human-attention.pdf)：后验/先验KL，不是UAEA可靠性测量。
- T6 — Tishby, Pereira & Bialek, [The information bottleneck method](https://arxiv.org/html/physics/0004057v1)：用目标变量定义相关信息。
- T7 — Littman, Sutton & Singh (2001), [Predictive Representations of State](https://proceedings.neurips.cc/paper/2001/hash/1e4d36177d71bbb3558e43af9577d70e-Abstract.html)：动作条件未来观察的预测表示。
- T8 — UC Berkeley CS188, [Value of Perfect Information](https://inst.eecs.berkeley.edu/~cs188/textbook/vpis/vpi.html)：期望效用与信息成本，原始教学资料。
- S1 — W3C Recommendation (2013), [PROV-DM](https://www.w3.org/TR/2013/REC-prov-dm-20130430/)。
- S2 — W3C Recommendation (2013), [PROV Constraints](https://www.w3.org/TR/2013/REC-prov-constraints-20130430/)。
- S3 — OpenLineage, [Object Model](https://openlineage.io/docs/spec/object-model/)：运行/静态血缘区分。
- S4 — Microsoft Architecture Center, [Event Sourcing pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)：append-only来源、派生视图及复杂性。

## 11. 知识连续性、证据入口与本轮变更

先读[Research Foundation Map](research-foundation-map.md)，再沿§6回顾冻结历史、
Memory及当前G0/G1范围。旧文档的日期、版本和验收结论保留，不追认升级。

Git思想血缘：
- `211379a`（2026-09-26）Harness baseline；
- `bca30f056e43a847a20fdcba0a676b67107ee545`（2026-10-05）semantic authority/文档治理；
- `122040dde1bf75b9d9eabd3ed00236cf8a1375e0`（2026-11-02）P0–P3.4 checkpoint；
- 当前未提交G0/G1及兼容性记录承接这些边界，不属于新增冻结设计。

既有本机运行证据：
- `/home/wqkan_wsl/uaea-n1x/runs/h3-results/interactive-32768-20261102-065220/`：
  app-server-events.jsonl / semantic-state-snapshots.jsonl。
- `/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/goal-compat-live-20261102T123059Z/`：
  各模式Raw、出站审计、Semantic、Goal及Execution轨迹。
- `/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/goal-compat-active-20261102T124823Z/`：
  采纳后真实读取及非法quote拒绝记录。
- `/home/wqkan_wsl/uaea-n1x/goal-integration/compat-20261102T122802Z/`：
  live-analysis.json、active-analysis.json、回归汇总；不是本轮新测。

首次研究整理仅新增本专题及研究地图有日期的索引；未改冻结历史或实现，
未启动模型/推理，未Commit/Push。首次审查记录：
/home/wqkan_wsl/uaea-n1x/research-records/information-lineage-20261102T130648Z

文档收敛补记（2026-11-02）：按用户顶层审计记录Research Baseline PASS、正式实施暂缓；
仅补充§2.2.1、§4.2/§4.3及研究分类范围，不改变原有证据等级或冻结历史。
本次只维护本专题及研究地图，未启动模型/新增实验/Commit/Push；增量Diff与检查记录：
/home/wqkan_wsl/uaea-n1x/research-records/lineage-semantic-closure-20261102T133224Z
