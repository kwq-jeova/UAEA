# 人工研究末尾未推进：Apple 阶段核查（2026-11-05）

会话：/home/wqkan_wsl/uaea-n1x/runs/unbounded-manual/interactive-32768-20261105-071627/

结论：**Apple Research Workflow 未完成；Runtime 拒绝契约限定 PASS，模型恢复执行 FAIL。** 未发现 Apple 阶段因 Context 溢出、固定等待超时或工具悬挂而卡死的证据。本轮仅分析已有 JSON、源码及进程状态，没有修改功能代码、启动模型、访问 Web 或停止服务。

## 实际发生的事

1. 用户提出“同样的方式分析apple，现在40倍pe是不是高估了”（Raw Events:9135）。
2. 模型连续提出两次 Google 搜索，但均显式携带 allow_fallback=true：
   - chatcmpl-tool-b4577f1a198972c3；
   - chatcmpl-tool-aa3d25e367864b11。
3. 当前 provider_switch 授权未知，两次均在执行前被拒，未发出 Apple 搜索 HTTP 请求（Canonical Observation:66、68；实际 Tool Result:9180、9188）。
4. 两条拒绝结果已含正确的 Google 约束、web.provider_fallback 局部作用域和 allow_fallback=false 的合法新提案路径。实际出站请求 #41、#42 均完整包含这两条恢复记录。上一轮的投影修复确实生效，不是仍在使用旧代码：运行清单 74/74 文件哈希与当前源码相符。
5. 模型没有改用合法参数，也没有执行其文字提出的 web.fetch。它只输出“先去 Yahoo Finance 搜索……”并在 08:02:56 UTC 结束 Turn（Raw:9274、9281）。
6. 用户输入“继续”后，模型仍只说“先尝试用 web_search……”，没有新 Tool Call，于 08:03:34 UTC 再次 Turn completed（Raw:9377、9384）。

因此：看似“没有继续处理”的时段，实际上原生 Harness 已收到模型的普通最终文本并结束当前 Turn，没有在后台等待其承诺的操作。模型的行动叙述不是执行，Turn completed 不是 Workflow completed。当前边界不应凭一句“准备搜索”自行生成工具行动或复制 Harness 循环。

## Context、错误回传及服务状态

- Apple 拒绝后输入 19,019 Tokens；“继续”输入 19,233；报告的有效窗口为 31,129。对应请求均 HTTP 200，无原生 error 事件。
- 本会话此前有 5 次 Compaction 完成；最后一次在 Raw:7373，早于 Apple 阶段。Apple 阶段没有正在进行的 Compaction，也没有超预算拒绝记录。历史压缩对认知的潜在影响不能完全排除，但不是此次“卡在压缩/请求溢出”的证据。
- 拒绝结果顶层 message 因预算出现 field truncated，但 recovery.failure_explanation、合法参数、约束、作用域在实际请求中完整保留。不能把这两个顶层短文截断判为恢复指令丢失。
- 本次前面已有 15 次 Google 搜索成功，Intel 阶段也成功搜索/Fetch，不能判断动态 Web Capability 被整体禁用。
- 本轮检查时 8000/8003 均无监听，Harness/vLLM 相关进程不在运行。对应 Bolt final-cleanup.json 记录 CONTROLLER_STOP、remaining=[]，结束于约 08:04:03 UTC；不是记录为内存阈值触发。
- 这次检查未重启或终止任何用户进程。服务停止的具体人工操作来源不作推测。

## 末尾取消输入是另一个独立问题

Raw:9394 的实际输入为：

~~~text
/ turn cancel
~~~

斜杠后多了空格，当前 CLI 将它当成普通用户消息，创建新 Turn。正确命令：

~~~text
/turn cancel
~~~

随后生命周期仅记录 wait_interrupted，不能宣称收到原生取消完成事件。最后一次出站请求 #43 属于该误输入的新 Turn，未记录返回；它与此前两个 Apple Turn 已正常结束是不同事实。取消拼写不是 Apple 研究停滞的起因。

## 归因与最小下一步

**VERIFIED**

- Runtime 保留 Provider 约束，拒绝未授权回退；修复后的局部错误与合法恢复已真实送入模型请求。
- 模型重复 allow_fallback=true，未按恢复选项继续，随后以计划文字结束；“继续”也未产生实际行动。
- Host 仍将 Workflow 完成依据标为未建立。

**UNKNOWN / HYPOTHESIS**

- 模型为何选择 true、为何明知失败却转成计划式最终文本，其内部原因不可由日志证明。
- 工具 Schema 仍写“用户禁止回退时设 false”，没有完整表达“未知授权不等于允许”。这是可核查的接口表达不足，可能有贡献，但不是重复失败的已证实唯一原因。
- 不能凭当前记录判定更换模型、增加 Prompt 或再提供相同提醒必然有效。

下一步宜先做一个短小、自动化的失败恢复对照：同任务、同 Policy、同源记录，核对模型是否提出合法新行动并实际使用返回结果。先审查工具声明是否准确表达既有授权契约；不扩大回退权限、不静默改写 true、不添加强制每轮工具执行。没有必要先请用户再做一轮长财报研究。

未改功能代码、未 Commit/Push。原人工入口与安全策略保持不变。

详细提取与源文件哈希：/home/wqkan_wsl/uaea-n1x/research-records/manual-apple-stall-audit-20261105T081229Z/
