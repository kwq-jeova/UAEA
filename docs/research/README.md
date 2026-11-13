# UAEA Research Foundations

Status: RESEARCH_FOUNDATION
Role: 研究导航，不是实现授权

## 最新研究状态：2026-11-13

[三场景联合验证](goal-continuity-three-scenarios-20261113.md)：M1 PARTIAL；M2跨会话显式纠正限定VERIFIED、抽象冗余PARTIAL；M3仍PARTIAL，M4/M5 UNKNOWN。A新head不由独立B/C继承；C两对ON/OFF并未证明结构化视图的额外决策收益。32版本是Thread可见集合限制，不是Profile总版本限制。Memory仍Research Reserved，无正式采纳或新Goal Engine。

最新[Git检查点](../implementation/checkpoints/goal-research-checkpoint-20261113.md)归档已有代码、场景、报告与摘要。以下旧段落保留当时判定，不能把旧“下一步/待修”当作当前命令；原始负面记录不覆盖。

| 正文 | 思想价值 |
| --- | --- |
| [Memory Boundary Architecture](memory/phase2b-memory-boundary-architecture.md) | Context/Candidate/Memory 分离，intake 选择与对抗评审，Goal/Failure/Observation lifecycle |
| [Memory Architecture Boundary v0.1](memory/memory-architecture-boundary-v0.1.md) | object/state/facet、关系与validity、reactivation；不是新的已实现engine |
| [Memory Architecture Fixtures](memory/memory-architecture-test-fixtures.md) | 100-turn 混合历史的atomic candidate/provenance与噪声验收思想 |
| [Context / KV Feasibility](context/runtime-web-context-kv-feasibility.md) | §§5–7的bounded projection、history风险、跨时间memory weight信号；旧实施计划已替代 |

[Research Foundation Map](research-foundation-map.md) 按 Goal/Memory/Episode/Context/Meta-cognition 连接以上思想及 archive 中的证据。
尚未实现不等于应归档；旧 runtime 假设不等于应恢复旧 execution stack。


## 2026-11-12 Goal研究阶段进度（独立分支验证前）

本节为当前研究进度索引，不替代冻结架构或正式Runtime基线。详细历史见[研究地图](research-foundation-map.md)及[真实恢复与纠正记录](goal-history-recovery-correction-20261112.md)。

| 事项 | 当前证据等级 |
|---|---|
| 真实历史Goal恢复 | 限定PASS：goal-history-recovery-20261112T061038Z |
| Step–Observation通用绑定 | 发现缺口，待最小修复；已有真实案例通过不等于通用校验完整 |
| 准确读取已有候选 | 已出现明确误述，待M2-A独立验证 |
| 用户纠正后的真实修订 | 未发生，保留原生负面证据 |
| M2受反馈纠正 | 一次失败观察，尚未完成读回/修订隔离 |
| M3跨轮状态一致性 | 完整闭环尚未建立 |
| M4自主生命周期 | UNKNOWN |
| M5相对Relevant History决策收益 | UNKNOWN |

事实依据：scripts/research/recover_goal_history.py；/home/wqkan_wsl/uaea-n1x/research-records/goal-history-recovery-20261112T061038Z/session/app-server-events.jsonl。模型完成声明不是Host完成事实。Sideband保持非权威，Memory仍Research Reserved。

## 2026-11-12 阶段补证：M2 独立读回与纠正

见[阶段结论](goal-m2-branches-20261112.md)、[M2-A独立报告](goal-m2-readback-20261112.md)、[M2-B独立报告](goal-m2-correction-20261112.md)。

| 项目 | 最新证据范围 |
| --- | --- |
| 历史恢复绑定 | VERIFIED，限定PASS；Step/Observation/Call/Turn/Thread/执行归属补齐，合法历史不变 |
| M1 / M2-A | M1 PARTIAL；M2-A全文及保存状态读回单样本PASS |
| M2-B | 单反馈样本FAIL：6次引用不合规拒绝、0保存，最终错误声称已纠正 |
| M3 | NOT RUN；无新head，能力UNKNOWN |
| M4 / M5 | UNKNOWN，不以明确反馈调用或传输完整替代 |
| 下一步 | 本轮证据已形成，暂停评审；建议仅研究当前触发quote/历史basis/拒绝状态理解 |

