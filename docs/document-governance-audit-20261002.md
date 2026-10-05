# UAEA 文档治理审计（2026-10-02）

Status: CURRENT
Role: documentation inventory / validity classification，不是新增 architecture
Review date: 2026-10-02（不代表重跑所有历史实验）

## 范围与判定

初始 `docs/` 共 34 份 Markdown，开始时工作树干净。逐份检查标题、阶段、正文中的 authority/运行路径、实验记录和研究概念；分类依据内容而非 Phase 或文件年代。
源码、运行配置、模型、secret、真实 artifact 均不修改。本轮不 commit/push。

| 分类 | 初始文档数 |
| --- | ---: |
| CURRENT_BASELINE | 4 |
| RESEARCH_FOUNDATION | 4 |
| HISTORICAL_EVIDENCE | 18 |
| SUPERSEDED_DESIGN | 2 |
| IMPLEMENTATION_NOTE | 6 |
| DUPLICATE / MERGE_CANDIDATE | 0 |
| OBSOLETE / SAFE_TO_ARCHIVE | 0 |

移动 24 份正文到分类目录，原路径保留 REDIRECT 导向页，原文件不再是第二个权威来源。既有 `archive/` 的 10 份文档原地保留；2 份 superseded 正文加入 `archive/superseded/`，物理归档总数 12（含索引，不等同于“失去研究价值”）。新增 index/map/audit 和兼容导向页不重复计入这 34 份分类样本。

## 逐份 Inventory / Boundary Matrix

标题使用原文；日期无明确证据时只给阶段，不用 filesystem mtime 冒充验证时间。
“当前引用”限定为治理前主 README 和上述 4 份 CURRENT_BASELINE；历史文档互引不冒充当前架构 endorsement。

### CURRENT_BASELINE

#### UAEA Boundary Integrity Audit（2026-10-02）

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/boundary-integrity-audit-20261002.md` |
| 正文位置 | [docs/current/architecture/boundary-integrity-audit-20261002.md](current/architecture/boundary-integrity-audit-20261002.md) |
| 日期 / 阶段 | 2026-10-02 |
| Topic | 边界完整性 |
| 当前 relevance | 当前语义/执行/evidence contract；Web 人工验收仍 PARTIAL |
| Architecture assumptions | Harness owns runtime，UAEA owns semantics |
| Superseded / replacement | 无 |
| 治理前当前文档引用 | docs/harness-runtime-baseline-20260926.md；docs/web-runtime-environment.md；README.md |
| Unique historical evidence | 是：真实 404 与投影失败、修复重放 |
| Future cognition value | 是：observation/authority/projection |

#### UAEA Harness Runtime Baseline

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/harness-runtime-baseline-20260926.md` |
| 正文位置 | [docs/current/runtime/harness-runtime-baseline-20260926.md](current/runtime/harness-runtime-baseline-20260926.md) |
| 日期 / 阶段 | 2026-09-26；10-02 收敛 |
| Topic | Harness freeze |
| 当前 relevance | 当前 generic runtime；末尾章节为历史 |
| Architecture assumptions | 本地 app-server + vLLM；非旧 Agent 双栈 |
| Superseded / replacement | 历史 Google unsupported 已由 backend/audit 替代 |
| 治理前当前文档引用 | README.md |
| Unique historical evidence | 是：生命周期/sandbox/trajectory 闭环 |
| Future cognition value | 是：hook/history 边界 |

