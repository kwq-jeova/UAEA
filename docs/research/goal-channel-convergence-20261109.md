# Goal 研究通道收敛：首条真实候选生命周期

日期：2026-11-09。**总体 PARTIAL；限定状态/供给契约 PASS；真实显式接口 PASS；自然形成与决策收益 UNKNOWN。**
源记录：/home/wqkan_wsl/uaea-n1x/research-records/goal-channel-convergence-20261109T121142Z/
延续：[上一轮零候选结果](goal-hypothesis-mechanism-20261109.md)，不覆盖、不混入旧批次。
本轮未 Commit/Push，未改变正式 Goal/Memory 采纳、Provider Policy、Phase-1、Harness 所有权或模型依赖。

## 1. 阶段 A：修复与反例

仅修改隔离研究通道，既有 Runner 和正式人工入口不变。

| 问题 | 复现 | 最小修正 | 限定验证 |
| --- | --- | --- | --- |
| 调用 ID/哈希正确，保存内容却不同 | 改存储 hypothesis、operation、parent、input/evidence 等值；旧审计可仍判 PASS | 保存原始 submitted_proposal；核对实际调用各字段、规范化继承文本、来源版本、父版本、owner 与完整 record hash | 旧误 PASS → 新 FAIL |
| 同 ID 后续投影的文本不同 | 保存正确，但给模型的 head 改写；旧审计只查 ID | 投影完整候选文本及 record hash；不再静默截为300字符；审计逐字段核验，区分缺席、错配及实际供给 | 旧误 PASS → 新 FAIL |
| 已提交后发布失败，被再次记为拒绝 | 原处理器先保存1个候选，再抛 ValueError：VERSION 与 REJECTED 同时出现，回执 success=false | 提交与发布分离；VERSION 是提交记录，PUBLICATION 是尝试结果；成功 Host 发布也不宣称模型已收到 | 保留1个版本，不写 REJECTED |
| 相同 Call ID 重试 | 保存后首次发布失败，再用原 payload 重试 | 返回同一 candidate/record hash，重试物化和发布；不同 payload 拒绝身份冲突 | 1个 VERSION、2次 PUBLICATION、无重复候选 |

快照使用临时文件后原子替换，是 Journal 的物化视图。
普通磁盘保存错误不改写已提交事实；同一 Call 重试可重新物化。
没有宣称电源故障 ACID、跨进程幂等重建或跨 Run 恢复。

评价器分别检查：
1. 原生 arguments → 已提交 record；
2. record → 实际落盘版本与 head；
3. record → 后续出站请求的完整内容、hash与时间顺序。
Host publication succeeded 不等于模型收到；缺失时序、未进入后续请求均不能假阳性 PASS。
快照缺少新版本为 PARTIAL；同身份内容错配为 FAIL。无候选仍为 UNKNOWN。

**最终115项 CPU 回归 PASS，0 FAIL**（final-tests.log）。
GPU 前113项已通过；其后仅进一步收紧离线审计的时间/快照检查及相关反例，运行中的源码 bundle 未改变。
旧源复现结果见 stage-a-counterexamples.json；测试中“正确quote＋错误解释”仍保留 semantic_correctness=not_established，
不以来源校验冒充语义真值。

修改范围：
- scripts/research/goal_hypothesis.py：原始参数、不可变版本绑定、精确投影、物化状态。
- scripts/research/goal_sideband.py：提交/发布/回执分离。
- scripts/research/goal_hypothesis_audit.py：字段、实际供给、时间与快照审计。
- benchmark/longitudinal_dialogue/test_goal_channel_consistency.py：反例回归。
- README-goal-hypothesis.md、研究记录及地图。
未改任何核心 Harness/Phase-1/Memory 源码；此前脏工作树保留。

## 2. 阶段 B：预登记的短真实对照

复用既有 Scenario Runner 和单个受保护 Bolt 服务：
32K、1GiB KV、36GiB引擎规划、单并发、Eager、64/64 UMA，资源阈值与 Fail-Closed 不变。
实际包元数据：Python3.12.3、Torch2.13.0、vLLM0.32.0、Triton3.7.1、FlashInfer0.7.0.post1、B12X1.5.1。
模型 Revision 下载元数据 cf2effc5c4b794ee9fb8d34eab3d1d65ce64142f；未执行全权重hash。

两场景分别三轮 × Relevant History / Shadow，共4会话、12真实用户轮，全部完成。
金融先行；仅在真实候选出现后，按预登记条件运行短非金融复核。
四会话各1次真实文件 Capability Observation，共4次；语义调用另计，不混成外部证据。
无实时行情、真实证券交易或真实用户投资决策。冻结来源为既有研究者摘录，不是历史时点原始行情快照。

