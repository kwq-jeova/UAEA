# Web Provider、时间与局部错误：最小修复（2026-11-05）

结论：**Runtime 事实供给/拒绝恢复限定 PASS；时间与研究行为仍 PARTIAL/UNKNOWN，未宣布真实 Workflow PASS。**

本轮未启动模型、未发真实 Web 请求、未停止外部服务；未修改模型依赖、安全监控、Phase-1、Goal Adoption、Memory Admission 或权限策略，未 Commit/Push。原有未提交修改均保留。

## 1. 根因与能力核查

依据人工会话 interactive-32768-20261105-053257，及 manual-time-permission-audit-20261105.md：

- Alphabet 阶段已有 5 次 Google 真实搜索成功。之后 3 次提案将 allow_fallback 改成 true，SharedBoundary 因 provider_switch 授权未知拒绝。不是对象切换后全网被禁止。
- Google 已通过 SerpAPI 接入，具备 Provider、回退、来源与日期过滤记录。未发现仍需移除的“Google 未实现/禁止使用”执行限制。配置缺失、配额/认证错误和不能保留日期过滤的回退限制有实际原因，保留。
- 原请求已包含 2026-11-05 / Asia/Shanghai、11月4日收盘要求。模型未取得对应行情就判断估值，并混入已标为模拟的价格，属于证据使用问题。
- Shared 的权限 Gate 提前拒绝后，未采集已有 Semantic Guard 约束，导致恢复显示 constraints_known=false。不是已知约束被删除。
- Fetch 的 max_chars=5000 在外部执行前抛普通 ValueError，Shared 无法确定异常是否产生过效果，因而保守记为 execution_unknown。
- 文件、HTTP 403、TLS 原因虽被保留，但局部作用域表达不足；模型还把 recovery_sources Context 块臆造成文件目录。

源码依据：phase2/web_adapter.py 的 _search_google / normalize_search_constraints；harness/execution_host.py 的 Policy；harness/semantic_execution_contract.py 的 Gate 与 Guard。未删除真实安全限制，也未扩大 Provider 权限。

## 2. 最小修改

| 文件 | 职责 |
| --- | --- |
| harness/semantic_execution_contract.py | 拒绝时也采集已有 Guard 约束；保留原决定、Contract ID 与独立 semantic_resolution_id；单独处理明确的执行前参数异常 |
| harness/recovery_observation.py | 回退拒绝限定为 web.provider_fallback；保留已知 Provider 与合法新提案参数；HTTP、超时、文件错误保持局部恢复语义 |
| harness/observation_boundary.py | CapabilityInputError 与局部失败投影；不根据异常文本猜原因、不据局部失败判定全网状态 |
| phase2/web_capability.py | Fetch 的确定性参数检查使用类型化 ValueError 子类；不改变上限，不替模型裁剪 5000→3000 |
| harness/codex_dynamic_tools.py | Shared/Legacy 类型化错误回传及模型可见字段保留 |
| harness/provider_history.py | 历史规范化保留失败作用域、HTTP 状态和错误类别 |
| harness/io_contract.py | Context 构造时重采样 Host UTC 时钟、标明来源与作用域；区分历史时点、交易日、来源覆盖、计算输入 |
| tests/test_provider_time_errors.py | 12 项定向回归，含本地 HTTP 实际接收与出站审计核对 |
| tests/test_harness_io_contract.py | 接纳时钟事实块 |
| tests/test_harness_runtime_connection.py | 固定测试时钟，继续验证文件根事实不重写其他契约 |
| tests/test_harness_dynamic_tool_adapter.py | 修正旧测试对已去重终结事实的错误索引；独立旧版本回放亦失败，证据保留 |

没有新增执行控制器、认知规则、股票/日期专用解析器或计算工具。显式 allow_fallback=true 仍按既有 Policy 校验，原 Action 参数不被静默改写。

### 错误与恢复

- 回退拒绝：明确拒绝对象；新请求使用允许的 Provider、allow_fallback=false，再经过当前 Policy。原拒绝不能被重试抹除。
- 参数错误：validation_failed / argument_validation / http_attempted=false；提示按当前 Schema 修正。
- 普通内部异常：仍为 execution_unknown，不将任意 ValueError 当成可安全重试。
- HTTP 403：保留状态，核对端点/访问条件或报告局部阻塞，不绕过安全检查。
- TLS/超时：保留类别，允许同 Provider/URL 的新提案；不自动重试、不绕过 TLS、不增加回退授权。
- 文件失败：local_filesystem_request，保留原错误与既有 section_not_found 等字段。冻结 Registry 吞掉的部分异常类型保持未知，不从字符串反推 errno。
- HTTP 200 挑战页：保留实际正文与状态，不伪造网络失败或已获取文章的证明。本轮未实现挑战页语义分类器；模型识别能力仍未验证。仅当上游明确报告 content_challenge 时，按局部内容失败表达。

