# 工具恢复与 64K Context 限定验收（2026-11-05）

**总体 PARTIAL：64K 加载、单次长输入及本次资源保护通过；减少 Compaction 的收益已观察到，长研究恢复与压缩后来源归属仍未通过。32K 保持正式回退，64K 仅保留显式实验入口。**

未修改 Phase-1、Codex Core、Goal Adoption、Memory Admission、执行权限、模型依赖、UMA 补丁或安全阈值。未 Commit/Push。两个本次拥有的模型进程及采样器均已清理，8000/8003 无监听。

## A. 工具恢复

### 已验证的机制

Apple 原会话的事实保持不变：模型两次显式请求未授权回退，收到合法恢复后改用计划文字结束 Turn。“继续”仍未产生新 Action。日志不能证明其内部推理原因。

本轮使用真实 Bolt + 固定 Codex rust-v0.163.0 + SharedExecutionBoundary，执行两个短自动案例：

| 条件 | 拒绝 | 新合法搜索 | 实际读取 | 最终版本与来源性质 | 耗时 |
| --- | --- | --- | --- | --- | --- |
| 原工具声明 | 1 次 | PASS | PASS | vLLM 0.32.0，明确为本地夹具 | 75.1 秒 |
| 授权含义澄清声明 | 1 次 | PASS | PASS | vLLM 0.32.0，明确为本地夹具 | 72.6 秒 |

两例都在同一个 Turn 内完成 allow_fallback=true 被拒 → 新提案 allow_fallback=false → 搜索 handler → Fetch handler → Response，没有追加“继续”，没有增加 Host 续跑循环。

**范围限制：**首次错误由预先注册的测试任务诱发，且初始任务明确要求依据 Tool Result 恢复。这证明既有循环具备恢复能力，不证明自然长研究中的恢复已可靠。工具 handler 是明确标记的本地夹具，没有访问 Google；其实际执行有 Registry、Decision、Observation、Raw Events 和出站审计证据。不能把它记为真实 Web 搜索验收。

### 最小修复

原工具字段描述仅说“用户禁止回退时设 false”，没有准确表达“未知授权不是允许”。现将 allow_fallback 描述明确为 Action Proposal；true 必须有有效回退授权，未知时可以提出同 Provider 的 false 请求。

这只是既有契约的正确声明，不授予权限、不替模型改参数，也不是新认知规则。两组都成功，**尚无对照证据证明这一措辞提高了恢复成功率**。

**判定：**

- Runtime 拒绝/回传及既有同 Turn 恢复路径：限定 VERIFIED / PASS。
- 模型在短、明确恢复任务中的合法行动：限定 PASS。
- Apple 式长会话恢复的一般能力：PARTIAL / UNKNOWN。
- 未引入自动新 Turn、无限重试、强制工具调用或第二套 Agent Loop。模型以普通最终文本结束时，Host 不将其计划转成未经提出的 Action，也不把 Turn completed 当 Workflow completed。

## B. 64K 引擎与 KV

两次服务均使用现有 vLLM 0.32.0、B12X、FlashInfer、单并发、Eager、64/64 UMA，显式 36 GiB 引擎规划与固定 1 GiB KV。原 32K 启动目录和全部锁定文件未修改。

64K 在独立目录复制已有启动/监控实现，仅改变实验路径和 max_model_len。Guard 的 Reason 函数逐字一致；Python supervisor 仅更换子脚本路径；Windows Commit、Available、Dedicated、Shared 遥测、WSL、Swap、3 秒监控新鲜度及 Fail-Closed 均保留。

| 项目 | 32K | 64K |
| --- | --- | --- |
| vLLM max_model_len | 32768 | 65536 |
| 固定 KV | 1 GiB | 1 GiB |
| 启动日志 KV 容量 | 96,743 Tokens | 109,817 Tokens |
| 日志理论并发 | 2.95x | 1.68x |
| 实际允许并发 | 1 | 1 |
| Harness 报告有效窗口 | 31,129 | 62,259 |
| 配置自动压缩阈值 | 24,576 | 49,152 |

