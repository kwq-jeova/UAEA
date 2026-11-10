# Memory 动态数学建模：Task、Goal 与经历的独立生命周期

日期：2026-11-09。状态：**RESEARCH / 总体 PARTIAL，核心理论选择待评审**。
本轮不是 Memory Engine、数据库方案或正式采纳算法。代码与数学探针均隔离；不 Commit/Push。

## 1. 起源与首要修正

直接起因是[真实 Goal 通道实验](goal-channel-convergence-20261109.md)的 form→withdraw。
但原始第三轮明确写“取消刚才的长期价值比较研究，改为审计已有资料”，不只是取消Apple子任务。
候选也描述这一比较方向，没有独立建立“AI产业长期投资研究”的上层候选。
所以：
- **VERIFIED**：一个非权威比较候选被显式取消、追加撤回版本，旧版本与原文仍保留。
- **UNKNOWN**：候选是否代表用户更长期Goal；是否应保留更高层方向。
- **CONFLICT**：仅凭这段实验就判“模型错误撤回长期Goal”，或判“撤回必须删除经历”。

用户的新例子是一个不同的研究问题：长期AI投资研究G、Apple估值任务T、已获得经历E与可能的记忆M。
若原文明示只取消T且G不取消，不能把取消作用域扩大到G。
若原文不清楚，允许竞争解释/UNKNOWN；Runtime不能靠关键词或候选ID自动知道语义层级。
本轮另有短真实Scope对照，结果见[Goal专项报告](goal-scope-transfer-audit-20261109.md)。

## 2. 已有UAEA基础，而非从零设计

| 对象/文档 | 实际能力或历史意图 | 不应扩大解释 |
| --- | --- | --- |
| Phase-2B Memory Boundary §§1A–1E | **DESIGN INTENT**：对象/状态/facet/证据分开，检索返回Projection | 历史草案不是现行Memory Engine |
| Memory v0.1 §§1A–1E | **DESIGN INTENT**：dormant/reactivated/superseded，证据追加引用；不是固定三档存储 | 三档不构成脑机制或已验证时间阈值 |
| memory/candidate.py: EvidenceReference、ScopeHypothesis、MemoryCandidate | **VERIFIED（结构）**：source_kind/id/event/location；scope及候选结构检查 | 有引用不证明支持；extraction_confidence未证明校准 |
| memory/sqlite_store.py | **VERIFIED（源码）**：Source/File/Conversation/Web Access/EvidenceReference/Candidate关联与追溯入口 | 表结构不决定认知模型；Source归档不等于Accepted Memory |
| Canonical / Semantic / ExecutionObservation | **VERIFIED（限定历史轨迹）**：发生了什么、来源/版本及解释可分 | Tool Success不推出结论正确或任务完成 |
| R0 / R1 | **VERIFIED（限定）**：同源派生、重复引用、外部事件边界可恢复 | 同hash重访不等于同一次执行；不同事件不证明统计独立 |
| G0/G1与研究候选版本 | **VERIFIED（限定）**：候选/采纳独立，追加版本和撤回；显式form→withdraw真实通过 | 跨Task/Run长期Goal形成、自动Memory采纳未证明 |
| Longitudinal Goal 2026-11-04 | 给定已审查语义输入时，简单历史状态已能完成若干更新 | 语义标注不是Runtime自行理解能力 |

参考：[Memory Boundary](memory/phase2b-memory-boundary-architecture.md)、
[Memory v0.1](memory/memory-architecture-boundary-v0.1.md)、
[R0](r0-information-lineage-20261103.md)、[R1](r1-information-dependency-20261103.md)、
[长期Goal研究](longitudinal-goal-runtime-20261104.md)。

## 3. 科学依据：人类记忆不是一条统一晋升流水线

这里的“科学支持”只表示论文所研究人群、任务与现象的证据，不代表UAEA实现或人脑全部机制已被证明。
本轮是选择性理论比较，不是系统性综述。部分作者托管PDF直接获取超时，相关公式通过可检索正文/索引片段核对；文献检索范围和限制列于literature-index.json。未复现作者数据拟合或全部原始模拟。

