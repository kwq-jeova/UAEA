# Goal State Inference 与 Proposal Interface：隔离对照

2026-11-10。研究候选仍为 opt-in、非权威、可撤销；Memory 数学研究保持 Research Reserved。
不改 Phase-1、Harness 执行循环、正式 Goal/Memory 采纳、Provider Policy、模型依赖或资源阈值。不 Commit/Push。

## 1. 问题与方法依据

本轮将四个可观测环节分开：用户方向的解释、是否需要候选变化、提案实际表达、
Host 合法性验证与反馈。内部理解不可直接观测，研究者只评价原始输入支持的输出解释。
正确引用不证明语义支持，保存不证明传输，传输不证明理解，候选不等于正式 Goal。

- [Dialogue State Tracking with Incremental Reasoning](https://aclanthology.org/2021.tacl-1.34/)
  研究逐轮对话状态及后续策略的关系。本轮借鉴“状态推断与下游动作分开评价”，
  不将槽值 DST/JGA 等同长期人类 Goal 的真值或形成能力。
- [When2Call](https://arxiv.org/abs/2504.18851)及[官方代码](https://github.com/NVIDIA/When2Call)
  把何时调用、澄清及无法作答与函数参数准确性区分。
  本轮据此保留 Task/Path 不变更反例、合理无提案及 UNKNOWN，不用调用次数衡量认知成功。
  未引入论文训练数据、框架或第二套执行循环。

NO_CHANGE / FORM / REFINE / REVISE / WITHDRAW / UNKNOWN 是研究判读词汇，
并非新增 Runtime 状态、授权或每轮必须返回的字段。
真实测试重点覆盖 FORM、NO_CHANGE 和 REVISE；未覆盖的操作不得因离线合同通过而算认知通过。

## 2. 最小研究入口与不可混用的反馈

现有 G0/G1 已有可选 final JSON 协商，但其字段与 sideband 的父版本操作不同。
本轮仅在 scripts/research 下新增 goal_envelope.py，复用 GoalResearch.submit 的同一
原始用户来源、Quote、当前父版本、Observation 引用、不可变 Journal 与候选投影。

| 接口 | 表达 | Host 验证时点 | 可观察反馈 |
| --- | --- | --- | --- |
| Sideband | 原生 goal_hypothesis 动态工具，现有 schema | 原生工具请求处理 | 同轮原生回执及后续出站上下文 |
| 约定 final envelope | 精确对象 answer + goal_proposal，内部字段与工具一致 | 原生 Turn 完成后的现有 observe_final 钩子 | 下一用户轮的 last_final_feedback 与实际 head |
| Relevant History | 普通回答与同一文件工具 | 无候选提交入口 | 原始历史及执行 Observation |

不设置强制 outputSchema/response_format，不从普通 prose、Markdown JSON 围栏或自称“已更新”中提取。
普通回答无提案；精确 envelope 中 null 也无候选。重复键、额外字段、错误 Quote/父版本仍拒绝。
final 提案的来源是实际原生 agentMessage ID，source_kind=model_negotiated_final_proposal，
不是伪造的 tool call。工具入口仍为 model_semantic_tool_proposal。

final 接口必须等 Turn 完成后才有 Host 回执，不能要求它在同轮回看尚未存在的回执。
因此“同轮状态反馈速度”存在机制差异，不能把两个接口宣称完全等价。
prepared_on_next_context_request 仅为准备状态；只有出站审计与成功 transport 才计供给。

## 3. 冻结设计、反例与范围

预登记 2×2 接口/邀请条件，加 Relevant History；每个独立会话 5 轮，最多25轮。
T0/S0 在方向变化轮不额外邀请评估；T1/S1 仅增加“评估是否调整，由你判断”的同一后缀。
共同首轮均显式邀请建立干净种子，不计自然 Goal 形成；后续不指定工具或操作。
T2 取消子任务，T3 仅改变 CPU/联网条件，均不应机械撤回长期方向。
T4 明确替换长期方向。T5 只能选读一份资料，须结合当前方向与版本适用性，
不能通过顺序读取、旧方案或哈希等同真值取得通过。

资料只包含本轮预定义方案及版本事实，没有旧实验结果或成功/失败提示。
同一作用域不跨 Run 复制对象，独立会话原生 ID 不同，语义种子和源字节相同。
所有组使用相同 source bundle；实际生成的回答历史不同，单次样本不支持统计或长期价值结论。

## 4. 原始证据与结果

**总体 PARTIAL；没有形成有效的完整接口维护对照，不支持替换 Sideband。**

原件（不得互相覆盖）：
- 首次来源/可用性诊断：/home/wqkan_wsl/uaea-n1x/research-records/goal-interface-20261110T050247Z
- 完整载荷控制：/home/wqkan_wsl/uaea-n1x/research-records/goal-interface-payload-20261110T050723Z

首次诊断只有1个原生完成轮：请求确实提供 Goal 工具且成功 transport，模型却称没有候选通道，
未生成工具调用或候选。不能将这个无种子会话当作维护失败或接口优劣对照。
完整保留后，仅把共同首轮的字段说明改为完整固定载荷，另建预登记与独立记录；
没有修改后续维护输入、候选验证或普通回答解析规则。这不是对原会话自动重试。
完整载荷控制若仍有种子失败即停，不再继续调整 Prompt 或自动重载。

### 4.1 实际覆盖，而非计划覆盖

完整载荷研究实际为 T0 的5轮与 S0 的1个原生完成轮。
S0 在种子门禁后停止，因此 Runner 接受计数为0，原生完成计数为1；
不能用任一计数掩盖另一事实。加首次诊断，共7个原生完成用户轮。

| 条件 | 实际结果 | 证据范围 |
| --- | --- | --- |
| T0 sideband，变更轮无额外评估邀请 | 同一干净种子 form 成功，后续0次更新 | 5轮完整 |
| S0 约定结构化 final，无额外邀请 | 输出正确载荷片段，但非完整协商 envelope，0提交 | 仅首轮；维护不可评价 |
| H Relevant History | 未执行 | UNKNOWN；不拿旧实验冒充本轮匹配基线 |
| T1/S1 明确邀请评估 | 未执行 | UNKNOWN；种子条件不满足后按预登记停止 |

全部组的冻结 source bundle 字节相同（130文件），仅选择研究 transport 的命令参数不同。
两个实际研究组 T1 原始用户输入逐字相同，未向模型供给此前实验结论。
但并未获得“相同已保存种子”的完整配对，也未完成 2×2，不能报告公平比较已通过。
本轮未启动金融/联网场景，无真实长期效用或跨会话恢复证据。

### 4.2 T0：理解变化，但未提交修订；后续来源执行失败

原生候选：
goal-candidate:39d54491ba6ba7e71caa3557
（form Call ID chatcmpl-tool-9a7881754c7140f4）。
前两次原生参数 candidate_id 为字符串 "None"，被拒绝；第三次真实 JSON null 通过。
原生事件与 Host 接收值可核查；字符串来自生成还是 vLLM Parser 的更早边界仍 UNKNOWN，
本轮没有修改 Parser 或替模型纠正参数。

候选原文为给定干净种子，来源、Quote、版本与回执绑定 PASS，
实际成功传输请求4–8均含正确 head，不将显式种子计自然形成。
T2 用户取消子任务，T3 仅更改 CPU/联网条件，模型均保持旧候选，语义区别合理。
T4 用户替换长期方向，模型正确复述项目归档方向，但没有 Goal 工具调用。
“已按新方向接收并记录”是含糊措辞，不能单凭它断言完成特定 Host 版本更新。
T5 明确说明 Host 仍保存旧文档助手候选，候选状态陈述与实际一致。

独立负例：T5 声称“实际读到的资料版本：section 3”，但该轮**没有 document Tool Call，
整个 T0 也没有文档 ExecutionObservation**。它根据用户给出的目录选择正确名称，
不能算真实读取或有依据的后续决策，建议还混淆了方案可证伪性与用户整体方向。
Runtime 没有把这段文字变为读取事实、来源 Evidence 或 Workflow 完成。

### 4.3 S0：内容草案存在，正式表达未发生，不能放宽解析补成功

成功传输的三个模型请求均含 final_proposal_schema 与完整 envelope 契约，
均没有 sideband Goal 工具，实际作用域与预登记相符。
原生 final ID：msg_8809da33459924a1。
完成事件位置：S0/interface-goal_shadow-r1/app-server-events.jsonl 第218行。

最终回答是：
> 我已为本轮建立实验种子。

随后给出 answer/goal_proposal JSON 对象，再附一段普通说明。
内部对象中的 form、null、hypothesis 与 quote 内容正确，但**整个 final 不是协商 JSON 对象**。
Host 记录 RESEARCH_FINAL_NO_PROPOSAL / ordinary_answer_not_extracted，
没有提交、没有版本、没有“拒绝后仍偷偷保存”。
“已建立”与实际空候选矛盾，是 VERIFIED 的模型状态陈述错误。
它也违反首轮“不读文件”，两次调用 read_section 读取 sandbox 目录，均真实失败并保留 Observation。

这证明在本样本中，“能写出正确载荷”与“按已协商接口提交”分离；
**没有证明 structured output 一般不可靠，也没有证明 Sideband 更优。**
本研究是可选 final-envelope 协商，未测试 API 强约束 structured output，两者不可混称。
不把包在普通文字中的 JSON 自动抽取入库，否则会改变本轮明确的控制边界。

另有独立合成格式控制：相同原始用户输入与候选内容，在临时状态里，
真实包裹文字回放产生0候选，人工构造的纯 envelope 产生1候选；
ActiveGoal 仍空，domain step runs 为0。此为确定性入口检查，不计真实模型接口成功。

### 4.4 成本与 Context

| 条件 | 完成原生轮 | Provider请求 | 累计输入/输出Token | Compaction |
| --- | ---: | ---: | ---: | ---: |
| T0 | 5 | 8 | 93,996 / 1,488 | 0 |
| S0 | 1 | 3 | 32,618 / 347 | 0 |

T0逐轮耗时73.67/31.84/36.62/30.30/59.85秒；S0额外包含两次错误读取。
S0不是完整5轮，**不能把较少Token当接口效率或认知收益**。
两组有效Context均31,129，最大单次实际输入分别14,298和11,437；
未观察Compaction或Context溢出。S0完整原生最终消息保留JSON后说明，不能归因为缺少闭合JSON的输出截断。
模型内部为何不遵循契约仍 UNKNOWN，不根据最终文字倒推隐藏思考。

### 4.5 复核入口、评价器与安全

comparison-facts.json、native-evidence.json、T0/S0-audit.json、selected-model-requests.json
分别提供事实、逐轮原生回答、结构检查和少量完整脱敏出站请求。
source-index.json 给出路径、行数、字节与SHA256；execution-lock/source-lock/frozen 保留运行源码与输入。
原生 final→版本绑定与 tool Call→版本绑定分别审计，未把 agentMessage ID 冒充工具调用。
已有全脚本 evaluator 对 T0 报 required_document_observation_missing，对 S0 另报缺轮；
保留 FAIL，不把它们重新包装为全部基础设施 PASS，也不误称已证明 Runtime 存储故障。

本轮独立 post-hoc inspector 初稿把“无候选”的投影判为 PARTIAL，已更正为 UNKNOWN；
更正前副本保留，分析脚本与结果单独锁定，未改原始模型记录。冻结前95项、收尾96项回归仅指仓库研究测试；新增一项真实包裹JSON负例，不重跑模型。
两个有界服务实例（首次诊断、完整载荷控制）均通过原保护预检。
合计524个有效 service样本：NVML峰值29.82GiB，Windows Dedicated峰值29.21GiB，
Shared峰值0.214GiB，Windows Available最低21.12GiB、Commit余量最低42.29GiB、
WSL Available最低17.51GiB、Swap峰值16KiB。内存域不相加。
均为研究门禁结束后的 CONTROLLER_STOP，无真实资源/遥测故障；模型/采样器 remaining=[]，
三个实际创建的Harness进程组均退出，8000/8003无监听。未关闭外部服务。


## 5. 工程检查

研究回归96项 PASS：既有85项加11项 final-envelope 负例与来源/版本/回执测试（冻结前95项，实际失败后补包裹JSON负例）。
测试证明研究入口确定性边界，不证明 Goal 语义质量或建议收益。
Runner 新增显式 --goal-channel envelope 选项；默认 legacy/sideband 行为保留。
研究 GoalResearch 只把 source_kind 从硬编码改为类属性，默认值不变。
全局 Harness、冻结 Runtime、模型与监控代码均未修改。

## 6. 待评审结论

| 维度 | 判定 | 限定结论 |
| --- | --- | --- |
| Runtime 来源/候选权威边界 | PASS（限定） | T0来源版本与出站一致；S0普通文字未升级；正式Goal始终空 |
| Goal 状态推断 | PARTIAL | T0区分Task/条件与新方向；不证明长期Goal形成 |
| Sideband 自主修订 | PARTIAL | 能理解新方向，未提交更新；不是工具存储已证明失败 |
| 结构化实际提案/后续维护 | FAIL / UNKNOWN | 首轮未形成约定提案，维护未测试 |
| 后续行动/真实决策价值 | FAIL / UNKNOWN | T0虚称读取；没有有效匹配行为价值对照 |
| 接口优劣、邀请效应、History增量 | UNKNOWN | 缺相同已保存种子的完整对照，未执行剩余条件 |

**独立判断：没有足够证据调整正式 Goal Proposal Interface。保留原 Sideband 和 isolated opt-in envelope，
不把候选自动从回答抽取，不开放采纳，不增加审核Agent/Goal Engine。**

如果架构评审仍希望继续接口研究，最小前提是先证明两个接口都能在明确协商下稳定建立种子，
并区分“可选回答协商”与“API强约束结构化输出”的不同实验对象；不可把一个接口只有草案
与另一个已有候选的后续行为直接比较。未验证的修改应另行预登记，不继续无界调整 Prompt。
本轮停止；不需人工长会话，也没有足够证据要求更换模型/架构。
