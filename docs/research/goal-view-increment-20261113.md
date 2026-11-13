# 当前结构化 Goal 视图 ON/OFF 增量研究（2026-11-13）

总体 **PARTIAL**。相同已纠正 checkpoint 的两个独立真实分支均完成，但结果是不同缺陷的取舍，没有获得结构化 Goal 视图超越普通历史的可靠决策收益证据。保留现有 Sideband，不新增维护层或正式架构。

批次：goal-view-increment-20261113T005334Z。一次预登记配对：p0=OFF，p1=ON，各一次、固定先OFF后ON、不追加提示或重试。

## 1. 精确研究对象

测量的是：**当前专用结构化 Goal 视图，相对于已经保留真实用户对话、Goal 工具调用和 Host 回执的普通历史，提供多少额外帮助。**

OFF 仍然有原始用户长期目的、历史成功修订、完整工具回执和语义历史背景；Host 仍保存同样的 Goal 状态，Goal 工具与权限也相同。OFF 不是“完全没有 Goal 机制”。相同或相近表现不能否定 UAEA Goal 研究，差异也不能自动证明哪种机制更优。

本次开放任务没有指定下一家公司或读取顺序：

> Intel这一轮分析先告一段落。接下来请你决定最值得优先推进的一条研究方向，说明为什么选它、暂缓哪些替代方向，并实际核验至少一项相关证据后给我判断。现有资料仍可只读使用；如果关键依据不足，请说明缺口，不编造。无需创建或修改文件，也不执行交易。

不预设唯一正确方向。重新研究 Intel 不是关键词层面的自动失败；需要说明为何在当前分析已暂告结束后，仍值得重新优先研究。Goal 复述、公司选择本身、模型自称采用 Goal 都不是决策价值证明。

[预登记](../../../research-records/goal-view-increment-20261113T005334Z/preregistration.json) /
[冻结任务](../../../research-records/goal-view-increment-20261113T005334Z/task.txt)。

## 2. 同一真实纠正 checkpoint 与供给核验

使用上一批 with_failure_details 的真实合法修订，保留原 Thread、Scope、父链、来源、Call ID 和幂等性记录：

- Thread：01a1cdd9-84df-7030-a240-4ea8f75089ea。
- 截止 Turn：01a1d243-a69f-79a0-a732-6376792fb2a3。
- 真实修订 Call：chatcmpl-tool-b5322cd622602c03。
- 当前全局 head：goal-candidate:ff2a010b338474f6ea3f66f5。
- 全局正文：**长期跨公司研究AI产业投资机会是全局范围目的。**
- 原全局版本：goal-candidate:098ea60b1c3caf2ca410b22d，作为不可变历史保留。
- 局部 Intel head：goal-candidate:0cb6591e2475fdd96208bc87，未改变。
- 两组均为3版本/2heads。局部候选仍有其原有财报背景，本次没有额外净化或替换它。

独立副本的 Native rollout 是原件精确前143行字节前缀，截止于真实修订 task_complete；切片 Host snapshot、Journal 和 HTTP 审计也只到该次修订。上一批已发生的 Apple/Alphabet 后续任务及其回答、工具调用不能带入本轮。

这是已验证的隔离研究状态组合与 Native 副本，不是通用 Runtime checkpoint 恢复。复制的 SQLite UI时序/缓存没有声称被完整回溯；CPU与真实出站请求均核查旧后续 Task、Turn、Call ID及答案标记未出现。当前证据范围内未观察到未来泄漏，不作任意历史恢复保证。原件哈希复核不变。独立审计在实验完成后以SQLite mode=ro检查checkpoint副本，意外新建空state_5.sqlite-wal及state_5.sqlite-shm；原已锁定数据库/rollout等文件哈希不变，原始历史home未改。两个sidecar保留并单列，不宣称审计后文件集合完全不变；该审计副作用未进入模型调用。

**干预范围：**

- ON：保留一个 external_uaea.goal_hypotheses 当前块，含全局、局部两个 head 和输入索引。
- OFF：只在隔离研究出站副本移除此块。
- uaea.goal_state 元数据、普通对话、历史成功/失败事实、实际回执、当前输入、工具 Schema/权限都保留。
- 因而本试验也不是“仅增加全局 Goal 文本”的消融；处理变量是整个现有当前视图。
- 同一共享只读资料根，匿名p0/p1 Native home，避免条件名称进入模型路径。
- GPU/模型加载一次；Context64K、KV1GiB、seq1、56/72、util0.65不变；每请求输出2048上限、每分支最多4请求、Turn420秒。未达到预算上限，不追加纠正机会。

先用真实 Codex→Bridge→CPU HTTP 接收器进行无模型供给检查，确认OFF0/ON1、普通历史同在且无旧未来任务；CPU固定回答不计认知结果。随后3个真实模型请求也全部满足对应视图数量。

两组**首请求**只在审计副本去除ON视图，并明确归一化当轮Input/effective-state/message ID、client_metadata、Host时钟和Native home路径后，剩余JSON完全一致；工具和证据权限相同。原始请求不改。处理本身改变输入长度与位置，固定顺序和单次生成/服务热态仍是限制，不能称为统计因果证明。

