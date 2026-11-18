# M3 收尾、M4 真实用户参与准备（2026-11-18）

M3 整体 **PARTIAL**；M4 长期自主维护与 M5 相对普通历史的省力价值为 **UNKNOWN**。以下受控实验使用研究者编写的安排和真实本地模型。人工参与准备使用 CPU 固定回复，新增自然用户和模型推理均为零。

| 本地 UAEA_DOCS 批次 | 原始观察 |
|---|---|
| `20261118_DeliveryStatusCloseout` | 上游事件名为 completed、载荷为 incomplete 的截断正文可查、可接续，不能自动算作完整答复。 |
| `20261118_M3ActionM4Readiness` | 采购配对交付持平。教学纠正中，助手声称已修正却零提案，还补写了用户免去的旧题。 |
| `20261118_M4Evolution` | 六轮均完整且无提案。临时代班后正确恢复采购风险和核验；长期替代后只有判断与核验，缺新人题干。两组 T3 都看得到原安排。 |
| `20261118_M4HumanPilotGate` | CPU 测试从空 profile 开始，更换进程后同一 Thread 保留前轮原话与答复，恢复时没有重做旧调用。 |

下次有自然改向，事前记下新旧安排分别会给谁交什么。先看首次有区别的成品是否交齐，再查助手声明及 Journal。若有忠实保存的新版本，在同一普通历史下核对它是否补回具体漏项；用户真实重申或返工另记。

## 同步的研究实现

研究驱动使用[预算策略](../../scripts/research/budget_policy.py)、[Native 与 SSE 连续性检查](../../scripts/research/continuity_checks.py)、[上游完成状态检查](../../scripts/research/upstream_delivery.py)和[封存点只读核验](../../scripts/research/check_checkpoint.py)。仓库保留这些批次实用的代码；带有原始会话的研究驱动、封存点和审计证据包保存在本地归档。生产入口、权限和 Guard 配置沿用原有版本。

[纠正教训连续性](../../scripts/research/correction_continuity.py)和[TaskDecision](../../scripts/research/task_decision.py)为显式研究入口；[S1 数学原型](../../scripts/research/s1_shadow.py)及[零件诊断](../../scripts/research/s1_parts.py)为离线研究。TaskDecision V2 接口改善后，仍只有 2/12 启用样本交付可用建议，原流程为 9/12。

本机 64K 实验使用 [Codex rust-v0.163.0](../../harness/versions.json) 的 Linux/aarch64 构建。2026-11-18 查询到上游稳定版为 [0.170.0](https://github.com/openai/codex/releases/tag/rust-v0.170.0)，其 UAEA 兼容性尚待实测。
