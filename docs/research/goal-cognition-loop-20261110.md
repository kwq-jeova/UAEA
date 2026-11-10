# Goal Hypothesis认知闭环：措辞混淆核查与受保护中断

日期：2026-11-10（Asia/Shanghai）。
**总体PARTIAL；新增真实闭环BLOCKED。没有新增认知成功或模型失败结论。**

原始研究目录：/home/wqkan_wsl/uaea-n1x/research-records/goal-loop-20261109T234248Z/
本轮仅研究Goal。Memory数学建模标记为Research Reserved，保留历史与Relevant History基线。
既有研究：[上一轮真实断点](goal-candidate-continuity-20261109.md)、
[显式形成/撤回](goal-channel-convergence-20261109.md)、
[作用域及真实供给审计](goal-scope-transfer-audit-20261109.md)。
未Commit/Push，未修改正式Runtime、Harness循环、Goal通道、模型依赖或安全保护。

## 1. 原失败的直接证据与因果限界

复核的是20261109_215858评审包对应原件，而非模型最终文字倒推执行：

- 首轮原文确含“请仅在现在保留一个……假设”；第二轮含“不需要为轮次新增记录”。
  模型后续将后者表达为“不新增轮次记录”。该差异可能影响工具适用范围理解。
- 原生唯一Goal调用chatcmpl-tool-8eaf6a3669b37e94，形成
  goal-candidate:984d008cbb262d0031e1dfa6。后四轮没有Goal调用、拒绝或提交。
- 最后出站request sequence 6仍有goal_hypothesis工具、真实当前用户原文、
  旧candidate的完整内容与hash。Journal/物化快照/出站head对应。
- 模型最后文字称“先前的可撤销假设撤销，新方向作为非权威候选保留”，但没有相应操作。
  Host保存的候选未变，正式ActiveGoal没有因此改变。
- 原件无第六轮，不能声称旧候选后来已被模型再次采用。

具体原件行号、请求ID、forwarded hash和原始语句：
original-case-review.json；原件目录仍保持不变。

| 可能机制 | 本轮结论 |
| --- | --- |
| 模型在文字中响应方向变化，但未提交更新 | VERIFIED：可直接观察；不能推断主观上“选择不更新”的原因 |
| “仅在现在”等话语被理解为后续不能调用 | HYPOTHESIS：有措辞依据，未建立因果 |
| 模型把普通回答当成已提交的Host状态 | VERIFIED的是错误状态声明；内部认知机制UNKNOWN |
| 实际已更新，但投影/回传丢失 | 未发现支持证据：原生提案不存在；不能把缺少提案归成发布失败 |
| 自主维护能力普遍失败 | UNKNOWN：原结论必须限定到这份脚本，不能排除指令范围混淆 |

因此保留旧失败，但不将其升级为“模型必然不会维护Goal”的证明。
最小修正选在研究Fixture：去掉首轮独占和“不新增记录”歧义，明确后续提案仍可选，
不修改Prompt模板/模型参数/Runtime认知策略，不强制每轮调用。
**措辞修正的行为有效性尚未验证。**

## 2. 冻结的最小真实对照

preregistration.json、dataset/scenarios.json及study/frozen.json在模型运行前固定。
复用现有Scenario Runner、sideband、原工具schema和有界投影；Relevant History先行，
随后Goal Shadow。相同8轮、同一ledger原文、同正文预算、只读文件能力。
首轮一次显式候选邀请，不把它当自然形成；后续不要求任何具体Goal操作。

| 轮次 | 情境与预定观察 |
| --- | --- |
| 1 | 真实读取；允许一次非权威种子 |
| 2 | 取消子任务，长期方向保持 |
| 3 | GPU/网络限制，Path改变而目的保持 |
| 4 | 澄清助手范围及自身解释；不强迫无必要Revision |
| 5 | 明确换成项目档案方向；检查声明是否对应提交 |
| 6 | 最小后续建议；核对最新head实际出站及回答 |
| 7 | 取消全部样例后续方向；历史经历保留 |
| 8 | 历史/实际状态探针；若此时才纠正，单独算提示后纠正 |

八轮不是自然长期用户实验。即使完成，当前用户消息本身也提供新方向，
不能仅凭回答正确就证明候选带来超越历史的因果收益。
候选缺席、无意义重复、合法保持、错误更新分别处理；
maintain不要求每轮生成版本。

## 3. 真实执行：首轮未完成，停止而不重试

实际仅启动一次受保护Bolt：32K、1GiB固定KV、36GiB规划、Eager、单并发、
64/64 UMA与全部既有阈值不变。配置/hash/版本预检PASS；
启动器自动执行的阈值/失效模拟烟测均按预期终止测试子进程。

服务原件：
/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261109T234316Z-32164cac/

模型90/90分片加载、服务READY；Relevant History首轮真实read_section成功，
但首轮最终回答前监控停止服务。下一次模型请求收到provider_connection_refused；
Runner保存失败与原Observation，停止，不发送下一用户轮，不切换到Shadow。

