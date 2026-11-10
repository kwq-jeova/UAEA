# 自动化多轮认知研究环境阶段验收

2026-11-09。**实验基础设施限定PASS；Goal认知覆盖PARTIAL；真实长期决策价值UNKNOWN。**
完成3个固定合成场景、两种模式及一次成对重复：8个真实Bolt＋Codex Harness会话，共20轮。
每会话2–3轮，不将跨会话总轮数包装成一次长期交互。

## 1. 审计与复用

| 已有组件 | 本轮用途 |
| --- | --- |
| scripts/h3_harness_interactive_repl.py 的 InteractiveAppServer | 直接调用start/run_turn/close，模型与工具循环仍由Harness控制 |
| h3_context_characterization.write_config/build_adapter | 固定32K配置、隔离Sandbox及既有文档Capability |
| ProviderHistoryBridge / EventNormalizer / TrajectoryWriter | 复用出站审计、消息历史、Canonical Trajectory和原始事件 |
| SharedExecutionHost / Semantic State | 决策、真实Observation、投影和正式状态分别保存 |
| GoalIntegration 的 off / shadow optional | 直接比较基线与已有候选机制，不创建Goal Engine或维护层 |
| 历史experience-transfer研究驱动与Evaluator | 继承独立会话、原始记录和实际执行判据的方式；旧脚本单轮、绑定旧数据，不直接当通用多轮入口 |

新增的只有固定脚本驱动、准备工具、离线审计及小夹具。没有第二套Agent Loop、自动对话模拟模型或独立语义裁判。
未修改任何既有Runtime、Harness、Goal Adoption、Memory或模型代码。

## 2. 固定场景与公平对照

1. **逐渐明确方向**：普通闲聊→社区口述历史项目→预算及不改写限制，3轮。
2. **Goal与Path**：审查研究依据→用户明确纠正在线页面只是手段，条件变为没有服务器，2轮。
3. **证据与纠正**：真实读取本地样本→限定单样本不能泛化→缺失文件失败后恢复原记录，3轮。

用户脚本为研究者编写的合成条件，原意/限制由文本预先给出，不是自然长期Goal真值。
不把预设关系标签放进模型输入，也不要求所有轮次用工具。

Relevant History使用既有历史/语义投影、Goal off；另一模式启用既有Goal shadow/optional。
两组脚本、文件字节、工具、权限、模型、32K窗口一致；每次新thread、home、adapter和workspace。
场景交替组别顺序，Path场景再以反向组别顺序各重复一次。
Shadow额外包含既有可选最终信封说明及候选视图，这是机制整体对照，不能把差异纯归因于某一语义表示。

Harness使用现有采样默认，本批出站无显式temperature/seed字段；没有为不同组调整提示、工具恢复策略或资源预算。
重复证明能重新执行并比较，不证明输出逐字一致或统计显著性。

## 3. 真实执行与行为

| 修正后完整批次 | Relevant History | Goal Shadow |
| --- | ---: | ---: |
| 新会话 / 用户轮次 | 4 / 10 | 4 / 10 |
| 累计输入Tokens | 113849 | 123675 |
| 累计输出Tokens | 1180 | 1319 |
| 会话累计秒数，含Harness开关 | 221.74 | 246.70 |
| 真实工具Observation | 2 | 2 |
| 原生Compaction | 0 | 0 |
| 正式ActiveGoal / Workflow完成 | 均无 | 均无 |

Token数为每thread最后一次累计计数之和，不叠加所有更新；不是单次Context长度。
实际模型有效窗口31129。24份出站请求快照均为redacted_complete，带消息清单、内容hash和transport记录；
脱敏结构快照不是原始wire bytes，成功传输也不证明模型理解。

**实验链路**：8/8会话及20/20原生Turn正常结束；均保存原始事件、Canonical Trajectory、投影、状态及出站审计。
Shadow投影确实进入对应模型请求，基线不含该投影，非只看配置日志。

**限定模型行为**：
- 两组在普通交流时没有声称新的持续目标，随后能讨论档案项目和原话保留限制。
  基线第2轮出现不必要的许可确认；这是普通行为问题，不是工具权限实际拒绝。
- Path首次和重复对照共四份最终回答均保留审查依据目标、将在线路径换成离线材料。
  原文已明说Goal不变，不能据此证明困难长期目标推断；基线首次还附加了“材料本身没变”的未证假设。
- 两组均真实成功读取一次ledger.md，再真实收到一次missing.md失败，最后从已有历史恢复正确记录码及路径。
  正文摘录hash和文件版本hash相符，首次请求不含隐藏记录码；失败未被说成成功读取。
  这是短历史中的恢复，不是Compaction后正文已退出Context的恢复，也不是公网Search/Fetch验证。