## 3. 时间、行情与数值边界

Host 时钟仅代表构造 Context 时的 UTC 快照，随既有刷新入口重采样。它不是用户请求日期、交易日判断或来源覆盖时间。用户时区/历史日期沿原始请求与 Context 保留，没有被 UTC 日期覆盖。

来源继续区分 accessed_at、来源声明的 published_at、需语义判断的 content_period。没有交易日历服务，也没有从发布日期推导财务期间或行情时点。查询包含日期不证明结果满足它。

复用既有 Python 确定性计算能力，CPU Decimal 独立复核历史回答内部算术：

- 16.54B − 16.51B = 30,000,000 USD（30M，不是 300M）。
- 16.51B = 165.1 亿，不是 16.51 亿。

此检查不验证现实财报、币种或行情来源。未增加计算 Capability/权限，也未实现最终自然语言回答的逐断言审查。模型能否主动计算并保持单位仍 UNKNOWN。仅提供时钟或说明不能修复认知质量。

## 4. 验证

~~~bash
python3 -B -m unittest tests.test_provider_time_errors -q
python3 -B -m unittest tests.<existing_module> -q
git diff --check
~~~

32 个相关模块，**442 项测试通过，0 FAIL**，含 12 项新增定向测试。完整模块清单及逐项日志见记录目录。

| 维度 | 结果与限定 |
| --- | --- |
| Google 接入 | 历史真实执行已成功；17 项既有 SerpAPI 离线测试通过，保留来源、日期过滤、脱敏及失败分类；本轮未重新访问 Google |
| 拒绝/重试 | 真实 Registry/Host + 假传输 PASS；保留约束、拒绝未授权提案、合法新提案可执行，重复 Action 不重复执行 |
| 参数/未知异常 | Shared 与 Legacy PASS；超限零 HTTP，普通未知异常不伪装成无效果失败 |
| HTTP/TLS/文件 | 定向 PASS；保留类别、原始原因，不形成全局不可用判定 |
| 时间/来源 | 跨日时钟、发布日期/访问时间区分 PASS；缺少来源覆盖事实时保持 UNKNOWN |
| 出站协议 | 本地 HTTP 服务实际收到请求，与 P0 脱敏审计一致；含历史日期、Host 时钟、Provider 与局部拒绝。不是 Bolt 实际采用信息的证明 |
| 财务算术 | CPU Decimal 一致性检查 PASS；模型实际运用 UNKNOWN |
| Model Behavior | 旧会话时间证据使用/恢复解释 FAIL；修复后的行为未测 |
| Workflow | 未开展新真实研究任务，不宣称 PASS |

AST 与 git diff --check 通过。Phase-1 子模块无变更；旧 UMA SHA256 仍为 54772815cecb6445485ff41bfeecf85082da6120c8e4615eff7066ddc544610e。模型服务、安全阈值及依赖未改动。

## 5. 记录、Diff 与回退

独立记录：/home/wqkan_wsl/uaea-n1x/research-records/web-time-error-repair-20261105T063436Z/

- this-stage.patch：仅本轮增量，不混入既有工作区修改。
- before/：本轮文件原状态；逐文件核对回退，不使用破坏性 Reset/Clean。
- regression-results.json、test_*.log：最终测试结果。
- offline-samples.json、fixture-execution-contract.trajectory.jsonl：明确标记假传输的 Host 执行记录。
- numeric-consistency.json：CPU 算术结果。
- changed-file-hashes.json、checks.json、baseline-stale-test.log：变更哈希、边界检查与旧断言证据。

HEAD 保持 2d8d68d26ff97a4bf007895ebef02724890fa817；未 Commit/Push。报告及 Diff 另复制至 Windows UAEA_DOCS。

## 6. 下一次人工验证

需要新 Harness 会话加载 Python 修改，不必重启正常运行的外部 Bolt。统一入口：

~~~bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
bash scripts/start_h3_harness_interactive.sh \
  --profile n1x --context 32768 --vllm-mode external \
  --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x \
  --execution-contract shared --goal-mode shadow --goal-projection optional \
  --reasoning-effort none --turn-timeout 0 --user-input-timeout 0 \
  --result-root /home/wqkan_wsl/uaea-n1x/runs/web-time-manual
~~~

若服务未运行，沿用 /home/wqkan_wsl/uaea-n1x/nemotron-bolt/start-bolt-32k.sh 及其保护；本轮未启动它。

最小验收：同主题先研究对象 A，再研究对象 B；指定历史日期、真实来源及不得用模拟值替代。检查第二对象合法搜索、缺失数据说明、局部拒绝后的合法恢复、来源与计算支持。不要求故意触发失败，不增加自动执行授权。

取消 Turn 使用 /turn cancel，而非 turn/cancel。人工不限时等待与资源保护保持原样。
