# Rejection Recovery Observation

Status: IMPLEMENTATION_NOTE
Reviewed: 2026-10-04
Role: 恢复投影修正及窄范围 acceptance，不改 authorization 或 semantic ownership

## 目标与职责

A rejected attempt must preserve the surviving constraints and expose a legal recovery path.
失败 attempt 仍是不可重放的历史事实；可重试是提出新的 action，不是重新激活旧 invocation。

```text
Runtime factual result
  -> normalized recovery observation
  -> bounded dynamic tool response
  -> provider-safe history observation
  -> model proposes a new action
  -> existing current-policy validation
```

Harness 继续承担 thread/history/执行生命周期；UAEA 只补恢复信息的 projection。
不修改 Google/SerpApi/proxy/20s timeout、Codex Core、semantic ownership/scope/effective state、
模型/量化/32K profile、frozen `8001`，不放宽任何授权规则。

## 最小 contract

`harness/recovery_observation.py` 提供一个纯 projection builder，schema 为
`uaea.recovery_observation.v1`。即时工具响应与历史投影复用它：

- reason 与 retryable。
- constraints_known、完整 active_constraints 和 effective_state_id。
- authorization state、source item/source turn、model proposal；unknown 不变成 granted。
- typed legal_next_steps，不包含实际 dispatch 或完整历史重放。
- policy_time 为 at_attempt；下一 attempt 必须重新检查当前 policy。
- interaction_failure_grants_authorization=false。

对于 Web semantic rejection，snapshot 已有 provider constraint 且授权 unknown 时：
可提出保持 provider、不降级的 `allow_fallback=false` 新 action；或正常对话请求授权并等待
后续用户输入。不能提出未经授权的 `allow_fallback=true`。
有合法 granted policy 时可以提供 fallback 选项，但历史 grant 不能覆盖后来的 revoke。
source/language 等其它约束完整保留，不将它们推断为 provider policy。

builder 不更改用户 policy、不修改原 proposal、不启动 planner、不执行请求，也不赋予新权限。
argument_updates 只描述下一次 proposal 的选项，仍经原有 validator/Capability Boundary。

缺少 context 时标明 constraints_known=false；不能将信息缺失解释成无约束。
`request_user_input is unavailable in Default mode` 映射为终结 interaction failure：
普通对话询问、等待真实 user reply，不自行默认同意，也不反复重放不可用 invocation。

## 两层投影

`HarnessToolDispatch.to_app_server_response()` 将当前 action validation 的约束/授权 snapshot
补进恢复投影，包括先通过 authority、后被 Web schema 拒绝的情况。原始 ToolResult/trace 不改。
预算不足时先压缩诊断及重复 metadata；完整 normalized recovery 必须保留，不能裁掉 hard constraints。
实在无法容纳时明确 projection error，不输出看似完整的残缺 recovery contract。
投影异常也纳入已有 REPL containment：返回 result_projection_failed，不终止整个对话。
若工具此前已成功执行，继续保留 execution_succeeded/actual_provider；不能把响应投影失败伪装为未执行。

`provider_history.py` 保持 REJECTED/FAILED/CANCELLED 隔离：发送副本中旧 call/result 仍为普通
assistant historical observation，保留 failure/recovery，不变成 active FunctionCall。
原始 rollout、raw events、canonical trajectory 仍完整保留；sequence/identity 不变。

## 实证结果与限制

原始失败 run：`D:\UAEA-runtime\h3-results\interactive-32768-20261003-043912`。
其三次 Web proposal 均在执行前被拒绝；不是 Google HTTP 失败。

使用现有人工入口自动复放相同两句自然语言输入：

```text
D:\UAEA-runtime\h3-results\interactive-32768-20261004-115740
```

两轮均 completed，但模型仅承诺搜索，没有实际 tool call；没有产生 rejection，不能拿来证明
recovery 成功。这说明自然语言 action initiation 仍不稳定，不标为完整 Web acceptance PASS。

确定性 rejection probe：

```bash
cd /mnt/d/UAEA
python3 -B scripts/h3_web_rejection_recovery_probe.py
```

artifact：`D:\UAEA-runtime\h3-results\web-rejection-recovery-20261004-120238`。
只用 provider fixture 注入一次 `provider=google, allow_fallback=true`，用户未授予 fallback；
Runtime 拒绝，原失败保留、http_attempted=false、authorization=unknown。
后续 proposal 与最终回复完全由真实本地 Qwen 生成，不由 fixture 提供成功 call，不替模型改参数。

Qwen 随后自主提出 `provider=google, allow_fallback=false`，原 validator 接受，实际 Google/SerpApi
执行成功：requested_provider=google、actual_provider=google、acquisition_backend=serpapi、
http_attempted=true、execution_succeeded=true、fallback_occurred=false、turn/completed。
无 provider HTTP 400，无 secret 泄露。诊断只限制输出为 384 tokens/request，不改变 context/GPU profile。

恢复路径 PASS 不代表自然语言行为全正确：模型把“尚未授权 fallback”口头说成“用户不允许”，
但 runtime state 仍为 unknown；并没有被模型改成 denied 或 granted。
这种表述质量与未发起工具调用，保留为人工复测风险，不通过修改授权规则解决。

同时重新执行 failed-attempt recovery：
`D:\UAEA-runtime\h3-results\failed-attempt-recovery-20261004-120428`，同一 thread 的四轮 completed，
包括 malformed refusal、普通对话、合法 File 和重启/resume；HTTP 400 为 0，canonical validation PASS。

## 最终回归

- targeted regression 156/156、full unittest 285/285、Phase-1 scripted benchmark 24/24。
- 覆盖 unknown/denied/granted、已撤销 grant 不被历史 recovery 恢复、交互不可用必须等待用户，
  两层投影一致性、预算不足不裁 hard constraints、projection failure 不退出 REPL或伪造 execution fact。
- 七个修改 Python 文件 `py_compile`、`git diff --check`、新增导航本地链接检查通过。
- 实际环境 key 只在内存用于扫描，295 个相关源码/artifact/私有 Harness home 文件及 git diff
  未发现 key 泄露；不输出 key。四个 canonical trajectory 均通过 reader/validator。
- 诊断进程正常停止，8002 已释放；frozen 8001 未启动、未修改。

## 停止点

Recovery contract 和真实 rejection -> legal HTTP 执行分别 PASS。
自然语言 Web acceptance 仍 PARTIAL；不声称搜索质量、来源约束或 search -> fetch 均已 CLOSED。
人工入口不变：

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

自然地请求 Google 搜索并要求返回实际找到的链接，不显式指定工具名称。
检查新 run 是否出现真正的 Web execution，而不是只有“正在搜索”的 agent message；
若被拒绝，检查 surviving constraints、authorization、legal_next_steps 及随后的独立新 call。
不自动进入 Goal/Memory 或 Web provider redesign。
