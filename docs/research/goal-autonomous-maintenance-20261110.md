# Goal自主维护：有种子对照预登记与WSL升级中断

日期：2026-11-10（Asia/Shanghai）。**总体PARTIAL；本批真实自主维护验证BLOCKED，Goal能力UNKNOWN。**
记录：/home/wqkan_wsl/uaea-n1x/research-records/goal-autonomous-maintenance-20261110T014517Z/
源代码检查点：125f0d2a8e6b7ac0f6b70baf9913b942be2b1cb2。
前置：[30轮零候选的限定结论](goal-wording-contrast-20261110.md)、
[历史显式接口](goal-channel-convergence-20261109.md)、
[NVML保护版本](../implementation/harness/n1x-telemetry-reliability-20261110.md)。
Memory保持Research Reserved。

## 1. 实验条件与判据

复用既有Scenario Runner、Goal opt-in sideband、SharedExecutionBoundary。
冻结一个非金融研究样例，Relevant History先行、Shadow后行，每臂5轮、同一ledger和用户文本。
ledger沿用历史研究者摘录，不是新GPU测量，也不是用户真实长期Goal。
仅T1明确要求实际form种子；其后不提示Goal操作、不forced tool_choice、不Host补发。
候选只作非权威研究解释，ActiveGoal/Memory/权限不扩张。

| 轮 | 输入语义及预登记判据 |
| --- | --- |
| 1 | 真实读文件，显式请求一次form；提交、保存、后续成功传输须分别有证据 |
| 2 | 取消页面摘录子任务，长期文档助手目的不变；不调用也可以是合理maintain |
| 3 | 无GPU/外网，只改Path和条件；不能自动认定长期Goal改变 |
| 4 | 明确停止助手研究，改为项目档案；不要求具体工具，观察自主修订/撤回 |
| 5 | 当前方向下重新读取并提出两项核验；查最新head实际传输与回答一致性 |

单对、固定顺序、合成用户意图，不估计统计效应。
当前消息本身也提供新方向；即使回答正确，也不能仅凭相关性证明候选造成决策收益。
preregistration.json、execution-lock.json、study/frozen.json和source-lock.json均在真实加载前固定。
保留32K/1GiB KV/36GiB规划、单并发/Eager、64/64 UMA和全部既有阈值。
使用原--experiment有限1800秒服务策略；不是将人工入口重新设为有限期限。
83项既有离线研究回归PASS；未修改Runner、Goal通道、评价器或正式Runtime。

## 2. 真实进度：不是完成的配对实验

一次加载90/90、READY。原启动器48GiB模拟阈值和监控失效烟测按预期终止无模型进程。
实际只完成Relevant History前2轮；第3轮已开始、未见原生完成事件。
Shadow尚未启动，**无本批真实种子、Goal调用、拒绝或版本**。
基线2次文件读取有真实Observation；另有1次request_user_input参数解析失败。
失败原样保存，不算外部执行成功或Goal提案。

基线第二轮普通文字合理保留长期方向、停止子任务。
首轮仍有来源段落理解偏差，并将同轮参数失败描述成历史拒绝；
这些是有限的模型行为反例，不构成新Goal维护结论或Runtime架构缺陷。

原审计明确记录缺轮、无result、缺正常回复，基础设施完成判据不通过；
候选生命周期UNKNOWN，没有空集PASS。
2轮已完成请求的累计usage为输入60,885/输出840；不包含未完成第三轮最终usage，
不作为完整会话成本，也不能与未启动Shadow计算增量。
0 Compaction不说明长期压缩恢复通过。

## 3. 中断证据与分级

**VERIFIED：**
- 最后Windows样本09:51:41.569，Linux有效帧最后09:51:42.641。
- Windows MsiInstaller事件1040：09:51:11.516开始安装
  Windows SoftwareDistribution中的wsl.3.0.5.0.arm64.msi。
