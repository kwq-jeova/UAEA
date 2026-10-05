# Web 网络可观测性：Phase 1

> Status: PARTIALLY CURRENT
> Role: IMPLEMENTATION_NOTE / 实际请求诊断
> Phase: 2026-10-02
> Still valid: PARTIALLY CURRENT：open/header/read仍有效；阶段stop历史
> Superseded: 授权/result修复以audit为准
> Current reference: [Documentation Guide](../../README.md)
> Governance reviewed: 2026-10-02（文档治理，不等于新实验验证）
> 局部维护/历史实施说明，不作为当前架构 authority；环境版本和旧待办不在本轮重新验证。

> 历史 checkpoint：诊断实现继续有效；下文的阶段等待与停止点记录当时状态。
> 后续人工 run 已记录真实 HTTP 200/404。授权与 typed execution observation 的当前修复见
> [Boundary Integrity Audit](../../current/architecture/boundary-integrity-audit-20261002.md)，不新增 timeout/retry。

本阶段只增加实际 UAEA Python 请求进程内的诊断。不修改 provider resolution、fallback 授权、
Semantic Ownership、Harness Core、20 秒 HTTP timeout 或现有 retry 行为。
Phase 2 的授权边界与 Phase 3 的 execution truth 须等待本阶段人工复测后另行推进。

## 记录位置

Google/SerpApi 与既有 DDG/Bing/fetch 共用 `phase2/network_observability.py` 的薄观测边界。
Google 请求仍使用原有 `_NoRedirect` opener；其它请求仍使用 `urllib.request.urlopen`。
不替换 HTTP client，不修改请求参数、header、读取上限或代理配置。
使用 `ContextVar` 隔离请求诊断，不做进程全局 socket/SSL monkey patch。

诊断是每个既有 access event 的附加 `metadata.network_diagnostics`：

- `request_start`、`credential_present`；凭据只记录可用性。
- `proxy_present`、`proxy_endpoint_redacted`、`proxy_bypassed`；在请求进程读取 urllib 代理环境。
- `events` 按实际边界发生顺序保存阶段与累计 `elapsed_ms`。
- `http_status`、`response_bytes`、`exception_type`、`cause_type`、`network_error_stage`、`error_kind`。

这些字段沿用内部 ToolResult/ExecutionObservation 进入 adapter trace，保留 thread/turn/call 身份。
模型可见 bounded projection 不增加网络诊断字段，也不改变 trajectory schema。
每次 fallback attempt 均有独立的 access event；通过原有 `related_access_event_ids` 查阅
`adapter/source.sqlite` 中对应 `web_access_events.metadata_json`，不要只看最后一个 provider 的错误。

## 可诊断阶段与限制

```text
not_opened
  -> open
  -> response_headers
  -> body_read
  -> body_read_completed
```

`open` 包含 DNS、TCP、proxy CONNECT、TLS 和响应头等待。现有 urllib 接口不能可靠拆开这些子阶段，
本阶段不将它们伪装成已观测信息。可区分：

- `connection_open_timeout`：`open()` 中的 timeout，不等同于已证明 TCP connect timeout。
- `response_read_timeout`：响应返回后的 `read()` timeout。
- `ssl_error`：直接或由 URLError 包装的 SSL 异常，保留实际边界。
- `proxy_error`：HTTP 407 或可识别的 proxy tunnel 失败。
- `http_error`：其它 HTTPError，保留状态码。
- `network_error`：不能进一步可靠分类的错误，不猜测代理或上游原因。

`not_opened` 可用于区分 credential validation 等发送 HTTP 前的失败。
代理字段表示 urllib 可见的配置及 bypass 判断，不证明 Clash 的上游节点或最终出口。
诊断不会自动 retry，不作语义判断，不授予 fallback 权限。

## Secret 边界

不保留 request URL、query、响应正文、异常 message/repr 或任何 key 值。
代理 endpoint 仅保留 scheme/host/port，去除用户名、密码、path/query/fragment；
实际 key 及其 URL 编码回显也会被脱敏。
原有 SerpApi secret isolation 与 provenance 规则不变。

## 人工复测

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

重新启动后输入严格 Google、不允许 fallback 的真实 Web 请求。若失败，提供 run 路径，
直接检查该请求进程留下的 `network_diagnostics`，不以另一 shell 的成功请求替代证据。

停止点：`PHASE 1 READY FOR HUMAN TEST`。不自动实施 Phase 2/3。

## 自动验证（2026-10-02）

- Targeted/相关 regression：111 项；全量 unittest：240 项；均通过。
- `py_compile`、`git diff --check`：通过。
- 真实现有 capability smoke：HTTP 200；20 秒 timeout 未变，无 fallback，未启动模型或 inference。
- 同一请求的 source history 和 adapter trace 均保存 `network_diagnostics`；模型可见 projection 不携带诊断。
- Artifact：`D:\UAEA-runtime\h3-results\google-backend-20261002-115335-2637bc77`。
- 真实凭据扫描仓库、当前 diff、新 smoke 及最近人工 artifact：385 个文件，无匹配。
- 网络失败阶段由模拟测试验证；真实人工 REPL 的失败复现仍待用户运行，不将成功 smoke 当成该项通过。
