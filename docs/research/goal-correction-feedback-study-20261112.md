# Goal候选纠正研究：评价修订与种子前置失败（2026-11-12）

**整体PARTIAL；M2尚未建立。** 评价标准修订完成，16项离线标注契约检查通过；一次真实Bolt+Harness种子建立没有发生Goal Tool Call，当前Host无候选。唯一纠正反馈未发送，后续M2/M3/M4不是FAIL，而是NOT RUN。不能将空状态结构PASS或模型候选文字当成闭环。

## 1. 评价标准v2：已完成，非Runtime语义裁判

分别记录三维：表达来源、意图主体、用户认可范围。用户可以转述模型计划；模型也可以解释用户目的，speaker或最后一条消息不能代替三维判断。

分别审查：
- 实质性目的/范围扭曲：Agent待办升级为用户长期目的、Task扩大为全部方向、无依据永久约束或建议被冒称已认可。
- 手段/执行混入：查询、读取、计算、补共识是否改变目的，须结合上下文。
- 无害背景冗余：额外财务事实、方法说明未改变目的/范围/约束，不因关键词或不够简洁直接判无效。

旧宽范围候选保留了有依据的投资研究核心，同时混入查询与保存操作；不能直接说核心目的被完全替换。旧局部候选中的真实财务数字也不因出现在目标文本就必然有害。旧严格clean-seed gate及停止事实保留，通过有日期附注澄清评价，不覆盖冻结批次。

用户当前澄清支持纠正当前解释，不证明其全部历史心理从未变化。孤立输入只能作语义分类；只有真实当前候选及Scope存在，才能评分maintain/refine/revise/withdraw。

最小修改：
- scripts/research/README-goal-hypothesis.md追加研究标注说明。
- 前轮A/B报告追加v2澄清；原运行、错误候选及NOT RUN不改写。
- 本批隔离review_rubric.py和rubric-fixtures-results.json：12组标注反例+4项缺字段/无真实种子Scope负例，共16检查；覆盖模型来源却是用户目的、用户只认可执行步骤、方法本身是目的、无害事实冗余、真实quote但解释无支持及当前澄清。
- 这些检查验证研究标注契约，标签由研究者依据场景给定，**不是Bolt语义准确率16/16**。actual_saved等标注也不证明保存，真正前置门以Native/Journal/快照交叉核对。

原Goal审计器负责身份、来源、版本、传输，不应改成关键词语义分类器。本轮未修改正式Runtime、Schema或SQLite。

## 2. 真实旧候选及恢复核查

旧批次：/home/wqkan_wsl/uaea-n1x/research-records/goal-intent-lifecycle-20261112T031832Z
旧Thread：01a1cdd9-84df-7030-a240-4ea8f75089ea
原始候选：goal-candidate:098ea60b1c3caf2ca410b22d
旧Call：chatcmpl-tool-9405f3f580097084；原Goal Journal行1、Native调用行60。

完整旧内容：

> 长期跨公司AI产业投资机会研究是全局范围目标，需从本地摘录之外查找更多AI行业与公司资料，并在可撤销的目标假设中保留。

表达源是旧模型；目的核心描述用户的实验方向；查询及保存是Agent工作/操作，未获逐字长期认可。旧输入quote合法，但不证明整个附加内容受到支持。这是本轮历史研究对象，不是新Thread已经存在的Goal。

恢复核查见restoration-review.json。Native有thread/resume，但Goal研究通道明确未实现跨进程完整Host恢复；Goal快照只含研究heads/versions，RuntimeObjectStore.snapshot为摘要，未直接导出完整注册输入、执行历史及处理Call映射。没有现成受验证的全量恢复路径；**不声称离线重放在原理上不可能**，本轮不为此扩展正式Runtime。

因此按授权选择独立批次、真实Sideband重建。旧candidate ID只保存在来源审计中，未粘到新模型请求当当前ID。旧Journal全文件hash复核未变。

