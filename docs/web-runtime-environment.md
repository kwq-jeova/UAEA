# UAEA Web 私有启动环境

本文件描述当前有效的私有启动环境。Google provider 已通过 SerpApi 接入；当前边界结论见
[Boundary Integrity Audit](boundary-integrity-audit-20261002.md)。本环境 helper 不修改 Harness Core 或 inference 配置。

## 一次性设置

在 WSL 中执行：

```bash
cd /mnt/d/UAEA
python3 -m phase2.web_environment --init-private-env
nano ~/.config/uaea/web.env
chmod 600 ~/.config/uaea/web.env
```

初始化只创建新文件，权限为 `600`，不会覆盖已有文件；代理值从当前环境复制，`SERPAPI_KEY` 留空。
在私有文件中填写真实 key。代理应填写实际 Clash HTTP/Mixed 端口，例如 `http://127.0.0.1:7897`；
同一代理的大写和小写变量必须一致。不要把 key 发到聊天、命令行、截图或仓库中。

```text
SERPAPI_KEY='<在私有文件中填写>'
HTTP_PROXY='http://127.0.0.1:7897'
HTTPS_PROXY='http://127.0.0.1:7897'
http_proxy='http://127.0.0.1:7897'
https_proxy='http://127.0.0.1:7897'
```

文件使用简单 env 赋值，可选 `export`；loader 不执行 shell 命令，不进行变量替换或命令替换。
默认位置是 `~/.config/uaea/web.env`，可通过 `UAEA_WEB_ENV_FILE` 指定其它仓库外路径。
已有非空进程环境优先于私有文件；不要残留旧的临时 export，以免覆盖私有配置。
loader 校验 POSIX 文件所有者与 `600` 权限，统一代理大小写，并为 `NO_PROXY/no_proxy` 保留
已有配置且补充 `localhost,127.0.0.1,::1`，防止本地 inference 请求进入 Clash。
`SERPAPI_KEY` 只留在 UAEA Web 所在进程，不传给交互 app-server 或 vLLM 子进程，避免 native shell
从继承环境中读取它。私有文件不是对同一 Unix 用户的安全隔离；native File 仍受现有 sandbox 约束。

## 统一人工入口

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

原有直接入口同样加载公共 helper，无需手工 export：

```bash
python3 scripts/h3_harness_interactive_repl.py --turn-timeout 420
```

旧 Phase-2 Web REPL 的 Python 入口也复用同一 helper；其 backend 和执行路径不变。
只有 Web 启动入口加载该文件，不扩展到不使用 Web 的 H3 File/context/lifecycle probe。

配置缺失时人工入口明确 warning，保留现有 DDG/Bing 能力；不把缺失 key 误报为“Web 全部不可用”。
文件不安全或配置无效则在启动 inference 前失败。检查与 SerpApi smoke 模式要求代理和 key 均存在：

```bash
bash scripts/start_h3_harness_interactive.sh --web-env-check
bash scripts/start_h3_harness_interactive.sh --web-env-smoke
```

这两个模式不启动 `8001`、`8002` 或 app-server。smoke 使用固定公开查询，可能消耗一次 SerpApi 配额。
只输出 credential availability、服务名、返回的 engine 与结果数量；不写 trajectory、source history 或响应快照。
SerpApi 请求 URL 含接口要求的认证参数，但只在内存用于 HTTPS transport，绝不作为 provenance URL 保存或打印。
不跟随重定向，错误响应、异常 URL 和原始响应均不输出。

`--web-env-smoke` 只验证环境与认证 transport，不代替 capability/model-mediated 验收。
Google backend 的独立接入历史见 [阶段记录](google-backend-phase1.md)；统一启动方式保持不变。

## 历史验证（2026-10-01）

- 实际 WSL 新子进程清除 key、代理及 `NO_PROXY` 后，经统一 wrapper 的 `--web-env-smoke` 启动。
- 私有文件权限 `600`；代理与 `SERPAPI_KEY` 均从文件加载为 `SET`；认证请求返回 Google engine 与有机搜索结果。
- 74 项 targeted/regression、219 项全量 unittest 通过；`py_compile`、Bash 语法检查与 Windows Git 的 `git diff --check` 通过。
- 针对真实 key 扫描仓库文件、当前 diff，以及最近两次人工 run 的日志、JSONL、SQLite 与页面快照：未发现泄漏。
- 测试未启动 inference/app-server；`8001` 未触碰，`8002` 的 32K、`0.75` 与 Hermes 参数保持不变。

全量测试显式指定仓库为 discovery 顶层，避免 `tests/memory` 与项目 `memory` 包同名：

```bash
python3 -m unittest tests.test_web_environment tests.test_h3_interactive_schema tests.test_harness_dynamic_tool_adapter tests.test_web_adapter_shell
python3 -m unittest discover -s tests -t .
```

该共享 checkout 使用 Windows Git 的 CRLF 规范化；WSL Git 的默认配置会把历史 CRLF 文件视为变更。
本轮不批量改历史行尾，diff 检查沿用 Windows Git；只为新 Bash wrapper 指定 `eol=lf`。