| 场景 | 第一轮 | 第二轮 | 第三轮 |
| --- | --- | --- | --- |
| 金融 | 读取冻结财报、比较意图；不要求Goal调用 | 明确请求可用工具记录非权威目的 | 明确取消比较，改审计；请求撤回/修订 |
| 非金融 | 文档研究助手、来源与自我纠正；不要求Goal调用 | 无GPU/外网，目的不取消；显式请求记录 | 澄清不自动采纳、不产品化；合适可保持，不强制新版本 |

脚本相同、文件版本和正文预算相同；仅 Shadow 有候选工具/视图。
Relevant History 在无该工具时按同一脚本用文字回答，不被要求调用不存在的接口。
每轮自由生成，无 forced tool_choice、无每轮候选配额、无第二个模型或第二套执行循环。
两个完整金融/非金融会话的读取正文与出站 hash 校验均 PASS。无 Compaction，本轮不声明压缩后候选恢复。

每个实时 bundle 冻结127文件，执行期间哈希全匹配。
最终离线审计器进一步收紧，另行保存版本hash；它未参与运行中的 Agent Loop。
HEAD 与脏工作树快照、模型配置/启动器/Codex二进制hash均有锁定，不能只靠 Git HEAD 复现。

## 3. 首条真实轨迹：金融 form → withdraw

### 显式形成

原生 Call：chatcmpl-tool-ab6447c426c5ce88
Turn：01a1c045-6ece-74a0-9eb1-e8ebcae56162
保存版本：goal-candidate:a25b38a97363fcc1b6ff53a0

操作 form，candidate_id=null。quote 关联本轮真实输入，历史 input_id 及原文hash可核查。
Journal、实际快照和随后 request sequence 4、5 的投影内容一致。

但其假设包含：
> 不做买入排名，不提供真实价格或外部证据。

这是语义偏差：原文说“当前没有决定买入排名”，以及“记录目的无需先取得真实价格/外部证据”，
不应把暂时状态外推为永久限制；其中“不提供外部证据”尤其缺乏原文支持。
**结构合法、来源正确，不能证明解释正确。** Host 未替模型修正该语义，也未将其采纳为正式 Goal。

### 用户明确取消后的撤回

原生 Call：chatcmpl-tool-90bac9bc8d259632
Turn：01a1c046-da1c-7703-a907-bc9f8adc0f02
追加版本：goal-candidate:ceaa59a8c12b6a72007d8ebb
父版本：goal-candidate:a25b38a97363fcc1b6ff53a0
操作 withdraw，状态 withdrawn；request sequence 6 确认实际供给。

旧版本保持原样，撤回作为新版本；当前 head 是撤回版本。
模型正确区分明确取消与缺少价格资料，正式 ActiveGoal 始终为空。
这是**显式请求驱动的候选生命周期证据**，不是自然长期 Goal Formation 或正式 Goal Evolution。

## 4. 非金融：真实拒绝、模型自行纠正、随后保持

第一轮模型只在文字中建议使用 maintain“保留并细化”，但没有候选、没有该调用；
不能据其文字宣称已维持或细化状态。这也是仍有接口概念混淆的负面结果。

第二轮：
- 第一次 Call chatcmpl-tool-9f80c5a6ff2e2fb3 缺少必填 candidate_id，真实拒绝，未保存候选。
- 模型收到错误后，在同一轮自行提交新 Call chatcmpl-tool-a41471f00ed3ebaa，补上 candidate_id=null。
- 保存为 goal-candidate:215cc78837321382566258e7；随后 request sequence 5、6 的实际输入匹配。
- Host 没有代填参数、改变权限、自动补发工具或添加用户“继续”。

候选仍包含“离线回放条件下”“基于ledger继续探索”等路径/条件描述，不能当作已抽象出通用长期目的的证明。
第三轮模型判断假设可保持，没有新 Goal Tool Call，也没有新版本。**文字保持与真实 maintain 操作分开记录。**
对用户澄清的响应可观察，但不宣称完成了真实 refine/revise 实验。

总计4个真实语义调用：3个版本提交（两根候选＋一次撤回）、1次拒绝。
三份已提交版本都完成了：原生参数绑定 → 落盘 → 后续出站内容核验。
拒绝不构成 Capability Observation，模型解释不构成外部来源。

## 5. 公平对照与实际收益

