# Goal Continuity：纠正、保持与行动选择联合验证（2026-11-13）

**总体 PARTIAL；A 跨会话显式纠正和 B 长期目标保持取得限定存在性证据，C 尚未证明结构化 Goal View 的决策增益。** 不新增正式机制，不把三场景合并为一个成功率，也不将 A 新 head 与独立 B/C 的行为拼成同一条认知演化链。六个预登记分支全部执行，失败/删失样本原样保留，本轮结束并提交评审。

批次：goal-continuity-three-20261113T030425Z。环境为 56/72 UMA、64K、1 GiB KV、单并发、utilization 0.65，Bolt + vLLM 0.32.0 + Codex 0.163.0。保持 Sideband、CURRENT、非权威候选、全部资源保护。未 Commit/Push，未修改正式 Runtime、Schema、权限或人工入口。

## 1. 基线与 32 版本勘误

读取 20261113_104111_GoalContinuity 及其原始研究批次，不重造种子。恢复入口已有 50 项 CPU/原始身份绑定及真实跨 Thread 读回证据，本轮不重复该工程验收。

冻结基线精确复制前批次 profile-initial-journal.jsonl（44,867 字节），SHA256 为 a8d1973aad1aae9bb15af7d11ebbe8ecb52ad5635a898b32d8da0c75763fdd7f。包含三版本、两 family、三次接受和六次历史拒绝；不包含上一批次后来的模型讨论或研究注释。每分支新 Thread、新 profile Journal、新 Native home，六份初始 Journal 同哈希，后续互不继承。

| 身份 | 基线及本轮处理 |
|---|---|
| 原 Thread | 01a1cdd9-84df-7030-a240-4ea8f75089ea，原身份保留 |
| 全局 family 根 | goal-candidate:098ea60b1c3caf2ca410b22d，旧污染解释作为不可变历史 |
| 当前全局 head | goal-candidate:ff2a010b338474f6ea3f66f5 |
| 当前全文 | 长期跨公司研究AI产业投资机会是全局范围目的。 |
| head hash | a3d425cfa4dd7ff1e461ef2fd7c08465ff58b2285fb5e225f27f85d9b3e4ba54 |
| 局部 Intel family | goal-candidate:0cb6591e2475fdd96208bc87，仍属原 Thread，不迁成新 Thread 当前候选 |
| Global 绑定 | 研究者沿用原 operator family 绑定，不是模型自主推断 Scope，也不是正式 Goal Adoption |

**文档勘误：32 是单个 Thread 可见候选版本集合上限，不是 Profile 总版本上限。** 包含该 Thread 可见 global family 的历史版本及本 Thread local 版本；其他 Thread 不可见 local 不计入。16 MiB Journal、2 MiB 单条、4200 字符当前视图、3 head、单 Turn 最多两次接受等既有限制不变。已更正研究入口、原报告及索引；旧 Windows 证据包不覆盖。

基线与执行代码见[checkpoint 锁](../../../research-records/goal-continuity-three-20261113T030425Z/checkpoint-lock.json)、[本轮研究 glue](../../../research-records/goal-continuity-three-20261113T030425Z/study_driver.py)、[冻结协议](../../../research-records/goal-continuity-three-20261113T030425Z/preregistration.json)。Journal 是隔离研究候选的唯一可修改来源；派生快照不作第二 authority。未恢复旧 Workflow/Step 为新执行。

## 2. 实验控制与证据口径

A/B 各一分支；C 两对，预登记顺序为 **A、C-ON1、C-OFF1、B、C-OFF2、C-ON2**。C 的顺序近似平衡线性暖机影响，不消除随机输出、顺序、引擎持续状态及样本不足的限制。没有更换输入、重跑失败分支、追加人工纠正或自动改参。

C 每组相同的普通 Relevant History 包含 16 条原始用户消息、真实资料读取调用/回执和已接受 Goal 调用/回执。逐项绑定原路径、行号、Thread/Turn。模型两组都可以看到原目的和已纠正 head 的历史回执；**OFF 仅去掉当前专用结构化 Goal View，不是删除全部 Goal 历史。**

相关历史由研究者预选，不能证明自动相关历史检索能力；通过相同的非权威历史消息提供，不登记为 CURRENT、不冒充新 Tool Observation、不恢复为可执行函数调用。保留现有 Host 预算，不扩大 24 KB 恢复块；普通历史按正常 Provider 输入受窗口预算约束。

