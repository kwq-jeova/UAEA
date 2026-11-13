# N1X 单时钟因果采样确认（2026-11-10）

状态：**监控安全门禁限定 PASS，真实金融对照另行报告**。

记录根目录：/home/wqkan_wsl/uaea-n1x/research-records/singleclock-20261110T122425Z/。
此目录是审查副本，**不是正式启动入口**。正式脚本仍在 nemotron-bolt/launch/；
运行前通过启动器 SHA256 pins、服务锁、资源门禁；不直接运行本目录副本。

根因已证实为旧 Windows Guard 使用不同系统 UTC 的差值，触发 LINUX_CLOCK_FUTURE。
绝对时钟偏差的底层原因 UNKNOWN。此次没有修改系统时钟或放宽未来容差。

## 时序与边界

Windows Stopwatch T0 在 Windows 原生内存/PDH 采集之前。
发布绑定 guard Run、sampler Run、严格递增 seq 和随机标记的请求；
Linux 读并消费本次标记后才查询 /proc 和常驻 NVML；Windows T1 验证原样返回。
要求 T1−T0≤3秒、Linux完整采集≤2秒。两侧 UTC 继续记录，但不作为跨系统年龄。
旧响应在唯一新请求等待期间不被接受、不触发重采集、不刷新原始期限。

每个标记最多消费一次；跨Run、错误标记、倒退、重放、失效、迟到均拒绝。
采集器错误退出；没有无限重试或旧样本兜底。
资源 Reason 函数逐字未变，独立 Windows 心跳守卫及 owned 进程组清理保留。

## 实际验证

- Python采集器10项、Windows消费者16项通过。
- 7种真实IPC/专用CPU进程故障：查询失败、2.1秒慢查询、丢确认、错标记、
  跨Run、重放、冻结采集器，全部Fail-Closed；进程及采样器remaining=[]。
- 正常12秒IPC以及样本UTC±1小时注入通过；后者仅改变测试帧，不改系统时钟。
- 50分钟真实无模型监控：3000.874436秒，2734次完整唯一确认，
  最大确认0.7410859秒、完整Linux采集0.229901485秒；无异常拒绝，清理通过。
- 通过上述门禁后安装，仅替换guard.ps1、guard_ctl.py及其pins；
  生产配置、NVML实现、模型参数、系统配置、Goal/Memory权威均未修改。
- 正式启动器smoke再通过：GPU48GiB模拟和Windows心跳失效均终止专用进程。

完整失败帧和时序保留在原记录；test-summary.json只是索引，不替代原件。
带.validated后缀的文件是实际安装版本，patch对照本轮开始的诊断版本。
测试脚本含原始隔离记录路径；复现时须使用新的独立测试目录，不能覆盖原件。

## 局限与回退

有限无模型观察不保证所有GPU负载下的实时调度；应用守卫不是CUDA硬分配上限。
既有vLLM N1X启动准入的额外UTC检查未改、未绕过；若拒绝必须停止。
不以本安全门禁证明Goal认知、语义正确性或完整Workflow通过。

完整before/pins在原记录根目录。回退须先停本次所有owned服务、核对当前哈希与后续改动，
再对两文件作定向恢复并重新生成对应pins/执行门禁；不整体覆盖用户修改。
旧UTC实现仍有已知误判，回退不等于允许无条件恢复模型实验。
本轮不Commit/Push。


## 随后真实负载更新

[完整恢复报告](../../../research/finance30-single-clock-validation-20261110.md)：
50分钟门禁通过后进行了一个真实模型批次；History完成14轮，
因NVML状态17被OS阻止访问而Fail-Closed。Goal组未运行。
此处无模型PASS不应扩大为负载下持续遥测可用PASS；不自动重试。
首因、次生postflight拒绝及清理均保留。
