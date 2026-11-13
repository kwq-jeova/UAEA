# Goal修订时机、抽象与价值：共同种子的有限对照

2026-11-10。**总体PARTIAL：20轮真实执行完成，未观察到种子后的Goal提交；没有证明决策增量。**
Memory继续Research Reserved。未Commit/Push，不改正式Runtime、Goal/Memory采纳、Harness所有权或模型依赖。

原件：/home/wqkan_wsl/uaea-n1x/research-records/goal-revision-timing-v1-20261110T031255Z
前置：[上一轮有效种子与显式修订](goal-autonomous-maintenance-results-20261110.md)。
本轮不重验既有版本机制；研究模型何时维护、表达什么及是否改变后续行动。

## 1. 最小设计与证据范围

四个独立Bolt+Harness会话，每会话5轮；原32K/1GiB KV/36GiB规划、单并发/Eager与全部保护不变。
H为Relevant History；N/E/X为现有opt-in Goal sideband。
三组均经真实form保存**完全相同的语义种子**：
> 研究能在多轮任务中追溯来源并修正误解的文档助手。

原始ID、时间及来源ID按独立会话自然不同，未复制对象或声称跨Run恢复。
种子是实验控制，不计Goal自然形成或模型抽象成绩。
前三轮和第五轮用户文本逐字相同；H/N全部用户文本相同；E/X仅第四轮增加不同邀请。
现有Marker/操作次数不作语义成功判据，人工预定的明确用户方向用于研究者审查，非Bolt自评。

| 轮次 | 情境 |
| --- | --- |
| 1 | 读既有观察第2节；有Goal工具时按给定干净文本建种子 |
| 2 | 取消摘录子任务，长期方向明确不变 |
| 3 | 本周无GPU/公网，只调整路径与条件，长期方向不变 |
| 4 | 明确从助手研究转为可复核项目档案；N无新增邀请，E只邀评估适用性，X明确要求实际修订 |
| 5 | 不重述新目标；自行选择并真实读取一张后续工作卡，再建议下一步、依据及改变选择的新观察 |

N是**变更轮无额外邀请**；共同第一轮仍允许模型判断后续维护，不等于完全无前置研究说明。
X未强制tool_choice，也未直接点名函数/指定operation；它是明确修订请求条件，
不是强制API可达性测试。旧的明确点名工具正控成功仍保留，不能由本轮未执行推翻。
本轮期望的X正控未触发，因此不能推断三种邀请等效、评估邀请无效，或识别邀请强度的因果效应。

同一ledger包含一段真实既有研究摘录及明确标注的两张合成工作卡。
四组实际均读到相同的历史节段和档案卡，源版本一致。
单例、固定顺序H→N→E→X，无随机重复；助手历史和调用时序不同，
不能把差异归因于某句邀请的独立因果效应，也不能推广为长期Goal能力。

## 2. 真实候选与操作选择

| 条件 | 种子ID | T4理解/选择 | 保存结果 |
| --- | --- | --- | --- |
| N 无邀请 | goal-candidate:f50f2eeedc0aa482c520be33 | 理解新档案方向，将旧种子描述为historical | 仍1个form，无更新 |
| E 仅邀评估 | goal-candidate:2a5d5bbbb813da732ae01771 | 明说旧候选不再适用，但选历史保留、口头UNKNOWN、无需更新 | 仍1个form，无更新 |
| X 明确修订 | goal-candidate:87ef2cf0492afa9b8eb25797 | 理解新方向，给出revise计划和较干净的新目的草案 | 仍1个form，无更新 |

各组T2/T3均保持原目的，没有把取消Task或本周资源变化误作长期Goal撤回。
这是本样例中合理不行动，不要求制造maintain版本。
所有首轮种子通过exact-seed实验有效性检查，T3前head文本仍一致。