#### UAEA Web 私有启动环境

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/web-runtime-environment.md` |
| 正文位置 | [docs/current/environment/web-runtime-environment.md](current/environment/web-runtime-environment.md) |
| 日期 / 阶段 | 2026-10-01—02 |
| Topic | 私有环境/启动 |
| 当前 relevance | 当前统一入口与 secret isolation |
| Architecture assumptions | WSL + 私有 env；本地模型/外部 Web 分离 |
| Superseded / replacement | 无；历史 smoke 数量不是本轮验证 |
| 治理前当前文档引用 | README.md |
| Unique historical evidence | 是：fresh-shell/auth/权限证据 |
| Future cognition value | 间接：安全采集基础 |

#### Phase-2B SQLite Source / Evidence Closure

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2b-memory/sqlite-source-evidence-closure.md` |
| 正文位置 | [docs/current/evidence/sqlite-source-evidence-closure.md](current/evidence/sqlite-source-evidence-closure.md) |
| 日期 / 阶段 | Phase-2B；2026-08-24 后 |
| Topic | Source/Evidence SQLite |
| 当前 relevance | PARTIALLY CURRENT：source/evidence 成立；旧测试计数/下一步是 checkpoint |
| Architecture assumptions | SQLite != Memory Store；无自动候选提取 |
| Superseded / replacement | 主路径/下一步由当前 audit 更新 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：真实 graph/attachment 导入计数 |
| Future cognition value | 是：EvidenceReference/source lineage |

### RESEARCH_FOUNDATION

#### Phase-2B Memory Boundary Architecture

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2b-memory-boundary-architecture.md` |
| 正文位置 | [docs/research/memory/phase2b-memory-boundary-architecture.md](research/memory/phase2b-memory-boundary-architecture.md) |
| 日期 / 阶段 | Phase-2B；8 月后 |
| Topic | Memory intake/authority |
| 当前 relevance | 概念与对抗评审有效；不是当前实现 |
| Architecture assumptions | 旧 Phase-1 ownership 仅思想血缘 |
| Superseded / replacement | 执行 ownership 由 Harness baseline 替代 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：intake 四方案与反对理由 |
| Future cognition value | 是：Goal/Failure/Observation lifecycle |

#### UAEA Phase-2B Memory Architecture Boundary v0.1

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2b-memory/memory-architecture-boundary-v0.1.md` |
| 正文位置 | [docs/research/memory/memory-architecture-boundary-v0.1.md](research/memory/memory-architecture-boundary-v0.1.md) |
| 日期 / 阶段 | Phase-2B；v0.1 |
| Topic | Object/state/facet/relationship |
| 当前 relevance | 研究 proposal；§1A–1E 优先于旧 tier-first 文字 |
| Architecture assumptions | Runtime Object → Candidate → Memory；旧 runtime wiring 非现行 |
| Superseded / replacement | 仅旧 tier-first/implementation assumptions；思想未 supersede |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：关系模型/状态机与决策表 |
| Future cognition value | 是：association/episode/reactivation |

#### Phase-2B Memory Architecture Test Fixtures

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2b-memory/memory-architecture-test-fixtures.md` |
| 正文位置 | [docs/research/memory/memory-architecture-test-fixtures.md](research/memory/memory-architecture-test-fixtures.md) |
| 日期 / 阶段 | Phase-2B fixture checkpoint |
| Topic | 100-turn 验收思想 |
| 当前 relevance | 结构 fixture 仍复用，不是 extractor/policy 已实现 |
| Architecture assumptions | Candidate 不等于 accepted Memory |
| Superseded / replacement | 无 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：atomic/provenance/explicit-vs-inferred 期望 |
| Future cognition value | 是：噪声/约束/关联与 outcome |

#### Phase-2B Runtime Web / Context / KV Feasibility Rehearsal

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2b-memory/runtime-web-context-kv-feasibility.md` |
| 正文位置 | [docs/research/context/runtime-web-context-kv-feasibility.md](research/context/runtime-web-context-kv-feasibility.md) |
| 日期 / 阶段 | Pre-Harness Phase-2B |
| Topic | Context/evidence/weight |
| 当前 relevance | 保留 §5–7/9 思想；W0–W4 实施计划过期 |
| Architecture assumptions | 旧 Agent.handle/WebShell；context != Memory |
| Superseded / replacement | 执行入口由 Harness/current audit 替代 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：记忆权重信号/投影风险 |
| Future cognition value | 是：working set/longitudinal evidence |

### HISTORICAL_EVIDENCE