- monitor-exception.json：Linux metric timestamp stale or invalid。
- linux-metrics.json：seq137、valid=false、error=TimeoutExpired。
- 采集实现launch/guard_ctl.py的metrics()使用2秒期限调用nvidia-smi；
  异常被记录并使采集退出。失效/迟到指标会被Windows拒绝，不能使用last-good继续。
- 当前证据定位到采集超时/新鲜度故障；nvidia-smi为何超时仍UNKNOWN。
  Windows和Linux采集器有各自run_id，不能仅因两个ID不同认定跨Run污染。
- 没有已记录的实际内存阈值触发。也不能凭失效前余量排除未采样瞬间的压力。

真实服务131个有效样本（模拟烟测另算）：

| 指标 | 观测极值 |
| --- | ---: |
| NVML占用峰值 | 29.05GiB |
| Windows Dedicated峰值 | 29.69GiB |
| Windows Shared峰值 | 0.188GiB |
| Windows Available最低 | 22.71GiB |
| Commit占用峰值 / 最小余量 | 70.97 / 43.51GiB |
| WSL Available最低 | 17.51GiB |
| WSL Swap峰值 | 约12KiB |

以上指标口径不同，不相加；采样极值不是瞬时安全保证。
详见safety-stop-review.json，原始resource-samples.jsonl完整保留。
最终模型进程组remaining=[]，监控remaining=[]，Harness进程组absent；
8000/8003无监听。没有放宽阈值、自动模型重试、重启WSL或停止其他服务。

**计划2会话16轮；确认完成0用户轮；真实文件Observation 1；Shadow未启动。**
interrupted-audit.json正确给出完成数0、基础设施通过数0、Goal生命周期UNKNOWN，
没有利用“有一次读取”或空候选集合判PASS。
新批次不能与11月9日已完成两会话十轮合并为成功对照。
因安全门禁故障停止真实测试，不把它归因于Goal候选能力、Parser或Context溢出。

## 4. 能安全完成的离线状态反馈核验

既有自动化研究套件83项、Goal契约34项，共117项通过。
没有改动既有测试判据以制造结果。

新增隔离offline-probe.py只调用冻结bundle中的既有GoalResearch/ProposalApp处理器：
研究者手写form→maintain→refine→revise→withdraw，沿本轮8条原文绑定来源与父版本；
中间不调用和末轮历史回顾时，旧记录/当前head均按结构预期保持。
5个不可变版本、同内容保持、refine/revise父引用、withdrawn新head、
旧父版本更新拒绝与无自动ActiveGoal/执行Observation均通过。
源文件、回执、完整逐轮准备视图见offline-replay/。

这些是**人工指定提案的确定性回放**：
没有真实LLM选择，没有实际provider传输，没有语义真值验证；
准备好的Context不等于模型收到，更不等于模型使用。
不能把该PASS称作新的真实Goal演化闭环。

结构上未发现必须新增通道的缺口：现有原生调用→提交/回执→不可变版本→head投影可表达更新。
历史真实form/withdraw已覆盖部分实际传输；自然形成、无提示修正及后续行为仍欠新证据。
现有通道不解析普通回答为提交，这是应保留的权威边界，而非待消除障碍。

## 5. 结论与下一步

| 维度 | 判定与证据范围 |
| --- | --- |
| 既有提交、身份、版本及权限契约 | VERIFIED：历史真实记录＋117项回归；不是语义证明 |
| 全操作状态表达能力 | PASS：本轮隔离脚本回放；真实refine/revise仍UNKNOWN |
| 上轮错误状态声明与缺少调用 | VERIFIED；未调用的内部原因UNKNOWN |
| 新措辞是否改善选择 | UNKNOWN：新对照中断，Shadow未启动 |
| 自然Goal形成与自主跨轮演化 | UNKNOWN：无新增有效模型样本 |
| 最新候选进入下一轮并影响建议 | UNKNOWN：未完成计划探针 |
| Relevant History增量价值 | UNKNOWN：不能作未完成的配对比较 |
| Fail-Closed与清理 | PASS（本次）；监控持续可靠性本次FAIL |
| 新的真实认知闭环 | BLOCKED：先恢复原阈值下的新鲜可用采集 |
| 总体 | PARTIAL，不采纳新认知架构 |

下一步最小事项是恢复既有监控采集可靠性，并在不放宽阈值、不缓存失效数据的前提下，
执行已冻结的对照；不得因本次中断改变Goal成败标准。
当前没有证据要求选择新Goal Engine、接管Harness、扩大权限或人工确认真实Goal。
不需要新的人工长会话，也不能把报告语句自动写成候选状态来补齐闭环。

本轮停止真实执行与新增研究。Memory维持Research Reserved；
不增加数学组合、维护层或正式采纳，不Commit/Push。
