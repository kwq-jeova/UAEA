# UAEA Documentation Guide

Status: CURRENT
Role: 文档树唯一总导航
Governance reviewed: 2026-10-02
Status updated: 2026-10-05（整理与上传；最新 authority 人工测试未进行）

## 五分钟阅读路径

1. [项目 README](../README.md)：当前目标、物理边界、主入口与 ownership。
2. [Harness Runtime Baseline](current/runtime/harness-runtime-baseline-20260926.md)：generic runtime 已 CLOSED；不需要 Core fork。
3. [当前信息边界 Checkpoint](current/architecture/cognition-boundary-checkpoint-20261005.md)：最新 ownership、阶段状态、证据等级与停止点；authority 人工 NOT TESTED。
4. [Web 私有环境](current/environment/web-runtime-environment.md)：当前启动命令、proxy/credential isolation。
5. [Research Foundation Map](research/research-foundation-map.md)：Goal/Memory/Episode/Context 思想血缘与缺失证据。

这条路径足以分清：已冻结的执行基线、已接入的有限 semantic bridge、尚未实现的 cognition。
不把某篇文档的 Phase、日期、标题里的 baseline 或旧测试 PASS 当作现行 architecture authority。

## Current Architecture

Harness owns thread/turn lifecycle、model invocation、context transport/compaction、native File/Shell/Sandbox 和 generic tool lifecycle。
UAEA owns capability contracts、semantic ownership/scope/effective state、bounded projection/validation 与 evidence/provenance。

当前阶段状态与信息边界：[2026-10-05 checkpoint](current/architecture/cognition-boundary-checkpoint-20261005.md)。
[2026-10-02 Boundary Audit](current/architecture/boundary-integrity-audit-20261002.md) 保留此前具体缺陷、修复和仍有效的 contract，后续状态由 checkpoint 更新。
有限 relation/extraction 不等于长期 Goal inference；ActiveGoal anchor 仍保留但未在 bridge 激活。
本轮只整理已有实现/决定并保存，不增加新的 architecture decision，不恢复旧 Agent execution loop。

## Runtime Baseline

- [Harness baseline](current/runtime/harness-runtime-baseline-20260926.md)：本地 app-server、native sandbox、事件/hook、trajectory contract。
- [当前环境与人工入口](current/environment/web-runtime-environment.md)：私有 env 与统一 wrapper。
- [失败 attempt 隔离与恢复](implementation/harness/failed-attempt-recovery-20261003.md)：原始 history 保留，provider-facing 副本投影；同 thread 重启恢复证据。
- 物理边界：RTX 5090 D v2 / 24GB / single GPU / Qwen2.5-14B-Instruct-AWQ / 4-bit AWQ / vLLM。
- frozen `8001` 不改；既有 `8002` 人工 profile 为 32768 / 0.75 / Hermes。旧 DS14B、16384、8192 的文档是实验记录，不替代此入口。

## Semantic Control Plane

[Boundary Matrix](current/architecture/boundary-integrity-audit-20261002.md#boundary-matrix) 和
[ownership freeze](current/runtime/harness-runtime-baseline-20260926.md#ownership-freeze) 是现行边界。
语义提取、task owner、scope、effective state、ProjectionRecord、Execution/SemanticObservation、授权校验已有薄 bridge；
shadow audit/terminal snapshot 已经人工补验；独立 promotion basis 与 interpretation/constraint 分离已实现，尚未人工验收。
当前 authority surface 只覆盖既有 Web directive contract；source preference 不再自动进入 authoritative constraints。
不等于 Goal Hypothesis/Memory/Episode 实现。

## Current Capability Baselines

- Web：Google 通过 SerpApi backend 已实现；provider/fallback、execution/evidence 和 bounded identity 见 [当前 audit](current/architecture/boundary-integrity-audit-20261002.md)。
- Web baseline 仍 PARTIAL：已有真实 Google search / fetch 成功证据，但自然查询、拒绝恢复、相关度及最终回答遵循事实不能统一宣称 CLOSED；最新 authority 下行为尚待人工验收。
- [SQLite Source/Evidence closure](current/evidence/sqlite-source-evidence-closure.md)：source identity/graph、EvidenceReference 已有；SQLite 不是 Memory Store。
- 网络故障维护见 [observability note](implementation/web/web-network-observability-phase1.md)，不是新的 provider 设计。

## Research Foundations

[研究索引](research/README.md) 与 [Foundation Map](research/research-foundation-map.md) 按思想问题组织，优先保留：
context != memory、object/state/facet、candidate/provenance/policy、association/validity、failure experience、长期证据权重。
研究草案有旧 runtime 假设，读取概念不能直接恢复其 implementation wiring。
没有单独完整 Goal Hypothesis 或 Episode acceptance 方案，不能把现有文档补写成“已经解决”。

## Historical Architecture

[历史索引](historical/README.md) 串联 Phase-1 freeze、Phase-2A artifact/LMF/vLLM 试验、Phase-2B 概念、H2/H3 与 Web backend 接入。
同一 Phase 可以同时有 CURRENT、RESEARCH、HISTORICAL 和 SUPERSEDED 文件；phase identity 与 document validity 分离。
历史失败假设、测试计数、旧环境版本、当时下一步均保留，不自动成为当前待办。

## Implementation Notes

[维护索引](implementation/README.md)：inference trace、stdlib SQLite 环境、实际 Web 请求诊断。
接口说明只覆盖各自层；不能将旧 ModelBackend trace 与 App Server trajectory 合并成一个权威数据源。

## Archived Material

[归档索引](archive/README.md)：原 probe/失败证据/README snapshot 与被替代设计。
archive 表示不处于当前实施主线，不表示内容全部错误；研究地图可直接引用归档中的有效思想。
不删除证据，当前无人授权按“过期”丢弃独有正文。

## 文档状态与来源规则

| 类别 | 含义 |
| --- | --- |
| CURRENT_BASELINE | 决定当前 architecture/runtime/capability contract；历史段落另标 |
| RESEARCH_FOUNDATION | 后续认知研究基础；不以“未实现”归档 |
| HISTORICAL_EVIDENCE | 某时点实验/决定发生了什么；不指导当前启动 |
| SUPERSEDED_DESIGN | 实施方案被替代；顶部给 current reference，全文保留 |
| IMPLEMENTATION_NOTE | 局部维护/接口/命令，不提升为 architecture authority |
| DUPLICATE / MERGE_CANDIDATE | 需先确认独有证据；本轮无此判定 |
| OBSOLETE / SAFE_TO_ARCHIVE | 需满足无独有证据/研究价值等条件；本轮无此判定 |
| REDIRECT | 原路径兼容页，不是第二份正文或第二个 authority |

顶层旧文件和 `phase2b-memory/` 入口只做 redirect，canonical 正文在分类目录。
完整逐份分类、迁移清单、conflicts 和 unresolved research 见 [治理审计](document-governance-audit-20261002.md)。
治理日期不等于重新验证全部历史模型、环境、外链或运行 artifact。