#### Google backend 接入：Phase 1（2026-10-02）

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/google-backend-phase1.md` |
| 正文位置 | [docs/historical/web/google-backend-phase1.md](historical/web/google-backend-phase1.md) |
| 日期 / 阶段 | 2026-10-02 Phase 1 |
| Topic | Google 接入证据 |
| 当前 relevance | backend 已实现；当时停止点不是当前计划 |
| Architecture assumptions | SerpApi backend != model-facing provider |
| Superseded / replacement | 当前 Web contract 以 audit 为准 |
| 治理前当前文档引用 | docs/web-runtime-environment.md；README.md |
| Unique historical evidence | 是：真实 smoke artifact/计数/secret 边界 |
| Future cognition value | 间接：执行 provenance |

#### UAEA Phase-2A-2 Backend Equivalence Validation

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2a-backend-equivalence.md` |
| 正文位置 | [docs/historical/phase2a/phase2a-backend-equivalence.md](historical/phase2a/phase2a-backend-equivalence.md) |
| 日期 / 阶段 | 2026-08；Phase-2A-2 |
| Topic | LMF/Mock contract |
| 当前 relevance | 历史 equivalence evidence |
| Architecture assumptions | Phase-1 Agent + ModelClient，LMF 当时 production |
| Superseded / replacement | 当前主执行路径由 Harness 替代 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：320.1s smoke/17 tests/24 cases |
| Future cognition value | 是：旧 observation/artifact 示例 |

#### UAEA Phase-2A Equivalence Matrix

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2a-equivalence-matrix.md` |
| 正文位置 | [docs/historical/phase2a/phase2a-equivalence-matrix.md](historical/phase2a/phase2a-equivalence-matrix.md) |
| 日期 / 阶段 | 2026-08；A/B/C |
| Topic | 变量隔离 |
| 当前 relevance | 研究方法保留；NOT PROVEN 为旧时点 |
| Architecture assumptions | DS14B + LMF/vLLM migration |
| Superseded / replacement | 当前 Qwen decision/audit 替代生产判断 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：A/B/C变量拆分与诊断缺口 |
| Future cognition value | 间接：证据归因方法 |

#### UAEA Phase-2A Initialization

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2a-initialization.md` |
| 正文位置 | [docs/historical/phase2a/phase2a-initialization.md](historical/phase2a/phase2a-initialization.md) |
| 日期 / 阶段 | 2026-08-04—05 |
| Topic | 初始化/早期 pin |
| 当前 relevance | 阶段记录，不是当前 commit/env 状态 |
| Architecture assumptions | de0ecb0 + LMF production + install pending |
| Superseded / replacement | 当前 README/submodule freeze 替代 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：早期基线与验证序列 |
| Future cognition value | 间接：Phase-1 血缘 |

#### Phase-2A Model Artifact Baseline

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2a-model-artifact-baseline.md` |
| 正文位置 | [docs/historical/phase2a/phase2a-model-artifact-baseline.md](historical/phase2a/phase2a-model-artifact-baseline.md) |
| 日期 / 阶段 | 2026-08-15；Phase-2A |
| Topic | Artifact 决策 |
| 当前 relevance | Qwen/AWQ 原始证据有效；8192 是实验边界 |
| Architecture assumptions | Phase-1 backend；物理参数限定 |
| Superseded / replacement | 当前 8002 Harness profile 不由本文件指定 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：WNA16 拒绝/传统 AWQ 对照 |
| Future cognition value | 间接：不可过度泛化 evidence |

#### UAEA Phase-2A-3 vLLM Backend Adapter

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2a-vllm-backend.md` |
| 正文位置 | [docs/historical/phase2a/phase2a-vllm-backend.md](historical/phase2a/phase2a-vllm-backend.md) |
| 日期 / 阶段 | Phase-2A-3；2026-08 |
| Topic | vLLM legacy adapter |
| 当前 relevance | 保留 contract/smoke；旧默认/指标非当前入口 |
| Architecture assumptions | DS14B + 8001 + ModelClient；LMF dual path |
| Superseded / replacement | 当前 Harness invocation 替代 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：旧 smoke/22 tests/partial semantic findings |
| Future cognition value | 间接：legacy 对照 |

