# UAEA

UAEA（Unified Autonomous Evolution Architecture）研究如何通过持续交互理解用户方向、修正认知，并改善未来决策。现有主路径为 **冻结的 Phase-1 语义契约 + Harness 执行基础设施 + 隔离的 Goal Hypothesis 研究**。

Harness 拥有 Agent Loop、工具执行与 Turn 生命周期；UAEA 维护来源、版本、候选状态和授权边界。坚持 **LLM proposes / Runtime validates**：来源合法、调用保存成功不等于语义正确，Retention 不等于 Adoption。


## 当前进度（2026-11-18）

M3 的候选修订、保存与跨进程恢复已有实例，整体为 **PARTIAL**。相同普通历史下的采购对照中，两组均交齐风险和下一项核验。M4 的两次换手实验里，临时代班结束后恢复采购交付；长期改成新人练习时，当期有题有答，下期漏了可作答的题干。两支均为零提案。M4 长期可靠性和 M5 决策增益仍为 **UNKNOWN**。

现已准备从独立空 profile 开始真实人工使用。CPU 演练验证了同一 Thread 的跨进程接续；实际用户是否少返工仍待观察。[阶段与运行边界](docs/research/m4-human-pilot-checkpoint-20261118.md) · [研究地图](docs/research/research-foundation-map.md)

## 2026-11-17 阶段记录

[S1零件单批回放与18真实请求](docs/research/s1-parts-20261117.txt)：P0限定22Journal/23输出去重6版本，3修订初标改向1/纠误解1/歧义细化1，2场景例外、合理重算核验0、明说不做却给数值1；事后行为检验6/6，未来真实取舍0。P1 FAIL：合理纠正误拦3/3→0/3仅构造，但同身份新用途误放；P2样本不足：可比5题type3/5、联合2/5，与关键词/多数类type3/5持平，4接手均20%无B收益；P3 FAIL：已知1/1、随机阴性0/50误报但仅49不同Turn，两个硬负例误报，单次修复1/2；P4样本不足。四项不并入正常Goal路径，保留标注/离线诊断；18Native/HTTP完整、无新用户必填字段或强制拒绝门。NVIDIA修复180s首次等待后继续同一请求至192.3s的预算偏差披露，未重发。原保护有效、Commit缓冲2.826GiB、模型停；未Commit/Push，不扩展滤波/选择似然。

上一轮S1 Shadow数学核查保留：

[S1 Shadow数学核查](docs/research/s1-shadow-20261117.txt)：最小支持评分滤波/例外FSM已隔离实现，25CPU与独立2400随机更新通过；C平坦不能有效纠正旧解释、N平坦仍随hazard漂移、η未校准。真实留出准入不足：指定导出仅1个项目会话24human、无Host执行身份；研究者场景/重复恢复不算独立用户变化。未拟合混淆矩阵/参数，B1–B4真实留出及校准NOT RUN/UNKNOWN。两条选定旧泄漏离线可标出，但同时scope变化，未证明消费状态比scope检查更强，亦无实际防止行为。仅Shadow、不写Journal/Context/SQLite、不加载GPU；S1 PARTIAL，M3 PARTIAL、M4/M5 UNKNOWN，停止待外部Audit、不进入S2、未Commit/Push。

## 2026-11-16进度（保留）

[当前NVIDIA主题八次接手](docs/research/current-task-topic-20261116.txt)：固定原话/历史/初始Goal，B仅增加当前NVIDIA主题，旧historical_topic完整保留。一次例外B两次仍明确误续；A一次许可未明确/只留计划、一次420秒截断（中间误续并已输出错误数值ROA）。持续解除两组均未重新禁用，完整答复均未完成有资产依据的ROA检验；一份A零工具却虚称读ledger。B四份有小结不等于研究正确，不改正式主题生成，停止标签变体。B一次真实form保存错误本地解释228f4e4，Global仍bded94；后续视图变化如实披露，不再声称该分支Goal全程固定。8分支7完整最终/1超时，24传输23完整1因超时断流，33读取30成功3失败；1692有效资源样本、Commit缓冲3.684GiB，模型停。用户明确取消额外AC检查，本批未查询AC，原资源Guard/阈值不变。M3 PARTIAL、M4/M5 UNKNOWN，TaskDecision仍默认关闭，未Commit/Push。

