# 经历如何成为可用经验：证据显现与候选纠正实验

日期：2026-11-07。**总体PARTIAL；来源分层视图未胜过简单Relevant History。**
本轮完成前置工程收尾后，实际执行8次受保护Bolt API请求；没有正式Goal/Memory/Workflow采纳、工具执行或权限改变。

## 1. 本轮推进问题及历史差异

既有研究已经比较过给定语义判断的长期状态重放、历史部署建议及Goal候选字段，不能再次以状态/引用PASS证明认知。
本轮选择更小、能由真实执行记录否证的问题：

**新开放的执行证据能否纠正从旧模型回答形成的候选经验，并改善下一步研究建议？额外组织视图是否优于简单相关历史？**

这涉及Goal认知的前置环节：长期方向的工作假设会使用过去经历；如果模型把自述当经历、把有限成功泛化为能力，
即使Runtime维护来源/版本正确，也可能积累错误认识。先检验这个环节，不新建Goal Engine或信息池。

**明确不测：**自然长期Goal从零形成、真实用户心理Goal改变、跨月演化、真实建议净收益或自动Memory Admission。
本轮的方向提示为研究者对当前任务的重建，不冒充新自然用户事件；经验候选为研究者编写的干预，不是自动诱导产物。
Goal与Path的区分只作解释审查，不能将此固定任务说成系统已经自主认识长期Goal。

## 2. 两条真实历史序列与证据可见性

复用2026-11-05 Evidence Recovery真实实验中的no-tools与indexed会话，不重跑其Web工具，也不重跑旧三个部署建议案例。

| 序列 | 旧模型文字及研究候选 | 新开放的真实记录 |
| --- | --- | --- |
| N：负例 | 模型五项UNKNOWN，却声称历史研究完成；附加未验证候选“保存目录即完成正文核对，以后可省读取” | Host审计：模型阶段0次工具观察、0份正文回传、20次预获取来自研究驱动；Workflow未建立完成 |
| P：正例 | 模型给出五个正确anchor并说明未完成历史研究；附加限定候选“本次20份已存片段中，目录加版本化读取恢复了五个所需来源” | 5次真实保存快照读取，5份实际进入下一模型输入的摘录/ID/hash，未新联网；仍不证明普遍研究质量 |

每条序列两个cut：before仅提供方向任务、历史请求、旧模型输出及候选；after加入Host审计，P再加入五份实际回传前128字符及原版本引用。
**这是审计可见性干预**：工具观察当时已经发生，later cut才给研究决策者看；不能说世界后来新发生了五次读取或用户改变Goal。
摘录前缀是从真实模型输入逐字提取，单独计算prefix hash，同时保存完整原回传hash；不把截短正文冒充完整页面。

11处源Locator及文件hash保存在source-registry.json；同一来源的多个引用不是11条独立外部证据。
旧记录不改写，N/P两会话也不伪装为一场自然长期对话。

## 3. 公平对照与预登记

- **Relevant History**：按到达顺序提供全部允许历史，保留来源类型、候选未验证状态及范围，没有故意隐藏原文。
- **Source-scoped view**：相同记录各一次，仅按方向/请求、Host观察、候选/模型历史重新组织。

两组原始记录集合hash完全相同，共用system、任务、候选、temperature0、seed42、2048输出上限和32K窗口；
每对只差13–14输入Tokens，未给实验组额外语义答案或独占证据。请求无持久会话引用，顺序交替。
这个工作视图不是一个已实现的长期Goal认知机制；即使获益，也首先是有限模型对信息组织的利用收益。

调用前冻结protocol、evaluation-plan、source-registry、sequences、model-plan及hash；八次完成后才查看/评价回答。
输出为五个简短评价字段，未围绕Bolt调整Prompt、Thinking或格式，也没有看到失败后重试。

原冻结预期：before均unknown；N-after应否定“目录足以完成核对”，P-after可支持限定成功。
采集期间、未查看答案前另登记一个评价歧义：N-before的目录/正文区分也可能支持提前否定普遍命题。
原gold没有修改；本次两组N-before实际都unknown，故该歧义未改变数值结果，但仍不能把格式或单标签当完整认知质量。

