# 本地 Goal 连续性：最小持久化与跨会话恢复（2026-11-13）

**工程基线限定PASS，整体研究PARTIAL。** 一次真实新Thread准确读回已恢复Goal，但未提出要求的待验证研究问题，保留过度弃答负面样本。没有证明自主维护或实际决策增益。

批次：goal-continuity-20261113T013426Z。有效基线为补齐校验后的profile-final及本批冻结源码；早期profile/verified-profile是中间工程副本，未泛称已修复迁移。不Commit/Push，不接入正式人工入口。

## 1. 现有架构及缺口

| 现有机制 | 已有能力 | 本轮确认的缺口 |
|---|---|---|
| GoalResearch / Sideband | Host校验CURRENT、版本、父候选和来源；接受事件写Goal Journal；状态快照可读 | 内存态未由通用Journal恢复；同Thread筛选；新Thread不能直接使用旧版本 |
| GoalIntegration | opt-in Goal候选与正式采纳分离、有限checkpoint | 需原Host请求/决定已存在；不是跨Thread研究状态库 |
| RuntimeObjectStore | Workflow/input/Step/候选等运行内对象 | Native resume不等于恢复这些Host对象 |
| Source SQLite / EvidenceReference | 来源版本、访问/消息及Evidence链路 | 没有现成Goal版本/head与研究Scope恢复契约；不应当作已采纳Memory库 |
| recover_goal_history.py | 已审查历史closure的限定、证据严格恢复 | 面向冻结单例/Goal-only层，非长期日常连续性入口 |
| Provider History / Context | 普通Native历史与非权威Goal视图可分别供给 | 新Thread没有旧普通历史；Goal视图不能冒充全部Task/执行上下文 |

因此不新增数据库或正式Schema。复用原Goal事件、Candidate Version及Sideband验证，以一个本地追加Journal作为隔离研究持久化authority。Source SQLite、Phase-1、Harness执行循环、权限及正式Goal机制均未改。

## 2. 实际实现与职责

新增：
- scripts/research/goal_continuity.py：单写者Journal、严格加载/导入、版本/head归约、显式family Scope绑定、PersistentGoals研究适配与有界视图。
- scripts/research/goal_continuity_session.py：引用已受保护模型服务的新Thread研究入口，复用ProposalApp/Harness。
- benchmark/longitudinal_dialogue/test_goal_continuity.py：CPU反例。
- scripts/research/README-goal-continuity.md：使用方法和边界。

**唯一可修改候选来源：profile-final/goal-journal.jsonl。** 接受/拒绝事件、原始参数、回执、输入/Observation历史副本及关联、Scope选择和研究注释都追加在同一Journal。每会话goal-research-state.json只作派生输出，从不载入为恢复authority，不能手改它来更新Goal。

本地fcntl排他租约防协作式并发写者；写前完整校验，追加并fsync。初始化也同步文件/目录。损坏行、部分尾行、序列/哈希错误、父链/身份不一致及不支持事件拒绝恢复，不静默回退为空状态。失败加载对象也不能输出部分Goal视图。相同Call重试不产生新版本，变更同Call实参拒绝。

这是Goal-only研究持久化，不是任意Runtime/Workflow恢复。旧版本、Candidate ID、owner、原Thread、父版本、CURRENT及历史依据分别保留；新Thread不伪造旧执行，不重放历史外部调用，不采纳ActiveGoal。

### 跨Thread Scope为何需要显式研究绑定

旧Schema没有可独立信任的“长期/global”字段，不能从模型措辞自动猜出Scope。family绑定是Host研究配置，**不修改候选正文/正式Schema，也不是采纳或语义真值证明**：