上一轮旧主题轮次标签记录保留：

[旧主题轮次标签八次接手](docs/research/topic-turn-label-20261116.txt)：原出站已是historical_topic，先纠正把console/topic当当前标签的旧解释；B仅改“上一轮任务主题”、原句不动，固定Goal/原话/历史/工具，各场景A/B两次反序。一次例外A两次明确误续，B一次误续/一次许可未明确；持续解除两组均两次继续允许。数值ROA仅原组持续解除1次，一次例外无数值越界，不能因没算认定识别到期。A有1次交付前回问，另1次框架后留取证给用户；B均有本地小结但仍错搬“本轮”，将旧“不要求现在算”说成当前“要求不算”。未支持先修正式轮次字段，继续区分时间绑定/不必与禁止/判断及执行，不重新开启TaskDecision。8Native/25响应完整，20读取尝试16成功4失败，0新Goal，视图固定。原保护/参数不变、Commit缓冲3.304GiB、模型停、未Commit/Push；M3 PARTIAL，M4/M5 UNKNOWN。

上一轮Goal H2与出站标注勘误保留：

[Goal H2：一次例外／持续解除暂停](docs/research/goal-h2-temporal-20261116.txt)：同一真实旧起点分别分出RH-only / RH+Goal，正常Harness接手4轮、13响应完整。一次例外两组均错延到NVIDIA，持续解除两组均继续允许；没有方向错误减少。仅历史一次例外零读取/只准备交付，另有Goal交出正文但同样错延；持续解除原流程5读、Goal2读，均有独立金融/证据问题，不能把有正文当可信建议。内部topic保留旧轮文字，但实际出站已标historical_topic（后续核验勘误），不能认定存在当前标签错误；head仍bded94含旧暂停条款，非准确更新Goal的纯收益测试。637有效服务样本、原线缓冲3.833GiB，模型已停；TaskDecision V2保持默认关闭，M3 PARTIAL、M4/M5 UNKNOWN，未Commit/Push。扩展前置失败series-09独立保留、不混计。

后续实际请求勘误：控制台topic不是模型收到的字段标签；旧内容已位于background.historical_topic，并有历史边界说明。[出站标注勘误](docs/research/goal-h2-temporal-20261116-erratum.txt)。原结果计数不变，原报告保留；新一轮只比较更具体轮次标签。

上一轮TaskDecision V2已收尾：

[TaskDecision v2：推荐关联判断，原文/推导分离](docs/research/task-decision-references-20261116.md)：原r06人工协议迁移CPU接口通过（非新模型）；ID格式完整暴露，15项任务测试+25原回归通过。真实六场景每臂各2次共24Native/HTTP/模型完整，修改版12份JSON均完整、2份Host接受；全文可用原流程9/12→2/12，完整判断9→4，仍有别名逐字拒绝、排序当资格、未知被抹平。平均22.79→53.14秒，无交付收益，按要求保留默认关闭诊断原型，模型已停、未Commit/Push。

上一轮TaskDecision v1保留：


[本轮任务资格记录→推荐最小实现](docs/research/task-decision-20261116.md)：新增默认关闭研究开关，复用当前Input/EvidenceReference、Harness结构化最终输出及同源短答，不写Goal/教训。11新CPU+25原回归通过，真实交付FAIL：说明投影版12启用均无协议记录；接线后6对原流程6行动合理、1未知标题过强，启用5字段/引文/覆盖拒绝+1输出截断，零可执行建议。不能将拦截当改善；平均23.85→67.31秒，先改引用接口而非加语义裁判。一次Commit规划拒绝独立保留，资源恢复后原预算/停止线通过；模型已停，未Commit/Push。

上一轮明确事实对照保留：


[已给/未给事实跨场景12次配对](docs/research/explicit-missing-facts-20261116.md)：固定原教训、诊断ON/新通用规则OFF，采购验收且当天可用vs仅验收、文档已提交获批vs批准状态未取，各3独立交错。采购明确事实2/3忠实、未知1/3全程保留；文档R2主条件各3/3区分，但1次错误总结两版都不满足（自己承认R1已批）。不能按最终选择判全通过，也不足以泛化所有领域都会混；优先定位采购时序关系和资格总结一致性。12最终/12响应完整、原保护不变模型已停，未Commit/Push。

