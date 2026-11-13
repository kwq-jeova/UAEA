# N1X GPU56/Host72 UMA对照：无模型核查与阻塞报告（2026-11-11）

**阶段A BLOCKED；目标56/72未实测；阶段B/C NOT RUN，模型加载次数0。**

本任务按用户“GPU Dedicated缩减、宿主增大”的含义，将56/72解释为GPU56GiB / Host名义72GiB。运行时实际为GPU72GiB / Host名义约56GiB，方向相反。BIOS设置内容未直接读取，不对用户实际选择过哪个界面项作推断。

## 1. 当前硬件和无模型资源（VERIFIED）

| 项目 | 本轮实测 |
| --- | --- |
| NVML Dedicated总量 | 72.000GiB |
| DXGI Dedicated描述符 | 71.986GiB |
| Windows可见物理总量 | 54.481GiB |
| Windows Available最低 | 40.552GiB |
| Commit Limit | 75.481GiB |
| 无模型Commit峰值 / 最低余量 | 15.140 / 60.341GiB |
| 原Commit停止余量 / 当前空闲缓冲 | 16.000 / 44.341GiB |
| NVML实际Used峰值 | 1.049GiB |
| PDH Dedicated / Shared使用峰值 | 1.038 / 0.068GiB |
| DXGI Local Budget / CurrentUsage | 109.717 / 0GiB |
| DXGI Nonlocal Budget / Shared描述符 | 0 / 38.481GiB |
| CUDA Driver API total | 109.717GiB |
| WSL MemAvailable最低 / total | 20.607 / 21.455GiB |
| Swap峰值 | 0MiB |

DXGI Local/Nonlocal预算只属于当前诊断进程，CurrentUsage=0不代表系统GPU无占用，也不是WSL可用预算保证。Shared描述符不是当前使用量；CUDA Total、Dedicated、Shared不得相加。

NVML及CUDA身份/容量查询返回成功，GPU为RTX Spark N1X。CUDA只调用cuDriverGetVersion、cuInit、设备名称/数量/总容量；没有创建CUDA Context、分配Tensor或加载模型。CUDA free、vLLM实际分配和KV容量本轮NOT RUN，不能用历史109817 Tokens替代。

Windows和Linux各15条只读有效采样：AC全部online、Windows采集最长15.714毫秒、Linux最长2.297毫秒。两组独立采集，不是同一Guard Run的因果确认样本。单时钟挑战/心跳链路未在新布局完成准入验证，不能宣布安全门禁PASS，更没有拿旧样本启动模型。

## 2. 版本与历史对照限制

| 项目 | 64/64历史批次 | 当前无模型核查 |
| --- | --- | --- |
| GPU容量 | 64GiB | 72GiB，非目标56GiB |
| NVIDIA驱动 | 617.42 | 621.14 |
| vLLM / Torch | 0.32.0 / 2.13.0 | 相同 |
| B12X / FlashInfer | 1.5.1 / 0.7.0.post1 | 相同 |
| Harness | codex-cli0.163.0 | 相同，实际二进制已查询 |
| Windows Commit Limit | 83.481GiB | 75.481GiB |
| 模型负载 | 3档API+6轮Harness | 未运行 |
| 负载NVML峰值 | 28.739GiB | NOT RUN |
| 负载Commit最低余量 / 安全缓冲 | 20.136 / 3.439GiB | NOT RUN |
| 输入/KV/推理延迟 | 34,017/40,016/48,016，Harness52,296 | NOT RUN |

历史基线为capacity64-resource-20261111T115509Z，和当前uma56-assessment批次分别保存。当前无模型60.341GiB Commit余量不能与历史有模型20.136GiB直接比较为收益。Commit Limit降低约8GiB是实测；因驱动及宿主背景也不同，不能把全部差异唯一归因于UMA。

模型路径和90个分片存在；config、权重索引及自定义Parser元数据hash与历史相同，但未重新哈希全部权重。131项正式源码与历史锁一致。即使之后布局正确，驱动变化也使该历史对照不再是仅改变UMA的严格A/B；本轮未升级或回退驱动。

计数更正：同一历史基线原始记录为3个独立长API请求+11个Harness请求，共14个完整推理请求；用户摘要的12个与原记录不符。tokenize/health不计入，原始证据未改写。详见historical-baseline.json。