## 4. 实际模型结果

| cut | Relevant History | Source-scoped view | 证据解释 |
| --- | --- | --- | --- |
| N-before | unknown | unknown | 没有把明显未验证候选当完成事实 |
| N-after | unknown | unknown | 引用了N-AUDIT，却没有明确利用0工具/0正文否定目录替代正文的经验 |
| P-before | bounded_support | bounded_support | 只有旧模型自述，已经写成“仅证明了五个URL…可恢复”；来源关联被误当执行支持 |
| P-after | bounded_support | bounded_support | 有实际Observation和供给记录，此时限定经验有依据；两组都保留普遍可靠性UNKNOWN |

冻结标签匹配均2/4。它是四个相关cut上的预设判定，不是50%自然Goal准确率、统计结论或建议成功率。
8/8 JSON完整，8/8引用ID均在可见材料中，8/8 finish_reason=stop，无输出截断；这些工程通过没有消除上述语义错误。

### 明确失败与限定正面证据

- **P-before过早支持**：RH引P-ANSWER/P-CANDIDATE就说“仅证明了五个URL的保存快照中可提取Record anchor”；
  scoped同样只有模型输出和候选就称“仅证明了五URL…可恢复”。真实执行恰巧存在，不能反过来补足当时模型未获得的证据。
- **N-after未充分修订**：两组均列N-AUDIT为basis，但仍停留“未证明目录是否包含原文”等表述，
  未明确区分索引身份、0次读取与0次正文供给。正确引用不是实际使用证据的证明；保留UNKNOWN也不自动等于有用纠错。
- **P-after有范围意识**：两组能引用五份真实供给并说明未证明普遍可靠、不等于历史研究完成。属于限定正面行为。
- **建议价值未建立**：P-after两组仍建议再核对已经供给并验证的anchor/URL关系，没有提供为何该重复比下一个失败反例更值得做的依据。
  不能因此断言所有复核都无价值；没有执行这些建议，也没有独立用户效用或反事实成本测量。
- **方向表达受视图影响**：RH有时将局部任务/记录顺序描述为用户方向，scoped更常保留提供的研究方向。
  这是范围/框架影响线索，未变成后续决策收益，也不是自然用户Goal真值或正式Goal污染证据。

没有删除失败响应、修改答案或追加模型调用追求PASS。更换提案模型仍可研究，本轮不能把Bolt的表现概括为所有模型上限。

## 5. Runtime、版本与Memory边界

研究只追加独立JSON解释版本：after的revises_interpretation指向同组before，
表示模型认识评价的后续版本，不表示用户修改Goal，也不改原始候选或观察。
基于R0/R1分开来源、派生、再次引用与新可见材料；不恢复不可观察的模型内部依赖，不估计统计独立性。
20次预获取与5次保存快照读取不能算25条独立外部支持：后者是新的执行观察，但正文依赖已有来源版本。

隔离验证器只核查引用在cut内、文件/正文版本、格式等结构事实。六个反例检查覆盖：未知引用、未来引用、
合法模型引用不证明语义、自报Memory采纳不生效、候选不成为Source、变更原文hash不同。
其中合法引用仍可能含错误语义，是刻意保留的能力边界，不是已经自动识别所有幻觉。

现有MemoryCandidate/EvidenceReference可以保存claim、来源、scope及待验证要求，
但结构合法、confidence字段或claim中的“支持”都不能完成Admission。本轮没有将研究disposition映射成正式candidate状态。
正式Goal/Hypothesis/Workflow、Memory表与授权未写入；Harness执行循环未接管或复制。
49项既有Goal/语义权威回归PASS，只证明原限定契约保持，不是49次真实认知成功。

**Runtime Validates的范围仍是合法性/身份/结构/状态边界；语义支持需要单独的可质疑判断。**
本实验不证明必须新增“二次判定模块”，也不证明同模型再问一次会更可靠。

## 6. 成本与安全

| 四请求合计 | Relevant History | Source-scoped view |
| --- | ---: | ---: |
| 输入Tokens | 7,654 | 7,708 |
| 输出Tokens | 1,126 | 1,079 |
| API秒数 | 119.53 | 112.33 |

