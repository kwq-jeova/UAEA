# Codex Harness 双版本升级记录

Status: CURRENT
Role: 当前依赖锁定、升级验收与回退说明；不替代 UAEA semantic contract
日期：2026-10-22

## 结论与边界

默认 Harness 升级为 `rust-v0.163.0`；`rust-v0.154.0` 的源码、二进制及既有运行目录永久保留。
版本选择以 [`harness/versions.json`](../../../harness/versions.json) 为唯一配置来源。
Codex Core 是仓库外独立 Git checkout，不是 UAEA submodule。
唯一现有 submodule `runtime/phase1-runtime` 仍锁定
`1f311291df027baceca40779643e5107b9eb6fb3`，本轮不改动。

本轮只升级执行依赖及诊断设施，没有修改 Codex Core、semantic extraction、authority、
provider history、Web provider、模型或推理参数。模型行为仍为 PARTIAL，不能把 Runtime 回归通过理解为 cognition 验收。
冻结 `8001` 未修改。真实模型测试顺序独占 `8002`，每轮结束均停止各自的 app-server 与 vLLM。
保持 RTX 5090 D v2 / 24GB / single GPU / Qwen2.5-14B-Instruct-AWQ / 4-bit AWQ / vLLM，
以及既有 `32768 / 0.75 / hermes` profile；两版上报 effective context 均为 `31129`。

## Version Inventory

| 项目 | 保留对照组 | 当前默认 |
| --- | --- | --- |
| Tag | `rust-v0.154.0` | `rust-v0.163.0` |
| Commit | `6b9826e3aa83b1a5947db50f4332cb9c65f1b340` | `83086188ae0614bd882818ff1aa23f3194962012` |
| Windows 源码 | `D:/UAEA-deps/codex/rust-v0.154.0` | `D:/UAEA-deps/codex/rust-v0.163.0` |
| WSL 二进制 | `/mnt/d/UAEA-runtime/codex/source-rust-v0.154.0-wsl-x86_64/codex` | `/mnt/d/UAEA-runtime/codex/source-rust-v0.163.0-wsl-x86_64/codex` |
| 构建 profile | 既有 `dev` | 独立 `dev-small` |
| 架构 | `x86_64-unknown-linux-gnu` | 同左 |
| 状态 | 旧产物版本及 SHA256 核验通过 | 从源码独立构建并核验通过 |