批次 goal-m2-branches-20261112T073526Z。此前失败不覆盖；无正式采纳、Memory工程化、Commit或Push。

### 2026-11-12：M2 CURRENT / 历史依据分离与失败反馈专项（启动前）

批次 goal-m2-current-feedback-20261112T083318Z。上一批真实拒绝/无新版本/最终错误状态声明继续保留；追加勘误：模型收到terminal_attempt_fact，不能声称完整committed=false Goal回执已送达。现有quote（当前触发）、input_ids（原目的依据）、candidate_id（被修正head）足以表达本例，正式Schema不改。计划一次独立B纠正，首次拒绝即停止；若未闭环，再以同一冻结真实失败请求只改变反馈表达作双组诊断；M3仅在真实修订后运行。M1 PARTIAL，M2-A限定通过，M2-B尚待本批次，M3未闭环，M4/M5 UNKNOWN；Memory Research Reserved。

### 2026-11-12：M2 引用/真实保存已推进，语义纠正与 M3 尚未闭环

- [M2实际修订及准入报告](goal-m2-current-correction-20261112.md)，批次 goal-m2-current-feedback-20261112T083318Z：一次反馈、2个合法revise，CURRENT quote与历史purpose input_ids分离，真实Host保存及后续同Turn投影、新ID报告VERIFIED；不是自然形成/M4。
- **M2-B PARTIAL**：新文本加入“不需要任何长期限制”，不能由“不自行添加长期限制”直接推出。M3语义门未过，下一用户Task NOT RUN；不把同Turn新head送达冒充M3。
- 本地研究工具说明准备了但未进入恢复Thread的实际请求，实际工具定义与上一批相同；不得把成功归因于说明改善。正式Schema不变。
- [失败反馈独立对照](goal-m2-failure-feedback-20261112.md)：旧“完整committed=false反馈已送达”表述已追加勘误；实际为terminal_attempt_fact。C1构造哈希错误原样保留，不作为有效比较；新批 goal-feedback-control-fixed-20261112T085326Z 用正确Host摘要完成一次C2配对。两组仍用历史quote、无状态回答，未证格式收益，状态理解UNKNOWN。
- M1 PARTIAL，M2-A沿用限定PASS，M2-B总体PARTIAL，M3 NOT RUN，M4/M5 UNKNOWN。无正式Runtime/Schema/授权/Memory变更，未Commit/Push；本轮限定验证结束。

### 2026-11-12：P1语义忠实性 / P2状态报告 / 条件式M3（启动前）

批次 goal-p1-p2-m3-20261112T093455Z。独立验证并恢复最新4版本/2个修订head，不重造种子；原一Turn恢复器不改，研究副本逐层校验Goal-only追加Turn。P1冻结三个独立表达分支；P2用真实旧拒绝记录加两组相同状态核对问题，只改变反馈文本；M3仅从合格真实候选选取。原Scope/来源/Journal保留，实际工具定义锁定，CURRENT不放宽；Memory Research Reserved。M1/M2语义仍PARTIAL、P2待验证、M3未建立、M4/M5 UNKNOWN。实验结果不得提前上调成熟度。

### 2026-11-12：P1三种表达 / P2状态报告限定实验结束

批次 goal-p1-p2-m3-20261112T093455Z。[P1语义与M3准入](goal-p1-faithfulness-20261112.md)、[P2失败反馈报告](goal-p2-state-report-20261112.md)。