先以真实 Codex→Bridge→CPU HTTP 接收器核对实际出站；随后独立 Audit Agent 复核两对真实模型首请求。归一化新 Thread、Workflow/Task、当前 Input、消息/effective-state ID、会话 home、Host 时间和 client metadata，移除 ON 专用视图后，**两对首请求均无其他差异**。后续请求随模型实际行为而不同，不宣称仍逐字一致。匿名 f0…f5 路径不暴露 ON/OFF 条件；视图增减不可避免改变长度与后续位置。

工具、Schema、冻结五文件、模型、采样、Context 和预算相同。每分支最多 4 次实际上游请求、2048 输出 tokens/请求、420 秒 Turn；总任务 2700 秒、最多一次模型加载。Harness 内正常参数自纠正可以发生，没有第二套 Agent Loop。

资料是既存研究者摘录及其中的原件哈希声明，不是本轮重新核实的官方完整财报或实时行情。冻结研究时点 11-10；11-09 保存的字节不能证明 11-04 当时已知。CURRENT 任务均为本轮研究者编写，不冒充现实用户当前投资意图。本文的数值正确性是相对冻结材料及独立算术，不是投资建议。

[原历史](../../../research-records/goal-continuity-three-20261113T030425Z/relevant-history.json) / [来源及哈希](../../../research-records/goal-continuity-three-20261113T030425Z/source-provenance.json) / [CPU 实际出站](../../../research-records/goal-continuity-three-20261113T030425Z/cpu-outbound-proof.json) / [独立核验](../../../research-records/goal-continuity-three-20261113T030425Z/audit-independent-checks.json)

## 3. 场景 A：跨会话纠正长期解释

当前输入要求：仍研究 AI 产业投资机会，但重点转为可检验的跨公司投资研究方法，不直接替用户作买卖结论；不将补行情/找共识等待办写成目的，不添加未表达的持仓、期限或风险偏好。未提供完整标准候选，未指定 revise 参数。

真实调用 chatcmpl-tool-98f84c205dd46177 选择 revise：

- 当前目标：goal-candidate:ff2a010b338474f6ea3f66f5。
- CURRENT quote：我仍希望长期研究AI产业投资机会，但重点是形成可检验的跨公司投资研究方法，而不是直接替我作买卖结论。
- 当前依据：input:a8c68dd6-90af-418b-b745-4e9eb330fcf4。
- 历史目的依据：input:f4e32d18-219d-4c3e-83ab-6b89201fee81。

Host 实际接受并保存 goal-candidate:76fe2c341f981c349d539f56，内容 hash b5b4e45bbfdd1e4e431ea1bed2f3303db425be27e7d389d28a2ad372d92653c0。已有契约用 metadata.previous_candidate_id 和来源关系记录父版本，不把顶层通用 parent_id="" 误读为断链。下一次成功传输请求携带新 head；旧三版本逐字段不变。最终回答准确给出新 ID、全文、Host 保存事实及 semantic_correctness 未确证。

**保存全文：**

> 长期跨公司研究AI产业投资机会是全局范围目的；重点是形成可检验的跨公司投资研究方法，不替用户作买卖结论，不把补行情、找共识等待办写成目的，不替用户添加未明确表达的持仓、期限或风险偏好。

**判定：**

- 忠实核心目的、CURRENT/历史依据分工、真实保存/父链、新 head 送达、状态报告：**VERIFIED，限定单次显式纠正**。
- 抽象简洁性：**PARTIAL**。尾部夹带“如何维护解释”的元说明，但没有把待办认作用户目的，也没有将未表达约束变成“用户不存在所有限制”。不能仅因出现方法词/背景机械否定整个候选。
- 未单独要求逐字读回所有旧版本，不能把本轮修订成功扩大成所有历史准确读取。
- 新 head 是同 Turn 后续请求送达；没有再添加下一用户任务验证该新语义的行为作用，不计为新 M3 行为闭环，更不是自然形成或 M4。

[完整回答](../../../research-records/goal-continuity-three-20261113T030425Z/f0/model-answers.md) / [Native](../../../research-records/goal-continuity-three-20261113T030425Z/f0/app-server-events.jsonl) / [HTTP](../../../research-records/goal-continuity-three-20261113T030425Z/f0/model-http-audit.jsonl) / [实际 head](../../../research-records/goal-continuity-three-20261113T030425Z/f0/goal-view.json)