混合 Attention/Mamba 的容量由引擎实际布局决定，不按窗口大小线性外推。以上理论并发不授权增加并发。1 GiB 已通过 64K 初始化，不需要增加到 2/3 GiB。36 GiB 是引擎规划，不是 Windows/CUDA 系统硬上限。

### 真实长输入

一次独立 Responses SSE 请求：

- 实际 API usage：**52,855 input / 37 output Tokens**。
- 首个可见输出文本：46.39 秒；总耗时：50.09 秒。
- 首、中、尾三个预先固定检索值全部正确，输出 JSON 完整，response.completed。
- 未发生输出长度截断、CUDA OOM 或保护阈值触发。

这是合成检索控制，重复文本明确不是独立证据；不是金融研究质量或完整 Workflow 验收。它证明真实处理超过 32K 的输入，**未做接近 65,536 Tokens 上边界的压力测试**。

## C. 相同历史片段的多轮 Harness 对照

输入来自人工会话 interactive-32768-20261105-071627 的已有工具记录与模型输出，类型保留为历史记录/模型 Claim。通过本地 Fetch 夹具供应 20 个不同片段，5 组读取后再核对来源锚点。

两组数据、模型、策略和工具预算相同；每个片段不超过 3000 字符，实验 Tool Result 预算为 7000 字符，未修改正式 4000 字符默认值。所有工具实际执行均有记录，但不是新的外部 HTTP 获取。

| 观测 | 32K | 64K |
| --- | --- | --- |
| 完成 Turn | 6 | 6 |
| Compaction | 5 | 1 |
| Fetch 执行 / 唯一 URL | 24 / 20 | 20 / 20 |
| 总耗时 | 718.62 秒 | 513.16 秒 |
| 最大观测模型输入 | 27,068 Tokens | 49,762 Tokens |
| 实际回传摘录哈希有效 | 24/24 | 20/20 |
| 最终五个目标锚点的正确分组归属 | 0/5 | 0/5 |

该样本中压缩次数和耗时下降，约节省 29% 时间，也没有出现 32K 的 4 次额外读取。但只有一条轨迹/配置，不是统计性能结论。

### 证据保真未通过

- 32K 最终只回答 ACK，未遵循新的来源核对请求。
- 64K 返回了分组列表和 UNKNOWN，但把片段 17、18、20 的锚点错配到第 1、2、5 组。它们是真实返回过的锚点，不是凭空制造的新 ID；问题是来源归属。
- 五个目标锚点中，64K 答案包含了一个值，但位置错误，不能计为正确归属。两组正确分组均为 0/5。
- 最终出站请求中，两组均只保留了五个目标锚点中的最后一个。即使仅一次 Compaction，也未保留之前四个细节。不能要求模型凭空恢复缺失内容；但不应以当前片段替代旧来源，允许 UNKNOWN。
- Host 的原始回执与摘录哈希没有被摘要改写；可观察到的是模型可见 Context 丢失细节和后续归属错误，不能宣称 Host 权威 Evidence 已被污染。

**结论：窗口扩容减少压缩，但没有在这组实验中证明压缩后证据保真得到解决。**

### 初始无效对照保留

最初把约 5K Tokens 的历史包直接当当前用户输入，触发 Host 必需恢复块 24 KB 限制，后续失败输入累计还触发原生 32K 请求拒绝。该试验不能公平代表网页工具回传，已标 INVALID_CAPACITY_COMPARISON，保留全部原记录，不混入上表。

这也暴露剩余边界：扩大模型窗口不会自动扩大 Host 24 KB 保护。大段当前用户粘贴输入仍可能被拒。正式 Runtime 本轮未放宽该限制。

## D. 资源与清理

以下为全程离散采样峰值/最低值，包含加载；不是瞬时分配硬上限，也不能把不同内存域相加。