**关键限制**：Shadow的10轮全为NO_GOAL_PROPOSAL，模型使用普通回答，没有形成实际保留候选。
这不是为了评分应当强制修复的格式错误，但意味着本批不能验证“已有Goal候选在多轮中演化/提升决策”的收益。
目前只建立了可运行、可观察、能比较这一负结果的机制基线。

## 4. 夹具修正与负面结果保留

首次适配检查把Capability名称误当协议名；实际document.read_section映射read_section，在模型执行前已修正。
随后首批本地文件工作目录与Sandbox分离，模型构造工作目录下的绝对路径，被正确拒绝并重复尝试。
受控中断该自有Harness；原日志、失败、已完成会话均保留，没有选择其中成功回答混入最终组别。

仅将研究驱动workspace对齐到隔离Sandbox，CPU真实检查相对/绝对路径均可读取，再启动全新完整批次。
不改变冻结Sandbox规则或把拒绝强制改成成功。missing.md仍按现有规则返回local_file_failure，不绕过权限。
这些设置与失败也有时间/Token成本，不能从本轮总工程成本中抹除；表格仅用于修正后同条件组别比较。

另外，gradual第3轮的topic字段仍保留首轮闲聊，而current_input_id、原请求及模型回答已更新。
本轮没有把Topic标签直接当作Goal真值，也没有据此断言权威Goal已污染。
这是一项既有投影表述风险，保留证据供后续研究；未为实验通过扩大Runtime修复。

## 5. 回归与安全

8项离线控制PASS：成对计划、非法/重复身份防护、控制指令隔离、已有输出不覆盖、
真实相对/绝对文件读取、声明不能代替Observation、失败/错源/无正文不算grounded、缺失会话不能算PASS。
自动判据仅评价结构与局部来源；定性行为复核另存，不由被测模型自评。

原32K、1GiB KV、36GiB引擎、64/64 UMA及Fail-Closed保护不变；64K入口未改。
951条Windows与WSL/GPU采样有效，范围含初始夹具故障与完整批次：
Dedicated峰值29.18GiB，Shared0.159GiB；
Windows Available最低22.15GiB，Commit余量最低45.37GiB；
WSL Available最低17.47GiB，Swap峰值0.016MiB。
不同内存域不相加，采样峰值不构成硬分配上限。

自有服务主动CONTROLLER_STOP，服务/采样器remaining=[]，8000/8003无监听。
启动器主动停止也显示Safety stop，不是本次发生资源事故。未终止外部服务。
97个既有Python文件与16项启动/补丁/保护文件哈希保持，Phase-1子模块干净；无Commit/Push。

## 6. 使用入口与阶段判断

- benchmark/longitudinal_dialogue/README.md：复现步骤、采样/超时/权限与评价边界。
- benchmark/longitudinal_dialogue/scenarios.json：三个固定脚本。
- scripts/research/longitudinal_prepare.py：新建唯一计划目录及冻结版本，不启动模型。
- scripts/research/longitudinal_dialogue.py：复用Harness执行多轮，未确认终止时不发下一轮。
- scripts/research/longitudinal_audit.py：离线读取轨迹，分开报告答案、Observation、正式状态和成本。
- benchmark/longitudinal_dialogue/test_contracts.py：CPU控制测试。

180s每轮和既有1800s实验期限仅适用于这项自动实验，不改变人工交互服务或Workflow生命周期。
本套件未触发原生request_user_input；不会编造用户答案，但条件式应答和输入等待终止尚未验收，不能从这20轮外推。

**建议接受这套限定实验基线，不新增测试平台或维护层。**
下一轮若有明确的候选机制假设，可在相同脚本/权限下替换一个输入处理方法，再检验是否产生额外行为。
如果依旧没有候选，先接受负结果，不为“通过”强制输出新字段。
自然Goal形成、跨会话演化、长Context/压缩恢复和实际建议效用仍是PARTIAL/UNKNOWN。
本轮不需要新的人工长会话或权限决定；后续只有真实语义真值/决策结果缺失或正式接线时再提交相应评审。

## 7. 原始证据

完整批次：
/home/wqkan_wsl/uaea-n1x/research-records/longitudinal-dialogue-fixed-20261109T064932Z/

原始夹具失败：
/home/wqkan_wsl/uaea-n1x/research-records/longitudinal-dialogue-20261109T064131Z/

每会话app-server-events、normalized-trajectories、execution-contract.trajectory、
model-http-audit、context-projections、semantic-state-snapshots、goal-events及turns.json保留。
audited-results、comparison-summary、behavior-review分别为结构/成本/独立定性评价。
frozen/protocol/fixture-manifest保留脚本、模式、代码和源文件版本；source hash检查在audited-results中。
safety/isolation-checks/final-verification保留完整运行范围及保护状态，Windows UAEA_DOCS保存审阅副本。