## 3. 当前准入与目标56GiB的独立矛盾

**当前硬件阻塞（VERIFIED）**：目标GPU56未生效；现有Guard还有64GiB身份绑定：
- guard.ps1:25要求DXGI Dedicated接近64GiB，:165要求NVML总量64GiB。
- n1x_memory_policy.py:52及:162要求NVML总量64GiB。
这些是验证布局的保护条件，不能为获得PASS静默删掉。GPU48GiB、Windows物理6GiB、Commit余量、WSL4GiB、Swap256MiB、采集2秒/新鲜度3秒等实际停止线未改。

现有--check仅执行一次且没有请求模型启动。创建的记录manual-20261111T124258Z-6fb54b90为空，未产生check.json或采样器；研究采集器随后因子进程stderr非UTF8发生UnicodeDecodeError，未保留原始退出码，因此不冒称取得了完整Guard拒绝日志或Guard PASS。停止判断依据是独立NVML/DXGI读数与明确源码门禁；没有再次尝试或修改Guard。

**正确GPU56下的静态规划冲突（VERIFIED规则，非56GiB实测）**：
原参数为显式36GiB规划、gpu_memory_utilization=0.6。现有policy:75要求：

    explicit_budget <= floor(min(CUDA_total, NVML_total) * utilization)

目标NVML56GiB、CUDA总量大于56GiB时，右侧为约33.6GiB，小于36GiB。固定1GiB KV路径仍经过这项独立规划校验，不能因绕过自动KV Profiling而跳过它。即使修改布局身份绑定，严格保持这些规划参数不变也无法通过当前规则。

这不证明56GiB GPU实际装不下模型；历史峰值28.739GiB也不能证明可以绕过规划门禁。当前只记录规则冲突，不降低36GiB、不修改0.6或任何政策例外，也不提出已验证的新预算。

## 4. 分层结论与下一步

- **资源分配收益 UNKNOWN**：目标56/72未取得，当前实际反向布局不能当作它的试验结果。
- **64K推理能力/1GiB KV/性能 UNKNOWN、NOT RUN**：没有任何本轮加载、长请求或Compaction数据。
- **长期适用性 UNKNOWN**：短时无模型读数不能替代加载峰值、持续监控和长任务稳定性。
- **执行边界 VERIFIED**：所有15项启动/监控/规划原件hash未变；正式131源码未变；没有UMA/驱动/Pagefile/WSL设置写入，没有新增Goal/Memory权限，没有Commit/Push，8000/8003无监听。

本轮结论是“配置确认未通过，停止”，不是“56/72劣于64/64”或“56/72内存不足”。没有自动尝试其他比例，也不自动恢复30×2。

需要用户评审的具体事项：
1. 先核对平台设置中GPU与系统内存的方向；若仍按本轮目标测试，必须在运行时得到GPU约56GiB、宿主名义约72GiB。本轮不代改设置或要求立即再次重启。
2. 在再次模型测试前，评审如何处理目标56GiB与既有64GiB绑定及36GiB/0.6规则的矛盾。所有参数保持不变与现有准入通过目前不可兼得，当前不擅自选择调整项。
3. 后续驱动若保持621.14，明确采用有驱动差异的历史对照；不能宣称严格单变量A/B。是否补新64/64批次由后续评审决定，不自动增加PC重启或实验。

## 5. 可复核证据

证据根：/home/wqkan_wsl/uaea-n1x/research-records/uma56-assessment-20261111T123952Z
- windows-dxgi.json：Dedicated描述符、Local/Nonlocal预算及进程作用域。
- windows-samples.jsonl / linux-samples.jsonl：各15条只读原始采样。
- nvidia-smi.json / environment.json：驱动、版本、CUDA低风险查询及模型元数据。
- preflight-summary.json / historical-baseline.json：本轮与历史分别汇总。
- readonly-reference/：只读Guard与N1X准入规则副本，行号可复核。
- guard-check-readout-error.json：采集缺口，未抹掉失败。
- original-pins.json / integrity.json：不变性核查。

本报告及研究地图索引是持久化文档增量；没有改正式Runtime。至此停止，等待用户评审。