上一轮采购教训句尾研究保留：

[采购教训“早于”句尾18次对照](docs/research/lesson-earlier-boundary-20261116.md)：当天/晚一天×不送正文/原教训/中性句尾×3独立交错。当天不送3次资格与选择正确；原文2正确1错排；中性最终3甲但1次资格标题矛盾。晚一天三条件均3次排除甲选乙。没有“只有原文反复收紧”的模式，不把单次差异定因或保存中性改写；已知可用事实被降级为仅验收/未知的失败保留。18最终/18响应完整，原保护不变模型已停，未Commit/Push。

上一轮单字段三状态对照保留：

[已知事实→结论单字段三状态对照](docs/research/known-fact-conclusion-20261116.md)：固定旧教训和诊断，直接供给SIM字段、关闭工具。基线与通用规则后各6题：文档80/0/未知均正确；采购晚一天均排除，但当天可用仍被两次误判不合格，未知标题仍过强。96T通用规则未修复主要错误，默认关闭；不将事实复述或个别价格理由改善算认知通过。12最终/12响应完整、25 CPU通过，保护不变模型已停，未Commit/Push。

上一轮收到教训后的资料交付研究保留：

[答复依据研究开关与12分支对照](docs/research/correction-response-basis-20261116.md)：从实际回执投影本轮取得的正文范围，两个领域共用、默认关闭。25 CPU、12最终/21模型响应完整。草案少读3文件，但采购需附件时启用组零读取错答，文档缺定稿误答0台；普通组也有日期正确仍选错。没有可靠交付收益，不默认接入；同义/近词检索仍有漏送误送，原保护/正式权限不变，模型已停，未Commit/Push。

上一轮适用范围研究保留：

[教训适用范围单点对照](docs/research/correction-lesson-scope-20261116.md)：只把检索依据改为已有适用范围，两次无关纠正不再送达旧采购正文，原记录保留。相关任务教训正文仍相同，到货两组均零读；新组必要可用条款一次漏取、另一次读对仍矛盾推荐，不能宣称稳定省查或无召回损失。20真实分支/37完整响应、19 CPU通过；原保护不变，模型已停，未Commit/Push。

上一轮最小连续性证据保留：

[纠正候选跨任务连续性：代码、接口与真实验证](docs/research/correction-lesson-continuity-20261116.md)。
新增显式研究入口，复用MemoryCandidate/EvidenceReference/SQLite，不改正式Memory Admission或默认人工入口。
两条候选真实保存，8/8启用新任务收到对应教训；16分支候选/来源保持。
基线6/8、启用7/8正确，但新增6次非必需读取和一次无效路径，错误推荐仍复发，不能宣布稳定省心收益。
源码与来源保护CPU最终16项通过；旧SQLite大测试有10项缺夹具失败，日志保留。原资源配置和Fail-Closed不变；未Commit/Push。

## 2026-11-15 进度快照（历史）

[近期研究汇总](docs/research/goal-evidence-handoff-status-20261115.md) · [历史报告简档](docs/archive/local-reports-20261115/README.md) · [本次Git同步范围](docs/implementation/checkpoints/goal-evidence-checkpoint-20261115.md)。

- **M2存在性已建立，M3仍PARTIAL，M4/M5 UNKNOWN。** 真实候选可修订、保存和跨会话恢复；尚未证明稳定自主维护或相对普通历史的决策收益。
- **镜子研究收尾，暂不正式接入。** 离线与真实Harness小样本没有显示稳定实际收益；P014不再调提示。
- **候选权限已澄清。** 非权威提议不要求另说“保存”；中性权限说明条件下已真实改向企业AI算力采购/部署风险。临时ROA安排仍可能混进Goal，例外到期和后续证据使用不可靠。
- **最新交付提醒：熟题局部改善，不是完整通过。** B回查前两家、补齐收入，但仍误报AMD资产未披露，最终3072上限截断；A摘要异常，迁移选点不满足较强待交付条件，只作旁证。
- 原Windows/WSL/AC及Fail-Closed、56/72/64K/1GiB/单并发保持；当日只做归档、CPU回归和Git同步，未运行新模型。

