# Historical Evidence

Status: HISTORICAL_INDEX
Role: 演进与复现实验导航；不指定当前启动参数

## Phase-1 / Pre-Harness

- [Pre-Harness freeze](../archive/harness/pre-harness-freeze-20260912.md)：旧 runtime、capability、SQLite 与物理边界的保存点。
- [旧 README 完整快照](../archive/harness/readme-before-boundary-audit-20261002.md)：项目 vision 与多阶段演进。
- 原始 Phase-1 设计与 benchmark 文档仍在冻结子模块 `runtime/phase1-runtime/docs/`，本轮不移动、不改写。

## Phase-2A：旧接线与最终 artifact 证据

| 正文 | 阅读目的 |
| --- | --- |
| [Initialization](phase2a/phase2a-initialization.md) | 早期 pin/LMF 与阶段验证，不是当前待安装计划 |
| [Backend equivalence](phase2a/phase2a-backend-equivalence.md) | contract 与旧 smoke 的证据 |
| [vLLM backend](phase2a/phase2a-vllm-backend.md) | legacy adapter；transport成功不等于semantic等价 |
| [Compatibility audit](phase2a/phase2a-vllm-compatibility-audit.md) | 当时 ABI/容量/安装决策 |
| [Environment bring-up](phase2a/phase2a-vllm-environment.md) | 环境隔离与旧部署门槛 |
| [Small-model smoke](phase2a/phase2a-vllm-small-model-smoke.md) | 小模型验证的证明边界 |
| [A/B/C equivalence matrix](phase2a/phase2a-equivalence-matrix.md) | backend/artifact/generation变量分开，不新增待办 |
| [DS14B root-cause](phase2a/phase2a-vllm-root-cause-analysis.md) | 完整失败证据与假设演进，最后§21包含Qwen控制 |
| [Artifact decision baseline](phase2a/phase2a-model-artifact-baseline.md) | WNA16拒绝、传统AWQ选择的证据 |
| [Qwen equivalence report](phase2a/phase2a-vllm-qwen25-equivalence-report.md) | 模型实测L0–L6与trace，不是开放任务保证 |

更早逐层差异记录保留在 [diagnostic archive](../archive/phase2a-vllm-diagnostics/README.md)。
旧 ModelBackend 主路径设计另列 [superseded](../archive/superseded/phase2a-model-backend.md)。

## Phase-2B：Phase 不等于有效性

[Memory/Context研究基础](../research/README.md) 保留未来价值；
[Source/Evidence closure](../current/evidence/sqlite-source-evidence-closure.md) 仍是 current source contract；
[旧目录计划](../archive/superseded/phase2b-memory-directory-plan.md) 已被实现事实与新文档结构替代；
[环境说明](../implementation/environment/python-environment.md) 只做局部维护。

## H2 / H2.5 / H3 与 Web

- [完整 Harness feasibility/probe 历史](../archive/harness/harness-feasibility-20260912.md)：包括local provenance、context、sandbox、trajectory、I/O与capability-state。
- [Google backend Phase1](web/google-backend-phase1.md)：接入时真实 smoke 与 secret evidence，旧“待人工”不是当前开发计划。
- [Web 网络诊断](../implementation/web/web-network-observability-phase1.md)：诊断机制有效，阶段停止点为历史。

不得删除唯一证据或为了收敛文档改写历史失败结论。正文中的绝对artifact路径是当时provenance，未在本轮跨机器验证。
