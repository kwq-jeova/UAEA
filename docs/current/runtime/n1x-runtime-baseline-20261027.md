# N1X 正式运行基线：32K + Hermes

Status: CURRENT
正式化日期：2026-10-27
统一入口验收日期：2026-10-28
配置来源：harness/n1x_profile.json
首次 32K 验收记录：evidence/n1x-32k-acceptance-20261027.json
统一入口验收记录：evidence/n1x-unified-entry-20261028.json

## 正式运行配置

N1X 与 5090D 使用 32768 Context 和 Hermes 工具解析规格。
N1X 采用 ARM64 Harness、端口 8000、外部服务生命周期；5090D 保留自己的 x86_64 产物、
8002 托管服务及 GPU 参数。固定版本仍为 Codex rust-v0.163.0。

| 项目 | N1X |
| --- | --- |
| Model / served name | Qwen2.5-14B-Instruct-AWQ |
| vLLM / Torch | 0.26.0 / 2.11.0 |
| Context / effective window | 32768 / 31129 |
| Tool choice / parser | enable-auto-tool-choice / hermes |
| URL / H3 profile | http://127.0.0.1:8000 / n1x |
| dtype / GPU memory utilization | half / 0.35 |
| max-num-seqs / enforce-eager | 1 / true |
| VLLM_WSL2_ENABLE_PIN_MEMORY | 1 |
| VLLM_USE_FLASHINFER_SAMPLER | 0 |
| UMA mem_utils.py SHA256 | 54772815cecb6445485ff41bfeecf85082da6120c8e4615eff7066ddc544610e |

vLLM 启动脚本与 H3 的 n1x 默认值均读取同一配置文件。正式 H3 入口仅接受 32768；
原生工具开关保持 W2-B 已验证设置，UAEA 动态工具保留。
启动 vLLM 前核对活动 UMA 文件的固定摘要；不一致时停止，不自动修复。
正式启动不再依赖 8K Bring-up 目录，也不重新安装依赖。

## 启动与退出

模型服务尚未运行时，在服务终端执行：

```bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
bash scripts/start_vllm_n1x.sh
```

原本地命令 /home/wqkan_wsl/uaea-n1x/start-vllm-32k.sh 仅转发到以上脚本，
不再保存独立参数。脚本不接受命令行参数覆盖；配置以 harness/n1x_profile.json 为准。

另一个终端：

```bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
python3 -B scripts/harness_version.py --verify-binary
bash scripts/start_h3_harness_interactive.sh --profile n1x --turn-timeout 420
```

Linux aarch64 默认选择 n1x；H3 只连接现有 vLLM，exit 只关闭自己的 app-server。
显式 --context 8192 被拒绝。实验副本 h3_harness_interactive_repl_n1x32k.py 已并入共同入口；
验收时的原始副本保存在本地冻结基线 accepted-entrypoints 中，不再并行维护。

## 统一 Harness 入口验收（2026-10-28）

两台设备统一使用 scripts/start_h3_harness_interactive.sh：

| Profile | 默认选择条件 | Context | 模型服务与生命周期 |
| --- | --- | --- | --- |
| n1x | Linux aarch64 | 32768 | 外部 8000；H3 退出不停止 vLLM |
| h3 | Linux x86_64 默认；5090D 可显式指定 | 32768 | 原有 8002 managed、model/path/GPU 参数不变 |

本次实际以 Bash 执行统一入口 --profile n1x，stdin 仅提供一个原始验收请求及 exit。
没有导入替代 REPL，没有 monkeypatch，没有 --context 覆盖，也没有重试模型工作流。
一次结构化 read_section、一次真实文件执行、Tool Result 和 Execution Observation 均 PASS；
章节原文及 SHA256 与独立读取一致。最终摘录仅合并排版空白，标点、链接及文字一致。
两次输入 7108、8058 Tokens，输出 44、67；有效窗口 31129，无 Compaction。
Turn 与步骤 completed；Workflow 仍 active、completion_established=false、unresolved 为空。

原始事件、Trajectory、语义快照、实际启动 argv 和逐项检查保存在：
/home/wqkan_wsl/uaea-n1x/audit/unified-entry-20261028-002155Z。
H3 退出后先确认外部服务仍存活，再停止本轮检查自行启动的模型服务；
原 frozen 32K 与 W2-A 快照、8K 归档、UMA 文件及 Runtime 保持不变。
既有 16 项 N1X startup / Harness manifest 回归通过，不新增测试用例或其它模型工作流。

## 固定版本与验收

