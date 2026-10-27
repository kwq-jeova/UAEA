# N1X W2-B：8K 外部 vLLM 与 ARM64 Harness

Status: ARCHIVED
Superseded by: docs/current/runtime/n1x-runtime-baseline-20261027.md
旧命令和结论仅保留为历史证据，不是当前运行说明。
日期：2026-10-27（Asia/Shanghai）
范围：W2-B 启动与协议验证。W2-C 真实工具工作流尚未执行。

## 固定基础

- Codex tag：rust-v0.163.0
- Commit：83086188ae0614bd882818ff1aa23f3194962012
- W2-A 只读冻结目录：/home/wqkan_wsl/uaea-n1x/baseline-harness-arm64-w2a-20261026
- 冻结目录包含 package、原始 evidence、FROZEN.json；48 个文件摘要验证通过。
- 原 W2-A tools 产物也保持未变；不复用或覆盖 5090D 的 x86_64 摘要。
- N1X 平台记录位于 harness/versions.json 的 linux-aarch64 条目，版本不变。
- vLLM 0.26.0、Torch 2.11.0、活动 UMA 补丁和原 8K 基线均未修改。

## 启动方式

先在独立终端启动工具解析实验服务：

    cd /home/wqkan_wsl/uaea-n1x/UAEA
    bash scripts/start_vllm_n1x_8k_experiment.sh

此脚本先验证基线 SHA256 和活动 UMA 补丁，再使用冻结的 8K 启动条件：
8192、8000、half、gpu_memory_utilization=0.35、max_num_seqs=1、enforce-eager，
以及 VLLM_WSL2_ENABLE_PIN_MEMORY=1、VLLM_USE_FLASHINFER_SAMPLER=0。
与原基线相比，只在独立实验入口增加 auto-tool-choice 与 Hermes 解析参数。
原 baseline-8k-20261023/start-vllm-8k.sh 不变。

另一个终端使用现有 H3 入口：

    cd /home/wqkan_wsl/uaea-n1x/UAEA
    python3 -B scripts/harness_version.py --verify-binary
    bash scripts/start_h3_harness_interactive.sh --profile n1x --turn-timeout 420

Linux aarch64 默认选择 n1x。profile 的默认值：

| 参数 | N1X |
| --- | --- |
| Context | 8192 |
| vLLM 模式 | external |
| URL | http://127.0.0.1:8000 |
| Model | Qwen2.5-14B-Instruct-AWQ |
| 产物、CODEX_HOME、workspace | /home/wqkan_wsl/uaea-n1x/runs 下独立目录 |
| Harness 二进制 | 冻结 W2-A package |

可通过 --base-url、--model 和各 root 参数显式覆盖。URL 必须是带端口的本地 HTTP 根地址，
不含 /v1；冻结 8001 被拒绝。服务实际模型与最大 Context 会在连接时检查。
N1X 不使用原 5090D 托管 vLLM 启动路径，不会重设其 CUDA_HOME 或 GPU 参数。

external 模式中，正常退出、初始化失败及其他异常都不启动或停止 vLLM。
H3 的 exit 只停止自己的 app-server。服务由其启动终端单独管理。
原 5090D 默认 32K / 8002 / managed 行为与原版本清单记录保留；--profile h3 可显式选择。

## 8K 容量处理

首次真实 turn 因默认原生工具描述使输入超过 8192 而失败，证据完整保留。
定位请求后发现原生 Multi-Agent namespace 与 Goal 工具占据大量上下文。
N1X profile 使用锁定版本已有开关关闭 multi_agent、multi_agent_v2、goals、memories、
view_image 和原生 web_search；UAEA 动态 read_section、list_files、web_search、web_fetch 仍保留。

没有更换基础提示，没有截断请求，没有放宽 UAEA 权威或语义投影，也没有修改 Harness 核心。
5090D 配置不增加上述 N1X 专属开关。

最终真实 turn：
输入 6758 tokens，输出 9，Harness 上报有效窗口 7782（模型服务配置仍为 8192）。
这证明短 turn 可运行，不代表满 8K 负载或多轮工作流已经验收。

## 验证结果

- Responses SSE：HTTP 200，response.output_text.delta 与 response.completed 均存在，
  返回 N1X_W2B_SSE_OK。
- 真实 app-server initialize、thread/start、turn/start、turn/completed：PASS。
- 使用现有 Bash H3 启动入口，返回 N1X_W2B_APP_OK；本轮模型未调用工具。
- H3 退出后外部 vLLM PID 不变，/v1/models 仍为 HTTP 200。
- 验证结束后仅停止验证驱动自己创建的实验服务，正常退出码 0。
- Harness/H3/N1X/Web 环境范围：237 项，235 PASS，2 个可选 installed-vLLM CPU 测试跳过。
- 全量：402 项，390 PASS，3 FAIL、7 ERROR、2 SKIP。10 项失败均属于缺少被 Git 忽略的
  tests/test_resources 私有 Memory 语料；相关源码未改动，未填充或伪造私有数据。
  不将全量结果表述为 PASS。
- 208 个受保护文件摘要一致，W2-A 冻结快照与原产物未变，Runtime 子模块干净。

本轮无 W2-B 协议阻塞；全量回归仍受私有 Memory 测试语料缺失限制。
W2-C 还需单独执行短小文件工具工作流，并验证真实调用与 Observation / Trajectory；
现有 workflow probe 的旧路径和 32K 固定参数需在该阶段转发 N1X 配置，不能原样运行。

## 外部证据

/home/wqkan_wsl/uaea-n1x/audit/w2-b-20261026T232218Z

关键文件：
w2b-result.json、freeze-verification.json、responses-result.json、responses-stream.sse、
appserver-features-off-result.json、final-harness-regression.json、final-full-regression.json、
vllm-experiment.log、owned-vllm-cleanup.json。

真实成功 run：

/home/wqkan_wsl/uaea-n1x/audit/w2-b-20261026T232218Z/h3-native-features-off/interactive-8192-20261026-233335

其中保留 app-server-events.jsonl、harness-versions.jsonl、connection.json、
semantic-state-snapshots.jsonl 和 normalized-trajectories。
初始过大请求及失败 turn 保存在同一审计目录的 h3-smoke、prompt-diagnostic 等目录中，
没有用成功重跑覆盖失败记录。
