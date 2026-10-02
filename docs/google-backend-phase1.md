# Google backend 接入：Phase 1（2026-10-02）

> 历史 checkpoint：保留接入时的范围、结果与人工停止点。后续真实人工 run 已成功返回 Google 结果，
> 最新投影缺陷和修复见 [Boundary Integrity Audit](boundary-integrity-audit-20261002.md)。
> 下文的“本轮/等待”仅描述当时状态，不是当前开发计划。

本轮仅实现 Google acquisition backend。Phase 2 的 semantic/provenance 专项验收与 Phase 3 的连续人工场景，
均须在当前阶段人工 PASS 后另行推进。本轮不改 Harness Core、semantic ownership/scope/authority 或 inference 配置。

## 调用边界

```text
provider=google
  -> existing UAEA WebAdapter
  -> SerpApi HTTPS request (engine=google)
  -> Google SERP JSON / organic_results
  -> existing WebSearchResult
  -> existing result filtering / relevance / evidence eligibility
  -> existing bounded Harness tool observation
```

输入 provider 枚举不增加 `serpapi`，不增加第二套 provider 字段。结果记录：

```text
requested_provider=google
actual_provider=google
acquisition_backend=serpapi
fallback_occurred=false
```

`actual_provider=google` 只在 backend 返回 `Success` 且 `search_parameters.engine=google` 后记录。
凭据、HTTP、网络、超时、限额或无效响应失败时 `actual_provider=null`，保留明确 execution status/reason，
不进入 relevance 评估。成功但没有候选结果仍属于 execution success，没有 evidence。

`allow_fallback=false` 不调用 DDG/Bing；只有 `allow_fallback=true` 且 Google 失败或没有可用候选时才允许沿用
现有默认 provider policy，并保留第一次 Google attempt 的 provenance 与最终实际 provider。
provider 未指定时继续使用原有默认 DDG/Bing 路径，不消耗 SerpApi 配额。

语言使用 `hl/lr`、地区使用 `gl`；来源域名与 source types 复用已有 query shaping/post-filter。
freshness 暂时复用原有 best-effort query shaping，不新增日期范围 schema，也不承诺精确时间覆盖。
本阶段不重写 relevance ranking。

## Secret 与 provenance

`SERPAPI_KEY` 仅从归一化后的进程环境读取。带认证参数的 URL 只用于内存中的 HTTPS transport，
不交给通用 `fetch_url`，也不记录到异常文本、日志、trajectory 或 SQLite。
持久化的 source URL 是不含 key 的 `https://www.google.com/search?...`；独立记录 acquisition endpoint 和 backend。
SerpApi JSON 在写快照前去除凭据字段并脱敏实际 key 的回显；不跟随 HTTP 重定向。
原始 organic candidate 继续保留在内部 snapshot/source history，模型只接收现有 evidence eligibility projection。

接口字段依据：[SerpApi Google Search API](https://serpapi.com/search-api)。这是第三方 Google SERP 获取服务，
不是 Google 官方 API；本地 Harness 和 Qwen inference 不因此改为远程模型。

## 自动验证与人工入口

独立 capability smoke，不启动 inference/app-server，固定公开查询可能消耗一次 SerpApi 配额：

```bash
cd /mnt/d/UAEA
python3 scripts/smoke_google_web_backend.py
```

它调用现有 `build_interactive_adapter`，经 ActionRequest/ToolRegistry 执行真实 Google backend，保存脱敏 report、
dispatch、source history 和结果快照。不宣称完成 model-mediated turn 或跨 turn 验收。

人工启动方式保持不变：

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

本阶段只需先输入：`仅使用 Google 搜索 LoRA training，不允许使用 Bing 或 DuckDuckGo，不允许 fallback。`
人工确认真实 Google 结果、自然语言回答及 provenance 后停止，反馈 Phase 1 PASS/FAIL。不得自动进入 Phase 2。

## Phase 1 自动验证结果

- Targeted/regression：87/87；全量 unittest：232/232；`py_compile`、Windows Git `diff --check`：PASS。
- Fresh WSL 子进程从私有 env 加载配置，经现有 dynamic adapter 执行真实 Google acquisition：PASS。
- `requested_provider=google`、`actual_provider=google`、`acquisition_backend=serpapi`、`fallback_occurred=false`。
- 8 个原始 organic candidates，3 个 citable candidates，现有 evidence status 为 `relevant`。
- Artifact：`D:\UAEA-runtime\h3-results\google-backend-20261002-105642-c1c3b2f6`。
- 实际 key 扫描仓库、当前 diff 和新 artifact 共 375 个文件，未发现泄漏；请求认证 URL 未持久化。
- 未执行模型 turn，未启动 inference/app-server，未触碰 frozen `8001`；上述结果不是 Phase 2/3 人工验收。

当前停止点：`PHASE 1 READY FOR HUMAN TEST`。等待人工 PASS 后才进入下一阶段。
