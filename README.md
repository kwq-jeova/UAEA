# UAEA

UAEA（Unified Autonomous Evolution Architecture）研究如何通过持续交互理解用户方向、修正认知，并改善未来决策。现有主路径为 **冻结的 Phase-1 语义契约 + Harness 执行基础设施 + 隔离的 Goal Hypothesis 研究**。

Harness 拥有 Agent Loop、工具执行与 Turn 生命周期；UAEA 维护来源、版本、候选状态和授权边界。坚持 **LLM proposes / Runtime validates**：来源合法、调用保存成功不等于语义正确，Retention 不等于 Adoption。

## 当前进度：2026-11-13

最新[三场景联合报告](docs/research/goal-continuity-three-scenarios-20261113.md)及独立审计总体 **PARTIAL**：

| 研究里程碑 | 当前结论 |
|---|---|
| 用户意图归属 M1 | PARTIAL；User Goal 与模型待办分离，受委托局部问题和持续目的仍有歧义 |
| 受反馈纠正 M2 | 限定存在性 VERIFIED：真实跨会话 revise、合法 CURRENT、Host 保存及新 head 送达；抽象冗余仍 PARTIAL |
| 后续连续性 M3 | PARTIAL；A 新 head 未由独立 B/C 继承，不拼接为新行为闭环 |
| 自主 Goal 生命周期 M4 | UNKNOWN；显式纠正成功不等于自主维护 |
| 超过 Relevant History 的决策价值 M5 | UNKNOWN；两对结构化 Goal View ON/OFF 质量和成本混合 |
| Goal Continuity 工程 | 隔离 Journal 持久化/恢复、不可变版本及 Scope 有限定证据；人工 Global family 绑定不计模型自主能力 |
| Memory | Research Reserved；不开放 Memory Admission |

本轮三场景：A 忠实核心修订并保存，B 结束 Intel 局部 Task 而保持长期 Goal，C 尚未证明结构化视图改善实际决策。12 个模型响应完整、13 次读取身份正确，不等于认知全部通过；保留金融指标、单位、时间错误和一个最终质量删失样本。

候选仍是 opt-in、非权威、可撤销解释，不能自动成为 ActiveGoal、可信 Memory 或执行授权。没有新增 Goal Engine、第二套 Agent Loop 或通用语义裁判。

### 当前 N1X 研究配置

| 配置 | 已验证的隔离研究入口 |
|---|---|
| UMA | GPU 56 GiB / Host 72 GiB |
| Backend | Nemotron Bolt 74B，vLLM 0.32.0 |
| Harness | Codex rust-v0.163.0 |
| Context / KV / 并发 | 64K / 固定 1 GiB / 1 |
| GPU utilization | 0.65，仅该隔离入口 |
| 安全 | 原 Windows/WSL/AC、单时钟遥测与 Fail-Closed；不降低阈值 |

这不是将所有正式入口切为64K或0.65。32K及64/64原启动配置仍保留；[历史32K运行基线](docs/current/runtime/n1x-runtime-baseline-20261027.md)不代表最新研究负载。容量、长期会话与资源证据见[Phase1 64K连续研究](docs/research/phase1-finance64-continuity-20261112.md)、[UMA限定负载](docs/research/uma56-controlled-load-20261111.md)。

## 阅读与研究入口

- [文档总导航](docs/README.md)与[当前进度](docs/current/README.md)：先区分冻结契约、研究机制和历史结论。
- [研究索引](docs/research/README.md)、[研究地图](docs/research/research-foundation-map.md)：保留正面、负面及 UNKNOWN，不按旧文档中的“下一步”自动执行。
- [Goal 连续性使用方法](scripts/research/README-goal-continuity.md)：本地研究 Journal 是单一候选 authority；不恢复旧 Workflow 为新执行。
- [Goal Sideband 研究通道](scripts/research/README-goal-hypothesis.md)：工具提案、Host 接受、保存、投影和认知判断分别评价。
- [本次 Git 检查点与证据范围](docs/implementation/checkpoints/goal-research-checkpoint-20261113.md)：代码、轻量回归、外部原始证据和已知限制。

原始研究记录保存在仓库外 research-records，Windows 评审包保存在 UAEA_DOCS。仓库提交源码、固定场景、报告及摘要/哈希，不包含模型权重、凭据、Native SQLite 或完整会话日志；外部原始证据路径不保证在新 clone 上存在。

