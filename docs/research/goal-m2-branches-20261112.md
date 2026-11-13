# Goal 恢复绑定修复与 M2 独立分支评审（2026-11-12）

总体 **PARTIAL**。恢复工程限定 PASS；M2-A 全文读回 PASS、归属解释 PARTIAL；M2-B 一次明确纠正 FAIL；M3 NOT RUN，M4/M5 UNKNOWN。没有新的正式架构变更依据。

本轮先登记上一批 goal-history-recovery-20261112T061038Z 的限定结论与缺口，再修复及开展新批次 goal-m2-branches-20261112T073526Z。上一批 Native 行385的错误保存状态声明仍保留为负面证据，不被本轮读回成功覆盖。

## 1. 项目节点与两份独立报告

- [M2-A：已保存候选读回](goal-m2-readback-20261112.md)：两个原文与 head准确，表达来源/意图归属仍有偏差。
- [M2-B：明确纠正后的修订](goal-m2-correction-20261112.md)：6次真实 revise 均因当前quote规则拒绝，模型虚称保存成功；不运行M3。
- [上一恢复实验](goal-history-recovery-correction-20261112.md)、[研究地图](research-foundation-map.md)、[阶段索引](README.md)、[当前导航](../current/README.md)。

真实历史恢复 ≠ 自然形成；本轮没有辅助生成新种子；CPU可表达性对照 ≠ 模型修订成功。各结论不合并为总体成功率。

## 2. 确定性缺陷、最小修复与重建

**VERIFIED**：旧恢复器只确认Step的Observation/Call分别存在及集合相同，交换两个Observation ID仍可能通过。旧版复现见 [old-binding-gap.json](../../../research-records/goal-m2-branches-20261112T073526Z/old-binding-gap.json)。修复仅在 [recover_goal_history.py](../../scripts/research/recover_goal_history.py)，未改正式Runtime或数据库：

1. 从原执行轨迹建立Observation → Call/Turn/Thread/Workflow/Input/Decision映射。
2. Observation与原Native调用、回执身份、执行决定及原用户输入Turn逐项绑定。
3. 每条Step同时核对其Call、Turn、Thread、Workflow/Input与完整执行决定。
4. 保留原Call幂等与禁止外部历史工具重执行机制；新映射仅是研究bundle审计信息。

[test_goal_recovery.py](../../benchmark/longitudinal_dialogue/test_goal_recovery.py) 在临时目录运行7个测试方法：合法绑定通过；新增8个错配反例拒绝（交换Observation、换Call、Step Turn/Thread、Observation Turn/Thread/Workflow、Input归属），并保留此前18个负例。未修改原Journal、Native事件或快照。结果见 [stageA-tests.json](../../../research-records/goal-m2-branches-20261112T073526Z/stageA-tests.json)。

独立临时重建后，除新增observation_bindings审计映射外，与上一恢复bundle完全相同；两条head及投影与原成功请求sequence4逐项一致。原历史2版本、1输入、4Observation、2已处理Goal Call及其身份均恢复。无模型Native同Thread恢复：0模型请求、0外部执行；见 [cpu-native-resume-r2/proof.json](../../../research-records/goal-m2-branches-20261112T073526Z/cpu-native-resume-r2/proof.json)。

**范围限制**：只恢复可证明的Goal/Input/记录到的Workflow-Step闭包；没有恢复不透明模型输出对象、旧ProjectionRecord缓存与未导出的planner缓存。禁止据此宣称通用Runtime完整恢复能力。

## 3. 冻结与对照边界

基线代码HEAD=125f0d2a8e6b7ac0f6b70baf9913b942be2b1cb2；工作树原有修改另外保留，执行使用冻结副本及132项来源哈希。180项运行输入锁、131项既有执行源锁及15项原始安全/模型固定项末检均无变化；见 [git-before.json](../../../research-records/goal-m2-branches-20261112T073526Z/git-before.json)、[input-lock.json](../../../research-records/goal-m2-branches-20261112T073526Z/input-lock.json)、[frozen/source-lock.json](../../../research-records/goal-m2-branches-20261112T073526Z/frozen/source-lock.json)、[final-audit.json](../../../research-records/goal-m2-branches-20261112T073526Z/final-audit.json)。

A/B恢复bundle完全相同、独立Nativehome/Journal/新Turn；共享只读模型服务顺序执行。首个请求不含另一分支新提示/A回答。初始Goal heads相同；input_index因本分支当前输入必然不同，不能要求整个投影逐字相同。

它们回答不同研究问题，**不是Relevant History与Goal Shadow的决策对照**。本轮不跑已暂缓的30×2，也不把A更低Token成本解释为更好决策。

## 4. 执行、成本与资源

配置保持GPU56/Host72、64K、KV1GiB、单并发、util0.65、Bolt/vLLM0.32/Codex0.163。引擎报告1GiB KV容量109,817 Tokens（max_model_len仍为65,536），36GiB预算见 [65536/kv-gate.json](../../../research-records/goal-m2-branches-20261112T073526Z/65536/kv-gate.json)、[65536/engine-verification.json](../../../research-records/goal-m2-branches-20261112T073526Z/65536/engine-verification.json)；未改变32K正式默认、64K入口、UMA或阈值。

