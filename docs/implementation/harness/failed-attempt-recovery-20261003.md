# Failed Attempt Isolation / Thread Recovery

Status: IMPLEMENTATION_NOTE
Reviewed: 2026-10-03
Role: 失败事实与 provider-facing history 的局部修复及恢复验收，不引入第二套 execution lifecycle

## 目标与原始故障

核心 invariant：一次非法工具 attempt 可以失败，但不得使整个 thread 无法继续。
历史是证据；模型上下文是对历史的投影。保留失败事实，不意味着再次构造可执行 invocation。

原始人工 artifact：

```text
D:\UAEA-runtime\h3-results\interactive-32768-20261003-033604
```

`app-server-events.jsonl` 中，`call_8894be30bd3833ae` 的 arguments 在 `max_results` 后混入
自然语言和占位链接。Harness 返回 `failed to parse function arguments`，未 dispatch 到
UAEA capability，也未发起 Web HTTP。随后同一 turn 的 continuation、下一轮普通消息和
再下一轮询问错误原因均出现 vLLM HTTP 400：`Expecting value: line 1 column 47 (char 46)`。
这不是 Google 网络、Web timeout 或 context window 超限。

## 实际 root path 与 ownership

审计源码为 pinned `rust-v0.154.0`，commit
`6b9826e3aa83b1a5947db50f4332cb9c65f1b340`，目录 `D:\UAEA-deps\codex\rust-v0.154.0`。

```text
model / Hermes tool output
  -> ResponseEvent::OutputItemDone
  -> Harness ResponseItem::FunctionCall
  -> record_completed_response_item / persisted rollout
  -> dynamic handler parse_arguments rejects malformed JSON
  -> function_call_output error remains in factual history
  -> next model request: clone_history.for_prompt / build_prompt
  -> Responses input[]
  -> vLLM construct_input_messages / preprocess_chat
  -> json.loads(function["arguments"])
  -> HTTP 400 before inference
```

源码依据：

- `codex-rs/core/src/stream_events_utils.rs`：先记录 completed ResponseItem，再 queue tool handling。
- `codex-rs/core/src/tools/router.rs`：FunctionCall arguments 作为字符串传入 ToolPayload。
- `codex-rs/core/src/tools/handlers/dynamic.rs`：此后才解析 arguments；此拒绝早于 UAEA dynamic adapter。
- `codex-rs/core/src/session/mod.rs`：conversation items 写入 history 和 rollout。
- `codex-rs/core/src/context_manager/history.rs`：`for_prompt()` 补 missing output、移除 orphan output，
  但不将已失败的 FunctionCall 转换为普通历史事实。
- `codex-rs/core/src/session/turn.rs`：下一请求由 Harness 重建完整 provider input。
- 本机 vLLM 的 `entrypoints/openai/responses/utils.py` 将 FunctionCall 重新构造成 assistant tool_calls；
  `entrypoints/chat_utils.py::_postprocess_messages()` 对历史 arguments 调用 `json.loads()`。

Harness owns 原始 thread/history、执行生命周期和拒绝结果；UAEA adapter owns 合法 structured
action 的 capability/authorization 校验。此次缺口是 Harness 到本地 provider 的 history
兼容边界，不是 UAEA Web provider resolution。无需改 Codex Core 或已安装的 vLLM。

## 最小设计

```text
Harness factual history / rollout / canonical trajectory
  -> UAEA local ProviderHistoryBridge
  -> project_provider_history(outgoing request copy)
  -> provider-safe input[]
  -> existing local vLLM 8002
```

`harness/provider_history.py` 仅对 outgoing request 深拷贝：

- malformed / 非 JSON object arguments 归为 `REJECTED`。
- 明确 schema/authority rejection 归为 `REJECTED`。
- 明确执行失败、timeout、crash/partial 状态归为 `FAILED`。
- pinned 的 aborted/cancelled output 或明确 cancellation 状态归为 `CANCELLED`。
- 以 native `call_id` 匹配 proposal/result；保持原先位置和顺序。
- 已终结 call 及其 output 转为普通 assistant observation，明确
  `terminal=true`、`replayable=false`、state/reason；不是 user authorization。
- 成功调用、成功但 low-relevance 的搜索、正常对话及 custom freeform tool input 保持原样。
- 原始 arguments、错误、native identity 仍在 rollout 和 canonical trajectory；不重写、不 rollback。

这是发送副本的投影，不改变 runtime 的真实执行状态，也不伪造成功。
不保存新的 authority state；每次从 factual input 重新推导，重启不依赖投影 sidecar。
projection observation 保留 requested/actual provider 与 execution success 的已有区分。

