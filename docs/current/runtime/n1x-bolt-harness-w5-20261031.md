# N1X Bolt Harness W5：PARTIAL
日期：2026-10-31。证据：/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/w5-20261031T095325Z；修正后复测：/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/w5-corrected-20261031T101203Z。

## 当前人工入口
统一入口与原Qwen默认连接保持不变。受保护的Bolt服务在8003就绪后：
```bash
bash /home/wqkan_wsl/uaea-n1x/UAEA/scripts/start_h3_harness_interactive.sh \
  --profile n1x --vllm-mode external --context 32768 \
  --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x \
  --reasoning-effort none --turn-timeout 420
```
该命令只连接外部服务，不加载模型、不代替Windows资源保护。
当前模型服务已停止，监控可靠性未重新验收；不要据此直接开启长期服务。
新--reasoning-effort low/medium/high只完成实现及离线回归，真实Bolt低effort验收未完成。默认none保留原配置行为。

## 结论
- 冻结Codex rust-v0.163.0/83086188ae0614bd882818ff1aa23f3194962012 ARM64，Bolt32K/单并发/Eager/固定1GiBKV/36GiB规划不变。
- app-server/Responses SSE、结构化动态调用、Runtime Observation和5轮基本链路成立。
- Bolt搜索1成功1超时；真实Fetch3次均网络不可达，没有成功取得正文。
- 两模型自然语言切换后task_id未变，不能宣称Goal/Evidence切换或研究完成PASS。
- 修正后复测因CIM内存采集超时终止于Qwen第4轮，没有再次启动Bolt；Thinking等补测NOT_RUN。

## 局部改动
1. 投影已知文件工具根目录，区别于Harness临时cwd；不扩大Sandbox。
2. effort从硬编码none改为可配置，写入配置和turn/start，默认none。
3. 非交互启动缺少代理时继承既有~/.config/wsl-proxy/proxy.sh，尊重disabled标记。
4. 单测及相邻夹具对齐；126项离线回归通过。
没有修改旧Qwen环境、Codex Core、Phase-1 Runtime、Kernel或系统内存配置。

先恢复并无模型验收监控采集可靠性，再补做Bolt路径、Thinking与真实正文获取；任务Scope问题独立处理，不扩展Goal/Memory。
历史记录保留，未Commit/Push。本轮已停止。
