# Goal M2 历史失败明细消融与条件式 M3（2026-11-13）

总体 **PARTIAL**。本轮取得一个显式反馈下、语义忠实且合法保存的 Goal 修订样本，并在同一 Thread 完成后续研究任务；但不能证明旧失败明细必然有帮助，也不能证明新 head 已产生超越 Relevant History 的决策增益。

批次：goal-failure-history-ablation-20261113T001107Z。

## 1. 评分器收敛与实验问题

逐 Call 字段评分修复已归档，旧4/6更正及失败记录保留。本轮不再重复评分器回归。[scorer-archive.json](../../../research-records/goal-failure-history-ablation-20261113T001107Z/scorer-archive.json) 钉选已审计的评分器、测试及更正记录，不把工程限定PASS升级为模型字段理解PASS。

研究问题改为：在相同修订任务下，六次旧失败提案的明细是否影响 CURRENT 引用选择？

两个独立 Native 副本均从同一真实失败历史 H、原始两 head Goal 状态及同一 Journal 前缀恢复。候选、原始用户历史、旧模型回答、当前完整修订输入、工具 Schema、文档权限、共享只读资料路径、模型与采样配置相同。

- **移除明细**：只在隔离研究的 Provider 请求中移除六条旧失败 fact。
- **保留明细**：保留同六条 fact，含实际参数、quote、错误及 committed=false。
- 原始 Journal、Native、已保存版本及 Host 权限均不改；失败事实不执行、不重放。
- 两组 max_output_tokens 均固定2048，Context64K、KV1GiB、seq1、56/72、util0.65与安全阈值不变。
- 每组一次，不改当前 Prompt 追求成功；首拒绝停止。首个合格组才允许一次条件式 M3；未合格组不追加纠正。
- 顺序预登记为先移除、后保留；无随机化或多次重复。

[预登记](../../../research-records/goal-failure-history-ablation-20261113T001107Z/preregistration.json) /
[当前修订输入与M3任务](../../../research-records/goal-failure-history-ablation-20261113T001107Z/scenarios.json) /
[仅处理变量的CPU检查](../../../research-records/goal-failure-history-ablation-20261113T001107Z/cpu-ablation-check.json)。

**因果限制：** 这是“失败调用明细”的消融，不是彻底删除曾经失败的整段交互。旧用户纠正和旧模型错误回答保留一致。实际请求还存在合法的新 Input/Turn/message/effective-state ID、Host时钟和 skills-root 路径差异；后者含条件名，有潜在线索泄漏。删除明细也改变输入长度与位置。因此固定核心变量不等于严格同字节单变量试验。完整差异已保留，未事后修改请求掩盖它们。

## 2. 两组实际结果

| 维度 | 移除失败明细 | 保留失败明细 |
|---|---|---|
| 真实提案 | 1次 revise | 1次 revise |
| 目标 | 原长期 head 098ea60b… | 相同原长期 head |
| 候选正文 | 长期跨公司研究AI产业投资机会是全局范围目标。 | 长期跨公司研究AI产业投资机会是全局范围目的。 |
| quote | 历史目的短句，非CURRENT | 当前输入中的纠正句，合法CURRENT |
| Host | 拒绝，committed=false | 接受并保存，committed=true |
| 版本/heads | 仍2版本/2heads | 3版本/2heads，旧全局版本不再为head |
| 拒绝/保存后状态理解 | CENSORED，按首拒绝停止 | 正确报告新ID、正文、保存、candidate而非ActiveGoal |
| M3 | 未运行 | 同Thread完成1个新任务，2次真实读取 |

两组固定先后、每组一次，服务热态和生成差异未被对消。本例中，移除旧失败明细没有消除历史 quote 误用；保留明细也没有阻止正确纠正。允许“失败反馈可能提供有用反例”的研究假设，但不能由一对样本断言它必要、充分或普遍有益。字段、来源位置、模型生成变化及顺序效应的作用仍 UNKNOWN。

### 移除组的失败证据

Call：chatcmpl-tool-9bcf4efd8d00ae92。