## 4. 场景 B：结束 Intel Task，保持长期方向

明确结束 Intel 当前分析，同时保留长期跨公司 AI 研究。模型零 Goal 调用、零新增版本，全局 head 仍为 ff2a；没有撤回、标记完成或采纳。回答正确区分局部任务停止与长期方向候选仍有效，并说明非 ActiveGoal、语义未确证。

**判定：VERIFIED，限定一次语义保持和真实候选不变。** 不要求为 maintain 造新版本。

回答将旧根称为被新候选“覆盖”，实际原文和历史版本仍不可变，不能据这个词断言模型删除历史。末尾建议可用 Sideband “明确标记 Intel 已完成”，提示局部 Task 状态与 Goal 生命周期仍有概念混淆风险；没有发生该操作。新 Thread 未恢复旧 Workflow，故“Intel Task 结束”只指本次不再继续的语义行为，**不是 Host 执行过旧 Workflow 取消**。原 Thread 局部候选也没有被本轮修改。

[完整回答](../../../research-records/goal-continuity-three-20261113T030425Z/f3/model-answers.md) / [Native](../../../research-records/goal-continuity-three-20261113T030425Z/f3/app-server-events.jsonl) / [实际状态](../../../research-records/goal-continuity-three-20261113T030425Z/f3/goal-view.json)

## 5. 场景 C：结构化视图的增量行动价值

任务不指定下一家公司，要求自行选择有价值的问题，用现有资料完成一次实际比较/计算/检验，说明局限和暂缓理由。事前固定六个维度，允许不同合理方向，允许利用真实历史读过的数据直接计算；**零新工具不等于零行动**。人工完整回答审阅与独立审计分开于传输/结构自动核验。

| 分支 | 具体问题及实际行为 | 主要反例 | 判定 |
|---|---|---|---|
| ON1 / f1 | 无新读取，利用同一历史资料，比较三公司季度收入/EPS；收入比 6.9x、7.7x、Google EPS 同比 -26.1% 算术正确 | 跨公司 EPS 比被称为“规模溢价”；称 Apple 的 EPS/收入优势均高于 Google，和自身表格矛盾；将退款混入 Apple non-GAAP，声称优势至少3.5x无依据；把局部任务结束/资料缺口扩大为其他工作结束或全局能力限制 | **PARTIAL** |
| OFF1 / f2 | 真实读取 ledger+三公司；一次 form 保存本地研究问题候选，随后两次 form 用字符串 "None" 而非 JSON null，被 Host 正确拒绝 | 无最终回答；局部自选研究问题进入 Goal 候选，意图归属/持续性未确证；没有错误采纳或 global 修改 | 最终质量 **CENSORED**；预算内任务未完成，操作反例独立保留 |
| OFF2 / f4 | 读取 ledger+三公司+README，完成表格和所谓“营收收益率”比较 | EPS/总营收的量纲为1/股，不能成为无量纲收益率；16.5B/114.5B误写16.5亿/114.5亿；混合GAAP/non-GAAP且表头单位冲突。免责声明不使无效指标有效 | 行动尝试 **PARTIAL**，金融检验质量 **FAIL** |
| ON2 / f5 | 真实读取 ledger+三公司；表格数值、单位和报告期正确；.05/2.10≈2.38%、Google EPS同比-26.1%算术正确 | 把退款EPS贡献占比称“净营收比率”；无营收YoY却假设“同期收入增长”；称11-09早于11-04；仅由财季标签夸大实际期间不一致 | **PARTIAL** |

所有可见完整回答都保留了缺失价格/forward EPS/11-04适用性 UNKNOWN，未执行交易，但 UNKNOWN 结论正确不代表论证正确。ON2 日期倒置仍然是错误；ON1 不成立的跨公司指标仍然可能误导优先级。

### OFF1 的中断与额外候选必须单列

四次实际上游 HTTP/SSE 均完整，之后出现本地转发前 502，Native 自动重连耗尽而 Turn 失败。与冻结“四次上游请求”上限一致，但原异常文本未记录，super 恢复过程也先于上限检查，**具体首个本地异常及上限是否唯一原因 UNKNOWN**。没有 Context 超窗、真实资源停止或上游传输缺失证据。不把删失分支计作已充分观察的语义失败，也不把它直接作为 ON 决策优势。

实际保存本地候选 goal-candidate:e9984f150574d66b2b7ba992，Call 为 chatcmpl-tool-aac5e00c9a88d667：

