# 生成与工具解析诊断

Status: IMPLEMENTATION_NOTE
Reviewed: 2026-10-04
Role: 仅补齐 parser 之前的证据，不修改生成、解析或 Web 执行行为

## 问题与边界

人工 run `interactive-32768-20261004-122440` 中，20:27:00 与 20:27:17
Hermes 记录 `JSONDecodeError: Expecting value: line 2 column 1 (char 1)`，
App Server 没有收到 `function_call` / `item/tool/call`。回复却先承诺搜索，后声称已完成。
因此失败早于 UAEA Web validation 与 HTTP execution；不是 Google 网络失败或授权拒绝。

旧 artifact 没有 parser 前的完整生成，无法倒推出实际非法 payload。
相同异常可以由空白 tool body 复现，但这不是证明该人工 run 的真实生成就是空白。

`No tool execution evidence -> model must not claim tool completion` 是已记录的验收要求。
本轮不实现完成声明检测、自动 continuation、工具调用修复或新的 truth engine。
`turn/completed` 表示 Harness 回合结束，不代表用户搜索任务成功。

## 最小实现

通过原人工入口的显式开关启用：

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420 --generation-diagnostics
```

不带开关时继续使用原 `vllm serve`；带开关时由
`scripts/h3_vllm_diagnostic_launcher.py` 在同一 API 进程安装仅观察的 wrapper，
随后调用原 vLLM CLI，`serve` 之后的 inference 参数完全一致。
不修改 vLLM 安装包、Hermes/parser 算法、Codex Core、Google backend、proxy、timeout、
authorization、semantic bridge、模型、AWQ、32K、GPU 0.75、Hermes auto tool choice 或 frozen `8001`。

`harness/generation_diagnostics.py` 观察实际安装的 vLLM Responses 接口：

- `SimpleContext.append_output`：stream 生成块、累计文本边界、最终原始生成片段。
- `ParsableContext.append_output`：非 stream 生成及终止信息。
- `Hermes2ProToolParser.extract_tool_calls` / `extract_tool_calls_streaming`：实际入参及返回结果。
- Hermes logger 的附加 handler：parser 内部捕获的异常类型及 JSON 行、列、位置。

wrapper 调用原方法一次，原入参、返回对象和异常保持不变。
diagnostic I/O 失败不改变 parser 返回；没有重试、纠正参数或补造 `function_call`。
仅在进程内增加观察 hook；关闭该启动选项后恢复未包裹的原安装包路径。

## 证据链与限额

每个新人工 run 额外生成 `generation-diagnostics.jsonl`，与 canonical trajectory 分开：

```text
generation_chunk / generation_finished
  -> hermes_input
  -> hermes_error（如果发生）
  -> hermes_outcome
  -> app-server-events.jsonl 的 rawResponse/completed / tool events / turn/completed
```

stream 与 full 解析可以发生在同一个 response；不要把 full 解析错误自动解释为 stream 同样失败。
`response_id` 来自 parser request；`engine_request_id` 来自生成引擎输出。
当前 vLLM 的 engine 子请求为 `<response_id>_<sub_request>`，原 ID 独立保留，不改写 native identity。
App Server 的 `rawResponse/completed.responseId` 可与 parser `response_id` 直接关联。
JSONL `sequence` 仅是诊断观察顺序，不是模型/Harness 的内部因果编号。

记录生成 `finish_reason`、`stop_reason`、chunk index、字符起止、token 数量、
tool tag 数量、脱敏生成片段、parser `tools_called` / tool count / content length / exception。
stream 的空 delta 或未形成工具名返回 `None` 本身不是解析错误。

不记录 prompt、完整 thread history、HTTP credential URL、token 内容数组或完整普通模型回复。
生成片段保留首个 tool tag 前最多 96 字符及后续区域；无 tag 时仅最后 256 字符。
脱敏后片段上限默认 4096 字符，超限保留头尾并标记 `fragment_truncated`。
每个 generation 最多记录前 256 个 chunk metadata，终止记录仍包含最后 8 个 chunk 边界，
并明确 `chunk_metadata_truncated`。单文件默认 8 MiB，超限写 `diagnostic_limit` 后停止采集。
超限、截断、redaction 或缺少 installation / finish 记录时，结论必须注明证据不完整。

先脱敏再裁剪：环境中已知 secret、credential 字段、Bearer、URL query/userinfo 与长 token 被遮蔽。
vLLM 子进程继续不继承 `SERPAPI_KEY`；key 不通过诊断 launcher 传递。
普通 query 等 bounded 内容仍可能包含用户输入，诊断文件应按私有实验产物处理。
文件以 append 模式创建并尝试 POSIX `600`；DrvFS 的实际权限仍受挂载设置影响。
不修改原始 trajectory 或已有人工 artifact；诊断 JSONL 不是 trajectory 的第二权威来源。

## 判断方式

- 最终 raw 生成自身缺少合法 tool body，finish 为 `stop`：优先归为模型输出/停止行为问题。
- finish 为 `length`：生成被截断，不能据此判定完整合法输出被 parser 拒绝。
- 最终 raw 有完整合法 tool JSON，但实际 Hermes 返回无 call 或错误：排查 parser/stream compatibility。
- full 与 stream 输入/结果不一致：结合 chunk 边界检查 streaming 状态或 final assembly。
- App Server 已收到有效 call 后才失败：回到 UAEA capability/result boundary，不能再归为本层错误。

代码 smoke 使用真实安装的 Hermes 在 CPU 上对普通文本、空白 tool body、合法 JSON 和跨块 tag
比较观察前后的返回值。fixture 不冒充真实 Qwen 生成，随机 call ID 不作为两次独立解析的相等条件。
下一次人工 run 才能提供待定位问题的真实 pre-parser 证据。
