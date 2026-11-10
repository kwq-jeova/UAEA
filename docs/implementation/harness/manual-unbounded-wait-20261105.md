# 2026-11-05 人工入口：不限时等待与持续事件处理

限定 Client Contract PASS。335 项定向回归通过，真实模型长任务尚待人工复测，不能扩大为 Model Behavior / Workflow PASS。
本轮未重启或停止现有 Bolt 服务，未加载模型、改变依赖或安全阈值，未 Commit/Push。

## 修改

- 统一人工 REPL 默认 --turn-timeout 0 --user-input-timeout 0。0 归一化为 None，表示没有整轮任务期限、没有用户答复期限。
- 等待原 Turn 期间持续处理消息、工具调用、Compaction 和终结事件，不在420秒后自动返回输入提示。
- 主动 Ctrl+C 返回控制提示时仍保留 pending Turn；可查看、继续等待或明确取消，不伪造取消/完成。
- 有 pending 时，复用现有终端 on_idle 继续消费原 Turn 事件；无 pending 时保留原输入方式。没有新增 stdin 线程、执行循环或 Runtime 状态机。
- 新请求隔离保留。/turn cancel 请求原生中断，必须收到实际终结才能释放；10秒取消控制交接结束不代表任务已停，pending仍继续处理。
- 人工 Bridge 的模型响应读取不限时；建立/发送回环连接保留10秒故障检查。其他调用方默认的有限 Bridge 配置不变。
- Run Manifest 记录两个 timeout 为 null、turn_wait_policy=unbounded；启动显示 Turn=unlimited; user reply=unlimited。
- 明确正数仍可用于有限实验；独立自动实验驱动未修改。共享人工 h3/n1x Profile 都采用不限时默认，端口、路径、Managed/External 选择不变。

## 保留的故障与安全边界

Windows Commit、物理 Available、GPU、WSL、Swap、监控新鲜度与 Fail-Closed 不变。
模型服务已有 manual 生命周期不变。初始化/健康检查、网页请求、进程清理等故障处理仍有各自有限等待。

固定 Codex rust-v0.163.0 内部仍有默认300000ms无流事件检测：
codex-rs/model-provider-info/src/lib.rs:66,513–516。
这是无模型流进展时的协议故障检测，不是整个任务只能运行300秒。
本轮未改 Codex Core/二进制，不能宣称已取消整个协议栈的所有超时。完全无流进展的极慢请求仍可能失败，须保留真实错误及未完成状态。
时间经过、用户回答和模型摘要均不自动授予权限或采纳 Goal。

## 验证

25个隔离模块，共335项，0 FAIL。新增13项覆盖：

- 无期限长时间模拟后仍处理工具、压缩和最终回答。
- 显式有限实验、pending身份及匹配Turn终结。
- Ctrl+C、恢复等待、取消与不伪造完成。
- 实际stdin管道与空闲事件消费，没有竞争读线程或日志洪泛。
- Native用户答复不限时、不自动选项、不自动授权。
- Harness退出能打断等待。
- 实际CPU回环HTTP验证：connect timeout=10，read timeout=None，SSE成功。
- CLI默认0、显式正数、非法负数及非有限值校验。

已有Shared/Legacy、Provider、Goal、Context/Compaction和Evidence回归通过。
独立无模型Manifest生成验证：两个timeout=null，等待策略unbounded；该文件不是模型运行验收记录。
16项启动/环境/旧Qwen UMA pin一致；Phase-1 submodule干净；Python AST、Bash语法及git diff --check通过。
检查结束8003仍监听；没有调用真实推理API或调整资源保护。

## 修改文件及回退

代码仅：

- scripts/h3_harness_interactive_repl.py
- harness/responses_bridge.py

新增测试：tests/test_manual_unbounded_wait.py。
研究记录由 ~/uaea-n1x/research-records/manual-unbounded-wait-current.txt 定位，含本轮前文件备份、精确Diff、回归日志、Manifest及hash。
工作区包含前几轮成果，回退应选择性对照本轮备份，不覆盖其他历史修改。

## 当前人工入口

现有8003服务可以继续用。重开Harness加载客户端修改即可；旧会话不会热更新，新进程也不自动恢复旧Turn。
将旧命令中的 --turn-timeout 420 改为0，避免显式覆盖新默认：

~~~bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
bash scripts/start_h3_harness_interactive.sh \
  --profile n1x --context 32768 --vllm-mode external \
  --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x \
  --execution-contract shared --goal-mode shadow --goal-projection optional \
  --reasoning-effort none --turn-timeout 0 --user-input-timeout 0 \
  --result-root /home/wqkan_wsl/uaea-n1x/runs/unbounded-manual
~~~

模型处理期间不需要反复输入“继续”。需要主动处理时，Ctrl+C返回控制提示，/turn status查看，/turn wait继续，/turn cancel请求实际中断。
在普通输入提示处Ctrl+C或exit退出Harness，External模型仍独立运行。
本次不保证研究结论正确、页面读全或401/429消失；下一步可复测同类长网页任务，不需要制造资源压力。
