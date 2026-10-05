# Research Foundation Map

Status: RESEARCH_FOUNDATION
Role: 思想血缘与证据入口，不设计新 Goal/Memory/Episode engine
Governance reviewed: 2026-10-02
Information boundary checkpoint: 2026-10-05（最新 authority 人工未验收）

## Longitudinal Cognition 前置边界

[当前 checkpoint](../current/architecture/cognition-boundary-checkpoint-20261005.md) 区分已经实现的
有限边界、人工证据与尚未实现的认知机制：

- retention != adoption；support != authorization；applicability != truth；provenance != correctness。
- projection 不能增加 authority；同一 call 的多份记录不能被当成独立 evidence。
- local action failure 不能无依据升级成 Goal/world conclusion；Goal cognition 与 execution authority 分离。
- high bar for promotion、low bar for retention；interpretation 可保留而不取得执行效力。

[shadow audit](../implementation/harness/semantic-promotion-shadow-audit-20261005.md) 已经人工补验；
[authority boundary](../implementation/harness/semantic-authority-boundary-20261005.md) 已完成有限实现和自动验证，人工尚未进行。
这些原则不是都已有 enforcement：独立证据计数、world conclusion validation、directive correctness
和 Goal/Memory/Episode engine 均未实现。

稳定 Goal + 新 evidence + continuation divergence 是待验证研究假设。
clarification 是否基于实质 action 分支差异，而不是一般 ambiguity classification，仍应通过
后续有限 probe 验证；不能在文档整理中冻结完整 branch tree、阈值、ontology 或 truth engine。

## Goal Hypothesis / Active Goal