原报告/失败原件保留；以下旧日期段是历史截面，其“暂停/下一步”不是当前指令。金融和采购方向是隔离实验材料，不自动成为真实用户个人Goal。

## 2026-11-14：Multi-Handoff Cognitive Continuity（历史补证）

[大阶段报告](docs/research/multi-handoff-cognitive-continuity-20261114.md)，批次multi-handoff-20261114T011921Z，总体 **PARTIAL**，限定研究已完成并停止，等待外部独立Audit AI和Architect决定下一阶段。

从真实B3继续主链6个新用户轮，经历3次受控压缩和Harness进程恢复；同一末端独立ON/OFF各1轮，合计8新轮、16完整响应、9真实读取，不能拼成一条连续10轮。原始版本/来源恢复限定VERIFIED；期间错配跨摘要进入实际计算，进度误报与摘要遗漏、旧open_questions共同出现，各因果贡献UNKNOWN。U8理解新目的但零Goal调用，旧head诚实保留；单次stale Goal View配对无增益证明、ON有来源错配反例。

研究入口独立compact改绑Input的CPU反例已用隔离路由规避，正式adapter未改；恢复器v1跨Input绑定缺口在新增v2离线补验，实际B3/s1/s2均通过。原失败、Journal、Native及工作树修改保留。M2既有存在性不变，M3沿用PARTIAL且本批没有新修订head使用成功，M4/M5 UNKNOWN，Memory Research Reserved。Commit最低缓冲0.709GiB，未越线但不支持扩负载；无权限/配置扩大、Commit或Push。


## 2026-11-13阶段记录（历史截面）

最新[M3连续行为与限定M4报告](docs/research/goal-m3-continuity-behavior-20261113.md)及独立审计总体 **PARTIAL**：

| 研究里程碑 | 当前结论 |
|---|---|
| 用户意图归属 M1 | PARTIAL；User Goal与模型待办分离，仍有方法/目的混写倾向 |
| 受反馈纠正 M2 | 限定存在性 VERIFIED：真实跨会话revise、CURRENT、Host保存和新head送达；不等于自主维护 |
| 后续连续性 M3 | PARTIAL；从A真实修订继续，跨Thread/跨便签Task后均有相容工作；Goal因果作用未确定 |
| 自主 Goal 生命周期 M4 | UNKNOWN；本次理解替代方向却两轮零提交，未虚称保存 |
| 超过 Relevant History 的决策价值 M5 | UNKNOWN；两次结构化View配对质量/成本混合，主ON有输出上限删失 |
| Goal Continuity 工程 | Journal/版本/Scope继续保持；Global family人工绑定不计模型自主能力 |
| Memory | Research Reserved；不开放Memory Admission |

本轮三个独立批次共8用户Turn、11完整传输，10完整生成、1个2048输出上限CENSORED；不把HTTP/Native完成等同答案完整。两组普通历史均保留真实A修订/回执，实验只评价当前结构化Goal视图的增量。用户指定后续以金融/股票研究为对象，不据此推断个人投资Goal或交易偏好。

随后按用户选择开展[真实金融来源案例](docs/research/goal-real-finance-case-20261113.md)：两组因预算与正文供给限制CENSORED；OFF自然保存了两个local提案版本，但没有形成合格长期维护/决策闭环。已完成独立CPU资料分段可达性验证，未重跑模型或修改正式接口。

最新[长期Context与可信证据大阶段](docs/research/context-continuity-trusted-evidence-20261113.md)总体 **PARTIAL**：真实同Thread受控Compaction、Host Goal/Scope/纠正恢复及后续两项经营率形成限定闭环；完整回答仍有单位/期间/资料范围错误。累计7请求、两次加载，内部Subagent核验完成，现已停止，等待外部独立Audit AI及Architect下一阶段决定。M3总体PARTIAL，M4/M5 UNKNOWN，无新的ON/OFF、采纳或权限开放。