| 指标 | 金融 Relevant History | 金融 Shadow | 非金融 Relevant History | 非金融 Shadow |
| --- | ---: | ---: | ---: | ---: |
| 完成轮次 | 3 | 3 | 3 | 3 |
| 累计输入 Tokens | 46,629 | 83,040 | 42,698 | 76,137 |
| 累计输出 Tokens | 1,944 | 1,930 | 839 | 1,443 |
| 真实文件 Observation | 1 | 1 | 1 | 1 |
| 已保存版本 | 0 | 2 | 0 | 1 |
| 被拒语义调用 | 0 | 0 | 0 | 1 |

Shadow累计输入159,177，Relevant History为89,327，约增加78.2%。
增加包括候选投影、工具回执和额外模型续答；不是单次Context溢出。
实际Harness报告有效窗口31,129，服务保持32,768配置，本轮无Compaction。

Relevant History也能用文字说明用户目的、接受取消、区分资源条件和目标。
Shadow提供了额外**可核验的版本/撤回记录**，但未证明更好的下一步决策：
- 金融两臂仍有单位错误，Shadow候选还增加了未经原文支持的约束。
- 非金融两臂建议仍较笼统；Shadow未证明下一步更有价值。
- 本轮未执行后续真实决策，也没有独立用户结果评价。

每组仅一对、基线先行，未随机化/重复估计；显式接口邀请是人为干预。
不能把额外工具交互的成本直接泛化为所有Goal研究成本，也不能将脚本成功称作长期收益。

## 6. 资源与清理

单次真实加载服务：
/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261109T121712Z-0d28a0b3

实际服务采样（排除模拟保护烟测）：
- NVML GPU峰值29.09GiB；Windows Dedicated峰值29.10GiB、Shared峰值0.23GiB。
- Windows Commit峰值69.57GiB，最小余量44.91GiB；Windows物理可用最低23.29GiB。
- WSL可用最低17.18GiB，Swap采样峰值仅约12KiB。
这些是采样极值、不同口径不可相加，不是硬分配上限或瞬时峰值保证。

原有48GiB/监控失效模拟烟测均按预期终止；不是实机曾达到48GiB。
真实服务无资源阈值触发。完成研究后 CONTROLLER_STOP，
退出码-15、remaining=[]；监控进程SIGTERM清理，remaining=[]。
外层启动器控制停止返回1不代表模型/Kernel失败，详细回执保留。
没有自动重启、重复加载或影响不属于本次的服务。

## 7. 结论、边界及架构评审

| 维度 | 判定 | 依据 |
| --- | --- | --- |
| 两项状态一致性修复 | PASS（限定） | 115项CPU控制、前后反例、真实提交/投影逐值对应 |
| 真实工具接口 | PASS（限定） | 两场景均得到有效 form；非金融缺参后真实纠正 |
| 显式生命周期 | PASS（限定） | 金融 form→withdraw，版本追加、父引用及供给完整 |
| 候选语义质量 | PARTIAL | 目的核心可辨，但金融多出约束，非金融仍混入路径 |
| 自发/自然形成 | UNKNOWN | 无未受显式邀请的根候选；仅两个Shadow第一轮，不足以判普遍FAIL |
| refine/revise、多候选竞争、跨Run | UNKNOWN | 本轮未实际覆盖 |
| 长期决策价值 | UNKNOWN | 基线也能响应修订，Shadow新增成本，缺少真实后续结果 |

**已确认当前Bolt、Parser和Harness并非绝对不能调用此接口。**
本批是明确请求后的正面证据，不能反推此前零候选内部原因已被证明。
可选工具触发/语义前提混淆仍是研究假设，不能用模型的解释当作因果证明。

目前足以保留一个 opt-in 的**显式、非权威、可撤销候选研究基线**，
不足以切默认、自动采纳、建设长期维护层或声称自然认知机制已形成。
建议评审这条真实轨迹及语义偏差后，再决定是否做一组“纠正已生成错误解释”的限定验证；
不增加通用语义裁判、模型专属Prompt分支或第二套Loop。

已到用户指定的首个真实生命周期评审节点，停止新增实验；无需人工长会话。
正式采纳、Memory Admission、执行授权与资源保护保持不变。

## 复核与回退

- preregistration.json、dataset：实验前固定的条件、原文与条件分支。
- stage-a-counterexamples.json、final-tests.log：旧误通过与修复后负例。
- finance-audit.json / engineering-audit.json：完整逐轮离线审计。
- evidence-summary.json、source-index.json：实际调用、行号、请求序号、版本hash与资源。
- before：本轮前源码；source-lock.json：实际运行bundle；最终审计器hash另列。
- 回退：不使用 --goal-channel sideband；默认legacy仍保留。局部撤销本轮研究文件应对照before，
  不得reset/clean覆盖其他既有工作。正式人工入口、Goal/Memory权限无需变更。
