# P3.5 Context Budget / Workflow Recovery — 2026-11-02

范围：限定工程契约收敛；不是 Research Workflow PASS。基线 main 122040dde1bf75b9d9eabd3ed00236cf8a1375e0；本轮未 Commit/Push。

## 根因与最小修改

人工会话 interactive-32768-20261102-033635 的压缩失败请求包含多版本 Host 投影。Bridge 将 Host 恢复块追加到已有历史，原生自动压缩未与 Host 恢复时机协调；配置未为工具结果和压缩提前留出足够余量。网络失败与超预算是两个独立问题：两次 Google TLS EOF 后，扩大 Provider 权限的提案被 SharedBoundary 正确拒绝，但失败结果没有完整、统一地传递合法恢复选项；失败历史被包装成 assistant 消息，也容易成为内部 JSON 回答的示例。

- responses_bridge.py：普通请求移除已有完整 Host 标签后注入一份最新快照；压缩期间只保留 Host 权威状态在模型窗口之外，下一普通请求恢复。只依据 Host 生命周期或专用 compact 路由，不能由模型文字启动此模式。
- Host 传输副本默认最多 24000 UTF-8 序列化字节。先移除可选说明和历史解释，再缩短来源摘录并重算实际片段哈希；原始请求、有效约束、来源身份/原始哈希、执行事实不得静默丢弃，仍超预算则 typed HTTP 413，禁止转发。Host 完整快照不受这个传输限额截断。
- h3_context_characterization.py：32K 的原生 auto-compaction 触发点为24576，预留25%；模型窗口仍32768。这是调度预留，不是所有请求的精确 Token 硬上限。
- h3_harness_interactive_repl.py：接入原生 compaction 生命周期；当前已绑定 Turn 收到明确输入超预算错误时仅中断一次，记录任务仍保留、Workflow 未完成；旧 Turn 的错误不影响当前 Turn。
- recovery_observation.py / web_capability.py / semantic_execution_contract.py：记录 TLS 失败类别；网络失败和执行前拒绝均回传合法选项。同 Provider/URL 使用新 Action ID、安全参数和当前授权重新验证，或明确报告阻塞。建议本身不执行重试、不授予权限。
- codex_dynamic_tools.py / provider_history.py / workflow_continuity.py：实际 Observation 保留恢复信息，失败历史作为外部事实回传；区分 recoverable_failure、blocked、已执行结果和 Workflow completion。未改变默认 legacy；shared 仍需显式启用。

没有修改 Codex Core、冻结 Phase-1 Runtime、模型依赖、UMA 补丁或安全阈值。

## 确定性验证

43个模块分进程运行：**472项，470 PASS、2 SKIP、0 FAIL**。其中新增20项 Context/Recovery 测试。覆盖去重/版本更新、压缩生命周期、摘要不授予权限、字节预算降级/拒绝、来源片段哈希、巨大原文的 Host 保留、typed 413 不出站、当前 Turn 单次中断、网络失败分类、安全新尝试、未授权 fallback 拒绝、重复 ID 不重复执行及失败不完成 Workflow。

复现命令：
```bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
python3 -B -m unittest tests.test_context_budget_recovery
```

完整模块清单及逐模块日志在本地记录 regressions.json / regression-logs/；沿用检查点的隔离模块运行方式，避免已有测试桩的跨模块导入污染。

历史请求离线回放：
- 原70项 → 普通请求46项 → 压缩请求32项，移除38个旧/重复 Host 块。
- 非 Host 用户历史、工具调用及结果不变；完整 Host 快照及时间事实不变。
- 下一普通请求恢复同一权威快照；没有从模型摘要恢复授权或生成执行事实。
- 数字是消息项/字节，不是 Token；没有将历史失败请求重新发送给模型。

## 受控 Bolt + Shared 真实验证

本地运行：
/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/p35-live-20261102T055242Z

模型仍为已验证32K、单并发、Eager、固定1GiB KV、36GiB引擎规划；为尽快验证自然生命周期，仅独立测试 codex-home 将 auto-compaction 触发点设12288。未修改正式24576设置，不是32K压力验收。

- 4个用户 Turn 均有对应原生终结事件；原生自动压缩 started/completed 一次，压缩后继续产生回答。
- 出站6次 HTTP200；压缩请求0个 Host 块，下一请求14个唯一 Host 块，保留当前 input_id、任务身份与失败 Observation；未发生重复 Host 注入。
- 真实 web.fetch 遭遇 SSLEOFError；模型前三轮如实报告未取得摘录、未完成研究。1条真实 Observation 的4次出站回传状态全部与 Host 一致。
- 第四轮未产生 read_section 调用，却声称尝试读取：**Model Behavior FAIL**，Host 未生成文件读取事实。该轮提示还错误预设“之前真实获得网页来源”，是测试夹具限制，不能用于证明正向来源保真。真实正向来源保留仅由本阶段历史离线回放及此前P3.4记录支持。
- Workflow 始终 active、completion_established=false；没有将模型声称或 Turn completed 提升为执行/完成事实。
- Dedicated峰值29.14GiB，Shared峰值0.133GiB；Windows Available最低26.85GiB、Commit峰值65.95/114.48GiB；WSL Available最低17.50GiB，Swap峰值约3MiB。保护模拟触发/过期数据均正常终止专用测试进程，本次模型退出后 remaining=[]、8000/8003无监听。
- 实测结束后另补两项低风险防护：完整 Host 快照的预算拒绝移到出站层、超预算中断严格绑定当前 Turn。二者完成CPU/回环HTTP回归，没有再次加载模型。原运行 source manifest 与最终差异均保留，不能宣称最终所有行均被真实运行覆盖。

## 判定与剩余边界

| 项目 | 结果 |
| --- | --- |
| Context Contract | 限定 PASS：历史回放、出站审计、受控原生自动压缩 |
| Recovery Decision / Observation | Contract PASS：离线重试/拒绝路径；真实 TLS 失败分类/回传 |
| Workflow State | PASS：未执行不生成事实，失败不完成任务 |
| Model Behavior | PARTIAL；末轮声称调用但未调用明确 FAIL |
| Research Workflow | 未通过：TLS仍失败，无新正文来源 |

可以结束本轮 P3.5 限定工程收敛。尚未证明正式24576阈值下超长任务一定成功，也不保证模型会选择合法重试或忠实使用恢复事实。24KB不等于Token；单条超长原文/工具结果仍可能超过总窗口，处理为明确阻塞并保留任务，不能无界重试。进程内稳定 Action ID 去重不等于跨崩溃 exactly-once。

## 人工入口与回退

本轮不要求人工验收，入口保持不变；未来已启动受保护 Bolt 外部服务后使用：
```bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
bash scripts/start_h3_harness_interactive.sh --profile n1x --vllm-mode external --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x --execution-contract shared --turn-timeout 420
```

此入口不启动或停止外部 vLLM。legacy 仍可显式选择，但不等同于回退本轮 Context 修复。逐文件回退应参考本地 before/ 和 P35.patch，对照工作区后应用；不得重置整个工作区或删除原始记录。

完整证据、回放脚本、回归日志、变更哈希：
/home/wqkan_wsl/uaea-n1x/contract-convergence/p35-20261102T054029Z/