- Codex tag：rust-v0.163.0
- 源码 Commit：83086188ae0614bd882818ff1aa23f3194962012
- ARM64 codex SHA256：a46cb75c1882238234f66c2fa78705dcea6fffbba3e5331c99afd7117c7d90d4
- bundled bwrap SHA256：cf387d7ee855eb5a87b2a257a3204e3872ec35dff0f09a54dcf96cf9585532da
- Runtime gitlink：1f311291df027baceca40779643e5107b9eb6fb3
- ARM64 二进制：/home/wqkan_wsl/uaea-n1x/baseline-harness-arm64-w2a-20261026/package/codex
- 固定 32K 配置及验收快照：/home/wqkan_wsl/uaea-n1x/baseline-32k-hermes-20261027

2026-10-27 的一次真实 read_section 调用、Tool Result、Execution Observation、
Raw Events / Trajectory 身份链与最终引用均 PASS。引用比较只忽略 CR/LF 换行。
输入分别 7128、8083 Tokens，输出分别 44、51；无 Compaction。
Turn 与执行步骤 completed，Workflow 仍 active、completion_established=false；
单次工具验收不代表整体工作流终结、多轮正确性或通用事实性已经通过。

验收读取的 README 内容 SHA256：
a6b85b87eb56f805d9955a263cf4b8716fff964d51f2b06adc84dd374a2ba335。
验收时 README 全文件 SHA256：
f2d60a940c3c0fc644037ae4596eaea8af0c57be0d15273ef36037d7ef225120。
原 README 副本保存在冻结基线 evidence/README.accepted.md，后续文档变化不重写验收依据。

原始证据保留在：
/home/wqkan_wsl/uaea-n1x/audit/w2c-32k-hermes-20261027T121726Z。
版本化摘要记录完整 thread/turn/call identity、文件摘要、Token、Workflow 状态和原始文件 SHA256。
冻结目录同时保存验收源入口、原始事件、Trajectory、语义快照、正式配置及 FROZEN.json。

## 8K 归档

[8K Bring-up 归档索引](../../archive/runtime/n1x-bringup-8k-20261027.json)
和 [W2-B 历史记录](../../archive/runtime/n1x-harness-w2b-20261027.md) 仅用于追溯。
原目录完整移至 /home/wqkan_wsl/uaea-n1x/archive/baseline-8k-20261023；
旧路径 baseline-8k-20261023 保留符号链接，使历史检查和日志中的地址继续有效。
七个原文件内容及摘要不变，旧 8K 工具实验配置保存为归档文本。
所有历史推理、失败、压缩和工具验收原始证据均保留。
8K 不再是正式入口选项或并行维护的启动配置。

## 正式化检查范围

本次只做启动配置收敛、既有入口检查、版本/摘要核对与本地提交。
沿用现有 N1X startup / Harness manifest 检查，不增加模型推理或工作流测试。
Phase-1 Runtime、Codex 二进制、vLLM 环境及 UMA 补丁保持原状态。

## 双平台同步前隔离检查（2026-10-28）

- n1x Profile 仅接受 Linux aarch64；h3 Profile 仅接受 Linux x86_64，错误平台在参数解析阶段报错。
- 每次解析参数时按实际平台选择对应 Codex 路径。缺少该平台产物的版本直接失败；
  ARM64 不允许静默使用仅有 x86_64 产物的 rust-v0.154.0。
- 已注册的显式 --codex-bin 覆盖会核对 build_target；
  所有实际执行的二进制（含未知显式路径）在 app-server 启动前检查 ELF 架构，再核验固定 SHA256。
- N1X vLLM 启动器在访问 UMA 文件前拒绝非 ARM64 Linux；5090D 的 h3 不读取 N1X profile 或启动器。
- 5090D 的 x86 二进制/构建记录、Managed vLLM、8002、qwen25-14b-awq、
  原模型与 venv 路径以及 GPU 参数保持原值。
- 最小入口/版本回归包含双平台参数模拟和反向二进制拒绝；在 N1X 校验实际 ARM64 ELF 与 SHA256。
  5090D GPU 启动、x86 二进制实机运行及真实推理仍须在 5090D 本机执行，不视为本次实机 PASS。

5090D 在其既有 WSL 仓库 /mnt/d/UAEA 内先确认工作区干净，再执行 git pull --ff-only，
git submodule sync --recursive 和 git submodule update --init --recursive。
随后运行 python3 -B scripts/harness_version.py --verify-binary，
再运行 bash scripts/start_h3_harness_interactive.sh --profile h3 --turn-timeout 420；
核对原有 x86 路径与版本、8002/Managed/32768/Hermes，完成一次真实 read_section 检查。
不复制 N1X 的 ARM64 产物、venv 或 UMA 补丁到 5090D。