- quote=“长期跨公司研究AI产业投资机会”，不在当前修订输入中。
- Host 实际返回 CURRENT 引用错误，未保存；不能声称模型又虚报保存，因为拒绝后没有完整最终回答。
- 另提出 evidence_ids=[execution:b6b9115d939ed816]。此ID不在已恢复的四个Observation中，也未出现在实际输入；本范围内没有可追溯依据。Host在quote处已拒绝，不能宣称其余参数已通过，也不能伪造第二次Host拒绝。

## 3. M2：合法、忠实、实际保存的限定存在性证据

保留组 Call：chatcmpl-tool-b5322cd622602c03。

    operation: revise
    parent: goal-candidate:098ea60b1c3caf2ca410b22d
    hypothesis: 长期跨公司研究AI产业投资机会是全局范围目的。
    quote: 请实际修订（revise）当前保存的长期用户目标候选：其中将你为了研究而补资料、查行情等工作需要，以及临时资料条件，写成了我的持续目的。
    input_ids: [input:071345a5-ebed-4433-9054-f52c4b43ce0b]

新版本：

    goal-candidate:ff2a010b338474f6ea3f66f5
    SHA256: a3d425cfa4dd7ff1e461ef2fd7c08465ff58b2285fb5e225f27f85d9b3e4ba54

分别核验：

1. **语义忠实性（本案例限定）**：保留原始用户“长期、跨公司、研究AI产业投资机会”及全局范围；去除查找更多资料等模型工作需要，没有加入“用户没有任何长期限制”等无依据否定，也未把创建/修订指令写入目的。
2. **引用合法性**：quote是当前完整用户输入的精确子串；当前Input ID确实登记。
3. **实际提交与保存**：Native参数、Host回执、Journal提交事件、payload/candidate哈希及父版本一致；不是模型口头宣称或Host补发。
4. **历史不变**：两个原版本全文仍保留。旧全局版本从当前head集合退出，局部Intel候选不变。
5. **实际后续供给**：新head及其哈希出现在之后3个完整传输的请求中，包括M3请求，不仅是本地投影准备。
6. **状态回报**：模型准确报告新ID/正文/committed=true、局部未变及没有ActiveGoal采纳。

引用质量仍有边界：提案 input_ids **仅显式提交当前纠正输入**，没有按提示把历史 f4 ID放进该数组。历史目的可沿 parent→原候选→原始 f4全文及保留的用户历史独立核验；模型也在最终回答中区分当前纠正依据和历史目的依据。不能把这些描述写成“提案已显式提交f4引用”，也不能仅凭合法链接证明语义。

当前反馈、M3任务及原种子用户角色输入属于固定研究脚本；“真实”指实际模型、Native、Host保存和工具轨迹，不代表已确认现实用户的当前投资目标或历史心理状态。这是**显式修订请求、已恢复真实种子、当前纠正引用指导**下的成功样本，不是自然Goal形成或稳定自主维护。M2可记录为限定通过的存在性证据，不是通用成功率。

[模型修订/后续完整回答](../../../research-records/goal-failure-history-ablation-20261113T001107Z/with_failure_details/model-answers.md) /
[原生提案与回执](../../../research-records/goal-failure-history-ablation-20261113T001107Z/with_failure_details/goal-wire-receipts.jsonl) /
[实际HTTP请求](../../../research-records/goal-failure-history-ablation-20261113T001107Z/with_failure_details/model-http-audit.jsonl)。

## 4. M3：状态与行动连续性成立，Goal因果增益未证明

在核验合法保存、忠实正文和完整后续供给后，按预登记放行一次任务：

> Intel当前局部任务先取消。这次转看Apple和Alphabet，自己确定最值得先核验的比较问题，并用已有只读工具实际开展研究。

实际行为：

- 模型转向Apple/Alphabet，提出外部政策因素与季度盈利比较的问题。
- 两次真实 read_section（新执行事实，但重读既有冻结资料，不是两份新独立外部证据）：afb7fea3fde4a5d0 读取 S-AAPL，9f7cb75c55359ef6 读取 S-GOOGL；Native→执行决定→Observation→回执身份和文件/正文SHA一致。
- 使用相应公司、季度/财政期间与单位，保留真实收盘价、forward年度EPS共识等缺失为UNKNOWN。
- 新全局head保持，没有因取消Intel当前任务错误撤回全局方向，没有把补齐资料重新写成长期目的。

“Intel任务已取消”在此是研究焦点切换的语义响应。没有正式Workflow取消或局部Goal withdraw调用，局部候选仍是candidate；不能把文字变成执行事实。