- VERIFIED：最新4版本/2修订head分层恢复，7篡改反例拒绝，真实出站工具/heads/输入可追溯，原记录不变。
- P1：3输入，2个完整Turn、1个首次quote拒绝后主动停止；0新版本。场景1仍把未知变成全部否定；场景2识别问题但以采纳禁用/版本不可变解释不能修订；场景3非CURRENT逐字引用被拒。没有合格候选，M3 NOT RUN。
- P2：相同状态核对问题的原反馈/明确状态配对均有完整回答。A混淆旧成功form和最新失败revise；B正确报告拒绝/未保存/head未变，但仍错配实际提案正文。两组都丢失失败Call→提案正文可见绑定，模型未保留该UNKNOWN；整体PARTIAL。
- 只提出在既有投影保留有界提交事实/身份的兼容建议，未改正式Runtime/Schema/权限；未新建语义裁判、Goal或Memory引擎。
- M1/M2语义仍PARTIAL；保留历史M2合规操作限定PASS；P2 PARTIAL；M3 NOT RUN，M4/M5 UNKNOWN。Memory Research Reserved，未Commit/Push。本轮停止评审，不重试取得PASS。


## 2026-11-12 Goal 失败提案历史投影工程收敛（最新）

[根因、修复、预算与真实出站核验](goal-failed-proposal-history-20261112.md)：批次 goal-failed-history-projection-20261112T115442Z，最终证据 final/。真实2次成功form/6次失败revise逐Call绑定原参数、正文、目标和Host committed；缺字段保持UNKNOWN，不借旧head。24,000字节新增失败事实cap与原Host恢复块预算分别限定；省略明确，身份放不下拒绝，冲突ID拒绝转发。64项CPU及无模型真实Codex→Bridge→CPU HTTP出站通过，Audit Agent独立工程限定PASS。原历史/heads/versions不变，无模型加载，无M2/M3重跑。

历史恢复限定PASS，Step–Observation已修；M2-A限定通过/语义PARTIAL；M2-B已有真实revise但语义忠实性未通过。失败状态理解旧样本受投影缺失影响，修复后模型理解UNKNOWN；M3 NOT RUN，M4/M5 UNKNOWN。Memory Research Reserved；无正式Goal/Memory采纳或权限改变。先独立工程复核，再安排下一阶段模型理解测试。


## 2026-11-12 投影修复后的真实状态读回与纠正（最新）

[限定模型验证报告](goal-postprojection-state-correction-20261112.md)：原批次 goal-postprojection-state-correction-20261112T122139Z 的P2被研究驱动误拦合法只读调用，标记CENSORED，不评为模型失败；只修研究拦截后另建 goal-postprojection-readback-repair-20261112T123257Z，相同问题得到一个完整真实回答。字段复核更正：hypothesis为4/6，另2条将quote误当hypothesis；target/committed分别6/6；旧回答quote未独立报告UNKNOWN。撤销完整绑定PASS，P2为PARTIAL，原模型记录不改。独立B提出语义忠实refine，但历史purpose quote不满足CURRENT，Host正确拒绝，0新版本，按首拒绝停止。M2-B保存闭环未成，M3 NOT RUN，M4/M5 UNKNOWN。保留两批原件与失败，未改正式Runtime/Schema/权限，未Commit/Push；没有因一次读回成功上调自主Goal或决策价值。下一步仅聚焦当前纠正触发证据与历史目的依据的工具绑定。


## 2026-11-12 Goal 字段理解与引用选择限定验证（最新）

[评分更正与新A/B](goal-field-understanding-correction-20261112.md)：旧P2按同Call字段复核为hypothesis4/6，2条quote误填；旧完整绑定PASS撤销。新A为hypothesis6/6、quote4/6、target6/6、committed6/6，前两条quote被扩写，整体PARTIAL；这些是一次回答中的相关字段，不是独立概率实验。B明确提供合法CURRENT句及历史f4依据，模型真实revise仍选择历史quote，Host正确拒绝、0新版本；语义方向基本保留但研究性质省略，PARTIAL。拒绝后状态回答CENSORED，新head投影无对象；M3按边界不运行，M4/M5 UNKNOWN。实际HTTP完整/源码与权限不变；不自动修参、重试或扩大Goal架构。原始模型记录保留，旧评价另存；独立审计已确认上述分维结果，整体PARTIAL，提交评审。