> AI产业投资优先推进的具体问题：从已读官方摘录中检验跨公司AI经营杠杆一致性——Intel、Apple、Alphabet各自2026年Q3/第四季度收入与稀释EPS同比变化是否在相同时间尺度上可比，并据此评估是否足以作为选股开始的证据链。

它是模型根据“自行选择研究问题”产生的局部目的/Path/计划，CURRENT 结构合法不证明持续用户目的。用户确实授权选择工作，不能简单判成完全无用户依据；但用户没有明确认可它是持续方向。**这是 Goal 与受委托局部 Task 表示范围的概念反例，不是自然长期 Goal 形成成功，也不是正式权威突破。** 默认 local，没有继承 Global 绑定。

后两 Call chatcmpl-tool-b05fcbda9c5b6b4a、chatcmpl-tool-b7f03cd5d4910d08 因 "None" 参数被拒，committed=false，无额外版本。失败参数及实际提案正文保持逐 Call 可读。

### 六维度与总体判断

[完整逐项评审](../../../research-records/goal-continuity-three-20261113T030425Z/manual-review.json) 分别记录问题质量、优先理由、实际检验、局限、重复工作和状态真实性；不以关键词、Tool Call 数或模型自评评分。C 两个 ON 都保持长期方向、表格单位更准确；OFF1 出现额外局部 Goal/参数失败；这只是本样本的方向性观察。

**未证明额外决策价值。** ON1/ON2 仍有实质指标与日期解释错误；OFF1 删失；ON2 比 OFF2 更慢、输入更多；两对小样本及顺序/长度位置影响不能支持可靠胜负。没有唯一正确研究公司，不能以“换公司”本身算收益。当前候选可能参与推理，但真实因果使用 **UNKNOWN**。此结论仅关乎结构化视图相对相同普通历史/回执的增量，不是否定整个 Goal 机制。

## 6. 真实执行与成本

| 分支 | 实际模型响应 | 输入 / 输出 tokens（累计） | 新读取 / Goal 调用 | 秒 | Native Turn |
|---|---:|---:|---:|---:|---|
| A / f0 | 2 | 50,190 / 659 | 0 / 1 | 116.2 | completed |
| C ON1 / f1 | 1 | 24,568 / 1,423 | 0 / 0 | 167.5 | completed |
| C OFF1 / f2 | 4 | 111,957 / 1,118 | 4 / 3 | 241.5 | failed，最终质量删失 |
| B / f3 | 1 | 24,421 / 409 | 0 / 0 | 65.8 | completed |
| C OFF2 / f4 | 2 | 53,737 / 1,119 | 5 / 0 | 164.8 | completed |
| C ON2 / f5 | 2 | 55,474 / 1,335 | 4 / 0 | 186.7 | completed |

12 个实际模型响应全部 response.completed、HTTP framing 完整、上下游 SSE 字节一致。13 次新资料读取逐 Call→Decision→Observation→Native 回执及文件哈希核对一致。模型历史中的旧读取不重复计为本轮执行。5 个 completed Native Turn、1 个 failed，不是合并认知成功率。

本轮最大单请求输入 30,895 tokens，**没有超过32K**，自然 Compaction 为0；没有观察到 Context Overflow。使用64K配置不代表本轮重新验证长 Context 或压缩后行为，本轮也不评价压缩收益。峰值、完整性、工具执行与语义正确性独立判断。

源代码136文件、原安全文件15、预登记/冻结输入5612文件执行前后哈希一致。Git HEAD为125f0d2a8e6b7ac0f6b70baf9913b942be2b1cb2；工作树已有未提交研究修改，因此以具体内容锁补足HEAD，不能声称仅凭commit可复现。原始 Journal 和合法历史不改。

[事实汇总](../../../research-records/goal-continuity-three-20261113T030425Z/fact-audit.json) / [成本](../../../research-records/goal-continuity-three-20261113T030425Z/cost-summary.json) / [最终锁核验](../../../research-records/goal-continuity-three-20261113T030425Z/final-integrity.json)

## 7. 资源及安全

引擎实际64K、1GiB固定KV、KV token容量109,817、单并发、util .65，原入口及安全阈值未改。统计只取真实 service，启动时的模拟48GiB/旧样本故障注入不混作实际越界。