#### UAEA Phase-2A-4 vLLM Compatibility Audit

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2a-vllm-compatibility-audit.md` |
| 正文位置 | [docs/historical/phase2a/phase2a-vllm-compatibility-audit.md](historical/phase2a/phase2a-vllm-compatibility-audit.md) |
| 日期 / 阶段 | 2026-08-05 |
| Topic | 兼容性/安装审计 |
| 当前 relevance | 版本/安装 pending 是当时观察，不是最新推荐 |
| Architecture assumptions | 单 GPU DS14B容量/当时wheel解析 |
| Superseded / replacement | 后续 Qwen 实验及 current baseline |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：硬件/ABI/容量决策依据 |
| Future cognition value | 间接：boundary/uncertainty |

#### UAEA Phase-2A-4 vLLM Environment Preparation

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2a-vllm-environment.md` |
| 正文位置 | [docs/historical/phase2a/phase2a-vllm-environment.md](historical/phase2a/phase2a-vllm-environment.md) |
| 日期 / 阶段 | 2026-08-05 |
| Topic | 环境 bring-up |
| 当前 relevance | 保留隔离原则；NOT STARTED/DS14B启动是历史 |
| Architecture assumptions | 旧环境/原始 BF16 capacity gate |
| Superseded / replacement | 当前环境入口/冻结 profile 替代操作指引 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：环境路径/容量/部署门槛 |
| Future cognition value | 间接：物理实验边界 |

#### Phase-2A Qwen2.5-AWQ vLLM Equivalence Report

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2a-vllm-qwen25-equivalence-report.md` |
| 正文位置 | [docs/historical/phase2a/phase2a-vllm-qwen25-equivalence-report.md](historical/phase2a/phase2a-vllm-qwen25-equivalence-report.md) |
| 日期 / 阶段 | 2026-08-15 |
| Topic | Qwen L0–L6 report |
| 当前 relevance | 有效历史 capability evidence，不是开放任务承诺 |
| Architecture assumptions | 冻结 Phase-1 + VLLMBackend |
| Superseded / replacement | 未被否定；当前 baseline 使用其证据 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：19/19 模型实测及55 trace |
| Future cognition value | 是：semantic observation/recovery examples |

#### UAEA Phase-2A vLLM Root Cause Analysis

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2a-vllm-root-cause-analysis.md` |
| 正文位置 | [docs/historical/phase2a/phase2a-vllm-root-cause-analysis.md](historical/phase2a/phase2a-vllm-root-cause-analysis.md) |
| 日期 / 阶段 | 2026-08-12—15 |
| Topic | DS14B !/NaN root cause |
| 当前 relevance | 唯一失败链保留；早期假设并存不等于现行 |
| Architecture assumptions | DS14B WNA16与后续Qwen control |
| Superseded / replacement | 生产决策以后续Qwen/audit为准 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：分层隔离、logprobs与artifact证据 |
| Future cognition value | 是：episode/experience case study |

#### UAEA Phase-2A-5 vLLM Small Model Smoke Validation

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2a-vllm-small-model-smoke.md` |
| 正文位置 | [docs/historical/phase2a/phase2a-vllm-small-model-smoke.md](historical/phase2a/phase2a-vllm-small-model-smoke.md) |
| 日期 / 阶段 | Phase-2A-5；2026-08 |
| Topic | 0.5B bring-up |
| 当前 relevance | 只证明小模型 serving，不是当前模型 |
| Architecture assumptions | WSL + 小模型；不证明14B quality |
| Superseded / replacement | 后续真实Qwen验证替代ready判断 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：早期smoke命令/观察 |
| Future cognition value | 间接：不同证据强度 |

#### UAEA Harness Feasibility Research

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/archive/harness/harness-feasibility-20260912.md` |
| 正文位置 | [docs/archive/harness/harness-feasibility-20260912.md](archive/harness/harness-feasibility-20260912.md) |
| 日期 / 阶段 | 2026-09-12—26 |
| Topic | H2/H2.5/H3全程 |
| 当前 relevance | checkpoint证据，不是当前操作计划；研究段落仍可入口 |
| Architecture assumptions | 从pre-Harness迁移到source-owned runtime |
| Superseded / replacement | 当前 Harness baseline/audit |
| 治理前当前文档引用 | docs/harness-runtime-baseline-20260926.md |
| Unique historical evidence | 是：provenance/context/sandbox/trajectory/protocol演进 |
| Future cognition value | 是：Goal/L0/context/experience hooks |