## 2026-11-13 Goal M2 历史失败明细消融及条件式M3（最新）

[限定研究报告](goal-history-ablation-m2-m3-20261113.md)：评分器问题归档不再重测；同候选/当前输入/Schema/预算，移除6条旧失败明细组仍误用历史quote被拒，保留组合法忠实revise并保存ff2a…，旧版本不可变，新head在3个后续完整请求中供给。该显式受反馈M2取得限定存在性证据；同Thread M3实际转读Apple/Alphabet且全局Goal保持。历史明细效应仅PARTIAL（固定顺序、一次、ID/时间/路径差异及条件名泄漏）；M3状态/行动一致性VERIFIED，因果使用与超Relevant History价值UNKNOWN，M3总体PARTIAL，M4/M5 UNKNOWN。财务解读仍PARTIAL；不升级长期认知成熟度为通用PASS。原架构/Schema/权限不变，无Commit/Push，独立审计已确认总体PARTIAL，交阶段评审。


## 2026-11-13 当前Goal视图相对普通历史的增量（最新）

[ON/OFF限定配对](goal-view-increment-20261113.md)，批次goal-view-increment-20261113T005334Z：保持同一已纠正checkpoint、历史/回执/工具/任务，仅当前结构化视图不同。两组均记得长期方向；OFF有4次真实读取但回到Intel的理由不足，ON暂缓Intel却未实施本轮核验，且把局部暂告结束说成已完成。供给与状态边界VERIFIED，行为总体PARTIAL，结构化视图增量及M5仍UNKNOWN。OFF保留Goal历史，不能将结果扩大为整个Goal机制成败。M2沿用限定存在性证据、M3仍PARTIAL、M4 UNKNOWN；不新增机制，不Commit/Push。

独立Audit Agent已复核本批次：总体PARTIAL，可归档限定研究；没有证明当前视图增量决策收益，不支持新增正式机制。


## 2026-11-13 Goal跨会话连续性（最新）

[持久化、恢复与一次模型读回](goal-continuity-20261113.md)，批次goal-continuity-20261113T013426Z：研究Journal单authority，保留原ID/Thread/父链/来源，global显式关联、local默认隔离；50CPU及实际新Thread供给/读回限定PASS。模型没有提出要求的待验证问题，整体PARTIAL；不计M3行动闭环，M4/M5 UNKNOWN。当前可用基线仅profile-final及冻结源码，保留Thread可见集合32版本（非Profile总版本）/16MiB Journal等上限和原保护。按次对话及研究注释方法见[研究入口](../../scripts/research/README-goal-continuity.md)，无正式采纳/架构升级，不Commit/Push。


## 2026-11-13 Goal Continuity 三场景联合验证（最新）

[纠正、保持及两对视图增量报告](goal-continuity-three-scenarios-20261113.md)，批次 goal-continuity-three-20261113T030425Z：同一44,867B真实checkpoint独立六分支；Global family是人工研究绑定。A一次明确纠正真实revise保存76fe…，CURRENT/历史purpose分离、父链/新head真实送达，核心目的忠实，尾部维护说明冗余PARTIAL。B零调用保持ff2a，不把Intel局部Task结束变成长期Goal完成；没有恢复/取消旧Workflow。C两对ON/OFF只去当前结构化视图，历史Goal/工具回执均保留；实际首请求归一化一致。ON仍有指标/日期错误，OFF1最终删失、OFF2单位/量纲错误；没有可靠增量决策收益。12个模型响应完整、13次新读取绑定、983有效service样本，安全正常停服。M2限定存在性VERIFIED，M3总体仍PARTIAL，M4/M5 UNKNOWN。A新head不拼接为B/C后续链；32上限是Thread可见集合，非Profile总版本。无正式架构/权限变更、未Commit/Push；Memory Research Reserved，本轮停止评审。