[官方稳定发布](https://github.com/openai/codex/releases/tag/rust-v0.163.0) 的 `draft=false`、`prerelease=false`。
Annotated tag object 为 `129b8ec7ee6f4511557a4856279f529025c25af4`，不能把它误当作源码 commit。
二进制与 bundled bwrap 的 SHA256 保存在 manifest；运行主入口会校验已注册二进制，并将
Tag、Commit、路径和实际 `--version` 追加记录到 run 的 `harness-versions.jsonl`。
未知显式二进制只记录 `commit=unknown`，不冒认锁定版本。

### 独立构建

新版官方 checkout 保持干净；为避免 Windows 挂载盘编译成本，使用独立构建 clone：

```text
source: /home/wqkan/.cache/uaea/codex-build-src/rust-v0.163.0
target: /home/wqkan/.cache/uaea/codex-rust-v0.163.0-target
rustc: 1.95.0 (59807616e 2026-04-14)
```

在构建 clone 的 `codex-rs` 下使用：

```bash
export CARGO_TARGET_DIR=/home/wqkan/.cache/uaea/codex-rust-v0.163.0-target
cargo build --locked -p codex-cli --bin codex --profile dev-small --jobs 2 --target x86_64-unknown-linux-gnu
cargo build --locked -p codex-bwrap --bin bwrap --profile dev-small --jobs 2 --target x86_64-unknown-linux-gnu
```

上游发布 checkout 的 Cargo.lock 把 160 个本地 workspace 包记为 `0.0.0`，与 tag 内
workspace version 不一致，首次 `--locked` 因此拒绝。仅构建 clone 先经 Cargo 生成 lock；
结构化比较确认这 160 项只改为 `0.163.0`，外部依赖与其它字段零变化，再执行上述 locked 构建。
官方 checkout 未改、旧 target 未复用。安装所需 `pkg-config`、OpenSSL 和 libcap 开发包时未升级或删除既有包。
`dev-small` 是上游定义的无 debug symbols 开发 profile，不是性能 benchmark 或 release 构建。

包内 `codex-resources/bwrap` 来自同 tag 的 vendored source。系统 PATH 没有 bwrap 时，
上游会提示改用该 bundled 文件；实际执行与拒绝检查通过，不通过关闭 sandbox 绕过。

## Compatibility Summary

新旧可执行文件分别生成 experimental JSON schema，并对比实际使用的接口：

- `AdditionalContextEntry` 的 `kind/value`、`application/untrusted` 保持；不改 authority 分层。
- `thread/start`、`thread/resume`、`turn/start`、`turn/interrupt`、`turn/completed` 的既有必填字段保持。
- `DynamicToolCallResponse.contentItems/success` 与 token usage、compaction 通知的既有必填字段保持。
- `turn/start` 新增可选 `disabledPluginIds/parentTurnId/rootTurnId`，`thread/start` 新增可选 `daybreakEnabled`；当前不使用。
- 新增可选 tool output retention/audio surface 不自动接入，也不改变 UAEA canonical trajectory 权威。
- 移除生成配置里两版均不识别的 root keys `skip_host_skill_discovery` 和 `disable_response_storage`。
  新版会显式报告忽略，旧版静默忽略；不改为启用其它 feature。Responses 的 `store:false` 由既有客户端维持。

UAEA 只新增 manifest 选择、环境隔离和启动 provenance；主入口、H3 context/File/lifecycle probe 共用选择。
`UAEA_CODEX_VERSION` 在启动进程时读取，优先于 manifest 默认；不支持运行中热切换。
`CODEX_HOME` 与 H3 临时 workspace root 增加 Tag 层级，每个 run 仍独立。旧状态不迁移、不覆盖。
`h25_source_owned_app_server_probe.py` 保留旧版固定引用，用于历史 H2.5 复现，不是当前人工入口。

Harness 继续负责执行 lifecycle、native sandbox、context transport/compaction；UAEA 继续负责
semantic state、执行权威、request/workflow 事实、provider-safe projection、capability 和 evidence。
普通 assistant JSON 从未被提升为真实 Tool Action；失败的 canonical fact 不因 provider-safe projection 而丢失。
本轮没有接入上游 Goal/Memory 功能。`thread/shellCommand` 是上游明确的 unsandboxed surface，
不用于证明 sandbox，也未加入 UAEA 路由；native 验证使用模型发起的 `exec_command`。

## Regression Results

| 验证 | v0.154.0 | v0.163.0 | 证据等级 |
| --- | --- | --- | --- |
| 同一完整 unittest | 395：393 PASS / 0 FAIL / 2 SKIP | 同左 | 单元与本地集成，不冒充真实模型 |
| 原 386 项覆盖 | 保留，原测试未删除 | 同左；新增 9 项版本/环境/配置测试 | Windows 395：389 PASS / 6 SKIP |
| 2 项可选 installed-vLLM 测试 | 安装环境另跑 2/2 PASS | 共用未改动 inference 环境 | 实际 Hermes CPU parser/context，不是 GPU inference |
| malformed → chat → valid File → interrupt → chat → 普通 JSON → reload | 7/7 terminal，0 provider HTTP400 | 同左 | 真实 app-server + controlled provider fixture |
| 同输入本地四轮 Workflow | 4/4；2 次真实 read_section | 同左 | 真实 Qwen + UAEA adapter |
| 同输入 Web 四轮 Workflow | 4/4 terminal；Google 请求 HTTP400、未 fetch | 4/4；Google search + fetch 成功 | 真实 Qwen/网络；不是等价网络成功率比较 |
| pre-turn injection | PASS | PASS | 真实模型 marker |
| native command | 已观察 exit 0 文件读取 | 已观察 exit 0 文件读取 | 真实模型 → Harness native exec_command |
| 显式 compaction / 后续 turn | PASS / completed | PASS / completed | 真实 Qwen；raw/canonical 事件未删除 |
| phase1 scripted benchmark | 24/24 PASS | 共用未变 submodule | 不调用 Harness，也不是新模型能力证据 |

WSL 全量跳过的是两项显式 opt-in installed-vLLM CPU 测试，已在 `/opt/uaea/vllm_env/bin/python`
下另跑通过；Windows 另有四项 POSIX 权限/WSL Bash 启动测试跳过，这四项在 WSL 已运行。
两版真实 Workflow 都保持同 workflow/root、调用身份、request 与结果关联、投影 <=2400，
canonical JSONL 经 reader/validator 检查；有模型叙述错误时不据此产生执行事实。
归档 trajectory 文件的只读 sequence/schema 校验通过；
主仓库及本轮 artifact 文件的真实 key 字节扫描未发现泄露，不输出 key 值。
扫描范围与数量见外部 `trajectory-validation.json` 和 `secret-scan.json`；
默认版本及版本隔离目录切换后，另一次四轮真实运行与无版本 override 的七轮协议检查也通过。
新版直接 sandbox 检查：读取 README 成功，写入拒绝 `errno=30`，网络访问拒绝 `errno=1`，
`NoNewPrivs=1 / Seccomp=2`。未放宽任何执行授权。

完整外部证据目录：`D:/UAEA-runtime/harness-upgrade-20261022`，不加入 Git。
其中 `schema-comparison.json`、`build-result.json`、各版本 `*-unit-release-check/unit-result.json`、
`*-interrupt/*/recovery-report.json`、`*-local*/*/*/workflow-continuity-summary.json`、
`*-live/*/*/workflow-continuity-summary.json`、`*-compaction/*/result.json`、
`candidate-native-explicit/*/result.json` 和 `sandbox-direct/denial-result.json` 分别保存独立证据。
初次构建失败、相对路径 File 被拒绝及模型只输出 JSON 的尝试均保留，不用成功重跑覆盖。

### 未解决但未证实由升级引入的风险

- 两版均曾输出普通工具 JSON 而未执行；新版明确指定 native tool 的诊断成功。不能宣称自然工具选择已稳定。
- compaction 后模型仍可能编造/误述文件事实；压缩 lifecycle 成功不等于 summary 的语义正确性。
- Web 对照旧版带 `language=zh` 请求遇到 SerpApi HTTP400，新版参数不同而成功；未更改 provider、网络或 timeout 来掩盖差异。
- 当前真实多轮输入约 15K；未做 32K 极限负载、自动阈值 compaction 或性能 benchmark。显式 compaction 的事件与续轮已验证。
- model-generated hallucination / request recovery 的既有 PARTIAL 不在依赖升级中扩成 cognition 修复。

## 查询、启动与回退

在现有 WSL 中：

```bash
cd /mnt/d/UAEA
python3 scripts/harness_version.py --verify-binary
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

单次显式回退，不改 manifest、不重用新版 thread/home：

```bash
UAEA_CODEX_VERSION=rust-v0.154.0 python3 scripts/harness_version.py --verify-binary
UAEA_CODEX_VERSION=rust-v0.154.0 bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

同一 shell 持续选择旧版可 `export UAEA_CODEX_VERSION=rust-v0.154.0`；
`unset UAEA_CODEX_VERSION` 恢复仓库默认新版。永久默认只修改 manifest 的 `active_version`。
已存在的 `8002` 会继续被拒绝复用，须先在原会话 `exit`；不影响 frozen `8001`。
Web 私有环境仍由统一入口加载；SerpApi key 不传给 Codex 子进程或版本查询子进程。
manifest 不含凭据，未来 Installer 可以读取，当前不引入 Installer/数据库。

复跑诊断时在新目录保留结果，版本由同一环境变量选择。例如：

```bash
UAEA_CODEX_VERSION=rust-v0.163.0 python3 scripts/h3_failed_attempt_recovery_probe.py --interrupt-smoke
UAEA_CODEX_VERSION=rust-v0.163.0 python3 scripts/h3_workflow_continuity_probe.py --scenario local --turn-timeout 420
NO_PROXY=127.0.0.1,localhost,::1 no_proxy=127.0.0.1,localhost,::1 UAEA_CODEX_VERSION=rust-v0.163.0 python3 scripts/h3_app_server_lifecycle_probe.py --compaction-smoke --turn-timeout 420
```

最后一条 legacy lifecycle probe 不加载 Web 环境，只用本地模型；显式 localhost bypass 避免系统代理影响本地健康检查。
本轮不自动推进任何 Goal/Memory 或 Web redesign。