## 3. 新批次、冻结条件与唯一种子请求

新批次：/home/wqkan_wsl/uaea-n1x/research-records/goal-correction-20261112T052947Z
新Thread：01a1ce41-26eb-7c70-80f8-e675eaf3eb8a
唯一用户Turn：01a1ce41-270d-7b70-8441-dd1577a5aae0
注册输入：见final-audit.json的input_id。

correction-scenarios.json预先固定最多6轮：种子→一次纠正反馈→中性状态读回→Apple新Task→长期方向变化→后续核验。门禁在第1/3轮后检查实际种子和纠正状态，不再要求“纯净措辞”。preregistration.json预登记单次加载、零重试、反馈仅第2轮；失败不修改提示反复求PASS。

首轮明确表述当前持续目的，引用上述旧模型解释，说明并非逐字认可，并请求通过可选Sideband原样保留为可撤销研究候选；旧记录不等于本轮提交。这是受控历史解释重建，不是自然形成能力测试，不把故意保留旧错误的请求当作新候选语义准确率测试。

这里可能同时存在“原样保留历史解释”与“可选用户目的工具”的理解张力；不能根据最终回答反推模型内部原因。没有新的接口A/B，不宣称因果归因。

未发送的唯一纠正输入原文：

> 刚才保留的解释里，有些内容其实是你为完成研究安排的资料获取、工作步骤或候选保存操作，并不是我的长期目的。请纠正你对我意图的理解：保留真正的用户目的，把这些工作需求放回执行计划。这次澄清不能客观证明我过去的心理状态从未变化。你认为应怎样处理，请依据真实状态说明。

它没有提供完整标准候选，也没有指定revise。因真实种子未建立，不能发送后把孤立语义改述计为生命周期纠正。

## 4. 实际执行与模型陈述

| 项目 | 实测及限定 |
|---|---|
| Native | 1 started/1 completed，单轮110.39秒 |
| HTTP与响应 | 2/2完整framing、2个completed，原始SSE/下游一致、无采集截断 |
| Goal定义 | 2/2实际出站请求包含goal_hypothesis |
| Tool Call | 上游SSE与Native均只有4个read_section；Goal调用0 |
| Host | Goal版本0、heads0、无Goal拒绝、无提交/发布成功 |
| 数据 | 实际读取ledger+Intel/Apple/Alphabet三小摘录，源hash匹配；无文件写权限 |
| Context | 最大输入17602、有效窗口62259；无Compaction/超窗 |
| 成本 | API累计输入28849/输出939 Tokens；非唯一信息量或有效bit |
| 正式状态 | ActiveGoal始终null，模型输出未变为来源证据，无Memory Admission |

Native最终正文行646，Turn完成行653。模型说：

> 历史解释（已保存在 ledger.md 中，可作为本轮可撤销研究候选）

又说：

> 我已按你要求保留这条历史解释为本轮的一条可撤销研究候选，但并未将其提交为正式 Active Goal。

它同时提到“旧记录不等于本轮已提交”。**ledger来源归属错误VERIFIED**：实际ledger是冻结资料目录，字节hash仍与frozen/catalog.md一致，不含这段候选，且无写入Observation。

“保留候选”的措辞与当前空Host状态未明确区分，但它没有给出Host回执/新ID，且有未提交限定。应记为保存状态表达含混/无实证，不能夸大成已经观察到一条具体虚假Host提交回执。模型在普通回答中重述旧文本，不是新候选保存。

失败位置在模型尚未产生Goal调用之前：没有Host拒绝可归因，也没有已提交后投影丢失。是本次输出/工具选择与来源陈述问题；是否由历史转述、可选工具理解或其他语义因素导致仍UNKNOWN。此前真实Sideband提交成功存在，不能凭此样本宣称Schema无法表达或接口永久失效。

## 5. 纠正前后及里程碑