| 指标 | 32K | 64K |
| --- | --- | --- |
| NVML Dedicated 峰值 | 28.92 GiB | 28.98 GiB |
| WDDM Shared 峰值 | 0.182 GiB | 0.190 GiB |
| Windows Available 最低 | 24.91 GiB | 24.72 GiB |
| Windows Commit 余量最低 | 46.57 GiB | 46.37 GiB |
| WSL Available 最低 | 17.48 GiB | 17.45 GiB |
| WSL Swap 采样最高 | 1.35 MiB | 1.35 MiB |

两次启动的阈值模拟及监控失效终止闭环均 PASS。真实加载/测试未触发资源保护。32K 试验在所有测例完成后达到预设 1800 秒实验期限，被正常清理；64K 由本次控制器主动停止。两个 service state 与采样器清理均 remaining=[]。

64K guard 在主动停止后输出 CONTROLLER_STOP/非零退出；这是本次发出的 stop，不是 OOM 或传感器失效。

## E. 修改、复现与回退

正式代码仅修改 scripts/h3_harness_interactive_repl.py：

1. 修正 Provider 回退字段的契约说明。
2. 增加显式 --experimental-context-64k；仅 N1X external + --context 65536 允许。

新增 tests/test_context64_experiment.py。相关 **157 项回归 PASS**，AST、git diff --check 通过。15 项启动/Runtime 锁定哈希、旧 Qwen UMA、Phase-1 清洁状态和端口清理合计 18 项检查通过。

32K/5090D 默认配置、原有服务启动器及所有旧记录保持原样。

### 隔离的 64K 实验启动器

/home/wqkan_wsl/uaea-n1x/nemotron-bolt/experiments/recovery-context64-20261105/launch/start64.sh

仅复现有限实验时：

~~~bash
bash /home/wqkan_wsl/uaea-n1x/nemotron-bolt/experiments/recovery-context64-20261105/launch/start64.sh --experiment
~~~

若另行决定人工体验 64K，统一 Harness 入口仍为：

~~~bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
bash scripts/start_h3_harness_interactive.sh \
  --profile n1x --context 65536 --experimental-context-64k \
  --vllm-mode external --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x \
  --execution-contract shared --goal-mode shadow --goal-projection optional \
  --reasoning-effort none --turn-timeout 0 --user-input-timeout 0
~~~

本轮不要求人工测试。实验启动器的 --experiment 有固定期限，不应误当人工不限时服务。回退仍使用未修改的 start-bolt-32k.sh，并在 Harness 使用 --context 32768、不加实验开关。

本轮增量 Diff 和 before/ 保留在：

/home/wqkan_wsl/uaea-n1x/research-records/recovery-context64-20261105T082201Z/

关键记录：design.json、replay-design-revision.json、experiment.py、long_input.py、recovery-32768-*/、tool-replay-32768/、tool-replay-65536/、comparison.json、long64-result.json、resources.json、regression-results.json、protected-checks.json、this-stage.patch。

模型加载/保护原记录：

- 32K：nemotron-bolt/records/manual-20261105T082202Z-78d71ea5/
- 64K：nemotron-bolt/records/manual-20261105T085607Z-67ca3667/

研究原型与夹具位于独立记录目录，没有成为正式执行入口。回退代码时只核对本轮增量，不覆盖原有工作区修改。

## F. 架构评审建议

- **VERIFIED：**现有同 Turn 恢复循环可执行合法重试；64K + 1 GiB KV 可启动并完成超过 32K 的实际请求；本样本压缩/耗时减少；安全保护与清理有效。
- **PARTIAL：**长会话中的恢复可靠性、跨 Compaction 的来源归属。
- **UNKNOWN：**声明澄清的独立行为收益、真实研究质量提升、65K 上边界压力、多次运行的稳定收益。
- **不建议立即改为默认常用 64K。**可以保留其为长任务容量实验选项；正式推广应另验证任务相关证据的保留/合法按需恢复，而非再加窗口或强制工具循环。
- 下一步最小问题：在压缩前明确哪些来源关系属于当前待回答问题，并在压缩后核对“模型可见/已丢失/可合法重新读取”，同时检查模型是否选择 UNKNOWN 或合法恢复。避免把所有旧内容无限重新注入。
