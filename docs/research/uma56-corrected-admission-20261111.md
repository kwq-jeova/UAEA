# GPU56/Host72已生效后的准入核查（2026-11-11）

**硬件确认VERIFIED；实际负载BLOCKED / NOT RUN，零模型加载。**

用户修正分配后，新建独立批次重新核查。当前NVML与DXGI均证明GPU56GiB生效，Windows可见物理约70.481GiB，符合宿主名义72GiB的方向。此前GPU72/Host56批次不混入本批次。

## 1. 新批次无模型实测

| 项目 | 当前实测 |
| --- | --- |
| NVML Dedicated总量 / DXGI Dedicated | 56.000 / 55.986GiB |
| Windows可见物理总量 / Available最低 | 70.481 / 56.446GiB |
| Windows Commit Limit | 91.481GiB |
| 无模型Commit峰值 / 余量最低 | 15.453 / 76.028GiB |
| 原公式所得Commit停止余量 | 18.296GiB |
| 36GiB规划所需初始余量 / 当前额外缓冲 | 54.296 / 21.731GiB |
| NVML Used峰值 / PDH Dedicated峰值 | 1.075 / 1.071GiB |
| PDH Shared峰值 | 0.070GiB |
| WSL Available最低 / Swap峰值 | 20.687GiB / 0MiB |
| DXGI Local / Nonlocal Budget | 109.717 / 0GiB |
| DXGI Shared描述符 | 54.481GiB |
| CUDA Driver API Total | 109.717GiB |

DXGI预算仅当前诊断进程作用域，不能当作WSL可分配保证；CUDA总量、Dedicated、Shared不得相加。CUDA只做驱动初始化和容量查询，无Context创建、Tensor分配或推理。

Windows/Linux各15条采样有效，AC全部online；采集最长分别24.279/1.946毫秒。独立采样不是已通过单时钟Guard的证明。

NVIDIA驱动仍621.14，vLLM0.32.0、Torch2.13.0、B12X1.5.1、FlashInfer0.7.0.post1、Harness0.163.0。模型配置、权重索引、Parser元数据与64/64历史基线相同。历史驱动617.42，因而即使之后运行，也应声明不是严格单变量A/B。

历史64/64 Commit Limit为83.481GiB，本次为91.481GiB；这是总提交上限变化的实测。当前76.028GiB是无模型余量，不得与历史有模型最低20.136GiB直接比较为运行收益。尚无本次负载峰值/KV实际容量/延迟/Compaction结果。

## 2. 实际拒绝与第二个独立阻塞

原启动器--check执行一次，退出1：

    Windows Dedicated capacity differs from verified64GiB layout

原始stdout/stderr按字节保留并生成可读转义版本，未发生上次UTF8采集缺口。拒绝发生于guard.ps1:25、模型和采样器启动之前。不能称为物理内存不足或56GiB GPU装不下模型。

即使只适配容量身份，n1x_memory_policy.py:74–75仍要求：

    explicit_budget <= floor(min(CUDA_total, NVML_total) * utilization)

原参数36GiB / 0.6在实际56GiB上限为33.6GiB，不能通过。这是现有代码规则的确定性冲突；不是已执行的vLLM初始化失败。固定KV并不跳过该本地规划校验。

当前宿主Commit/物理/WSL读数未显示压力，但不能用这些读数覆盖容量和规划门禁。

## 3. 未应用的最小兼容适配提案

已准备proposed-compatibility.diff和proposal.json，**仅供评审，未修改任何正式或运行中的配置**：

1. 在实验专用Guard及本地N1X规划策略中，把预期容量64GiB适配为已验证的56GiB。
2. 仅隔离64K参数把gpu_memory_utilization从0.6调整为0.65；显式引擎规划保持36GiB，KV保持1GiB。
3. 全部资源停止线、单时钟挑战、2秒采集/3秒新鲜度、并发1、采样配置、32K默认保持不变。未来若获批，需要隔离接线及原件备份/精确回滚，不直接将此Diff应用到默认入口。

数值关系：

| 参数组合 | Dedicated×util规划上限 | 实际显式规划 |
| --- | --- | --- |
| 历史GPU64×0.6 | 38.4GiB | 36GiB |
| 当前GPU56×0.6 | 33.6GiB | 36GiB，冲突 |
| 提案GPU56×0.65 | 36.4GiB | 36GiB |

该提案不增加显式规划，调整后的绝对利用率规划上限仍低于历史38.4GiB，GPU48GiB等提前停止条件不变。固定KV路径不使用util自动分配KV；但这不等于已证明新实验行为或安全性，仍须无模型保护验证及真实准入。

**为何需要用户决定：**原对照要求明确禁止同时修改gpu_memory_utilization或其他规划参数。这一提案改变了该数值，且需适配现有布局绑定，当前不将“继续实验”解释为允许自行违反这项限制。也不降低36GiB、增加KV或删去检查来获得PASS。

若批准此唯一兼容差异，应在Manifest中披露，之后才继续原定34K/40K/48K及短Harness负载。若坚持0.6和36GiB数值全部不变，现有策略下无法加载，需要停止；目前不预设改写规划规则。

## 4. 当前结论与证据

- 硬件目标56/72：VERIFIED。
- 无模型资源读数与版本：VERIFIED；尚未证明加载后的安全缓冲。
- 原标准入口准入：BLOCKED，原始拒绝日志已保留。
- 64K加载/KV/性能/长期收益：UNKNOWN / NOT RUN。
- 56/72相比64/64的运行收益：UNKNOWN，不以空闲数据替代。
- 正式131源码及15项启动/保护原件hash不变。没有运行模型、修改系统设置、扩大权限或Commit/Push；8000/8003无监听。

本轮证据：/home/wqkan_wsl/uaea-n1x/research-records/uma56-corrected-20261111T130950Z
- windows-dxgi.json、windows-samples.jsonl、linux-samples.jsonl：本批次原始读数。
- nvidia-smi.json、environment.json：版本、低风险CUDA查询和模型元数据。
- guard-check.json及原始.bin：一次真实无模型检查的拒绝。
- preflight-summary.json：资源和规划算术。
- readonly-reference/：当前未改写规则。
- proposed-compatibility.diff、proposal.json：未应用的评审提案。
- original-pins.json、integrity.json：不变性核查。

当前已停在需要调整原实验约束的评审节点；不自动加载或继续长实验。