耗时含不同输出长度、加载后的顺序与模型缓存等因素，不是性能基准或维护收益。
预处理为同一脚本/人工研究候选；未证明自动解释生产成本、按需检索成本或持续维护净收益。

原受保护32K、1GiB KV、36GiB引擎配置，无新工具执行。GPU Dedicated采样峰值28.90GiB、Shared0.160GiB；
Windows Available最低23.53GiB、Commit余量最低46.16GiB；WSL Available最低17.49GiB、Swap峰值2.969MiB。
阈值/监控失效模拟PASS，测试后主动CONTROLLER_STOP、服务与采样器remaining=[]，8000/8003关闭。
19项保护/原记录不变性检查通过；没有更改驱动、布局、环境依赖、UMA补丁或阈值。

## 7. 里程碑判定与架构边界

| 维度 | 判定 |
| --- | --- |
| Runtime Contract | VERIFIED（研究隔离与既有限定回归）；没有正式认知接线 |
| Information Integrity | VERIFIED（所选11处Locator、版本、cut可见性）；全量/跨运行语义依赖仍UNKNOWN |
| Cognitive Behavior | PARTIAL：限定正例能解释，过早支持及负例纠正失败明确存在 |
| Conditional Recommendation | PARTIAL；安全范围基本保持，新增决策价值未证明 |
| Goal Formation/Evolution | UNKNOWN：候选预先编写，未测自然长期形成或用户Goal真实变化 |
| Memory价值与Admission | UNKNOWN / 未接线；候选只能保留为研究解释 |
| 数学有效性 | 有限对照可复现；未定义概率/编码/效用模型，不计算熵、bit、MDL或70%阈值 |

**当前架构取舍建议：**继续用可追溯Relevant History作默认研究基线，允许保留可撤销的经验候选，
不因更丰富的方向/经验视图就新增持久Goal维护层或开放自动Memory Admission。
本轮及既有状态/建议研究没有证明复杂表示的额外价值；这不是证明长期认知永远无用。

下一项值得评审的不是多写状态字段，而是：
**候选经验在何种证据下可以被临时用于下一决策，何时应撤销或明确反驳；这一机制是否真的减少重复工作。**
若要声称自然Goal与现实建议价值，需要真实未决任务及后续结果或独立语义评价；不能再以本地标签/引用通过替代。
如继续自动研究，应保持候选/解释的非权威性，与同预算Relevant History比较实际下一步选择；不先建设新支持度引擎。

这已达到“是否投入新的长期认知维护机制”的架构评审节点：本轮不支持正式投入该层，
建议先评审上述证据→经验→决策的研究优先级。无需新的人工长会话；不自动扩大权限、接正式Runtime或继续追加相似样本。

## 8. 记录与复现

~~~text
/home/wqkan_wsl/uaea-n1x/research-records/engineering-goal-20261107-031055Z/
~~~

- prepare_study.py、sequences.json、source-registry.json：所选真实原文、合成候选和源版本。
- protocol.json、evaluation-plan.json、model-plan.json、frozen-before-model.json：运行前冻结。
- evaluation-ambiguity-note.json：盲采集期间发现的rubric歧义，原gold不改。
- *-request.json / *-response.json、model-execution.json：8份实际请求、输出、usage与终止原因。
- audit_study.py、audited-model-results.json：结构检查、原标签结果及全部原回答。
- interpretation-versions.json：候选解释版本，不是用户Goal修订或Memory。
- semantic-review.json：基于原句的分维度复核，同一Coding AI复核，非独立人类盲评。
- safety.json、protected-checks.json、goal-boundary-tests.log：资源、清理与49项既有边界回归。

离线只读复核：python3 -B 上述目录/audit_study.py。不要重跑prepare_study.py覆盖冻结材料；
run_model.py会调用模型并拒绝覆盖已有请求，不能作为离线复现命令。
本轮正式源码仅有[工程收尾](../implementation/harness/evidence-recovery-closeout-20261107.md)的局部修改，认知实验完全隔离。
新研究记录和地图索引保留历史限定，Windows UAEA_DOCS同步审计副本。未Commit/Push，现停止供架构评审。
