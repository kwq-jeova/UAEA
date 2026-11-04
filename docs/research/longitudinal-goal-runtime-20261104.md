# Longitudinal Goal Cognition：Runtime离线建模与验证（2026-11-04）

结论：**总体PARTIAL**。本轮证明的是给定来源与可审查语义判断时，如何保存/更新非权威认知视图，
不是自动长期Goal Formation，也不是条件建议已经有实际价值。
公平的简单历史基线与动态候选机制打平；没有证据支持新增Goal Engine、Information Pool或概率状态机。

## 1. 研究目标与独立判断

**VISION**：在持续交互中理解用户当前方向和条件性发展方向，区别短期任务、长期方向与自身误解，
在有依据且值得干预时提出建议，允许不建议；建议不等于执行、正式Adoption或授权。
这是用户本轮明确调整后的研究主线，**不继续以Bolt Prompt/Thinking/JSON优化为主线**。
[上一轮候选表达负面结果](goal-candidate-scope-20261104.md)作为历史证据保留，不改写。

**独立判断**：当前最小问题不是找一个新的Goal概率公式，
而是让“观察记录、解释候选、支持/反证判断、当前视图、正式决定”拥有不同生命周期。
错误解释可以被保留和反驳，但不能仅因后来重复、摘要或字段变化就变成用户历史。
状态容器与可追溯更新可以确定性实现；语义支持是否正确，不能靠容器或hash自动证明。

本轮全部离线，不启动Bolt、vLLM、Harness或新工具执行；复用既有真实记录。
不修改正式Goal Adoption/Authorization/Memory、Phase-1、Harness所有权或资源保护。
原型仅在research-records中，正式入口不读取。

## 2. 可复用组件与真实缺口

| 组件 | 代码/既有证据 | 本轮复用与限制 |
| --- | --- | --- |
| Phase-1 GoalHypothesis / ActiveGoal / Workflow | runtime/context_manager.py:47；runtime/runtime_objects.py:99/129 | 核查既有职责，不重新启动Agent；不把GoalHypothesis当ActiveGoal |
| RuntimeObjectStore / RuntimeObjectRecord | runtime/runtime_objects.py:22/267 | 实际导入并仅向objects追加研究记录/视图；没有改源码或新增正式存储层 |
| G0/G1 | harness/goal_integration.py:86/151/183/319 | 原始来源、候选/采纳、控制与恢复边界保留；本轮既有34项Goal回归通过 |
| Semantic Interpretation | harness/semantic_interpretation.py:60 | 已能保存候选、原文span与model事件；明确semantic_correctness=not_established，没有现成通用语义审查器 |
| Canonical / Observation / Evidence | R0实体与R1分类、原始Execution轨迹 | 复用来源ID/版本/同源映射；执行成功不推出Goal完成或内容语义正确 |
| Context / Compaction | R0已定位的两份真实摘要 | 作为派生Claim重放；窗口供给与Host保留记录分开，不从摘要恢复权威 |
| Longitudinal认知依据判断 | 目前没有独立可验证的通用实现 | 本轮用独立登记的研究标注模拟，生产质量来源仍UNKNOWN |

代码位置的实际hash/行号在runtime-code-evidence.json；上表runtime路径位于冻结子模块runtime/phase1-runtime内。
**重要复用边界**：Phase-1的record_workflow_candidate会调用ensure_active_goal（runtime_objects.py:328）。
这是旧执行路径的既有行为，不能因为复用Store就将其接入Harness认知研究。
本原型不调用这些方法，不恢复执行循环。

G0候选owner与current_task_id关联，限定控制也校验现有所有权。
本研究每段序列有固定研究Scope、任务作为可变子视图；**未证明生产系统已经解决跨Task/跨Session长期Goal所有权**。
正式接线前仍需核查这些Scope关系，不能把人工研究Scope当现成产品能力。

## 3. 最小认知表示与更新

使用现有对象容器保存四类互不替代的记录：
1. 原始观察/执行记录：身份、内容版本、原始Locator与已知Root。
2. 模型或Compaction解释：原样作为未验证Claim；不读取Bolt特定字段、Thinking或Confidence来形成方向事实。
3. 研究认知依据：有来源的task/declare/replace/support/refute/condition判断。
4. 不可回写的版本视图：当前请求、候选方向、条件、未解决冲突、旧方向及其依据。

这些是**隔离的研究表示**，不是正式Schema/API，也不新增全局信息池。
不同原始协议可以进入同一“未验证解释”入口；不要求不同模型提出相同解释。
候选引用同一来源不会累加独立支持，解释也不能验证它自己。

### 3.1 认识更新与用户修订