#### UAEA Pre-Harness Baseline

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/archive/harness/pre-harness-freeze-20260912.md` |
| 正文位置 | [docs/archive/harness/pre-harness-freeze-20260912.md](archive/harness/pre-harness-freeze-20260912.md) |
| 日期 / 阶段 | 2026-09-12 |
| Topic | Pre-Harness freeze |
| 当前 relevance | legacy/A-B baseline保存 |
| Architecture assumptions | Phase-1 + WebShell + 8001/8192 |
| Superseded / replacement | 主路径由Harness baseline替代 |
| 治理前当前文档引用 | docs/harness-runtime-baseline-20260926.md |
| Unique historical evidence | 是：freeze/reuse/limits/physical boundary |
| Future cognition value | 是：UAEA Core Research/reuse matrix |

#### Historical README Snapshot

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/archive/harness/readme-before-boundary-audit-20261002.md` |
| 正文位置 | [docs/archive/harness/readme-before-boundary-audit-20261002.md](archive/harness/readme-before-boundary-audit-20261002.md) |
| 日期 / 阶段 | 2026-10-02归档；原Phase1–Harness |
| Topic | 旧README snapshot |
| 当前 relevance | 仅历史，不作为当前架构入口 |
| Architecture assumptions | 多阶段并存/旧主路径描述 |
| Superseded / replacement | 当前主README + audit |
| 治理前当前文档引用 | README.md |
| Unique historical evidence | 是：原README全文/项目vision |
| Future cognition value | 是：早期架构思想血缘 |

#### UAEA Phase-2A Backend Equivalence Matrix

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/archive/phase2a-vllm-diagnostics/phase2a-backend-equivalence-matrix.md` |
| 正文位置 | [docs/archive/phase2a-vllm-diagnostics/phase2a-backend-equivalence-matrix.md](archive/phase2a-vllm-diagnostics/phase2a-backend-equivalence-matrix.md) |
| 日期 / 阶段 | Phase-2A早期；2026-08 |
| Topic | layer matrix |
| 当前 relevance | 历史差异矩阵；不是新benchmark backlog |
| Architecture assumptions | LMF vs DS14B vLLM |
| Superseded / replacement | 后续artifact/Qwen结论 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：逐层DIFF/UNKNOWN现场证据 |
| Future cognition value | 间接：evidence limitation |

#### UAEA Phase-2A vLLM AB Difference Report

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/archive/phase2a-vllm-diagnostics/phase2a-vllm-ab-difference-report.md` |
| 正文位置 | [docs/archive/phase2a-vllm-diagnostics/phase2a-vllm-ab-difference-report.md](archive/phase2a-vllm-diagnostics/phase2a-vllm-ab-difference-report.md) |
| 日期 / 阶段 | Phase-2A早期；2026-08 |
| Topic | A/B差异报告 |
| 当前 relevance | 历史假设与优先级保存 |
| Architecture assumptions | 未隔离artifact变量的LMF/vLLM比较 |
| Superseded / replacement | A/B/C变量框架与Qwen控制 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：参数/stop/结构差异 |
| Future cognition value | 是：hypothesis revision case |