## 保留的执行与权威边界

以下冻结职责继续有效；历史人工环境的具体参数另有日期，不将其解释为最新研究配置。Phase-1 不因本轮 Git 同步而变更。

## 当前架构与职责

```text
User
  -> UAEA semantic extraction / scoped effective state
  -> bounded pre-turn additionalContext
  -> source-owned local Codex app-server (rust-v0.163.0; v0.154.0 retained)
  -> UAEA local provider-safe history projection
  -> replaceable model Backend / local vLLM
  -> model action proposal
  -> UAEA semantic validation / ToolRegistry capability boundary
  -> execution observation / bounded actionable evidence
  -> Harness continuation / turn completion
  -> raw events / semantic diagnostic snapshots
```

**Harness Runtime Baseline: CLOSED**。**Codex Core fork: NOT REQUIRED**。

| Harness owns | UAEA owns |
| --- | --- |
| thread persistence / turn lifecycle / model invocation | capability-specific semantic contracts |
| generic context transport / token window / compaction mechanics | semantic extraction / classification / ownership / scope |
| native File / Shell / Sandbox | effective semantic state / bounded semantic projection |
| generic tool lifecycle / continuation | 独立 promotion basis / semantic authority / action validation |
| raw runtime event emission | evidence semantics / provenance / trajectory normalization |
| generic execution mechanics | future Goal / Memory / Episode cognition |

UAEA → Harness：typed `additionalContext`、dynamic tool schema、经过语义校验的 capability result。
Harness → UAEA：有序 thread/turn/item events、tool result、command execution、token usage、错误及 terminal boundary。
执行事实以结构化 result 为准；requested provider、actual provider 和 successful execution 不可互相替代。

## 历史 5090D 人工入口与保留配置

```text
RTX 5090 D v2
24GB VRAM
single GPU
Qwen2.5-14B-Instruct-AWQ
4-bit / AWQ
vLLM
```

冻结的 `8001` 保持原配置。当前人工 Harness 使用既有 `8002` diagnostic profile：
`max_model_len=32768`、`gpu_memory_utilization=0.75`、Codex `model_context_window=32768`、
`--enable-auto-tool-choice --tool-call-parser hermes`。实际 effective window 可能由 Harness 再折算，不改实验条件。

在已配置的 WSL 中：

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

`python3 scripts/harness_version.py --verify-binary` 查询实际锁定版本；
在启动命令前加 `UAEA_CODEX_VERSION=rust-v0.154.0` 可单次回退，使用独立 `CODEX_HOME`。
默认值只在 `harness/versions.json` 维护；启动 artifact 的 `harness-versions.jsonl` 记录实际 Tag/Commit。

Web 代理和 `SERPAPI_KEY` 自动从仓库外 `~/.config/uaea/web.env` 加载；权限必须为 `600`。
不要将真实 key 写入 repo、命令行或聊天；[私有环境配置](docs/current/environment/web-runtime-environment.md)。
该入口保留停止 app-server/8002 的原逻辑，不启动旧 direct Web REPL。

## Phase-1 Semantic Baseline 的状态

冻结子模块：`runtime/phase1-runtime`，commit `1f311291df027baceca40779643e5107b9eb6fb3`。

- Phase-1 generic runtime mechanics：作为 legacy/A-B baseline 保存；主路径由 Harness 接替。
- Phase-1 semantic architecture：通过 `harness/semantic_state_adapter.py` 复用
  `ContextManager`、`TurnRelationRecord`、`ExecutionObservation`、`SemanticObservation`、
  `RuntimeObjectRecord/Store`、`WorkflowRunRecord` 与 `ProjectionRecord`。
- Workflow/Step records 在 bridge 中提供 task identity/ownership 和行动事实记录，不启动旧 planner 或 execution loop。
- ActiveGoal anchor 代码保留，但当前 Harness bridge 不激活；`ActiveGoal != future longitudinal Goal Hypothesis`。
- 当前有限 relation/extraction surface 不是完整 intent arbitration，也不保证任意多 topic/隐含任务切换。
- Goal Hypothesis Sideband 和本地 Continuity 已在隔离研究入口实现，正式 ActiveGoal 不自动采纳。
- Working Memory / Episode / Experience engine 未接入；Memory Candidate/SQLite source-evidence 资产保留，不等于可信长期记忆已建立。

## Web Semantic / Evidence Boundary