[checkpoint切片证明](../../../research-records/goal-view-increment-20261113T005334Z/checkpoint/native-cut-proof.json) /
[CPU实际出站](../../../research-records/goal-view-increment-20261113T005334Z/cpu-view-outbound-proof.json) /
[受控项、归一化及不可变性](../../../research-records/goal-view-increment-20261113T005334Z/controls-and-immutability.json)。

## 3. 真实结果：方向与行动不能互相替代

| 观察维度 | OFF：普通历史 | ON：再供给当前结构化视图 |
|---|---|---|
| 长期方向 | 明确保留长期跨公司AI产业投资研究 | 同样保留长期跨公司AI产业投资研究 |
| 优先选择 | Intel Q3非GAAP运营表现与估值分析 | 长期跨公司方向，以Apple/Alphabet作支点 |
| 暂缓方向 | 宏观AI与Apple/Alphabet比较 | 当前Intel财报与估值分析 |
| 本轮真实读取 | INTC、AAPL、GOOGL、ledger，共4次 | 0次；引用历史已实际读过的资料 |
| 当前证据动作要求 | 实际读取并核对摘录，已观察 | 没有本轮新的核验行动 |
| 主要问题 | 把Intel单公司核验说成跨公司框架的“必要前序”，依据不足；回到已暂告结束对象 | 方向仍宽泛，主要复述既有目标；把“告一段落”扩大为局部目标“已完成” |
| 新Goal调用/版本 | 0/0，合理不提交不单独计失败 | 0/0，相同 |
| 当前Host head | 原两head保持 | 相同；没有正式完成/撤回 |

### OFF：有实际行动，但研究选择理由不足

Call→Native→执行决定→Observation→工具回执逐条核对，4次均成功、身份及路径/正文/文件哈希匹配：

- chatcmpl-tool-b372f0a2feb4fc04：S-INTC。
- chatcmpl-tool-99dd57bfa9e6e737：S-AAPL。
- chatcmpl-tool-aac1388118d74d14：S-GOOGL。
- chatcmpl-tool-b47b50aad9bb7939：ledger目录。

它没有丢失长期Goal概念，没有编造真实报价或年度forward EPS。但仅凭现有摘录容易取得，不能证明继续Intel是跨公司研究的必要前序；没有报价/forward共识，也不意味着所有跨公司研究问题都应暂缓。重新选择Intel的说明不足以建立更有价值的下一步。不能把4次读取直接算为4份新外部独立证据——它们是对既有冻结文件的重读/目录读取。

### ON：保持方向更贴近当前转场，但没有落实当前核验

完整回答确实暂缓Intel，保留跨公司目的，并使用历史Apple/Alphabet数据。**“已读资料”有先前真实Observation支持，不判成伪造读取。** 但是本轮没有新的Tool Call、检验问题或证据动作，不能把“核验证据”段落自动计为执行了当前核验要求。

本任务并非要求为调用而重复读取；更有价值的行动也可以是利用已有内容完成一个新的、可核查的比较/计算或验证。ON没有展示这样的新行动，只列既有数字和资料缺口。因此，本轮行动要求未充分满足；这不是简单“零工具=失败”的评分。

它还说“局部范围目标已完成”。用户只说本轮告一段落，Host局部候选仍为candidate，Workflow仍active，无完成或撤回工具事件。因此：
- 作为局部任务完成的推断，证据不足；
- 若理解成正式状态报告，则与Host不一致；
- 不能把这句话变成Runtime完成事实，也不能声称它已违法修改状态。

ON所谓“超出当前Scope”没有显示新的拒绝或授权决定。实际工具限于只读本地材料；不能由资料或可用工具有限推导用户长期目标只允许这些工作。缺口判断应保持能力、资料、语义范围区分。

[OFF完整回答](../../../research-records/goal-view-increment-20261113T005334Z/p0/model-answers.md) /
[ON完整回答](../../../research-records/goal-view-increment-20261113T005334Z/p1/model-answers.md) /
[逐Call/请求事实核验](../../../research-records/goal-view-increment-20261113T005334Z/fact-audit.json)。

## 4. 金融证据与语义边界

资料沿用研究者保存的官方文档摘录和目录；本轮没有联网重核官方全文，也没有实时行情、真实交易或后续决策结果。记录的冻结研究时点是11-10，要求的历史估值点为11-04，字节在11-09保存，严格11-04已知性仍UNKNOWN。系统当前日期与数据适用期不混同。

两组列举的主要收入、EPS、期间和单位与摘录相符；ON将Alphabet127577 million换成127.577B正确，OFF没有把Intel Q4季度EPS指引当成forward年度EPS。真实价格、年度共识和完整电话会议缺失都保留。来源存在/数字吻合仍不能证明“优先研究谁”是最佳判断。没有用跨公司每股EPS大小直接推导投资优劣；也不把本研究输出当真实投资建议。

## 5. 成本、传输与资源