| 指标 | A | B |
| --- | ---: | ---: |
| 新用户轮次 | 1 | 1（预登记第2轮因M2未过门未运行） |
| 完整模型请求 | 1 | 4 |
| input累计 / 最大单请求 | 20,700 / 20,700 | 84,011 / 21,642 |
| output累计 | 1,211 | 1,654 |
| Turn耗时 | 124.24秒 | 223.81秒 |
| Goal调用/接受/新版本 | 0/0/0 | 6/0/0 |
| 新外部Observation | 0 | 0 |
| Compaction / 硬超窗 | 0/0 | 0/0 |

总5请求均HTTP framing完整、response.completed、上下游字节一致，无采集预算溢出。不能将HTTP 200或请求开始视作完成，也不能将原历史4次读取再计为本轮读取。两条head全文实际进入全部5个成功请求，非仅本地投影准备。

资源491样本均有效；AC563样本均在线。NVML峰值28.410GiB、PDH Dedicated峰值28.407GiB、Shared峰值0.137GiB；Windows Commit Limit91.481GiB，最低余量26.399GiB、距原动态停止线缓冲8.102GiB；Windows Available最低33.722GiB，WSL最低17.625GiB，Swap峰值0.0117MiB。单时钟新鲜度上界最大0.276秒，采集最大0.129秒。仅为短测试安全证据，不外推长期稳定。详见 [resource-series.csv](../../../research-records/goal-m2-branches-20261112T073526Z/resource-series.csv)、[final-audit.json](../../../research-records/goal-m2-branches-20261112T073526Z/final-audit.json)。

测试后主动CONTROLLER_STOP，服务、采样器、AC observer及两Native进程均清理，8000/8003端口清空。monitor记录中的通用“Safety stop”文本对应CONTROLLER_STOP，primary_sensor_failure=null；不是本轮保护故障。

## 5. 里程碑和下一步

| 里程碑 | 当前判断 |
| --- | --- |
| 历史恢复 | **VERIFIED，限定PASS**；本次补齐选定轨迹的Step–Observation身份绑定。 |
| M1用户意图归属 | **PARTIAL**：能够区分部分目的/任务，仍混淆存储位置、表达来源及资料需求。 |
| M2-A准确读回 | **VERIFIED / PASS本单样本**，不能证明所有情况下都读准。 |
| M2-B受反馈纠正 | **FAIL本单样本**：合理草案与真实提案已出现，但未提交且虚称保存。 |
| M3跨轮更新后使用 | **NOT RUN / UNKNOWN能力**：没有新head，不制造后续闭环。 |
| M4自主生命周期 | **UNKNOWN**；明确反馈下调用不能替代自主维护。 |
| M5实际决策增益 | **UNKNOWN**；本轮无匹配Relevant History决策实验。 |

**HYPOTHESIS**：模型将历史purpose支持和当前变更触发混淆，并把拟提交内容当作已保存内容；具体内部原因不可见。本例不能证明模型一直读不准，也不能证明接口不可表达——临时CPU对照已有合法修订路径。

建议的下一个最小问题：在相同冻结候选下，模型能否区分“当前纠正触发引用”和“历史目的支持”，并在committed=false后如实保留旧head。应预登记有界接口理解/失败反馈对照，不扩大Goal状态、存储、语义裁判或自动补发；一次成功仍不代表M4/M5。若无法解决，应保留模型行为限制，而不是重复同脚本到PASS。先交本轮评审，再决定是否继续该窄问题。

**UNKNOWN**：换模型或改接口说明的收益、语义判断的稳定性、后续真实行为和长期决策价值。没有证据要求新Goal Engine/subject字段/数据库Schema/权限变更；Memory维持Research Reserved。本轮未Commit/Push，未覆盖原失败，未改变人工入口或正式Runtime。

原始证据定位总表：[evidence-index.json](../../../research-records/goal-m2-branches-20261112T073526Z/evidence-index.json)；完整结构审计：[branch-evidence.json](../../../research-records/goal-m2-branches-20261112T073526Z/branch-evidence.json)、[final-audit.json](../../../research-records/goal-m2-branches-20261112T073526Z/final-audit.json)。停止于本轮独立M2证据节点，不安排人工长会话。

## 2026-11-12 追加勘误：拒绝回执实际供给边界

原报告“拒绝回执实际进入后续成功请求”的说法不够精确。Native确有ok=false、committed=false的Host回执；但模型后续出站接收的是provider_history转换后的terminal_attempt_fact，保留error、execution_succeeded=false、result_available=false，**没有committed、ok和Goal head变化字段**。因此原失败只证明该转换反馈条件下的误报，不能证明完整Goal回执条件下仍误报。原始失败及已保存状态不变的结论保留。新批次见 goal-m2-current-feedback 后续节点，Schema CURRENT规则不放宽。