#### Phase-2A vLLM Equivalence Analysis

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/archive/phase2a-vllm-diagnostics/phase2a-vllm-equivalence-analysis.md` |
| 正文位置 | [docs/archive/phase2a-vllm-diagnostics/phase2a-vllm-equivalence-analysis.md](archive/phase2a-vllm-diagnostics/phase2a-vllm-equivalence-analysis.md) |
| 日期 / 阶段 | Phase-2A早期；2026-08 |
| Topic | 早期归因 |
| 当前 relevance | 结论有时点，不复活旧调参计划 |
| Architecture assumptions | Agent+ModelBackend；DS14B |
| Superseded / replacement | 后续matrix/root-cause/Qwen证据 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：初期根因排序与边界 |
| Future cognition value | 是：从假设到后续证据 |

#### UAEA Phase-2A vLLM Migration Context Manifest

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/archive/phase2a-vllm-diagnostics/phase2a-vllm-migration-context-manifest.md` |
| 正文位置 | [docs/archive/phase2a-vllm-diagnostics/phase2a-vllm-migration-context-manifest.md](archive/phase2a-vllm-diagnostics/phase2a-vllm-migration-context-manifest.md) |
| 日期 / 阶段 | Phase-2A早期；2026-08 |
| Topic | 旧环境manifest |
| 当前 relevance | 仅当时环境，不是当前物理配置 |
| Architecture assumptions | de0ecb0/DS14B/16384/.7/LMF |
| Superseded / replacement | 当前README/runtime/env guide |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：当时路径/配置/benchmark集合 |
| Future cognition value | 间接：experiment provenance |

### SUPERSEDED_DESIGN

#### UAEA Phase-2A-1 Model Backend API

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2a-model-backend.md` |
| 正文位置 | [docs/archive/superseded/phase2a-model-backend.md](archive/superseded/phase2a-model-backend.md) |
| 日期 / 阶段 | Phase-2A-1；2026-08 |
| Topic | 旧主模型调用设计 |
| 当前 relevance | legacy API仍存在；不指导Harness主路径 |
| Architecture assumptions | Agent owns prompt/parser/recovery，LMF production |
| Superseded / replacement | Harness baseline + Boundary Audit |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：旧adapter接口演化，保留全文 |
| Future cognition value | 是：只复用边界思想不恢复实现 |

#### Phase-2B Memory Directory Plan

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2b-memory-directory-plan.md` |
| 正文位置 | [docs/archive/superseded/phase2b-memory-directory-plan.md](archive/superseded/phase2b-memory-directory-plan.md) |
| 日期 / 阶段 | Phase-2B早期 |
| Topic | 旧目录/未实现计划 |
| 当前 relevance | marker-only/Do not implement SQLite 已过期 |
| Architecture assumptions | 旧 Phase2 code/docs tree，backend路径 |
| Superseded / replacement | 当前 docs guide + source/evidence closure |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：为何推迟空模块的决策 |
| Future cognition value | 有限：不从目录反推认知架构 |

### IMPLEMENTATION_NOTE

#### UAEA Inference Trace Layer Design

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/inference-trace-layer-design.md` |
| 正文位置 | [docs/implementation/inference/inference-trace-layer-design.md](implementation/inference/inference-trace-layer-design.md) |
| 日期 / 阶段 | Phase-2A trace design；2026-08 |
| Topic | legacy inference trace |
| 当前 relevance | PARTIALLY CURRENT：inference/runtime trace区别仍有效；旧实施计划不是当前待办 |
| Architecture assumptions | ModelBackend.generate trace；非App Server trajectory |
| Superseded / replacement | Harness event contract/audit更新主路径 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：完整token/config/stop metadata设计 |
| Future cognition value | 是：原始采样与语义解释分离 |

#### Phase-2B Memory Python Environment

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/phase2b-memory/python-environment.md` |
| 正文位置 | [docs/implementation/environment/python-environment.md](implementation/environment/python-environment.md) |
| 日期 / 阶段 | Phase-2B environment checkpoint |
| Topic | stdlib SQLite env |
| 当前 relevance | 隔离原则可维护；路径/版本/empty schema仅当时观察 |
| Architecture assumptions | Windows venv != WSL inference env |
| Superseded / replacement | 当前 Web WSL startup 以 web env guide 为准 |
| 治理前当前文档引用 | 否 |
| Unique historical evidence | 是：venv/sqlite smoke观测 |
| Future cognition value | 间接：轻量持久化维护 |