“之前”是§2真实历史候选；**“之后”没有新候选**。新批次没有父版本、新head或后续用户轮次，不能拿旧ID、旧B成功投影或空快照PASS补齐。

| 里程碑 | 当前判断 | 证据范围 |
|---|---|---|
| M1 用户意图归属 | PARTIAL | v2标注可用；本次有模型解释误归ledger的反例，未新增形成候选质量证据 |
| M2 受反馈纠正 | NOT RUN / UNKNOWN能力 | 真实种子前置未成立，反馈尚未发送；不是已证明纠正失败 |
| M3 跨轮状态一致性 | NOT RUN | 无新版本/下一用户轮；空状态完整性不算M3通过 |
| M4 自主生命周期 | NOT RUN | 没有实际当前种子，不能对孤立变化指定操作 |
| M5 决策增量价值 | UNKNOWN | 旧Relevant History保留，本轮无匹配收益对照 |

Agent To-do是否被清除：旧记录仍含混合内容，未被改写；新记录不存在。**不能宣称污染已修复**，也没有错误内容新升为ActiveGoal、Memory或执行授权的证据。

## 6. 安全、审计与修改范围

固定56/72、64K、1GiB KV、单并发、util0.65；实际模型就绪97.08秒、36GiB预算、KV109817逻辑Tokens。原GPU、Commit、WSL、电源、单钟新鲜度和Fail-Closed保持。

服务329条有效采样（Guard全流程335条），NVML峰28.204GiB，Shared0.131GiB，Commit最低余量26.287GiB、距原停止线7.991GiB；Windows可用最低33.576GiB、WSL17.619GiB，Swap峰0.011719MiB。AC414条有效在线；10项CPU故障反例拒绝。没有真实资源/遥测停止。

实际停止是研究者依据无种子写gate-1-review.json pass=false，后续研究驱动记Preregistered study gate not passed；模型服务CONTROLLER_STOP清理，primary_sensor_failure=null、剩余进程为空，8000/8003端口无监听。不是模型服务异常或反馈超时。

174项输入锁、131份冻结/当前执行源码、15份正式安全/启动原件未变。保留原工作树；只更新研究说明、旧报告附注、本报告、研究地图和隔离脚本/证据，不Commit/Push。

复核入口：
- historical-seed.json、restoration-review.json：旧来源与恢复限定。
- correction-scenarios.json、preregistration.json、evaluation-private.json：冻结设计。
- session/app-server-events.jsonl、goal-events.jsonl、goal-research-state.json：真实执行与空候选。
- session/model-http-audit.jsonl、streams：2个真实请求/响应，工具定义和完整性。
- analysis/answers.json、requests-audit.json、final-audit.json：原文、来源错误证明、版本与安全hash。
- rubric-fixtures-results.json：16个合成标注检查，非认知成功率。

## 7. 独立判断与下一步

评价边界已经修正；本轮没有因方法词、财务事实或措辞不够纯净拒绝候选。真正阻塞是**没有真实候选提交**，应与候选语义质量分开。

当前不支持新增Goal Engine、正式subject字段、Memory层、第二Loop或通用语义裁判，也不把源身份校验提升为真值证明。Sideband已有可用提交证据；新样本未证明结构障碍。对M2/M3的承诺不能建立在文字“已保留”上。

下一次最小研究应先确保可审计种子：可选择独立、明确标识的Sideband提交能力正控制，或先证明隔离Host恢复的对象/来源/版本完整性。两者不混成自然Goal形成；未拿到真实种子仍不得评分M2。纠正阶段仍只给一次反馈，不由Host补候选，不为得到PASS反复修改语义输入。

本批按预登记保留负面结果并停止追加模型请求，提交研究评审；不安排人工长会话，不上调Goal成熟度。Memory保持Research Reserved。需要的是解决研究前置条件，而不是据本次输出扩大正式Runtime。