- task变化不自动改变持续方向。
- condition变化只更新所依据的条件，允许路径可行性变化。
- support可保留一个解释，但不按出现次数或第N轮自动形成正式Goal。
- refute纠正解释，不将被否认的猜测存成“用户以前确有、现在取消的目标”。
- declare是研究审查者对当前明确方向的解释，不等于正式Adoption或权限。
- 不相容declare保留冲突；只有带明确替换依据的replace才能关闭已知旧用户方向。
- 后来用户确实选择以前否认的方向，可以从新时点提出当前方向，不能反写早期历史。
- 旧版本按ID/hash解析，不默认取最新。

No ActiveGoal、No Goal Hypothesis与信息论Null Model仍分别成立。
本研究全程没有正式ActiveGoal，但可以保留多个解释或明确的非权威方向视图。

### 3.2 必须公开的语义前提

研究标注已经包含“这是条件变化/明确替换/认识纠正”等语义判断；这部分**不是Runtime从原文自动推导的能力**。
标注与答案在执行前分别冻结，预测器不读取gold；但同一Coding AI编写和审核，非独立人类盲评。
概念词表也预先给定，不是自主发现新的Goal语义类别。

来源登记/quote有效只能证明可追溯；不能证明标注者理解正确。
单个错误但被登记为可用依据的判断，仍能污染认知视图，见§7。
未来生产中如何获得、复核及撤回这类判断，是本轮暴露的最小缺口。

## 4. 55条记录的多轮实验

| 序列 | 记录 | 来源与覆盖 |
| --- | --- | --- |
| S-A | 9 | 新合成：档案方向保持、临时问答、经费/网络变化、反复受阻、明确改为自行车方向 |
| S-B | 8 | 新合成：日志/软件比较的多个解释，早期UNKNOWN，反证，后续新明确承诺 |
| S-C | 7 | 新合成：手稿目录、模型误解、真实澄清、同源回显、错摘要、后来的真实修订 |
| S-D | 6 | 新合成：天气/饮食/出行/假设，保持无长期方向 |
| H8 | 8 | 原10-28人工会话的八轮用户原文；同一研究主题，**不是八组独立长期会话** |
| R0-A | 6 | 原G0/G1会话的两条用户输入、一次真实文件Observation及三种同源表示 |
| R1-C | 3 | 原11-02会话三次真实Fetch，包含同版本内容重访 |
| R0-C | 2 | 原11-02会话两份真实Compaction输出，记录为派生信息 |
| BOLT-N07 | 6 | 旧合成原文和真实Bolt两种响应；是“模型在合成输入上的输出”，非自然人长期交互 |

共9段序列、55条记录；合成多轮判断30个检查点，其他25条分层报告。
H8只用可恢复用户输入及来源，未继承旧模型答案/Goal标签；缺失链接指代仍未知。
H8在八个时点都正确保留当前任务、没有擅定长期Goal；
动态模式可保留研究兴趣解释，不能称为用户长期承诺。

历史来源分别核对原文件hash、JSON Pointer和已有R0/R1版本；
全部事件与字段定位在source-index.json，真实文件版本在source-manifest.json。
R0-A同源表示在Observation之后做审计重放，其后置排列不是原生时间顺序或新的外部事件。
R0/R1各Run内按已有锚点使用，不强行合并成跨Run绝对时间线。
BOLT-N07的两个响应是相同输入的独立实验臂，不伪装成一场自然会话中的连续信念变化。

## 5. 公平对照与主结果

三种模式使用相同来源、研究语义判断、固定选项与资源条件：
- Current Task Only：不保留长期方向，作为明确消融；保留相同条件与安全/来源机制。
- Explicit History：保留明确历史方向，允许用户真实替换与认知纠正，没有人为禁止更新。
- Versioned Hypotheses：在同样明确方向之上，额外保留可选解释及反证。

**版本、来源、冲突保护是三种模式共用基础，不能只算作动态模型的收益。**

| 给定研究语义判断的检查 | 当前任务消融 | 简单历史 | 动态候选 |
| --- | --- | --- | --- |
| 30个合成时点方向匹配 | 20 | 30 | 30 |
| 9个条件选项集合匹配 | 5 | 9 | 9 |
| 同时检查“建议种类＋选项”的匹配 | 2 | 9 | 9 |
| 原人工8轮：不强行确立长期方向 | 8 | 8 | 8 |
| 原人工8轮：当前任务保留 | 8 | 8 | 8 |

原始集合指标的5/9包含“因不知道Goal而返回空集”恰好与受阻空集相同；
补充审计区分无知弃答与正确识别瓶颈，完整决定只有2/9。gold/原文未改，没有把空集巧合算正确诊断。
以上都是相关检查点，不是自然语言准确率、独立样本或建议成功率。