- 工作记忆可涉及注意、短暂激活与长时表征的整合，并不要求每个经历按“短→中→长”三级移动。
  Baddeley的episodic buffer是有限容量的整合假说；Cowan讨论的是特定任务中的注意容量，
  不能将人类chunk数换算为LLM的Token预算。
  [Baddeley 2000](https://pubmed.ncbi.nlm.nih.gov/11058819/)；
  [Cowan 2010](https://pmc.ncbi.nlm.nih.gov/articles/PMC2864034/)。
- 陈述性与非陈述性记忆具有不同功能依据；事件、事实、技能可互相影响，但存一个流程说明并不证明获得了技能。
  对UAEA而言，程序性候选也不能获得自动执行权限。
  [Squire & Zola 1996](https://doi.org/10.1073/pnas.93.24.13515)；
  [Reber等1996实验](https://pubmed.ncbi.nlm.nih.gov/8918990/)。
- 遗忘可能涉及可及性、干扰和线索，而非仅物理痕迹按钟表时间消失。
  [Lewandowsky等2009](https://pmc.ncbi.nlm.nih.gov/articles/PMC3980403/)。
  **工程推演**：检索降权与保留/删除策略应分开；隐私或明确删除请求仍需独立政策。
- 某些恐惧条件化研究表明，提取后记忆可再次变得可修改；不是“每次回忆都必须改写事实”的普遍规律。
  [Nader等2000](https://www.nature.com/articles/35021052)。
  UAEA应允许更新解释版本，不能模拟人类重构错误而覆盖原始Observation。
- 奖励动机与24小时后场景记忆的关系有具体实验支持；
  不意味着LLM自评“重要”就构成可校准Memory价值。
  [Adcock等2006](https://pubmed.ncbi.nlm.nih.gov/16675403/)。

“中期保持”可以是观察时间段或多尺度动力学，不必是第四种存储器。
“像人”不是唯一工程目标：人类的错忆、来源混淆与过度熟悉也应作为反例，而非复制目标。

## 4. 四个实质不同的候选模型

以下区分：原理论核心 → 本轮数学示意 → UAEA适配假设。
没有把所有模型拼为一个新Runtime，也没有赋予任何分数采纳权。

### A. ACT-R式使用历史与线索激活（优先研究的最小竞争模型）

科学动机是频率、近因与间隔影响可及性；基础强度常用历史时间幂函数之和的对数。
[Anderson & Schooler 1991](https://journals.sagepub.com/doi/abs/10.1111/j.1467-9280.1991.tb00174.x)；
[作者ACT-R方程材料](https://act-r.psy.cmu.edu/wordpress/wp-content/uploads/2012/12/39jra_cds_2000_a.pdf)。

**状态与工程适配式（HYPOTHESIS）**：
经历i有可核查编码/练习时间集合T_i，内容/来源版本s_i，检索线索相似度C_i(q_t)；
d>0为衰减形状，τ_0>0为时间单位，δ>0防止零时差奇点。

\[
 B_i(t)=\log\sum_{\tau\in T_i}
 \left({t-\tau+\delta\over\tau_0}\right)^{-d},\qquad
 A_i(t,q)=B_i(t)+\lambda C_i(q).
\]

原理论还有情境激活、噪声、阈值/延迟等机制；这里不是完整ACT-R复现。
A首先是**排序强度**，不是内容真值、记忆重要性或授权概率。
若采用logistic提取率、T=F exp(-A)等反应函数，噪声/阈值/F必须用实际提取行为拟合；
LLM总体延迟受prefill、解码、排队影响，不能直接作为人类提取潜伏期去拟合。

不需要预设短中长三档。对d>0，
\[
 (1+t/\tau_0)^{-d}={1\over\Gamma(d)}
 \int_0^\infty u^{d-1}e^{-u}e^{-ut/\tau_0}\,du .
\]
这是Gamma积分恒等式，说明该核可表示为连续指数时间尺度混合，
**不是发现了人脑时间常数**。有限K项近似可减少全历史计算：
h_ik(t+Δ)=exp(-Δ/τ_k)h_ik(t)+新增编码，B≈log Σ_k w_k h_ik；
τ_k、w_k需辨识，不能把它们直接命名为三个脑区。

**适用与风险**：
- Goal/Task结束只改变当前线索C，不必清空T、s或来源记录；无Goal仍可由其他线索检索。
- 重读可以提高练习可及性；但同一来源重复投影不能增加“独立支持”。
  编码、检索练习、模型复述必须分别记账。
- 高频错误也能高激活，所以不能用A判断真假或让高A覆盖矛盾证据。
- 直接计算约O(Σ|T_i|)，固定核近似约O(KN)状态；另需候选检索索引，但本轮不建索引。
- d、λ与阈值易混淆；时间单位、使用窗口和选择偏差需固定。人类常用参数不是UAEA参数。
- 可证伪：预登记参数、在未来真实查询的时间外留出集比较检索遗漏/错供及成本，
  若不优于相同信息预算的Relevant History，就否定新增激活项的工程价值。

### B. CMR / retrieved-context：情境漂移与关联再激活

该理论研究自由回忆中的时间、语义和来源组织；
重新激活项目可带回关联情境。
[Polyn、Norman & Kahana 2009](https://pmc.ncbi.nlm.nih.gov/articles/PMC2630591/)；
[后续compound-cuing实验](https://memory.psych.upenn.edu/files/pubs/LohnKaha14b.pdf)。

设项目表征f_t、单位情境c_t、项目→情境矩阵M_FC及反向矩阵M_CF：
\[
 c^{IN}_t=\mathrm{normalize}(M_{FC}f_t),\quad
 c_t=\rho_t c_{t-1}+\beta c^{IN}_t,\quad
 a=M_{CF}q_t.
\]
在向量单位化条件下，
\[
 \rho_t=\sqrt{1+\beta^2[(c_{t-1}^{\top}c^{IN}_t)^2-1]}
 -\beta c_{t-1}^{\top}c^{IN}_t .
\]
0≤β≤1；来源与时间可有不同漂移率，编码与提取也可不同。
关联学习可用外积示意 ΔM_FC=η c_t f_t^T、ΔM_CF=η' f_t c_t^T，
但这是说明输入输出关系，**不是作者完整竞争/停止机制的实现**。

**UAEA假设**：Task切换可改变活动情境而不删除旧关联；后来AI产业线索可能再激活Apple经历，
但不重新授权被取消任务。未知Goal不妨碍普通情境线索存在。
**反方**：语义特征和Goal关系仍需解释能力；慢漂移可能把旧任务带入新任务，错误复述也能污染情境。
参数β、关联率、竞争/停止规则与表征选择未辨识，不是“关联图越大越好”。
稠密矩阵约O(D_f D_c)；若一项目一维随N增长，成本与干扰明显。
最小区分实验须比较当前线索基线与跨任务回忆顺序/错误闯入，不能仅展示可回忆旧内容就判模型更优。

### C. Complementary Learning Systems（CLS）：快速经历、慢速结构整合

原理论用互补的快速经历学习与渐进结构学习处理干扰与泛化的矛盾。
[McClelland、McNaughton & O'Reilly 1995](https://web.stanford.edu/~jlmcc/papers/McCMcNaughtonOReilly95.pdf)；
[作者2016更新](https://pubmed.ncbi.nlm.nih.gov/27315762/)。

通用数学示意（不是唯一CLS方程）：
\[
 \theta_f\leftarrow\theta_f-\eta_f\nabla L(o_t;\theta_f),\qquad
 \theta_s\leftarrow\theta_s-\eta_s
 \nabla \sum_{e\in\mathcal R_t}w_e L(e;\theta_s),\quad\eta_s\ll\eta_f.
\]
θ_f记录具体经历，θ_s提取跨经历规律，R为replay样本。
实际神经/网络实现可能不同；两个学习率不是短中长三个文件夹。

**UAEA假设**：Task结束后具体经历仍可供未来提炼；旧解释失败可保留为反例，而非全部遗忘。
**主要障碍**：缺乏经过核验的抽象目标与效用标签；replay错误摘要可巩固幻觉；
replay也不增加外部独立证据。模型Backend是黑盒，不能把CLS直接解释为每轮LoRA训练。
维护成本包含回放、冲突与遗忘评估，远高于已有历史检索。
应有“同等预算下泛化提高且原始来源可恢复”的留出证据，才考虑该方向；
当前不存在支持正式慢速维护层必要性的结果。

### D. 潜在原因贝叶斯模型：更新旧解释，还是新情境

条件化研究用隐藏原因解释同类刺激在不同情境下的更新和恢复；
“行为消退”不必等于痕迹删除。
[Gershman、Blei & Niv 2010](https://www.cs.columbia.edu/~blei/papers/GershmanBleiNiv2010.pdf)；
[Gershman等2017](https://elifesciences.org/articles/23763)。
已查[勘误](https://elifesciences.org/articles/28693)：实验给药时点示意和一个公式后定义曾修正；
本轮没有复现其全部模拟。

观测x_t为线索、r_t为实际结果，潜变量z_t为情境原因（**不是直接定义人的Goal**）。
简化表示：
\[
 \gamma_t(k)\propto p(x_t,r_t\mid z_t=k,\theta_k)
                 p(z_t=k\mid z_{<t},\Delta\tau),
\quad
 w_k\leftarrow w_k+\eta\gamma_t(k)x_t(r_t-w_k^\top x_t).
\]
例如x|z可设Gaussian，r|x,z可设线性Gaussian；时间核先验对已有原因累积邻近经历质量，
新原因有浓度参数α。选择这些分布就是实质假设，不能用LLM confidence代替似然。
需要测量结果、参数估计、留出log-loss/校准检验；α、观测噪声和更新率可能互相补偿。

优点是允许竞争原因及“同一解释被更新/新的情境形成”两种可能。
缺点是自然语言语义特征与真实结果不足时，漂亮的posterior只是主观建模输出；
当前数据尚不足以辨识它。大K或粒子近似成本可增长至O(PKD)及更多历史状态。
高后验不能阻碍用户明确合法修订，也不能直接采纳Memory或授权。
若换观察窗口/噪声先验就任意改变Goal解释且无法改善留出预测，应暂停概率建模。

## 5. 独立比较与首选

| 目标 | A 激活 | B CMR | C CLS | D 潜在原因 |
| --- | --- | --- | --- | --- |
| 时间/使用影响可及性 | 直接、少参数 | 情境漂移与邻近 | 快慢学习 | 时间先验/结构变化 |
| 线索召回、Task后再关联 | 有，需情境项 | 最直接的核心解释 | 可从经历重放/概括 | 按情境重新推断 |
| 纠错/冲突 | 本身弱，需独立版本语义 | 允许联想也会闯入 | 可修正也会巩固错误 | 可区分原因，但依赖似然 |
| 语义真假或权限 | 均不能保证 | 均不能保证 | 均不能保证 | 均不能保证 |
| 当前可辨识性 | 最容易开展小留出检验，仍未校准 | 特征/漂移/竞争混淆 | 数据/训练目标不足 | 语义真值与结果不足 |
| 当前新增工程成本 | 较低 | 中到高 | 高 | 中到高/随K增长 |

**首选研究候选：A，线索条件下的ACT-R式激活；不是选择完整ACT-R架构。**
理由是当前已有来源/时间/实际访问记录，新增变量最少、可与Relevant History做嵌套消融。
先研究“额外使用历史能否改善下一次正确检索”，而不是先建Memory Engine。
**B是最有价值的竞争方案**：若出现仅当前线索不能解释的跨任务复现/关联顺序，再检验情境漂移。
C/D保持理论候选，暂不组合四套系统。

反方论证：A可能只是给良好的相关历史加了不必要的近因偏置。
本轮探针确实暴露了这一点。因此首选是“最小可证伪试验对象”，不是生产核心理论已经胜出。
若实际留出数据也显示无增益，应保留Relevant History并停止激活工程化。

## 6. 共同形式化：保留、正确性、适用性、关联、授权分开

这不是新公共Schema，而是研究数学变量说明。

对来源s、解释版本h_v、记忆候选m：
- R_s：原始观察/内容版本是否仍可解析。
- H_v：某主体在某时刻提出的解释及其历史版本。
- V(h_v,t,scope)：解释在该时空范围的适用判断，允许UNKNOWN/受反驳。
- A_ig(t,scope)：经历i与某Goal解释g的关联；不要求一对一，也不要求总有Goal。
- P_i(q,t)：当前线索下的检索优先级。
- D：独立的Admission/Authorization决定引用。

关键非蕴含：
\[
 TaskEnded\not\Rightarrow GoalWithdrawn,\quad
 GoalWithdrawn\not\Rightarrow \neg R_s,\quad
 High(P_i)\not\Rightarrow True(h_v),\quad True(h_v)\not\Rightarrow Authorized(action).
\]
这些是不蕴含关系，不是说高分必假。编码/练习时间不等于来源发布时间或内容适用期；最近访问的旧行情仍可能过时。
明确Task取消若原有候选只描述该Task，可以撤回该候选；范围判定仍是语义判断。
Goal被误解时，修订的是H，不应反写“用户历史上确实有这个错误目的”。

“模型曾说X”这个事件与“X在世界中为真”是两个不同对象。
纠正X时保留原始事件可以帮助错误审计，但不得把X继续作为当前知识供给；
如果后续任务是研究误判本身，X可连同反驳和旧版本身份被检索。
所谓“重新巩固”应在UAEA表现为解释/关联的可追溯再评价，不是改写来源正文。

取消Goal可降低关联检索权重；以后新Goal可重新引用同一历史来源，
不复活旧Task、旧授权或失效行情。“新用途”不让旧内容自动变成当前事实。
无ActiveGoal、无GoalHypothesis时也可以保留Observation、提出Memory Candidate；
何时正式采纳仍受独立Policy，不是本轮方程决定。

## 7. 最小CPU探针与负面结果

隔离脚本 scripts/research/memory_activation_probe.py；结果 memory-probe.json。
仅合成三类记录：久远AI来源、近期无关来源、被标记为错误且superseded的解释。
语义向量与适用性标签由Fixture预先给定，不是Runtime自动识别，不是人类记忆拟合。

6项代数/生命周期检查通过：Task取消不改Goal；Task/Goal变化不删历史字节；
无Goal也可由内容线索检索；旧错误解释保留但不作当前事实；
20次派生投影不增加外部编码次数；练习可改变可及性但不新增外部支持。
这些只是显式表示的性质，不证明系统学会了这些语义。

公平基线Relevant History使用同样完整记录和同一线索相似度，正确找回旧AI来源。
A在d={.2,.5,.8}、λ={0,.5,1,2,4,8}共18组参数中，仅9组同样正确，9组被近期无关来源压过。
没有选“最佳参数”冒充验证成功。

示例：d=.5、当前t=100、旧来源t=0、新来源t=99，时间单位1。
B_old=-.5 ln101，B_recent=-.5 ln2；相似度差1，则需λ>1.961才不被近因压倒。
这个阈值由该合成例子导出，不是UAEA/人的通用阈值。
**VERIFIED（计算）**：未校准激活会损害本例检索；**UNKNOWN**：真实用户任务中是否有收益。

## 8. 下一步最小、可证伪实验设计（待本轮理论方向评审，不提前执行）

先收集少量真实后续查询及当时可用来源，切分训练/未来留出；
用户当前任务原文与审查者标注给出“需要何种经历、为何适用/已过时”，保留分歧与UNKNOWN。
不由被测LLM自评建立真值，不把后来的成功方案当唯一正确答案。

对照：
1. 现有Relevant History（强基线，相同候选信息与Token预算）。
2. 相同线索＋激活A；仅少量预登记参数，时间外训练，冻结后评估。
3. 只有出现必要关联现象后，才加入B的情境漂移；不一开始组合CLS/Bayes。

成对反例：只取消Apple任务/明确取消长期AI方向；
旧解释被纠正/用户真实改方向；无Goal仍有价值的经历/高频但错误的复述；
旧方案条件未变/新资源使旧方案重新可行。
指标：正确经历可召回、过时/错误内容闯入、来源与反驳可恢复、禁止任务重启、后续真实步骤是否减少无依据弯路、
Token/工具/存储成本。仅检索命中改善不能直接宣称决策净收益。

失败/止损：不优于基线；参数跨时间窗口不稳定；必须依赖无来源语义标签才能取胜；
增加重复引用却无新观察；改善召回但增加错误执行/权限风险。
任何正式Admission或执行契约变化另行评审。

## 9. 本轮结论分级

- **VISION**：经历可积累、理解可修正，未来帮助真实决策，不是无限存聊天。
- **VERIFIED**：既有局部血缘和候选版本、两项评价器反例修复与真实旧轨迹复审；CPU探针的负面结果。
- **DESIGN INTENT**：Memory对象/facet/状态/证据分离，保留与Adoption分开。
- **HYPOTHESIS**：A的激活项或B的情境再激活可在未来查询中提供增益。
- **UNKNOWN**：人类机制对UAEA的参数迁移；Scope语义真值、独立证据估计、概率校准、跨RunMemory认知与决策收益。
- **CONFLICT**：Task取消级联删除Memory；用重复、自评confidence、Token或权威标签伪造有效bit/真实概率；高分自动Adoption。

Shannon熵H(X)=-Σp(x)log2p(x)、surprisal=-log2p(x)只有在明确观测单位和概率模型后才可计算；
它们不是Goal重要性、记忆真假或建议成功率。
当前不计算“有效bit”，不将MemoryCandidate.extraction_confidence转作Bayes概率。
数学候选比较已到需要选择理论实验方向的评审节点；建议A作为最小竞争模型、B保留竞争解释，
**不批准新Memory层、不自动接入Runtime**。