- bootstrap显式指定历史全局family根098ea…；其当前head为ff2a…。
- 局部Intel根0cb6…保持local，仅原Thread可见，不迁入新Thread。
- 新form默认local，后续研究者可按明确用户依据bind-scope；模型无此操作工具。
- 新Thread修订已关联global时，新版本拥有新Thread/当前Input身份，parent仍指真实旧版本；不是把旧ID粘到新Thread改写原记录。
- 只在此opt-in适配器中解析已关联历史parent/input依据。CURRENT仍在当前Thread当前登记输入核对，历史quote不能直接通过。

上下文最多4200字符、3个head，区分当前解释、历史版本、不可采纳及语义未确证状态；必要依据按预算提供并标记省略。历史输入明确不能代替当前CURRENT。原Native文件失效则source_status为unavailable/mismatch；保留Host副本不等于外部来源重新核实。旧Observation保留ID/调用/版本关联，未构造新Step来冒充新执行。原始历史缺失的降级和canonical Journal损坏的拒绝是不同保证。

## 3. 原始Journal与恢复视图对应

真实历史基线来自上轮已保存忠实修订，不重新要求模型造种子。导入前重新比对锁定原文件、Native用户文本/Call/回执、原始Journal、版本/父链、Step与Observation绑定。

| 项目 | 原始事实 | 新Thread恢复 |
|---|---|---|
| 原Thread | 01a1cdd9-84df-7030-a240-4ea8f75089ea | 原身份不改，作为历史来源 |
| 版本数 | 3 | 3，不重复创建 |
| 原全局版本 | goal-candidate:098ea60b1c3caf2ca410b22d | 历史、current=false |
| 已纠正全局head | goal-candidate:ff2a010b338474f6ea3f66f5 | 唯一跨Thread当前head |
| 当前全文 | 长期跨公司研究AI产业投资机会是全局范围目的。 | 精确一致 |
| 当前内容hash | a3d425cfa4dd7ff1e461ef2fd7c08465ff58b2285fb5e225f27f85d9b3e4ba54 | 精确一致 |
| 局部Intel | goal-candidate:0cb6591e2475fdd96208bc87 | 未进入新Thread当前候选 |
| 原成功/失败Call | 3次实际保存、6次拒绝 | 分开保留；拒绝不产生版本/head |
| ActiveGoal | 空 | 空，无自动采纳 |

本研究种子用户角色输入属于此前冻结实验，不代表已确认现实用户的当前投资目标。导入成功、新会话读回、自然Goal形成、用户真实意图确认不能混为一谈。

[原始与恢复核对](../../../research-records/goal-continuity-20261113T013426Z/profile-before-model.json) /
[CPU真实出站](../../../research-records/goal-continuity-20261113T013426Z/cpu-outbound-final-proof.json)。

## 4. CPU验收与审计发现

最终50项定向回归通过：本轮24项、既有Sideband/失败历史相关26项。覆盖关闭/重开/另一Python进程、重复恢复、父链、全局/局部隔离、失败不成为head、CURRENT不放宽、撤回保留历史、单写者、坏文件拒绝、派生cache不载入、预算省略及正常/失败/大正文工具回执。

另有真实历史bundle的原件对照反例：正常3版本/4Observation通过，伪造正文并重算自哈希、新增虚构Observation、交换Step引用、不同Turn、重复Step均拒绝。均使用临时副本，原研究记录不改。

独立审计发现并参与复核的缺陷：
1. 入包Observation最初只校验自哈希；修复为与锁定原trajectory、Native调用/回执、Step身份及完整Host结果关联。
2. 正常失败工具曾被错误要求成功status/正文；修复后真实失败读取可继续归档，不补成成功。
3. 有界content_excerpt曾被当作完整正文对hash；现在以原Host完整结果核对完整hash，保留实际摘录长度/完整长度，复用原serializer核对有界Native回执。约78K字符真实CPU读取通过，不改正文hash。
4. Observation映射与Scope变量遮蔽导致正常导入拒绝，已分名修复。
5. 失败reload对象曾可能提供部分已归约状态，现拒绝继续投影。

