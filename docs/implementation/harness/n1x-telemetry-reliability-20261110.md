# N1X遥测可靠性最小修正

日期：2026-11-10。**短时安全门禁PASS；持续无人值守可靠性UNKNOWN。**
记录：/home/wqkan_wsl/uaea-n1x/research-records/telemetry-goal-loop-20261110T001159Z/

## 原故障与时序

原件manual-20261109T234316Z-32164cac中，Guard报Linux metric timestamp stale or invalid，
最终seq137记录valid=false、TimeoutExpired。guard_ctl.metrics()唯一有该期限的子进程是
2秒nvidia-smi查询。确认采集失效，不等于确认GPU内存越界或Goal推理失败。
原131个服务成功样本采集0.0327–0.4848秒，Windows记录UTC减Linux UTC为-0.547至2.124秒；
记录时间并非同步时钟测量，不能由负值直接证明时钟偏移。超时底层原因仍UNKNOWN。

周期约1秒，命令可耗时2秒，另有进程启动/退出、序列化、调度与跨系统读取；
对上次成功样本的3秒期限裕量小，但不能据此直接放宽期限。
旧UTC写在查询完成后，不能完整反映此前WSL内存读取的年龄。

## 最小修改与不变项

仅修改独立启动资产：
- launch/nvml_metrics.py：标准库ctypes，持有单个只读NVML句柄，明确C ABI，检查单GPU及容量数值。
- launch/guard_ctl.py：替换每次CLI启动；UTC取最早观察开始，记录查询耗时/来源，失败记录错误类型与详情后退出。
- launch/SHA256.json：刷新授权修改的文件并纳入新helper；其余原有pins逐一保持。
- launch/README.md：标记当前采样方式及回退证据。

Windows Guard、supervisor、service参数、UMA补丁、Runtime依赖不变。
NVML总容量本机与CLI同为64GiB；未用CUDA109GiB口径替代Dedicated。

NVML也是nvidia-smi的底层库，并非独立故障恢复观测。
官方依据：[NVML说明](https://docs.nvidia.com/deploy/nvml-api/nvml-api-reference.html)、
[查询接口](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html)、
[WSL查询限制](https://docs.nvidia.com/cuda/wsl-user-guide/)。
本机只验内存API，不扩大为所有NVML查询支持。

没有采集重试、替补来源或last-good无限使用。
API返回错误：写invalid、退出；API挂住：样本不再前进，Windows3秒新鲜度/序列检查拒绝，
停止写工作负载心跳后独立Linux3秒监督也能终止模型。
collector本身由既有独立控制进程按PID身份/进程组清理。
该机制不能保证驱动/内核不可中断挂死时一定可清理，仍需保留失败记录并停止实验。

48GiB Dedicated、Windows6GiB可用/Commit余量max(16GiB,20%)、WSL4GiB、
Swap256MiB、3秒新鲜度全部原样保留。计划预算不是硬CUDA上限。

## 短时验证与可复核结果

| 验证 | 实际结果 |
| --- | --- |
| 40对低资源直接NVML/CLI读取 | 同容量64GiB；NVML中位0.854ms、p95 1.490ms、最大1.583ms；CLI中位58.535ms、p95 78.761ms、最大79.996ms |
| 6项Python反例 | PASS：最早时间戳、禁止CLI调用、API失败抛出、invalid覆盖旧样本并退出、关闭句柄/错误状态/非法计数拒绝 |
| 原ReadLinuxMetrics函数10项原生PowerShell测试 | PASS：正常接受；无效、跨Run、逆序、过旧、过于超前、采集太慢、缺字段、负数和序列冻结拒绝 |
| 两次独立无模型进程故障注入 | 冻结采集器、invalid帧均触发实际Guard终止，目标及子进程remaining=[] |
| 原启动器--smoke | GPU48GiB模拟阈值、Windows心跳失效均通过；没有实际制造压力或加载模型 |

见telemetry-benchmark.json、telemetry-tests.log、freshness-tests.json、
fault-freeze-result.json、fault-invalid-result.json、monitor-gate.json。
故障注入用研究目录内的Guard副本，仅运行原有CPU烟测case；正式Guard未改。
冻结生产者是对无新数据的注入，不是假称已经复现真实NVML驱动死锁。
API错误单元反例与外部无新数据终止分别覆盖。

## 结论与边界

**VERIFIED**：单次CLI超时路径、直接NVML本机内存API、短时延迟差、无效/过期时真实终止与清理；
计数和新鲜度阈值代码未改。
**PARTIAL**：消除每次CLI进程开销为有根据的可靠性改进，不证明原超时根因完全解释。
**UNKNOWN**：驱动偶发阻塞、长时间运行与其他负载下的故障率。

满足进入一次原保护下的限定Goal实验条件；真实负载资源和采样结果另在Goal专项记录报告。
真实受控运行V1已完成：1652个服务样本覆盖约1699秒、5会话30轮；
GPU查询中位0.233ms、p95 0.654ms、最大1.994ms，完整采样最大8.882ms，无采集中断。
ControllerStop由本研究Driver主动请求，外层monitor-exception中的该控制停止不算遥测故障。

### 停服后的迟到成功检查V2

收尾CPU虚拟时钟反例发现：V1可能将迟到返回标为valid并继续，外部读者若没读到慢帧，
不能把下一快帧当成已证实的故障恢复。保留红灯反例，不掩盖这项实现遗漏。
V2保留原CLI的2秒采样预算：调用返回后若完整采样超过2秒，写invalid并退出，
不允许再用快帧覆盖。无法在Python内强行取消挂住的C API，仍由不变的外部3秒保护负责停模型。
2.1/3.1秒虚拟成功返回在V1失败、V2拒绝。最终7项Python测试（含两边界子例）PASS；
最终版本重跑原--smoke与无模型invalid/freeze进程集成均PASS，旧记录另存。

**模型运行使用V1，未为V2重载模型。** 执行中全部样本远低于2秒，V2仅收紧迟到拒绝；
其真实负载效果仍需未来使用观察，不能把V1运行直接标为V2实机PASS。
V1源码/pins保存在monitor-executed-v1，最终源码/pins及diff另外锁定。
任何再次失效仍停止，不因短时PASS放宽阈值或自动重启。
Memory维持Research Reserved。无Phase-1/Goal/Memory采纳或权限变更，不Commit/Push。