**VERIFIED**：在给定语义前提时，简单历史已经足以完成这组方向保持、明确修订和已知选项判断。
动态候选额外展示了候选/反证连续性，但没有改善上述主结果。
**UNKNOWN**：它是否提高真实条件建议价值或自然长期Goal理解。
因此不支持为这些结果升级为复杂概率Goal Engine。

### 5.1 多轮状态的具体证据

- S-A：前6轮档案方向保持；第3轮经费降低，只剩远程选项；网络断开后两个已知选项都受阻。
  第5轮状态低波动但任务未完成、optimality=UNKNOWN；网络恢复后可行选项改变。
  第7轮才依据明确替换转为自行车方向，旧档案方向保留结束依据。
- S-B：前5轮方向仍UNKNOWN，支持/反证集合变化；第4轮否认自己的日志计划，不制造“取消旧用户Goal”。
  第6轮用户新承诺才成为明确研究方向，旧版本仍保留早期UNKNOWN/反证。
  这不是固定轮数阈值，也不能把后续承诺反推成早期一直存在的真实目标。
- S-C：错模型解释、回显和摘要不改变家族目录方向；用户第6条记录明确改公众展览才更新。
- S-D：六轮自由交流及假设保持无明确长期方向，不以话题次数构造稳定Goal。

这些结果的解释能力来自输入语义判断；不能据此宣称从零自动Formation或识别私有心理状态。

## 6. 窗口、历史版本与条件推演

55个时点×3模式×窗口1/3/all，共495项Host保留状态检查通过。
这检验的是**保留完整Host记录时，缩短供给窗口不会改变本地认知视图**，
不是实测模型收到/使用了投影，也不是新的真实Codex Compaction验收。
版本按旧ID/hash仍可解析，恢复仅从保留的原记录重放，不凭摘要或快照自造权威。

另做不保留Host账本的冷短窗口回放：
S-A最终只看1条，无法恢复自行车长期方向；看3条可恢复新方向，却没有旧档案历史。
S-B只看最后1条也不足以恢复最初的承诺；带原记录的恢复则一致。
缺失应保持UNKNOWN，不声称全局跨Run身份、正式冷启动或长期持久化已经解决。

条件推演使用作者预设的cost/network选项表，与合成/用户报告条件核对：
返回可讨论选项、已知选项受阻、需要信息、需要方向澄清或弃答。
不排序真实效用、不搜索所有现实路径，不执行任何动作。
S-A的9个完整决定，简单历史与动态都9/9；只能称有限可行性筛选PASS。
**可行不等于有价值，稳定不等于最优，已知选项受阻不等于所有现实路径都不可行。**

若没有需要区分Goal的给定决策选项，仅有候选歧义也不应打断当前明确请求。
本轮局部修正了原型此处：H8保留研究兴趣解释，但无给定分支，所以不主动追问长期Goal。
这不是证明真实主动建议时机正确；实际价值、用户打扰代价和效用仍UNKNOWN。

## 7. 认知幻觉、冲突与剩余FAIL

16组离线候选质量干预：合理提议、错误反复声明、不同模型意见/同模型改口、虚假历史摘要，
均不改变已有认知核心，也不新增外部支持。它们是合成干预，不是16场真实多模型验收。
原BOLT-N07真实错误响应也作为未验证Claim保留，没有进入用户历史或正式Goal。

**本轮发现并修正的确定性缺陷**：
初版把相互矛盾的两个已登记declare解释，后一个当成用户修订，制造旧目标被替换的历史。
conflict-diagnostic-before.json保留了实际错误。隔离原型修正为保留冲突，等待明确替换依据；
对三个模式共同应用，未修改正式Goal机制。23项补充控制通过，含顺序不变、冲突后合法更新、
旧引用保持、反证不变历史、已有方向的替换目标校验。
初版代码/结果及增量Diff全部保留；冻结主输入/答案不改。

**仍然存在的FAIL**：
semantic-review-fault.json将一条真实档案原文配上错误但登记合法的“自行车方向”解释。
错误认知被接受，正式ActiveGoal仍为空。
这证明正确来源、登记、版本与合法边界**不能保证认知解释正确**。
拒绝模型自评作为独立审查，不等于已获得可靠的生产语义审查能力。
原型能管理依据，但尚不能自动判别所有支持关系。

主检查338项满足预期，其中**1项是成功复现上述能力局限**，不是338项全都消除幻觉。
另23项补充控制、1项不必要澄清检查、既有34项Goal回归通过。
修补脚本第一次在AST检查中发现换行转义错误，未执行有问题的版本；原文件另存，随后语法和回归通过。
这些数量不能相加为认知能力得分。