`harness/responses_bridge.py` 使用 stdlib HTTP，仅监听随机 loopback port，upstream 必须是
本地 diagnostic HTTP endpoint，并拒绝 `8001`。仅在发现 terminal attempt 时改请求 history；
正常请求保持原始 bytes，响应/SSE 原样流式传递。不增加 inference runtime、tool retry 或 Web timeout。
`provider-history-decisions.jsonl` 只记录 identity、终结判定、raw hash/reference；不记录完整请求、
headers、credential 或带 key 的 URL。request sequence 是 bridge 接收顺序，不是 Harness 因果序号。

人工入口自动启用该投影层。新 thread 使用原生非 ephemeral rollout；`InteractiveAppServer.start()`
支持 `resume_thread_id` 从磁盘恢复，不使用实验 history override。外层未捕获的 dynamic adapter
异常返回明确终结 tool result，不让 Python exception 退出整个 REPL。
每次 writer 生命周期有独立 run identity，canonical 文件仅追加；raw events 和 stderr 也不覆盖已有内容。

## Recovery acceptance

诊断入口：

```bash
cd /mnt/d/UAEA
python3 -B scripts/h3_failed_attempt_recovery_probe.py
python3 -B scripts/h3_failed_attempt_recovery_probe.py --live-vllm
```

已通过真实 source-built Harness 协议恢复验证和真实 Qwen 的普通对话/重启恢复验证：

```text
D:\UAEA-runtime\h3-results\failed-attempt-recovery-20261003-040728
D:\UAEA-runtime\h3-results\failed-attempt-recovery-20261003-041002
```

后者 `recovery-report.json`：同一 thread 的四次 `turn/completed` 均为 `completed`；
malformed call 未进入 UAEA execution；Web HTTP 为 0；合法 existing File 执行 1 次；
history HTTP 400 为 0；原始 malformed payload 和 persisted rollout 均保留；两个 canonical
trajectory 均通过 reader/validator。关闭并重新启动 app-server 后，以同一 thread_id 恢复并继续生成。

最新版代码再次通过确定性恢复 probe，artifact 为
`D:\UAEA-runtime\h3-results\failed-attempt-recovery-20261003-042430`；独立 run identity 与
decision journal 的 thread/reference 字段也保持有效。最终 targeted regression 94/94、
full unittest 274/274、Phase-1 scripted regression 24/24、六个变更 Python 文件的
`py_compile`、`git diff --check` 和新增导航的本地链接检查均通过。

验收性质必须分开：坏调用和合法 File proposal 来自可控 provider fixture，用于确定性故障注入；
普通对话和 runtime 重启后的对话实际由本地 Qwen/vLLM 生成。不是宣称模型自主生成了 fixture。
合法后续工具复用 `document.read_section`，不是 Google end-to-end 验收；Web 人工 acceptance 尚待继续。

另外对原始人工 artifact 做只读离线对照：投影前，当前安装 vLLM 的历史预处理函数复现同一
`column 47` 错误；投影后成功解析。原始三组 proposal/result 及 artifact 均未被修改。

## Generalization 范围与剩余 gap

| Surface | 当前结论 |
| --- | --- |
| malformed function arguments / provider JSON preprocessing failure | 自动测试及真实 Harness/Qwen 恢复 PASS |
| schema-invalid / unauthorized dynamic action | 明确 rejection output 转历史事实，自动测试 PASS |
| dynamic timeout / crash / partial execution | 有明确 terminal result 时投影，异常不退出 REPL，自动测试 PASS |
| cancelled / aborted dynamic execution | pinned output 和明确状态可识别，自动测试 PASS；未制造真人取消 workload |
| native/custom freeform 失败且无结构化 terminal metadata | PARTIAL：不从任意文本猜测状态；需另有证据才扩展映射 |
| server-side `previous_response_id` 隐藏历史 | 未验收；当前主路径 full-input/store-disabled，不启用该模式 |
| compaction 后历史形态 | 本轮不强制触发，保持既有 PARTIAL，不改变 compaction mechanics |

Hermes/model-output 的首次 malformed 责任仍有未决项：现有 artifact 证明进入 Harness 时
arguments 已损坏，未捕获本次原始 model token stream，不能仅凭结果判断是模型格式生成还是
Hermes 拼接问题。修复不依赖这个责任先解决，也不掩盖原始失败记录。

## 停止点

不修改 Codex Core、semantic ownership/scope/effective state、Google backend、proxy、Web timeout、
frozen `8001`、模型精度/量化/32K profile；不引入第二 runtime、Goal/Memory/context framework。
恢复 invariant 已验证，下一步只恢复真实人工 Web search → fetch acceptance：

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

网络与模型自然语言质量仍按原有 evidence/execution boundary 验收，不以 recovery PASS 代替 Web PASS。