#### Web 网络可观测性：Phase 1

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/web-network-observability-phase1.md` |
| 正文位置 | [docs/implementation/web/web-network-observability-phase1.md](implementation/web/web-network-observability-phase1.md) |
| 日期 / 阶段 | 2026-10-02 |
| Topic | 实际请求诊断 |
| 当前 relevance | PARTIALLY CURRENT：open/header/read仍有效；阶段stop历史 |
| Architecture assumptions | urllib边界；不猜测DNS/TLS；不加retry |
| Superseded / replacement | 授权/result修复以audit为准 |
| 治理前当前文档引用 | README.md |
| Unique historical evidence | 是：真实artifact/诊断分类 |
| Future cognition value | 是：failure evidence |

#### Harness 历史文档归档

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/archive/harness/README.md` |
| 正文位置 | [docs/archive/harness/README.md](archive/harness/README.md) |
| 日期 / 阶段 | Harness归档索引 |
| Topic | 历史导航 |
| 当前 relevance | 当前历史导航；治理前 replacement 链接已更新 |
| Architecture assumptions | archive非错误/非主路径 |
| Superseded / replacement | 无；治理更新导航 |
| 治理前当前文档引用 | docs/harness-runtime-baseline-20260926.md；README.md |
| Unique historical evidence | 否：索引可再生成，目标内容不可删 |
| Future cognition value | 是：发现来源入口 |