最新[资料可达性与Context联合评估](docs/research/evidence-context-accessibility-20261113.md)总体PARTIAL：已修复800字符正文fallback与UTF-8二次截断，A自主定位完整财务表送达；A最终研究驱动Compaction删失保留，B明确缺失场景保持UNKNOWN，C两成品仍有科目/利润率和阅读完整性错误，Goal增量价值UNKNOWN。六个A/B请求的字节hash与API Token精确核账；固定64K及原资源保护，未Commit/Push。

候选仍是 opt-in、非权威、可撤销解释，不能自动成为 ActiveGoal、可信 Memory 或执行授权。没有新增 Goal Engine、第二套 Agent Loop 或通用语义裁判。

### 当前 N1X 研究配置

| 配置 | 已验证的隔离研究入口 |
|---|---|
| UMA | GPU 56 GiB / Host 72 GiB |
| Backend | Nemotron Bolt 74B，vLLM 0.32.0 |
| Harness | Codex rust-v0.163.0 |
| Context / KV / 并发 | 64K / 固定 1 GiB / 1 |
| GPU utilization | 0.65，仅该隔离入口 |
| 安全 | 原 Windows/WSL/AC、单时钟遥测与 Fail-Closed；不降低阈值 |

这不是将所有正式入口切为64K或0.65。32K及64/64原启动配置仍保留；[历史32K运行基线](docs/current/runtime/n1x-runtime-baseline-20261027.md)不代表最新研究负载。容量、长期会话与资源证据见[Phase1 64K连续研究](docs/research/phase1-finance64-continuity-20261112.md)、[UMA限定负载](docs/research/uma56-controlled-load-20261111.md)。

## 阅读与研究入口

- [文档总导航](docs/README.md)与[当前进度](docs/current/README.md)：先区分冻结契约、研究机制和历史结论。
- [研究索引](docs/research/README.md)、[研究地图](docs/research/research-foundation-map.md)：保留正面、负面及 UNKNOWN，不按旧文档中的“下一步”自动执行。
- [Goal 连续性使用方法](scripts/research/README-goal-continuity.md)：本地研究 Journal 是单一候选 authority；不恢复旧 Workflow 为新执行。
- [Goal Sideband 研究通道](scripts/research/README-goal-hypothesis.md)：工具提案、Host 接受、保存、投影和认知判断分别评价。
- [本次 Git 检查点与证据范围](docs/implementation/checkpoints/goal-research-checkpoint-20261113.md)：代码、轻量回归、外部原始证据和已知限制。

原始研究记录保存在仓库外 research-records，Windows 评审包保存在 UAEA_DOCS。仓库提交源码、固定场景、报告及摘要/哈希，不包含模型权重、凭据、Native SQLite 或完整会话日志；外部原始证据路径不保证在新 clone 上存在。

## 保留的执行与权威边界

以下冻结职责继续有效；历史人工环境的具体参数另有日期，不将其解释为最新研究配置。Phase-1 不因本轮 Git 同步而变更。

## 当前架构与职责

```text
User
  -> UAEA semantic extraction / scoped effective state
  -> bounded pre-turn additionalContext
  -> source-owned local Codex app-server (rust-v0.163.0; v0.154.0 retained)
  -> UAEA local provider-safe history projection
  -> replaceable model Backend / local vLLM
  -> model action proposal
  -> UAEA semantic validation / ToolRegistry capability boundary
  -> execution observation / bounded actionable evidence
  -> Harness continuation / turn completion
  -> raw events / semantic diagnostic snapshots
```

**Harness Runtime Baseline: CLOSED**。**Codex Core fork: NOT REQUIRED**。

| Harness owns | UAEA owns |
| --- | --- |
| thread persistence / turn lifecycle / model invocation | capability-specific semantic contracts |
| generic context transport / token window / compaction mechanics | semantic extraction / classification / ownership / scope |
| native File / Shell / Sandbox | effective semantic state / bounded semantic projection |
| generic tool lifecycle / continuation | 独立 promotion basis / semantic authority / action validation |
| raw runtime event emission | evidence semantics / provenance / trajectory normalization |
| generic execution mechanics | future Goal / Memory / Episode cognition |