这些都是工程缺陷，不能计为模型认知失败。已保留中间副本和独立反例意见；CPU固定回复也不计模型能力。真实Codex→Bridge→CPU HTTP请求确认新Thread实际收到global/current与historical标记，原Goal Schema不变。

[最终CPU日志](../../../research-records/goal-continuity-20261113T013426Z/cpu-regression-final.log) /
[历史篡改反例](../../../research-records/goal-continuity-20261113T013426Z/import-counterexamples.json)。

## 5. 一次真实跨会话模型验证

### 启动失败与修复必须分开

原65536启动复制遗漏此前批准的overlay，run-service的PYTHONPATH指向不存在目录，因此实际加载正式默认64GiB容量校验而退出。尚无预算admission、权重加载或模型请求；Goal行为CENSORED，不是资源越界或Goal失败。

补齐与上轮逐文件hash一致的56/72兼容overlay，另建65536-compatfix及独立AC日志，追加限定启动预登记。没有改变策略、停止线、模型、采样或研究输入。原启动失败未覆盖。

控制器的engine-verification.json仍写在旧65536目录；[明确归属记录](../../../research-records/goal-continuity-20261113T013426Z/engine-verification-bound.json)已逐值对照compatfix Guard的admission/post-profile事件，不能把它归给首次失败。

### 实际请求与模型行为

- 新Native Thread：01a1d2be-834f-79b1-ad9a-0ab1a7ea21fe，不resume旧Thread。
- Host进程先前关闭、从profile-final加载；不恢复旧Workflow。
- 1个用户Turn、1个模型请求；输入11,540、输出531 Tokens，分支62.839秒。
- 完整response.completed、HTTP framing完整、上下游SSE一致；0工具调用、0新候选版本。
- 实际请求包含ff2a当前head、098ea历史、两段历史依据及原工具契约，local Intel候选未迁入。
- 模型准确读回正文、ID、revise、历史版本与依据，区分旧输入与今天当前输入；没有虚称修改或读取。
- 原三版本不变，原Journal初始44,867字节保持原样前缀；仅追加本轮输入/Turn历史和之后研究者注释，未覆盖旧版本。

**读回限定PASS；后续讨论PARTIAL。** 模型遵守暂停当前Intel研究，但以无资料为由没有提出要求的“待验证研究问题”，说“不编造问题”。对市场事实保留UNKNOWN正确；提出标为待验证的问题却不必声称已知事实。本例表现偏保守，且输入中的“没有资料就明确未知”可能影响表现。没有改Prompt重试，也没有把这个问题归为存储错误。

[模型完整回答](../../../research-records/goal-continuity-20261113T013426Z/model-session/model-answers.md) /
[请求、状态和成本核验](../../../research-records/goal-continuity-20261113T013426Z/model-proof.json)。

## 6. 安全与实现边界

沿用56/72、64K、1GiB KV、seq1、util0.65。最终KV逻辑容量109817 Tokens；本轮短请求不重新证明64K长负载稳定性，没有Compaction压力测试。

compatfix服务163条有效资源采样、249条有效AC样本；NVML峰值28.728GiB、Shared峰值0.247GiB、Windows Commit最低余量23.092GiB，距原停止线缓冲4.796GiB，WSL最低可用17.630GiB。正常CONTROLLER_STOP、remaining=[]，端口及Harness进程清理。没有实际内存/遥测保护触发；守卫故障自检不是service越界。首次失败与最终有效运行分别记录，不拼接为一次成功运行。

[资源汇总](../../../research-records/goal-continuity-20261113T013426Z/resource-summary.json) /
[冻结输入与源码核验](../../../research-records/goal-continuity-20261113T013426Z/final-integrity.json)。

本轮只新增隔离研究脚本、测试、文档；不改正式Runtime、Goal Schema、SQLite、Phase-1、Harness执行所有权、Provider Policy或采纳权限。Memory仍Research Reserved，原脏工作树保留，不Commit/Push。

## 7. 长期研究入口与可证伪计划