**VERIFIED：共3个真实form、0个后续Goal RPC/原生结构化提案、0个修订或撤回、0个拒绝。**
三份源/版本绑定、物化快照与后续成功出站head均对应；未发现已提交但丢失的变更。
T4/T5请求有Goal工具和完整旧种子；单次输入报告最大17547 Token，有效窗口31129，
各组0 Compaction，没有本次Context溢出/历史证据退出的记录。

N/E保留历史不必然错误：候选非权威，历史解释可以保留。
但普通文字历史化/UNKNOWN不等于持久化适用性或版本变更。
N的“historical状态”没有对应Host状态，Host仍为candidate；
E准确说candidate，其UNKNOWN只是普通评估，不是已保存字段或校准概率。
不能将这些表述提升为Host事实，也不能仅据没有调用判所有语义理解失败。

X原生第四轮明确写：
> 使用goal_hypothesis调用operation=revise，将hypothesis更新为“整理可复核的项目档案；旧助手经历仅保留用于历史审计”……

这是可读的模型草案/计划，**不是实际工具提案或已提交版本**。
X同时承认旧候选仍是原文本，没有声称修订已提交。
所以“方向理解、草案表达”和“完成实际修订要求”必须拆开：前两者有证据，后者未完成。

## 3. 抽象质量与后续行为

- 三份已保存种子由研究者预定，不计模型抽象成功。
- X的文字草案概括了新目的与历史边界，没有混入工具操作或临时资源条件，
  是一个限定的合理摘要实例；但没有新的已保存候选，不能宣布“修订后候选质量改善”。
- N/E/X都读到了Archive follow-up work card（第3节），与H一致。
  原始调用、成功Observation、源/节选hash及实际出站正文均可复核。
- 旧种子滞留在这一次后续读卡中**没有可见地把动作导向旧助手卡**；
  不等于证明长期/压缩后无风险，也不证明模型内部没有使用旧候选。
- 四组核心建议均是对照Call ID和source_hash。没有证明Goal组比H发现了更有价值的下一步。
- H和X存在由哈希一致推到事实/整个索引正确的过度推论；N/E提出的改变选择条件也未经效用验证。
  这是模型推断与建议质量限制，不新增Runtime通用语义裁判。

因此后续实际读卡动作限定PASS；“真实决策价值、稳定适用性维护”仍UNKNOWN。
Task本轮只要求读卡和建议，没有执行卡内索引检查；读取成功不得变成已核验档案或Goal完成。
全部20轮Host快照ActiveGoal为空、Workflow completion_established=false。

## 4. 成本与公平比较

| 条件 | 累计输入/输出Token | 出站请求 | 文件Observation | 保存版本 |
| --- | ---: | ---: | ---: | ---: |
| H Relevant History | 85989 / 838 | 7 | 2 | 0 |
| N 无额外邀请 | 99225 / 1401 | 7 | 2 | 1 |
| E 评估邀请 | 98516 / 1076 | 7 | 2 | 1 |
| X 实际修订邀请 | 112014 / 1324 | 8 | 2 | 1 |

N/E/X输入分别比H多15.4%/14.6%/30.3%，这些是本次累计使用量，不是Goal Entropy或真实效用。
额外成本含工具描述、种子回执/投影、生成历史和X不同调用时序，不能全归因于T4措辞。
四组均完成同一读卡动作，没有新的独立结果证明更高建议收益。
**VERIFIED的是额外观测成本与没有观察到动作优势；不是Goal Cognition总体无价值的证明。**

## 5. 两项实验有效性问题与最小处理

### 夹具编号错误

首个准备批次误把目录写成零基；冻结工具实际按1起算，0是首节别名。
发现后停止自身H Runner，保护收尾及清理通过，尚未进入Goal条件。
该试运行完整保留于：
/home/wqkan_wsl/uaea-n1x/research-records/goal-revision-timing-20261110T030524Z/
不并入20轮，不计模型失败。修正后的资料在模型运行前由实际read_section验证：
2=历史、3=档案卡、4=助手卡，章节互不串入。没有修改冻结工具。

### 离线评价器strip缺陷

