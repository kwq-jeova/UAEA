# UAEA

UAEA（Unified Autonomous Evolution Architecture）当前以 **Phase-1 semantic baseline + 本地 Harness Runtime Baseline** 为主路径。
Harness 承担成熟执行基础设施，UAEA 保留语义组织、capability contract 与 evidence/provenance，
后续研究转向 longitudinal cognition，而不是继续扩建通用 Agent Runtime。

文档总入口：[Documentation Guide](docs/README.md)。按当前基线、研究基础、历史证据和维护说明阅读，不按 Phase 名称推断有效性。

当前阶段与停止点：[2026-10-05 信息边界 Checkpoint](docs/current/architecture/cognition-boundary-checkpoint-20261005.md)。
[2026-10-02 Boundary Audit](docs/current/architecture/boundary-integrity-audit-20261002.md) 保留此前修复依据，不能用旧测试或等待状态替代最新结论。
**最新 semantic authority 迭代：实现/自动验证 PASS，人工测试未进行，阶段整体 PARTIAL。**
今天仅整理并保存当前集成 checkpoint，不继续开发，不把模型自然语言行为或完整 Web acceptance 写成 PASS。

## 当前信息边界阶段

| 阶段 | 当前结论 | 下一步 |
| --- | --- | --- |
| Harness Runtime Baseline | CLOSED，保持既有 ownership 与物理边界 | 不继续扩建 generic runtime |
| Failed-attempt / recovery / observation | 恢复与结构边界已有验证；模型行为仍有残余风险 | 保留逐轮证据，不增加错误分类或网络补丁 |
| Semantic Promotion Shadow Audit | 最新人工 run 已验证 audit/terminal snapshot 边界 PASS | 诊断不授予权威 |
| Retained interpretation / execution authority | 实现与自动验证 PASS，人工 NOT TESTED | 等两轮新进程人工 probe |
| Goal Hypothesis / Memory / Episode | 尚未实现新的 cognition engine | 不在本 checkpoint 自动启动 |

当前只把有独立依据的有限 Web directive 投影成 execution constraint；topic/source preference
保留为低权威 interpretation。`strength`、provenance 或投影位置不自动授予权限。
qualified constraint 走 `application`，其余 semantic context 走 `untrusted`；
projection 与 action validation 使用同一 effective view。详见 [阶段实现与人工观察点](docs/implementation/harness/semantic-authority-boundary-20261005.md)。

## 当前架构与职责

```text
User
  -> UAEA semantic extraction / scoped effective state
  -> bounded pre-turn additionalContext
  -> source-owned local Codex app-server (rust-v0.154.0)
  -> UAEA local provider-safe history projection
  -> local vLLM / Qwen2.5-14B-Instruct-AWQ
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

## 物理边界与人工入口

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

Web 代理和 `SERPAPI_KEY` 自动从仓库外 `~/.config/uaea/web.env` 加载；权限必须为 `600`。
不要将真实 key 写入 repo、命令行或聊天；[私有环境配置](docs/current/environment/web-runtime-environment.md)。
该入口保留停止 app-server/8002 的原逻辑，不启动旧 direct Web REPL。

## Phase-1 Semantic Baseline 的状态

冻结子模块：`runtime/phase1-runtime`，commit `1f311291df027baceca40779643e5107b9eb6fb3`。

- Phase-1 generic runtime mechanics：作为 legacy/A-B baseline 保存；主路径由 Harness 接替。
- Phase-1 semantic architecture：通过 `harness/semantic_state_adapter.py` 复用
  `ContextManager`、`TurnRelationRecord`、`ExecutionObservation`、`SemanticObservation`、
  `RuntimeObjectRecord/Store`、`WorkflowRunRecord` 与 `ProjectionRecord`。
- workflow record 在 bridge 中只提供 task identity/ownership，不启动旧 planner、step 或 execution loop。
- ActiveGoal anchor 代码保留，但当前 Harness bridge 不激活；`ActiveGoal != future longitudinal Goal Hypothesis`。
- 当前有限 relation/extraction surface 不是完整 intent arbitration，也不保证任意多 topic/隐含任务切换。
- Goal Hypothesis / Working Memory / Episode / Experience engine：本轮均未实现。
  既有 Memory Candidate/SQLite source-evidence 资产保留，不等于长期认知层已接入。

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

下一研究方向仍是 UAEA Episode / Goal Hypothesis / Working Memory / associative relation；
但当前先等待 retained interpretation / execution authority 的人工结果，不直接启动认知引擎。
信息保留、解释、依据、权威与修订关系的有限阶段状态见 [当前 checkpoint](docs/current/architecture/cognition-boundary-checkpoint-20261005.md)，
思想血缘与未决问题见 [Research Foundation Map](docs/research/research-foundation-map.md)。
只有 missing lifecycle hook、unobservable critical state、impossible context projection
或 generic runtime capability 真正不足，才重新打开 Harness work；不自动开始下一阶段实现。