| 指标 | OFF | ON |
|---|---:|---:|
| 完成用户Turn | 1 | 1 |
| 完整模型请求/响应 | 2 | 1 |
| 首请求输入Tokens | 27,092 | 28,217 |
| 累计输入Tokens | 60,003 | 28,217 |
| 累计输出Tokens | 1,191 | 781 |
| 实际本轮只读调用 | 4 | 0 |
| 用户Turn耗时 | 177.278秒 | 106.009秒 |
| 分支总耗时（含恢复/清理） | 178.491秒 | 106.771秒 |

当前视图首请求增加**1,125输入Tokens**。ON累计成本更低，主要伴随没有新读取/后续请求；不能当作等质量任务完成的效率收益。没有多次重复/顺序对消，不估计稳定性能优势。

3个响应均response.completed、HTTP framing完整、上下游SSE字节一致；无输出上限截断或Context Overflow观察。无自然Compaction，本轮不能评价压缩压力下的增量价值或普遍长期稳定性。64K是固定已有实验配置，不再测容量极限。

一次加载，控制器总耗时403.960秒。service资源367条有效样本、AC435条有效且均在线：
- NVML峰值28.565GiB，DXGI Dedicated峰值28.563GiB，Shared峰值0.218GiB。
- Windows CommitLimit91.481GiB，最低余量23.608GiB，距原停止线最低缓冲5.312GiB。
- 原停止公式free<=max(16GiB,20% CommitLimit)保持，不擅自换成历史固定数字。
- Windows最低可用32.654GiB、WSL最低可用17.619GiB、Swap最多12,288字节。
- 单时钟因果年龄上界最大0.111秒。
- 正常CONTROLLER_STOP、remaining=[]，端口8000/8003无遗留监听。

Guard启动时的资源/过期样本故障自检是安全机制自检，不是service实际越界。本次无实际资源或遥测保护中断。未改正式Runtime/Schema/Goal/Memory权限、模型参数或原始历史；源代码/安全pins和checkpoint前后核验不变。新代码仅隔离研究干预/恢复/取证。原脏工作树保留，不Commit/Push。

[资源原始汇总](../../../research-records/goal-view-increment-20261113T005334Z/resource-summary.json) /
[预登记及输入锁](../../../research-records/goal-view-increment-20261113T005334Z/input-lock.json)。

## 6. 里程碑与独立判断

| 事项 | 本轮结论与证据范围 |
|---|---|
| 当前视图ON/OFF供给差异 | VERIFIED：同checkpoint、实际出站0/1及审计归一化一致 |
| 长期Goal保持 | 两组均有正面观察，限本配对，不是长期成功率 |
| Goal与局部任务区分 | PARTIAL：OFF优先级依据不足；ON暂缓Intel但误报完成 |
| 实际后续行动 | OFF4次读取可追溯；ON历史依据真实但本轮核验不足 |
| Goal head/权限边界 | VERIFIED：两组状态未改，ActiveGoal为空，无正式完成提升 |
| M2受反馈忠实修订 | 沿用上一批限定存在性证据，本轮未重测 |
| M3最新状态供给及相容行为 | PARTIAL；ON无本轮证据行动，不能宣布更完整认知闭环 |
| 结构化视图导致了什么决策改善 | UNKNOWN；本例看到选择差异，没有建立可靠净收益 |
| M4自主生命周期 | UNKNOWN，本轮零操作不能单独证明或否定 |
| M5超普通历史的实际决策价值 | UNKNOWN |
| 复杂维护层/新接口必要性 | 没有新增支持证据 |

原driver的result.M3_run=false是“没有另加一个条件式后续Turn”的固定声明，不能代替本轮行为评价；本轮本身就是纠正checkpoint之后的开放后续任务。所有评分以上述真实事件、原答、Host状态为准。

**HYPOTHESIS**：当前视图可能有助于将注意力从局部任务转回长期方向；也可能只让回答更贴合Goal措辞而减少实际核验。本对不足以区分视图显著性、生成差异、资料稀缺和顺序效应。不能据ON更短更快主张其优于普通历史，也不能据OFF有读取主张OFF决策更好。

下一步最有辨别力的方向，是观察模型能否从持续目的选出一个**新的、证据可支持且值得检验的问题**，并真正完成该检验；在不同但预先固定的转场任务上对消ON/OFF顺序。避免把“再读四个现有文件”或“再次复述长期Goal”当目标。无需新增语义控制器、Goal Engine、复杂数学层或强制工具调用。本轮不继续追加模型请求取得PASS，先提交本配对及独立审计供评审。

## 7. 独立审计

Audit Agent已完成独立只读与CPU复核，最终结论**PARTIAL，可归档限定研究**；未发现需改正式架构、权限或保护的新增问题。独立核验checkpoint截止、实际出站因子、两组完整回答、Call/Observation/Host绑定、成本和资源，确认M3仍PARTIAL、M5 UNKNOWN，不支持ON胜出。审计SQLite副作用已透明记录。完整意见见[independent-audit.md](../../../research-records/goal-view-increment-20261113T005334Z/independent-audit.md)。模型自述不能作评审真值。