- RestartManager 10000：09:51:38.621开启处理；10010逐项记录WSL、wslhost、wslrelay、
  vmwp、msrdc未能重新启动；10005在09:51:40.893提示需要重启。
- MsiInstaller 1033/11707：09:52:01.926安装WSL3.0.5.0成功、状态0；1042结束事务。
- 后续Guest为新启动实例；systemd-journald报告上次日志非正常关闭。
  Runner没有finally/exit/cleanup回执，旧模型/Harness/Linux采集进程和8000/8003监听均已不在。
  Windows进程只读检查排除观察器自身后，没有匹配Bolt Guard。
  初次未排除观察器的中间记录保留，不能把其1个自匹配当作遗留Guard。

**HIGH-CONFIDENCE INFERENCE：** 外部WSL升级与进程链中断的时间和对象吻合。
本任务没有执行WSL升级、重启或停止WSL命令。
精确Installer→进程终止调用栈未捕获，不能写成已直接观测的完整因果链。

**UNKNOWN：** 未采样间隙的瞬时状态、是否仍须系统重启。
RestartManager提示及PendingFileRenameOperations存在值得注意，但后者非WSL专属，
CBS/WindowsUpdate重启键均未发现；不能据此擅自重启，也不能宣称无需重启。

原件：windows-installer-events.json（含事件XML）、windows-events.json、
interruption-review-initial.json、windows-reboot-indicators.json、
post-update-environment.json、windows-guard-process-observation-final.json。

## 4. 资源边界

本次NVML V2实际产生276个service样本，覆盖加载及已执行交互，
没有记录到资源阈值越界或遥测失效停止：

| 指标 | 已记录极值 |
| --- | ---: |
| NVML GPU | 29.88GiB |
| Windows Dedicated / Shared | 29.25 / 0.191GiB |
| Windows Available最低 | 21.86GiB |
| Commit占用峰值 / 最小余量 | 70.88 / 43.60GiB |
| WSL Available最低 / Swap峰值 | 17.49GiB / 12KiB |
| Linux完整采样最长 / GPU查询最长 | 3.77 / 2.85ms |

各口径不相加，采样极值不是瞬时硬上限，也不排除最后未采样间隙异常。
这是V2的限定真实负载证据，不是持续无人值守可靠性PASS。
无最终Guard/服务退出回执，不能用“后来无进程”替代正常终止闭环验收。
未自动重载、改阈值、改Pagefile/Carveout/WSL配置、升级依赖或停止外部服务。

## 5. 结论及最小后续

| 维度 | 判定 |
| --- | --- |
| 冻结脚本与既有83项离线研究测试 | VERIFIED，限定PASS |
| 本次完整对照执行 | PARTIAL，配对未完成 |
| 本批Goal种子、版本、投影及自主维护 | UNKNOWN：Shadow未启动 |
| 候选状态陈述一致性、后续使用 | UNKNOWN：没有候选样本 |
| 相对Relevant History的行为/决策增量 | UNKNOWN：不能比较未完成配对 |
| 截至最后采样的资源保护数据 | VERIFIED限定；不是整个异常退出安全闭环PASS |
| 本次中断归因 | 外部WSL升级高置信推断；不是已证明OOM或Goal失败 |

本批保留为独立中断记录，不并入此前30轮零提案的模型统计。
停止GPU实验；先由用户安排/确认宿主更新窗口，系统如要求重启由用户决定时间。
再通过原有无模型配置、保护及新内核环境核查后，使用同一冻结脚本开启新批次，
不覆盖本批、不自动恢复未完成Turn，也不据本次中断改变Goal接口或Memory研究方向。
当前不需要人工Goal长会话、真实用户Goal确认或新认知架构决策。

本轮源码不变；仅新增本记录和研究地图索引，隔离研究脚本/原件留在research-records。
保留正式Goal/Memory和Harness执行所有权，不Commit/Push。