**M3总体PARTIAL**：

- 新状态实际供给及真实后续行动是 VERIFIED。
- 行为与修订目的相容、未继续执行旧污染待办，有限定观察支持。
- 但当前任务本身指定了Apple/Alphabet，Relevant History也能解释AI方向。未做Goal-view开/关或匹配Relevant History对照，因此**不能确认这两次行动由新head导致**，更不能认定有决策增益。

财务解释也为PARTIAL：冻结材料是研究者保存的官方文档摘录，未重新核验市场事实。主要数字和单位匹配；但“Alphabet收入远超Apple”对约11.4%的差异表述偏强，跨公司每股EPS相近不能据此推断盈利结构或韧性；表内“2025同期EPS下降”时间措辞不准，正文才正确说明2026相对2025下降0.75约26.1%；摘录未披露外因不能泛化整份财报没有披露。不把这些问题转成新的Runtime金融裁判，也不以完成读取宣布投资判断正确。

## 5. 成本、安全及原件

| 阶段 | 输入tokens | 输出tokens | 完整模型响应 | 用户Turn |
|---|---:|---:|---:|---|
| 移除组修订 | 22,204 | 191 | 1 | 首拒绝停止，0完成 |
| 保留组修订 | 52,222 | 871 | 2 | 1完成 |
| 保留组M3 | 57,594 | 1,235 | 2 | 1完成 |

5个响应均 response.completed / HTTP framing完整，上下游SSE一致，输出均低于2048上限。无Compaction/Context Overflow。两组完成程度不同，不能把修订阶段的累计成本差或耗时差当作公平收益/性能对照。

一次模型加载，整体512.112秒；468条有效service资源样本。NVML峰值28.659GiB、Shared峰值0.173GiB；Windows Commit最低余量23.474GiB、距离原停止线最小缓冲5.178GiB；WSL最低可用17.603GiB。AC及单时钟遥测正常，计划CONTROLLER_STOP/remaining=[]，原安全阈值未放宽。

正式可执行源码、安全/模型pins及源Native home不变；真实历史及失败记录保留。新代码仅隔离研究请求消融与审计脚本，不自动从普通回答创建Goal，不放宽CURRENT，不增加Goal/Memory/执行权限，不Commit/Push。

[fact-audit.json](../../../research-records/goal-failure-history-ablation-20261113T001107Z/fact-audit.json) /
[固定项与原件核验](../../../research-records/goal-failure-history-ablation-20261113T001107Z/controls-and-immutability.json) /
[资源](../../../research-records/goal-failure-history-ablation-20261113T001107Z/resource-summary.json)。

## 6. 里程碑与提交评审的问题

| 事项 | 当前结论 |
|---|---|
| 逐Call评分器修复 | 已归档限定PASS，不再重测 |
| 历史失败明细消融 | PARTIAL，观察到不同结果，因果不确定 |
| M2受反馈忠实修订 | **限定存在性PASS**：一次合法忠实保存及准确状态回报 |
| M3状态/行动连续性 | VERIFIED观察；**总体PARTIAL** |
| 新head对行动的因果影响 | UNKNOWN |
| M4自主生命周期 | UNKNOWN |
| M5超Relevant History的决策价值 | UNKNOWN |

建议下一项最小研究：从本次已纠正checkpoint复制两个分支，保持相同当前任务和全部Relevant History，只比较是否提供**当前结构化Goal视图**；历史真实用户、成功提交和回执两组均保留。采用匿名存储路径避免条件名泄漏，记录必要ID/时间差异；观察有区分力的行动、错误和成本，接受无额外收益。

不需要再改评分器、扩展CURRENT、叠加Prompt重试或进入30×2。现有Sideband足以产生本次M2证据，尚无新架构障碍。本轮已到达M2纠正与后续行动的实质性限定里程碑，提交人工阶段评审；**不自动接入正式Runtime或扩大权限**。

## 7. 独立审计

Audit Agent已独立核验两个首请求的0/6事实差异、受控项及额外混杂、新版本与父链、三次后续投影、M3两次真实Observation与资源/源码边界。最终书面意见另存本批次 independent-audit.md。消融因果、M3因果和财务判断的限制必须保留，不能合并成整体认知PASS。
