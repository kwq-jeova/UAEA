# CASE_TIMEOUT 生命周期边界核查与最小修正（2026-11-05）

结论：**限定工程验证PASS；默认人工服务已移除固定实验停服期限。未加载Bolt，未声称长期稳定性已验收。**

## 原因与范围

旧启动器本来名为manual，但复用了实验期限：
- launch/config.json.session_timeout_seconds=1800；
- Linux guard_ctl.py实际硬编码service1800秒；
- Windows guard.ps1兜底1810秒；
- Linux采样器1850秒退出，心跳读取还限制整个文件不得大于2MiB。

这限制了整次模型服务（含加载、对话间停顿），不是Context上限、单次推理超时或Workflow期限。
2026-11-05人工会话CASE_TIMEOUT即来自该路径；配置字段单独修改无法解决全部问题。

## 四类生命周期

| 对象 | 当前边界 | 不赋予的语义 |
| --- | --- | --- |
| 自动实验 | 显式--experiment，默认1800秒；监督与采样寿命按同一run-policy派生 | 到期不表示任务成功 |
| 人工模型服务 | 默认manual，无固定实验期限；用户停止、服务错误或安全保护可终止 | 活着不表示Workflow进展或完成 |
| 单次请求/等待 | Harness现有--turn-timeout（人工命令420秒）与pending/wait/cancel；加载就绪另有900秒超时 | 外层等待结束不表示模型服务/Workflow结束 |
| UAEA Workflow | Host独立保留请求、Action/Observation及状态；模型不可用不能自动完成/删除 | 不等同Turn、模型PID或实验批次 |

在同一Host/Bridge仍存活时，模型服务停止后重新受保护启动，可继续利用保留历史；本轮通过本地HTTP恢复模拟验证该传输边界。
**跨Harness重启的自动完整任务恢复没有在此实现或验收。** 未增加Workflow状态机、第二执行循环或Memory Admission。

## 修改

### 本机独立启动器（不是模型依赖）

- start-bolt-32k.sh：普通命令保持人工模式；增加--experiment作为显式有限实验入口；--check/--smoke保留。
- launch/config.json：default_service_lifecycle=manual，旧session字段改名experiment_timeout_seconds=1800。
- guard.ps1：每次保存run-policy.json；人工模式无elapsed截止，实验模式派生Windows兜底与采样寿命；显示模式与运行时长。
- guard_ctl.py：人工service和采样器无固定实验截止；实验仍有限期；smoke保留120秒。
- heartbeat只读取64KiB尾部完整记录，原始日志仍追加保存；不将2MiB累计文件大小当服务寿命。
- sampler在Windows owner心跳10秒不推进后自清理，避免孤儿采样器。**这不是安全阈值放宽**：工作负载supervisor原有3秒新鲜度门禁不变。
- validate.py及SHA256.json：只更新本轮5个启动文件的pin。vLLM/Torch/UMA、服务参数、env/CUDA工具链pin保持不变。
- launch/README.md：记录当前人工/实验入口与已知限制；历史事故记录保留。

### UAEA传输边界

- harness/responses_bridge.py：本地ConnectionRefused返回明确uaea_provider_unavailable、HTTP400且retryable=false；保留请求/Observation，不等同权限拒绝，不自动加载服务。
- 只对“连接被拒绝、上游尚未接收请求”的情形处理；没有把已执行失败或中途断流伪装成安全自动重试。
- tests/test_harness_provider_history.py新增两项：拒绝后的Host状态保留；同一Bridge在模拟provider重新监听后可传递原历史继续。
- 本轮未继续修改正文投影/Goal语义算法；此前工作区改动均保留。

## 保留的保护

Windows Reason函数逐字对比未变；Linux sensor AST对比未变。
GPU/NVML与WDDM Dedicated48GiB、Windows Available6GiB、Commit余量max(16GiB,20%)、WSL Available4GiB、Swap256MiB、3秒工作负载心跳及PID身份/进程组清理均保留。
监控缺失/无效/过期继续Fail-Closed；manual不代表无人监控、不限制资源或自动重启。

## 验证

- 9项生命周期CPU模拟通过：manual越过虚拟4000秒无CASE_TIMEOUT；实验1800秒仍停止；资源保护仍可触发；大于2MiB日志有界读取且原文不改；采样超旧寿命与owner丢失自清理。
- 133项仓库定向回归通过，0FAIL：Bridge、Context预算、Goal、执行闭环、Turn关联与来源投影。
- PowerShell AST、Bash语法、版本/hash配置检查通过。
- **真实无模型smoke通过**：模拟GPU48GiB触发及真实Windows心跳过期均终止本阶段创建的无模型进程，子进程和sampler清理为空。
- **真实固定Codex rust-v0.163.0无模型链路通过**：对故意关闭的loopback端口只尝试1次；native Turn failed、Workflow仍未完成、0工具执行、无挂起Turn。
- 本地HTTP provider恢复测试验证原上下文和成功工具历史继续保留；不是Bolt语义恢复验收。
- 首次独立native探针遗漏配置目录导致初始化失败，记录保留；使用正式write_config后才计入上述真实链路验证。

没有真实运行30分钟以上Bolt。虚拟时间/CPU保护通过不能扩大为长期实机PASS。

## 当前人工入口

模型终端，默认人工持续监护：
~~~bash
bash /home/wqkan_wsl/uaea-n1x/nemotron-bolt/start-bolt-32k.sh
~~~
终端应显示Lifecycle: manual；不再提示session limit30minutes。只有显式--experiment才使用实验期限。
不要为日常人工交互添加--experiment；不要关闭资源/心跳保护。

新Harness终端：
~~~bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
bash scripts/start_h3_harness_interactive.sh \
  --profile n1x --context 32768 --vllm-mode external \
  --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x \
  --execution-contract shared --goal-mode shadow --goal-projection optional \
  --reasoning-effort none --turn-timeout 420 \
  --result-root /home/wqkan_wsl/uaea-n1x/runs/context-lifecycle-manual
~~~

可继续普通人工交互，自然越过原30分钟后再发一个小请求，保留运行目录与模型侧日志用于核查。
不要求持续高负载，不必为了测试制造OOM或故意杀进程。长Turn返回输入提示时使用 /turn status、/turn wait 或 /turn cancel。
模型资源保护停服时不要视为Workflow完成；重新启动前确认原保护已清理。
仅退出Harness会保留External服务；测试结束后在本人本次模型终端Ctrl+C并等清理。

## 风险、回退与证据

本轮未改Phase-1、Codex Core、依赖/UMA补丁、系统/WSL配置、内存阈值或正式Goal/Memory权威。
未Commit/Push；不自动启动下一阶段模型测试。
回退依据本轮before-launch/和before-repo/增量Diff，不使用全仓reset/clean，不覆盖其他未提交工作。

记录：/home/wqkan_wsl/uaea-n1x/research-records/case-timeout-lifecycle-20261105T004256Z
无模型保护记录：/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261105T004753Z-ba04bd7e
native-no-provider-with-config/RESULT.json、regression-results.json、lifecycle-unit.log、static-checks.json为直接入口。