Google semantic provider 已由 SerpApi backend 实现；`serpapi` 只是 acquisition backend，不是 model-facing provider。
Harness/inference 仍在本地，Web 请求是显式外部 capability。

- 输入只有 `provider`、`allow_fallback`，结果分离
  `requested_provider/actual_provider/acquisition_backend/fallback_occurred/fallback_reason`。
- strict `allow_fallback=false` fail-closed；显式 provider 缺少 fallback policy 时不执行。
- 在 semantic bridge 中，模型提出 `allow_fallback=true` 不构成授权：
  只有有效 user-derived scoped policy 可授予；unknown/pending 被拒绝。
  provider 未指定且不显式提出 fallback 的既有默认 policy 保持不变。
- 执行失败不进入 evidence relevance 分类；raw provenance 保留，
  low-relevance links 不作为 model-visible citable evidence。
- bounded result 可减少 snippets、metadata 和候选数量，但保留每个候选的完整 `title/url` 及来源 identity。
  projected citable count 与实际保留列表一致；无法容纳身份时明确报告限制，不输出残缺 URL。
- 来源/语言/时间要求仍是 best-effort，不承诺真实“热度排行”或跨站点访问成功。
- 网络诊断在实际请求进程记录 open/header/read、HTTP/SSL/proxy/timeout 信息；不进入 model-visible projection。
  timeout 仍是 20 秒，不新增 retry。

[Google backend 历史接入记录](docs/historical/web/google-backend-phase1.md) ·
[网络诊断](docs/implementation/web/web-network-observability-phase1.md) ·
[当前边界与剩余风险](docs/current/architecture/boundary-integrity-audit-20261002.md)

## Trajectory 与验证

Normalizer → Writer → canonical run-level JSONL → Reader/validator 的 contract 保持：
`<run_id>.trajectory.jsonl` 是 writer run 的 canonical source；
thread 文件只是 derived projection。sequence 是 UAEA 接收顺序，不是 Harness 内部因果序号。

Lifecycle probe 和当前人工 REPL 均接入 writer；人工 run 保存 `app-server-events.jsonl`、adapter trace、
source history、semantic snapshots 与 canonical normalized trajectory。
未来 cognition 必须优先消费 raw trajectory，不能把 compacted summary 当唯一原始经历。
失败 attempt 事实永久保留；发送给 provider 的副本将明确终结调用投影成不可执行 observation，
不让 malformed history 阻断后续 turn。[隔离边界与同 thread 恢复证据](docs/implementation/harness/failed-attempt-recovery-20261003.md)。
拒绝结果通过 [typed recovery observation](docs/implementation/harness/rejection-recovery-observation-20261004.md)
保留有效约束/授权来源并给出新 attempt 的合法选项；历史 policy 不是未来授权，重试仍经过当前 validator。

```bash
python3 -m unittest tests.test_harness_boundary_integrity tests.test_harness_semantic_state_adapter
python3 -m unittest discover -s tests -t .
python3 runtime/phase1-runtime/tests/runtime_benchmark/phase1_runtime_benchmark.py --mode scripted --level all
```

真实失败 artifact 与只读重放证据见 Boundary Audit。修改后须人工复测真实 search → fetch，
确认模型引用的是 retained candidate，而不是自行补造链接。

## 历史与下一步

历史不删除；[原 README](docs/archive/harness/readme-before-boundary-audit-20261002.md) 保存此前
Phase-1/Phase-2A、LMF 和早期 Harness 的完整描述。
[Harness baseline](docs/current/runtime/harness-runtime-baseline-20260926.md) 保留冻结依据；
[历史索引](docs/archive/harness/README.md) 区分当前结论与阶段记录。
LMF/其它 inference adapter 是保留的研究资产，不是当前 Harness 验证路径。

当前研究保持在 Goal Hypothesis 的语义忠实性、跨会话连续性及实际决策价值验证；下一轮是否扩大研究由阶段评审决定，不因归档或 push 自动开始实验。Memory 数学建模仍 Research Reserved。

冻结权威关系见[信息边界 checkpoint](docs/current/architecture/cognition-boundary-checkpoint-20261005.md)；该历史文档的人工待验状态不代替2026-11-13研究结论。只有现有 Harness 缺少必要执行事实、状态可观察性或投影能力，才重新讨论基础设施；模型语义错误不自动要求新增 Runtime 纠错层。