UAEA → Harness：typed `additionalContext`、dynamic tool schema、经过语义校验的 capability result。
Harness → UAEA：有序 thread/turn/item events、tool result、command execution、token usage、错误及 terminal boundary。
执行事实以结构化 result 为准；requested provider、actual provider 和 successful execution 不可互相替代。

## 历史 5090D 人工入口与保留配置

```text
RTX 5090 D v2
24GB VRAM
single GPU
Qwen2.5-14B-Instruct-AWQ
4-bit / AWQ
vLLM
```

冻结的 `8001` 保持原配置。当前人工 Harness 使用既有 `8002` diagnostic profile：
`max_model_len=32768`、`gpu_memory_utilization=0.75`、Codex `model_context_window=32768`、
`--enable-auto-tool-choice --tool-call-parser hermes`。实际 effective window 可能由 Harness 再折算，不改实验条件。

在已配置的 WSL 中：

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

`python3 scripts/harness_version.py --verify-binary` 查询实际锁定版本；
在启动命令前加 `UAEA_CODEX_VERSION=rust-v0.154.0` 可单次回退，使用独立 `CODEX_HOME`。
默认值只在 `harness/versions.json` 维护；启动 artifact 的 `harness-versions.jsonl` 记录实际 Tag/Commit。

Web 代理和 `SERPAPI_KEY` 自动从仓库外 `~/.config/uaea/web.env` 加载；权限必须为 `600`。
不要将真实 key 写入 repo、命令行或聊天；[私有环境配置](docs/current/environment/web-runtime-environment.md)。
该入口保留停止 app-server/8002 的原逻辑，不启动旧 direct Web REPL。

## Phase-1 Semantic Baseline 的状态

冻结子模块：`runtime/phase1-runtime`，commit `1f311291df027baceca40779643e5107b9eb6fb3`。

- Phase-1 generic runtime mechanics：作为 legacy/A-B baseline 保存；主路径由 Harness 接替。
- Phase-1 semantic architecture：通过 `harness/semantic_state_adapter.py` 复用
  `ContextManager`、`TurnRelationRecord`、`ExecutionObservation`、`SemanticObservation`、
  `RuntimeObjectRecord/Store`、`WorkflowRunRecord` 与 `ProjectionRecord`。
- Workflow/Step records 在 bridge 中提供 task identity/ownership 和行动事实记录，不启动旧 planner 或 execution loop。
- ActiveGoal anchor 代码保留，但当前 Harness bridge 不激活；`ActiveGoal != future longitudinal Goal Hypothesis`。
- 当前有限 relation/extraction surface 不是完整 intent arbitration，也不保证任意多 topic/隐含任务切换。
- Goal Hypothesis Sideband 和本地 Continuity 已在隔离研究入口实现，正式 ActiveGoal 不自动采纳。
- Working Memory / Episode / Experience engine 未接入；Memory Candidate/SQLite source-evidence 资产保留，不等于可信长期记忆已建立。

## Web Semantic / Evidence Boundary

Google semantic provider 已由 SerpApi backend 实现；`serpapi` 只是 acquisition backend，不是 model-facing provider。
Harness/inference 仍在本地，Web 请求是显式外部 capability。

- 输入只有 `provider`、`allow_fallback`，结果分离
  `requested_provider/actual_provider/acquisition_backend/fallback_occurred/fallback_reason`。
- strict `allow_fallback=false` fail-closed；显式 provider 缺少 fallback policy 时不执行。
- 在 semantic bridge 中，模型提出 `allow_fallback=true` 不构成授权：
  只有有效 user-derived scoped policy 可授予；unknown/pending 被拒绝。
  provider 未指定且不显式提出 fallback 的既有默认 policy 保持不变。
- 执行失败不进入 evidence relevance 分类；raw provenance 保留，
  low-relevance links 不作为 model-visible citable evidence。
- bounded result 可减少 snippets、metadata 和候选数量，但保留每个候选的完整 `title/url` 及来源 identity。
  projected citable count 与实际保留列表一致；无法容纳身份时明确报告限制，不输出残缺 URL。