## 8. 五个维度的独立判定

| 维度 | 判定 | 证据范围 |
| --- | --- | --- |
| Runtime Contract | PASS（限定） | 隔离研究视图无正式Adoption/权限/执行；既有Goal34回归；非生产长期接线 |
| Cognitive Behavior | PARTIAL，有明确FAIL | 语义标注下更新可重复；无审查时不自动认识；错误合法审查可污染认知视图 |
| Information Integrity | PASS（限定） | 选定来源/版本/重复Root/旧引用；跨Run、全量依赖和语义支持UNKNOWN |
| Conditional Recommendation | PARTIAL | 固定选项可行性/弃答；实际推进价值和用户效用UNKNOWN |
| Mathematical Validity | PARTIAL | 有限离散定义可复核；尚无可校准的概率、编码或效用模型 |

没有计算Entropy、MDL、有效bit、互信息、70%阈值或建议成功概率。
Shannon不能单独确定Goal语义、价值或授权；候选数量和重复次数不被当作信息量。
本轮不要求概率模型，因为简单状态基线尚未失败到需要该复杂度。
相同可观察历史可能对应不同私有目标；仅凭这些轨迹无法唯一识别真实Goal。

## 9. 实现、证据与复现

独立目录：
/home/wqkan_wsl/uaea-n1x/research-records/longitudinal-goal-20261104T021359Z

- make_data.py / sequences.json / source-registry.json：原始流与源登记。
- review-registry.json：已包含语义工作的研究判断，不能误作Runtime自动推理结果。
- gold.json / frozen-before-experiment.json：输入与答案预先固定。
- view_replay.py：使用既有对象容器的离线认知视图，不是正式Runtime模块。
- run_study.py / predictions.json / versions-and-objects.json：三基线完整输出与历史版本。
- window-checks.json / cold-window-results.json：保留账本与裸短窗口分别报告。
- proposal-noise-results.json / no-review-results.json：候选质量与缺少语义判断的界限。
- conflict-diagnostic-before.json / initial-prototype/ / research-prototype-fix.diff：原型错误与可回退修正。
- checks.json / supplementary-checks.json / semantic-review-fault.json：边界检查与已知FAIL。
- recommendation-decision-audit.json / no-unnecessary-clarification-check.json：选项种类审计与弃答。
- source-index.json / source-manifest.json / runtime-code-evidence.json：事件字段、原版本与代码依据。
- goal-regression.stderr.log：34项既有Goal测试实际记录。
- analysis.json / results.json：分维度结论。

离线复现：
`python3 -B /home/wqkan_wsl/uaea-n1x/research-records/longitudinal-goal-20261104T021359Z/run_study.py`
`python3 -B /home/wqkan_wsl/uaea-n1x/research-records/longitudinal-goal-20261104T021359Z/supplementary_checks.py`

不要重新运行make_data.py来覆盖冻结依据；复核既有源版本即可。
本轮未运行模型，原始来源hash只是版本一致性，不是数字签名或语义真实性证明。
所有原有工作区变更保留；仓库仅新增本记录与地图索引，不Commit/Push。
人工入口、默认Goal模式和模型加载命令保持不变。

## 10. 架构建议与最小下一步

**建议保留简单历史状态＋共用来源/不可回写版本基础，候选/反证作为可选研究视图。**
不需要新Information Pool、第二执行循环或六套认知算法。
当前没有证据表明更复杂动态机制在方向或有限选项判断上优于简单历史。

下一步最值得评审的不是Bolt提示或新Goal概率，而是：
**认知依据评价如何产生、记录、冲突处理和撤回；如何始终区别“系统改了看法”与“用户改了方向”。**
优先对照现有semantic_interpretation、G0候选及RuntimeObjectRecord元数据，
在独立复核的小批真实历史上检验“错误支持→后续反证→认知修正”的完整链。
本轮研究登记不能直接搬成生产信任根，模型自证亦不能填补这个缺口。

如果评审同意后续原型，只收敛已有记录间的依据/评价关系；正式接线前需明确：
- 语义判断来源、有效Scope、历史引用与撤回行为；
- 当前Task与跨Task认知视图的所有权；
- 形式合法但语义错误时的保留/弃答/质询策略；
- 候选推进方向必须有条件与价值依据，不能仅凭Goal稳定就打断用户；
- 如何在同一原始观察上独立评价，而不是模型提案给自身贴真值。

**当前可继续研究动态认知，但不具备宣称自动长期Formation、可靠主动建议或生产接入的条件。**
保留UNKNOWN，不要求先补齐全部R0/R1或建立统一ID数据库。
完成本轮限定建模、复现和Windows文档镜像后停止，提交架构评审。