#### Phase-2A vLLM Diagnostic Document Archive

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/archive/phase2a-vllm-diagnostics/README.md` |
| 正文位置 | [docs/archive/phase2a-vllm-diagnostics/README.md](archive/phase2a-vllm-diagnostics/README.md) |
| 日期 / 阶段 | Phase-2A归档索引 |
| Topic | 诊断导航 |
| 当前 relevance | 当前历史导航；治理前 active summary 措辞已修正 |
| Architecture assumptions | archive evidence ≠ operating guide |
| Superseded / replacement | 旧 active summary 已替换为历史定位与 current 导航 |
| 治理前当前文档引用 | docs/harness-runtime-baseline-20260926.md；README.md |
| Unique historical evidence | 否：索引，无独立实验正文 |
| Future cognition value | 间接：查证据 |

#### Phase-2A Document Archive Index

| 项 | 审计记录 |
| --- | --- |
| 原路径 | `docs/archive/phase2a/README.md` |
| 正文位置 | [docs/archive/phase2a/README.md](archive/phase2a/README.md) |
| 日期 / 阶段 | Phase-2A归档索引 |
| Topic | Phase2A导航 |
| 当前 relevance | 当前历史导航；原 active documents 清单仅作历史记录 |
| Architecture assumptions | Phase身份不等于文档当前有效 |
| Superseded / replacement | 本轮历史索引与guide |
| 治理前当前文档引用 | docs/harness-runtime-baseline-20260926.md；README.md |
| Unique historical evidence | 否：索引，无独立实验正文 |
| Future cognition value | 间接：演进导航 |

## 冲突与处理

| 冲突 | 文件 | 当前解释 / 处理 |
| --- | --- | --- |
| LMF production、DS14B、旧 de0ecb0 pin、安装 pending 被称 current | Phase-2A initialization/model-backend/vLLM backend/environment/compatibility、旧 diagnostics | 标记 historical/superseded；当前 Qwen/Harness/physical boundary 由 current guide/README 指定。旧数据不改写 |
| 同一 Phase 的失败假设与最终 Qwen PASS 并存 | equivalence matrix、root-cause §1–20 与 §21、Qwen report | 保留证据演化，不把阶段 NOT PROVEN 当现行 blocker；不抹去未验证的 DS14B 同 artifact 分支 |
| Phase-1 拥有 generic lifecycle，与 Harness ownership 冲突 | Memory boundary / v0.1、runtime Web/KV feasibility | RESEARCH_FOUNDATION；概念可复用，旧 Agent.handle/authority wiring 不作为接入指令 |
| object-state-facet 与 tier-first 两种 Memory lifecycle | memory-architecture-boundary-v0.1 §1A–1E / §2 | 顶部及 §2 标明优先级；后者为保留的早期解释，不产生两个现行状态机 |
| marker-only / 不实现SQLite 与已有 Source/Evidence ingestion 冲突 | memory directory plan、Python env 的 empty schema smoke | directory plan superseded；env 只保留隔离/当时 smoke，SQLite closure 不等于 Memory实现 |
| Google unsupported / Phase1待人工 与真实backend成功并存 | Harness baseline历史段、旧Harness probe、Google/network Phase1记录 | current audit与env说明有效，历史等待/unsupported仅当时事实；修复后search→fetch仍待人工确认 |
| archive索引仍把旧Phase2A文档称active | archive/phase2a/README、diagnostics/README | 改为历史导航，显式指向 current baseline |

## Unsafe To Archive / Merge Decisions

Memory 两份 architecture 文档有重叠，但分别保留 intake/adversarial debate 与 state/facet/relationship/validity 决策，不能按重复文档删除或合并证据。fixture 含独立验收期望；Web/KV 的 §§5–7 是 cognition 基石。它们均留 research，不入 archive。

root-cause、Harness feasibility、pre-Harness freeze、Qwen report、SQLite closure 有唯一实验/决定/identity 证据；允许迁到 historical，但不得当作无价值材料。旧 README 是完整快照，不是可安全丢弃的重复。

旧 inference trace 设计与 Harness trajectory 是不同层，不是 duplicate；不能合并成一个“运行日志”而损失 inference/runtime 区分。三个旧 archive README 属维护索引，仍需保留导航。

## 尚未确定 / 未声称解决

所有 34 份文档已有 primary 分类；没有待定类别。尚未冻结的是研究结论，而不是遗漏分类：隐含 task arbitration、长期 Goal inference、Episode boundary、associative retrieval/policy 和 memory weight。
历史环境版本/路径没有在本轮重新安装或验证；历史 artifact 外部绝对路径只作为 provenance，不保证跨机器存在。外链本轮不做网络探测。
归档大文件含有仍有价值的研究段落，Research Foundation Map 直接链接这些段落，不把文件在 archive 中等同于思想过期。

## 治理规则与验证

Current docs 决定当前 contract；Research docs 不宣称实现；Historical docs 决定某次实验发生了什么；Implementation notes 不能提升为 architecture authority；REDIRECT 仅保留路径兼容。
每个 canonical 正文新增轻量治理 header，旧正文保留。移动前原内容和 hash 已在本次会话内保存；
24 份正文移除治理 header 后原文逐字符一致，2 份仅规范化 EOF 空白，5 份只修 relative links 或增加 lifecycle 阅读注释，
3 份原索引修正导航。之后 superseded 两份只增加具体 replacement 链接；不改实验结论或删除正文段落。

## 本轮验证结果

- 审计覆盖原有 34 份文档，逐份分类与证据记录完整；新增导航和跳转页不重复计入分类统计。
- 24 对原路径 / canonical 正文均存在；原路径为 REDIRECT，canonical 正文不是第二份跳转页。
- 主 README 与 docs 共 67 份 Markdown、231 条本地链接：目标文件与章节锚点全部可解析。
- 正文保留检查通过：差异限于治理 header、相对链接修复、索引导航、Memory lifecycle 阅读注释和 EOF 空白；历史实验结论未改写。
- 私有环境中的真实 credential 在内存中与 Markdown、Git diff 比对：零命中，不输出 secret 值。
- 修改范围仅为主 README 和 docs Markdown；未修改源码、测试、模型配置、运行参数或 artifact；文件删除数为 0。
- `git diff --check` 通过；未执行 `git add`、commit 或 push。
- 本轮仅做文档验证，未运行模型、推理实验或 unittest；未验证外部网页与历史 artifact 的跨机器可用性。

本轮到此停止，不实现 Goal/Memory/Episode。