- 来源/语言/时间要求仍是 best-effort，不承诺真实“热度排行”或跨站点访问成功。
- 网络诊断在实际请求进程记录 open/header/read、HTTP/SSL/proxy/timeout 信息；不进入 model-visible projection。
  timeout 仍是 20 秒，不新增 retry。

[Google backend 历史接入记录](docs/historical/web/google-backend-phase1.md) ·
[网络诊断](docs/implementation/web/web-network-observability-phase1.md) ·
[当前边界与剩余风险](docs/current/architecture/boundary-integrity-audit-20261002.md)

## Trajectory 与验证

Normalizer → Writer → canonical run-level JSONL → Reader/validator 的 contract 保持：
`<run_id>.trajectory.jsonl` 是 writer run 的 canonical source；
thread 文件只是 derived projection。sequence 是 UAEA 接收顺序，不是 Harness 内部因果序号。

Lifecycle probe 和当前人工 REPL 均接入 writer；人工 run 保存 `app-server-events.jsonl`、adapter trace、
source history、semantic snapshots 与 canonical normalized trajectory。
未来 cognition 必须优先消费 raw trajectory，不能把 compacted summary 当唯一原始经历。
失败 attempt 事实永久保留；发送给 provider 的副本将明确终结调用投影成不可执行 observation，
不让 malformed history 阻断后续 turn。[隔离边界与同 thread 恢复证据](docs/implementation/harness/failed-attempt-recovery-20261003.md)。
拒绝结果通过 [typed recovery observation](docs/implementation/harness/rejection-recovery-observation-20261004.md)
保留有效约束/授权来源并给出新 attempt 的合法选项；历史 policy 不是未来授权，重试仍经过当前 validator。

```bash
python3 -m unittest tests.test_harness_boundary_integrity tests.test_harness_semantic_state_adapter
python3 -m unittest discover -s tests -t .
python3 runtime/phase1-runtime/tests/runtime_benchmark/phase1_runtime_benchmark.py --mode scripted --level all
```

真实失败 artifact 与只读重放证据见 Boundary Audit。修改后须人工复测真实 search → fetch，
确认模型引用的是 retained candidate，而不是自行补造链接。

## 历史与下一步

历史不删除；[原 README](docs/archive/harness/readme-before-boundary-audit-20261002.md) 保存此前
Phase-1/Phase-2A、LMF 和早期 Harness 的完整描述。
[Harness baseline](docs/current/runtime/harness-runtime-baseline-20260926.md) 保留冻结依据；
[历史索引](docs/archive/harness/README.md) 区分当前结论与阶段记录。
LMF/其它 inference adapter 是保留的研究资产，不是当前 Harness 验证路径。

当前研究保持在 Goal Hypothesis 的语义忠实性、跨会话连续性及实际决策价值验证；下一轮是否扩大研究由阶段评审决定，不因归档或 push 自动开始实验。Memory 数学建模仍 Research Reserved。

冻结权威关系见[信息边界 checkpoint](docs/current/architecture/cognition-boundary-checkpoint-20261005.md)；该历史文档的人工待验状态不代替2026-11-13研究结论。只有现有 Harness 缺少必要执行事实、状态可观察性或投影能力，才重新讨论基础设施；模型语义错误不自动要求新增 Runtime 纠错层。


## 2026-11-17 Goal Cognitive Reliability（PARTIAL，已停止待外部审计）

[研究收尾](docs/research/goal-cognitive-reliability-20261117.txt)：复用修复P0及原Native/HTTP/Journal，区分改目的、纠误解、Task和例外；S1继续Shadow，不自动融合。新批次从真实AMD完成点分Goal视图ON/OFF两臂，原拟6轮；实际2次恢复、2次自然Compaction，但均420秒CENSORED、0最终，4依赖NOT RUN。A35读取仅5个Call回执进入后续请求，B4读均送达；B摘要现金流原表正确，却将未交付的NVIDIA小结记作完成。首请求存在非Goal预算挤出混杂，不能估纯Goal视图因果收益。885有效服务样本，Commit原线缓冲2.994GiB；无额外AC检查，模型已主动停止。M2存在性保留，M3 PARTIAL、M4/M5 UNKNOWN；无正式Runtime/Schema/权限改变，不Commit/Push，不进入S2/S3。