旧document_hash_check对行范围重建做.strip()，丢弃真实工具正文保留的节尾空行。
于是原四份审计infrastructure_contract均为false；原报告保留，不覆盖。
原生正文hash与出站hash一直一致，源文件本身未变化。

仅修正scripts/research/longitudinal_audit.py一行，使用与既有行范围语义一致的精确join，不strip。
新增两项反例：合法节尾空行旧误失败；自洽伪造的去空行Observation旧误通过。
旧评价器26项局部测试中2项失败；修复后85项研究回归PASS。
新审计另存*-audit-exact-whitespace.json，四组8份Observation严格源匹配，
实际正文供给完整，基础设施判据4/4通过。**这不改变0次修订和认知/价值结论。**

未改运行时或已执行bundle；执行版本、后验评价器及diff分别锁定。
修改范围：离线评价器、对应研究测试、本报告与研究地图；隔离Runner仅420秒等待与只读种子门禁，
不提交/修补候选、不接管Harness循环。

## 6. 资源保护与复核

正式批次1005个service样本：NVML峰值30.12GiB，Windows Dedicated29.52GiB，
Shared0.240GiB，Windows Available最低22.38GiB，Commit最小余量43.08GiB；
WSL Available最低17.52GiB，Swap峰值16KiB，Linux完整采样最长1.82ms。
口径不相加，采样极值不是硬上限。无资源越界/遥测失效停止。
本研究主动ControllerStop后模型、采样器remaining=[]，4个Harness进程组absent。
无外部服务被停止；原阈值、Provider Policy、Context/KV及依赖不变。

复核：
- preregistration.json、condition-diffs.json、fixture-validation.json、execution-lock.json；
- H/N/E/X-evidence.json及*-audit.json原始审计；
- comparison-facts-posthoc.json、*-audit-exact-whitespace.json及posthoc-evaluator-lock.json；
- source-index.json、raw-function-and-rpc-index.json、evaluator.patch、evaluator-red/green.log；
- 各会话原生events、Goal Journal、逐轮快照及model-http-audit原件。

## 7. 判定与下一评审点

| 维度 | 本轮结论 |
| --- | --- |
| 明确任务/条件/长期方向区分 | VERIFIED，有限脚本下合理；不推广到自然长期意图 |
| Goal操作选择 | PARTIAL；Task/Path不更新合理，N/E历史保留可有理由；X实际修订要求未完成 |
| 抽象质量 | 文字草案有合理实例；新持久化修订不存在，质量UNKNOWN |
| 提交/版本/投影与权威边界 | VERIFIED限定；Host只记录真实form，没有把计划变成状态 |
| 后续行动 | 四组真实读对资料；未观察到旧head损害这一次动作 |
| 超越Relevant History的决策价值 | UNKNOWN；已观察到额外Token，没有相应动作收益证据 |

本批不能将“三组0修订”解释为普遍没有Goal理解能力。
真正暴露的研究限制是：**当前sideband把语义提案信号与模型选择执行工具绑定**。
X已经表达合理草案与合适操作，但没有结构化提交；无法仅用空版本链衡量语义提案质量。
未发现注册、保存、权限或投影的确定性故障，模型内部不执行原因仍UNKNOWN。

独立建议：停止重复措辞试验，保留H基线和现有工具正控，先评审一个有限的输入契约对照：
利用既有明确结构化回复研究入口与sideband分离比较提案表达和工具选择，或更换提案生产模型。
不能自动解析任意普通文字、自动补发提案、引入第二Loop或开放采纳权限；
已有结构化入口也不预设一定有效。正式接入另行评审。

另一项需明确的研究语义是候选用于解释“当前方向”还是记录“曾经的解释”：
保留旧历史合法，不应为更新计数强迫修订；若要维护当前解释，应能说明它相对普通历史的实际收益。
现有版本机制已保留历史，不因此新增Goal/Memory Engine、长期维护层或全局Information Pool。
本轮已到提案入口与用途的研究评审节点，停止新增模型实验；无需人工长会话或真实Goal确认。