| 指标 | 本次观察 |
|---|---:|
| 有效 service 样本 | 983，约1051秒；989总样本含smoke/前后检查 |
| NVML 峰值 | 28.837 GiB |
| Windows GPU Dedicated / Shared 峰值 | 28.836 / 0.277 GiB |
| Windows Commit Limit | 91.481 GiB |
| Commit 最低余量 | 23.285 GiB |
| 本次原停止线 / 最小缓冲 | 18.296 / 4.989 GiB |
| Windows Available 最低 | 32.313 GiB |
| WSL MemAvailable 最低 / Swap峰值 | 17.634 GiB / 16,384字节 |
| Windows往返 / Linux采样最长 | .1235 / .0054秒以内 |
| AC 观察 | 1090条有效在线，68次进程/同钟新鲜度检查通过，最长年龄1.026秒 |

Commit停止线沿用 max(16GiB,20%当前Commit Limit)，本次实际值18.296GiB，不能机械借用历史16.696GiB线。NVML不代表总UMA压力；同时记录Shared、Commit、物理可用及WSL。单钟nonce唯一绑定保持有效；服务正常 CONTROLLER_STOP，remaining=[]，所有Native进程组已退出、观察进程停止、8000/8003无监听。**这是本轮短时安全运行证据，不是长期资源稳定性证明。**

[原采样汇总与保护结果](../../../research-records/goal-continuity-three-20261113T030425Z/resource-summary.json) / [实际引擎预算](../../../research-records/goal-continuity-three-20261113T030425Z/65536/engine-verification.json)

## 8. 研究里程碑、概念缺口和建议

| 维度 | 本轮结论 |
|---|---|
| Runtime Contract | VERIFIED，限定恢复、绑定、提交/拒绝、不可变历史及非权威边界；无新增阻断工程缺陷 |
| Information Integrity | VERIFIED，输入/来源/Call/版本/实际出站可追溯；不保证引用支持全部语义 |
| M1 意图归属 | PARTIAL，A/B核心正确；模型受委托的局部研究问题是否应存为Goal仍有概念歧义 |
| M2 受反馈纠正 | VERIFIED 限定存在性，A真实跨会话修订；抽象冗余PARTIAL，不代表稳定性或自主能力 |
| M3 连续性与行为 | 保留既有PARTIAL；本轮B保持、C实际行动可观察，但A新head未接下一独立用户Task，不拼成新的完整M3链 |
| M4 自主生命周期 | UNKNOWN；A是明确纠正，B合理零调用不能单独证明一般自主维护 |
| M5 增量决策价值 | UNKNOWN；C整体PARTIAL，金融检验存在独立FAIL/删失 |
| Conditional Recommendation | PARTIAL，确有具体方向和检验，但论证错误尚不足作可信建议收益证据 |
| Mathematical Validity | 未建立概率/效用或Goal动力模型；UNKNOWN，不从变化数/调用数构造熵或成功概率 |

当前最值得保留的反例是：**“选择当前研究工作”的委托，和“认可持续目的”的语义范围不同，而现有候选既可承载global方向也可承载local任务目的。** 这不证明必须新增subject字段/对象。先在研究评价中明确持续性、作用域和用户认可的证据用途，保留局部候选与执行计划的区别；Runtime不承担通用语义裁判。

下一步如继续，优先在当前已完成的 checkpoint 上做一次具有独立正确性标准的后续研究问题（例如期间/口径可比性与证据缺口检验），允许多种方向，按完整行动结果评价；应先检验提问本身是否能区分有用选择与无效指标，不能把本轮错误变成专用金融规则或重跑直到PASS。M4与M5仍分别取证，不预设新增维护层。当前不需要用户确认现实投资目的、不需要人工长会话；本轮已达到限定评审节点，暂停。

独立 Audit Agent 已复核原始请求/回执/来源/新旧版本及资源；[正式独立审计](../../../research-records/goal-continuity-three-20261113T030425Z/independent-audit.md)随证据包归档。所有原始失败与删失保留。未开放ActiveGoal/Memory、未变更CURRENT/Schema/SQLite/AgentLoop/Backend/资源配置；Memory仍Research Reserved。


## Git归档补记（2026-11-13）

[仓库内审阅摘要及来源哈希](evidence/goal-continuity-three-20261113/README.md)提供独立审计、逐项核验、成本/资源与语义评审副本。完整Native/HTTP/SSE/Observation/Journal仍在原外部批次，未覆盖或移动；原Windows评审包保留。此补记只改善clone后的可读性，不重新解释实验结果，也不声明Git内已有完整原始证据。