1. [Pre-Harness freeze](../archive/harness/pre-harness-freeze-20260912.md#reuse-matrix)：区分旧控制平面与 UAEA Core Research，保留 epistemic update/problem boundary 的归属。
2. [Memory Boundary](memory/phase2b-memory-boundary-architecture.md#goal-lifecycle)：Goal 从 active control object 到 durable candidate 的条件；不能因为出现 goal 字样就持久化。
3. [Memory v0.1](memory/memory-architecture-boundary-v0.1.md#3-memory-object-taxonomy)：Goal/intent/preference/unresolved issue 与 evidence/validity 的区分。
4. [Harness ownership audit](../archive/harness/harness-feasibility-20260912.md#harness-capability-ownership-audit)：Harness thread goal metadata 不等于 UAEA Goal Hypothesis。
5. [当前 boundary](../current/architecture/boundary-integrity-audit-20261002.md#boundary-matrix)：实际 ActiveGoal 未激活；现有 task/scope bridge 不能冒充长期 Goal 推断。

可继承的是身份、authority、durability、revision 与 evidence 思想，不是旧 Agent/workflow cursor 执行。
现有 docs 没有完整 longitudinal Goal Hypothesis 方案；goal inferred/strengthened/changes behavior、future branch 更新仍缺真实长期证据。

## Memory / Candidate / Evidence

1. [Memory Boundary](memory/phase2b-memory-boundary-architecture.md#1a-architecture-review-result)：raw context、candidate、accepted memory、retrieval projection 不同。
2. [Memory v0.1](memory/memory-architecture-boundary-v0.1.md#1d-memory-relationship-model)：derived_from/supported_by/supersedes/conflicts_with/refines/related_to；关联不是证明。
3. [Fixtures](memory/memory-architecture-test-fixtures.md#architecture-expectations)：atomic claim、scope hypothesis、显式/推断 provenance 和 rejected candidate。
4. [Source/Evidence closure](../current/evidence/sqlite-source-evidence-closure.md#5-evidencereference-bridge)：已有 source graph/EvidenceReference，不自动生成 Memory。
5. [Context/KV §7](context/runtime-web-context-kv-feasibility.md#7-web-evidence-and-memory-weight)：recurrence、correction、cross-session persistence、successful reuse 与外部证据的权重信号。

Memory 文件两份不是可安全合并的重复：一份保留 intake/debate，另一份保留 state/facet/relationship/validity。
§1A–1E 的 reviewed abstraction 优先于旧 tier-first 文字；这些是研究 proposal，不是新冻结 schema。

## Episode / Experience

1. [Memory Boundary 的 Experience debate](memory/phase2b-memory-boundary-architecture.md#challenge-does-experience-duplicate-memory)：experience 先作为 evidence packet，避免盲目新增 durable store。
2. [Memory v0.1](memory/memory-architecture-boundary-v0.1.md#1b-current-core-abstraction)：episodic 是 facet，failure lesson/decision可共享同一证据来源。
3. [DS14B root-cause](../historical/phase2a/phase2a-vllm-root-cause-analysis.md)：真实失败→层级假设→artifact/Qwen control→有边界的决定；适合未来 experience case，不能重跑为本轮任务。
4. [Harness lifecycle audit](../archive/harness/harness-feasibility-20260912.md#deeper-app-server-lifecycle-audit) 与
   [raw trajectory contract](../archive/harness/harness-feasibility-20260912.md#harness-event-normalizer--uaea-trajectory-contract)：pre-turn/raw/post-turn hook 是未来 intake 来源，不是 evaluator 已实现。
5. [本次真实404/投影证据](../current/architecture/boundary-integrity-audit-20261002.md#证据与判定)：区分 execution failure、semantic transformation failure 与模型自行补全。

仍无独立已冻结的 Episode segmentation/Experience evaluation 文档；本轮只标出思想来源，不补写架构。

## Context / Working Memory / Association

1. [Harness Context Runtime vs UAEA Context Semantics](../archive/harness/harness-feasibility-20260912.md#harness-context-runtime-vs-uaea-context-semantics)：HOW context is carried 与 WHAT matters 分开，含真实 history pollution。
2. [Context/KV §§5–7](context/runtime-web-context-kv-feasibility.md#5-context-construction-risk)：bounded projection 与 noisy/stale evidence 风险；旧8-turn ContextManager不是当前Harness context policy。
3. [v0.1 relationship/activation](memory/memory-architecture-boundary-v0.1.md#1d-memory-relationship-model)：related_to/refines/instance_of 和 dormant/reactivated 是关联检索思想，不是 associative retrieval 已实现。
4. [100-turn fixture](memory/memory-architecture-test-fixtures.md#fixture-coverage)：混合topic、noise、unresolved issue、supersession，可作为未来选择上下文的验证来源。

旧文档中的 working_context 是当时避免混淆 durable Memory 的命名，不禁止未来独立 Working Memory 研究。
完整历史不等于合适 working set；目前不能把有限 reference token 识别当成“第一个方向”的通用对象绑定。

## Meta-cognition / L0 / Future Branch

[Harness ownership audit](../archive/harness/harness-feasibility-20260912.md#harness-capability-ownership-audit) 保留 UAEA meta-cognition/L0 归属；
[旧项目 vision](../archive/harness/readme-before-boundary-audit-20261002.md#1-project-vision) 保留 observation/trace→evolution 的动机。
Phase-1 L0 benchmark 是既有路由/能力验证，不是通用 L0 meta-cognitive module 的实现证明。
现有 docs 只有 principle/hook/evidence 来源，没有成熟 future-branch hypothesis update 方案；不得凭关键词补造研究结论。

## 只保留思想，不恢复 implementation

| 材料 | 可继承 | 已 superseded 的接线 |
| --- | --- | --- |
| Memory Boundary / v0.1 | authority、candidate policy、identity/validity | 旧 Phase-1 generic lifecycle / planner hierarchy作为现行执行权威 |
| Runtime Web/Context/KV rehearsal | raw/projection/evidence/weight | W0–W4、WebShell→Agent.handle 主路径 |
| Inference trace note | inference metadata与semantic observation分层 | 旧 ModelClient 作为当前 Harness 调用主路径 |
| Pre-Harness / old README | freeze历史、Core research归属 | 双执行栈、LMF/vLLM双主验证路径 |

当前 execution/hook 以 [Harness baseline](../current/runtime/harness-runtime-baseline-20260926.md) 为准；
新增 cognition 要从这些真实边界读取证据，不以文档治理授权实现。
