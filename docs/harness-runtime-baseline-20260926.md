# UAEA Harness Runtime Baseline

日期：2026-09-26

本文件记录当前 UAEA × Codex Harness 集成的冻结判断。它是当前版本的
现行入口；完整的阶段性审计、probe 过程和历史决策保留在
`docs/archive/harness/`，不删除、不重写。

## Baseline Verdict

```text
Harness Runtime Baseline: READY TO FREEZE
Harness integration work: STOP
Codex Core fork: NO
```

当前结论是 generic Harness runtime 已经足以作为 UAEA 后续
Goal / Memory / Episode 研究的执行边界。后续问题不再默认通过扩建
Harness 解决。

## 已闭环范围

### Local Runtime And Model Plane

```text
source-owned Codex app-server
  -> local Responses transport
  -> local vLLM
  -> Qwen2.5-14B-Instruct-AWQ
```

Harness 以本地进程运行。H3 diagnostic 路径使用本地 vLLM `8002`；
冻结的 Phase-2 endpoint `8001` 未被修改。当前物理边界仍然是：

```text
Windows 11
WSL2 Ubuntu 24.04.x
NVIDIA RTX 5090 D v2
24 GB VRAM
single GPU
Qwen2.5-14B-Instruct-AWQ
4-bit / AWQ
vLLM
```

### I/O And Lifecycle

已验证的 App Server 外层输入包括：

```text
thread/start
turn/start
turn/start.additionalContext
dynamicTools
model/provider
sandbox / approval policy
```

已验证的事件包括：

```text
thread / turn lifecycle
user message
agent message
dynamic tool call/result
commandExecution
token usage
error / cancellation
contextCompaction occurrence
turn/completed
```

`turn/start.additionalContext` 可作为稳定的 pre-turn application context
入口。`turn/completed` 可作为 UAEA 外层 post-turn trigger。

### Tool And Capability Boundary

动态工具路径已经闭环：

```text
Harness dynamic tool call
  -> HarnessDynamicToolAdapter
  -> UAEA ToolRegistry / Capability
  -> bounded ToolResult
  -> Harness continuation
  -> turn/completed
```

已验证或纳入现有 contract 的 capability 包括：

```text
mock.external_operation
document.read_section
fs.list
web.search
web.fetch
```

Harness-native command/file 路径也已验证。source-owned Codex 使用 bundled
`codex-resources/bwrap` 创建 read-only sandbox，模型可通过
`commandExecution` 读取 `README.md`，获得结果后继续回答并完成 turn。

### Trajectory

当前 trajectory infrastructure 已闭环：

```text
App Server raw events
  -> HarnessEventNormalizer
  -> UAEA TrajectoryEvent
  -> HarnessTrajectoryWriter
  -> canonical run-level JSONL
  -> HarnessTrajectoryReader / validator
  -> per-turn reconstruction / thread projection
```

canonical 文件格式：

```text
<run_id>.trajectory.jsonl
```

thread 文件只是 derived projection，不是第二个权威数据源。事件保留
Harness native identity、UAEA 接收顺序、provenance 和 raw event reference。

真实 H3 artifact 已验证：

```text
JSONL readable: PASS
sequence monotonic: PASS
identity preservation: PASS
turn reconstruction: PASS
thread projection consistency: PASS
native command failure preservation: PASS
```

### Runtime Facts And Web Contract

UAEA 当前只向 Harness 投影最小 runtime facts 和 effective capability state：

```text
model/provider
Harness native filesystem/shell policy
shell network restriction
UAEA dynamic web.search/web.fetch availability
```

Harness 负责承载 context、thread history、token window、compaction 和
generic execution；UAEA 负责 capability-specific semantics。

Web semantic boundary 已冻结到当前研究所需的最小范围：

```text
web.search input:
  provider
  allow_fallback
```

执行结果单独记录：

```text
requested_provider
actual_provider
fallback_occurred
fallback_reason
```

显式 provider 且缺少 `allow_fallback` 时 fail-closed，不静默降级。搜索结果
同时区分 raw provenance、candidate evidence 和 citable evidence。低相关
结果保留在 raw trajectory/source history，但不作为 model-visible citable
evidence。

## Ownership Freeze

Harness owns：

```text
thread persistence
turn lifecycle
context transport
token window
compaction mechanics
native file/shell/sandbox execution
generic tool protocol
retry / continuation / execution lifecycle
raw event emission
```

UAEA owns：

```text
capability-specific semantic contracts
Runtime Facts / Effective Capability State
Web provider/fallback/evidence semantics
trajectory normalization and provenance preservation
Goal Hypothesis
Problem Space / Boundary
Working Memory
Memory and Evidence interpretation
Experience / Episode evaluation
training trajectory and LoRA research
```

UAEA -> Harness boundary：

```text
additionalContext
dynamicTools
model/provider selection
sandbox / execution policy inputs
bounded capability results
```

Harness -> UAEA boundary：

```text
ordered App Server events
tool calls/results
native command execution state
token usage
compaction markers
errors/cancellation
turn/completed
canonical raw trajectory
```

## Residual Risks

以下问题已被确认，但不阻止 generic Harness baseline freeze：

```text
full thread history may pollute later turns
compaction internal input/output details are only partially exposed
modelContextWindow may differ from configured 32768
model may overgeneralize shell network restrictions
model may cite URLs outside returned citable_results
Google provider is not implemented
provider/domain/source constraints remain partly best-effort
system PATH may still warn about bubblewrap although bundled bwrap works
```

这些问题分别属于 UAEA future cognition/evidence work、provider capability
limitation 或环境残留风险，不构成 generic Harness lifecycle blocker。

## 后续边界

当前不继续扩展：

```text
Goal Engine
Memory Manager
Working Memory implementation
Web provider redesign
Codex Core fork
新的 generic Runtime subsystem
```

下一阶段应进入 UAEA-owned：

```text
Goal Hypothesis
Problem Boundary
Epistemic Update
Memory / Episode architecture
trajectory evaluation
```

只有出现以下架构级事实时才重新打开 Harness 集成：

```text
缺失稳定的 pre-turn lifecycle hook
关键 tool/result/error/compaction state 无法观察
无法重建 thread/turn/item identity 或事件顺序
tool result 后无法恢复 model continuation
当前 pinned runtime 无法可靠执行 native sandbox
generic runtime capability 确实无法由 App Server 提供
```

## 历史文档

完整研究过程和旧阶段结论保留在：

```text
docs/archive/harness/harness-feasibility-20260912.md
docs/archive/harness/pre-harness-freeze-20260912.md
```

H3 diagnostic scripts、trajectory implementation 和测试继续保留在当前
源码路径，用于复现和回归，不作为新的 Harness 扩建计划。