[使用方法](../../scripts/research/README-goal-continuity.md)提供：空白profile初始化、引用已有Guard的按次输入、新Thread恢复、显式Scope绑定、查看与追加研究注释。日常真实研究应新建空profile，不把本次冻结金融种子自动当现实用户Goal。

本批工作Journal：research-records/goal-continuity-20261113T013426Z/profile-final/goal-journal.jsonl。已追加一条semantics注释，关联新Thread和真实请求，记录过度弃答及措辞混杂；它不是Goal/可信Memory事实。

| 后续阶段 | 最小可证伪目标 | 当前状态 |
|---|---|---|
| 1 保存/恢复 | 进程关闭后候选、parent、来源及head保持，新Thread不带入local/权限 | 本轮限定PASS |
| 2 多次真实对话 | 用户纠正后实际修订；Task取消不误撤回长期Goal；偏好不被无依据添加 | 待逐次积累，不强制提案 |
| 3 压缩/历史受限 | 标记来源缺失，避免旧候选复活；限制Context后仍可适当继续 | NOT RUN |
| 4 ON/OFF及History | 在同证据下改善研究问题、行动与结果，而非仅准确复述或少耗Token | UNKNOWN |

每个checkpoint记录Journal尾部hash、代码/配置、Native/HTTP、供给视图及原答；失败区分store、projection、semantics、reference、conceptual、unknown。存储/投影正确仍允许暴露模型或Goal定义缺陷。

竞争假设：
- 持久化候选能防止每次重造历史，但可能只是冗余摘要；需Relevant History对照。
- 稳定head不一定代表有效推进，可能只是未维护或Goal过宽。
- 错误解释跨会话可能被反复强化；纠正后应检查旧版本是否仍误作当前依据。
- 显式family Scope选择可安全隔离，但未证明覆盖真实并行/渐变Goal；不能用绑定规则证明语义。
- 本次正确读回仍过度弃答，反驳“只要记住Goal，就能自动得到有价值下一步”的简单假设；尚不足否定Goal研究。

## 8. 限制与最终判定

只支持Linux/WSL、本地单用户、协作式单写者；不是多用户身份/安全认证系统。Hashchain不能单独发现删除完整合法尾部后的回滚；fsync依赖底层文件系统/设备保证，未做PC断电实验。没有自动迁移、合并任意历史或自动修复损坏文件。

保留原Thread可见集合32候选版本研究上限（不是Profile总版本上限）、每Turn最多2次接受、Journal16MiB/单条2MiB及4200字符视图限制。达到上限Fail-Closed，长期容量/检索成本仍UNKNOWN；没有宣称完成无限期维护层。历史外部证据不恢复成新执行，现有evidence_ids的当前执行校验也未为了跨会话放宽。

| 维度 | 判定 |
|---|---|
| 本地持久化/重新打开/重复恢复 | 限定PASS |
| 原Journal→新Thread非权威视图 | VERIFIED |
| 模型准确读回 | 限定PASS，一次显式读回 |
| 正常后续讨论 | PARTIAL |
| 自主跨会话生命周期M4 | UNKNOWN |
| M3实际行动与M5增量决策价值 | 未升级，PARTIAL/UNKNOWN |
| 新Goal/Memory引擎或正式架构改动必要性 | 没有新增证据 |

独立Audit Agent已复核工程反例与实际请求/原答/资源，结论工程限定PASS、整体PARTIAL。完整意见见[独立审计](../../../research-records/goal-continuity-20261113T013426Z/independent-audit.md)。本轮到此暂停，交阶段评审，进入后续长期证据积累准备，不继续追加模型请求或自动接入正式入口。


更正（2026-11-13，三场景研究前）：32限制来自GoalResearch.submit对len(self.records(state))的检查。PersistentGoals.records返回当前Thread可见的global family全部版本及本Thread local版本；Profile内其他Thread不可见local版本不计入。原评审包及原始证据不改，不能把该限制表述为Profile总版本上限。
