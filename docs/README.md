# UAEA Documentation Guide

Status: CURRENT
Role: 文档树唯一总导航
Governance reviewed: 2026-10-02
Status updated: 2026-11-13（研究归档与进度同步；不改变冻结契约）

## 五分钟阅读路径

1. [项目 README](../README.md)：当前目标、物理边界、主入口与 ownership。
2. [Harness Runtime Baseline](current/runtime/harness-runtime-baseline-20260926.md)：generic runtime 已 CLOSED；不需要 Core fork。
3. [当前进度](current/README.md)与[Goal三场景报告](research/goal-continuity-three-scenarios-20261113.md)：最新研究等级、反例和停止点；[信息边界 Checkpoint](current/architecture/cognition-boundary-checkpoint-20261005.md)保留冻结契约和当时验证。
4. [Web 私有环境](current/environment/web-runtime-environment.md)：当前启动命令、proxy/credential isolation。
5. [Research Foundation Map](research/research-foundation-map.md)：Goal/Memory/Episode/Context 思想血缘与缺失证据。

这条路径足以分清：已冻结的执行基线、已接入的有限 semantic bridge、隔离 Goal 研究与未证实的长期认知收益。
不把某篇文档的 Phase、日期、标题里的 baseline 或旧测试 PASS 当作现行 architecture authority。

## Current Architecture

Harness owns thread/turn lifecycle、model invocation、context transport/compaction、native File/Shell/Sandbox 和 generic tool lifecycle。
UAEA owns capability contracts、semantic ownership/scope/effective state、bounded projection/validation 与 evidence/provenance。

最新研究状态见[2026-11-13联合研究](research/goal-continuity-three-scenarios-20261113.md)；正式信息边界仍参考[2026-10-05 checkpoint](current/architecture/cognition-boundary-checkpoint-20261005.md)，其旧待验项不是本轮进度。
[2026-10-02 Boundary Audit](current/architecture/boundary-integrity-audit-20261002.md) 保留此前具体缺陷、修复和仍有效的 contract，后续状态由 checkpoint 更新。
有限 relation/extraction 不等于长期 Goal inference；Goal Sideband 与 Continuity 仅为非权威研究入口，ActiveGoal 不自动采纳。
本轮只归档已有修复、研究与证据，不增加架构决定，不恢复旧 Agent execution loop。

## Runtime Baseline

- [2026-10-22 Harness 版本升级](current/runtime/harness-upgrade-20261022.md)：默认 v0.163.0；保留 v0.154.0，双版本源码、构建、真实运行和回退证据。
- [Harness baseline](current/runtime/harness-runtime-baseline-20260926.md)：本地 app-server、native sandbox、事件/hook、trajectory contract。
- [当前环境与人工入口](current/environment/web-runtime-environment.md)：私有 env 与统一 wrapper。
- [失败 attempt 隔离与恢复](implementation/harness/failed-attempt-recovery-20261003.md)：原始 history 保留，provider-facing 副本投影；同 thread 重启恢复证据。
- 历史5090D入口：RTX 5090 D v2 /24GB/Qwen2.5-14B-AWQ；保留原配置。
- 当前N1X隔离研究：56/72 UMA、Bolt74B/vLLM0.32.0、64K/1GiB/单并发/util0.65、Codex0.163.0；保留32K回退与原保护，不等于全入口默认切换。
- frozen `8001` 不改；既有 `8002` 人工 profile 为 32768 / 0.75 / Hermes。旧 DS14B、16384、8192 的文档是实验记录，不替代此入口。

## Semantic Control Plane

[Boundary Matrix](current/architecture/boundary-integrity-audit-20261002.md#boundary-matrix) 和
[ownership freeze](current/runtime/harness-runtime-baseline-20260926.md#ownership-freeze) 是现行边界。
语义提取、task owner、scope、effective state、ProjectionRecord、Execution/SemanticObservation、授权校验已有薄 bridge；
shadow audit/terminal snapshot 已经人工补验；独立 promotion basis 与 interpretation/constraint 分离已实现，尚未人工验收。
当前 authority surface 只覆盖既有 Web directive contract；source preference 不再自动进入 authoritative constraints。
以上人工待验为历史记录；Goal Hypothesis 有隔离研究实现，不代表自动采纳或 Memory/Episode 已接入。

## Current Capability Baselines

- Web：Google 通过 SerpApi backend 已实现；provider/fallback、execution/evidence 和 bounded identity 见 [当前 audit](current/architecture/boundary-integrity-audit-20261002.md)。
- Web baseline 仍 PARTIAL：已有真实 Google search / fetch 成功证据，但自然查询、拒绝恢复、相关度及最终回答遵循事实不能统一宣称 CLOSED；最新 authority 下行为尚待人工验收。
- [SQLite Source/Evidence closure](current/evidence/sqlite-source-evidence-closure.md)：source identity/graph、EvidenceReference 已有；SQLite 不是 Memory Store。
- 网络故障维护见 [observability note](implementation/web/web-network-observability-phase1.md)，不是新的 provider 设计。

## Research Foundations

[研究索引](research/README.md) 与 [Foundation Map](research/research-foundation-map.md) 按思想问题组织，优先保留：
context != memory、object/state/facet、candidate/provenance/policy、association/validity、failure experience、长期证据权重。
研究草案有旧 runtime 假设，读取概念不能直接恢复其 implementation wiring。
Goal Hypothesis 已有隔离Sideband/Continuity及M2限定证据；M3仍PARTIAL，M4/M5 UNKNOWN。Memory保持Research Reserved，正式Goal/Memory采纳及Episode acceptance不能写成“已经解决”。

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

N1X历史正式32K配置见[32K + Hermes运行基线](current/runtime/n1x-runtime-baseline-20261027.md)；当前64K隔离研究与56/72资源证据见[Phase1报告](research/phase1-finance64-continuity-20261112.md)。未统一修改正式默认配置。


## 2026-11-13 Git阶段同步

[检查点及可复核证据摘要](implementation/checkpoints/goal-research-checkpoint-20261113.md)记录此次归档范围和CPU回归。Commit/Push仅同步已有成果，不授权新模型实验、正式采纳或配置切换。
