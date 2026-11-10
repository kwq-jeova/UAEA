# 2026-11-05 大量网页读取后不再回复：只读诊断

会话：interactive-32768-20261105-013051。
结论：存在客户端等待/事件消费衔接问题，未发现“Runtime 因读取量大而禁止最终回答”的证据。Research Workflow 未完成。
本轮仅分析，不改代码、不重新测试模型、不停止当前8003服务、不Commit/Push。

## 直接事实

- 6个真实用户Turn；5个completed，第6个没有终结记录。第5个虽completed，但只说“继续获取后续内容”，并未完成要求的最后推理。
- 全会话19次真实工具请求：6次成功Search、3次Search校验拒绝、10次Fetch（4次网络成功、2次缓存续读成功、1次401、3次429）。
- 最后一轮12次工具请求后进入第二次Compaction；第一次pre-turn Compaction完成，第二次mid-turn未在Raw Events中记录完成。
- 第6轮09:46:23左右开始；09:52:14开始mid-turn Compaction；09:53:23客户端wait_timeout（420秒）；09:53:43记录new_input_blocked。
- 该新输入未被发送、未作为新的用户请求保存，避免混入仍未终结Turn；不是答案审查拒绝。
- 第18次模型出站请求明确request_kind=compaction、tools=[]。上游HTTP200，收到166331字节协议流后Bridge记录BrokenPipeError；这不是166331字符回答，更不能证明已生成完整答案。
- BrokenPipe只证明Bridge向下游写入失败。当前日志不能精确证明是手工退出、其他客户端关闭还是具体哪次关闭动作；不把它写成模型或Runtime主动拒答。
- 17份已完成模型响应记录中，最大inputTokens=26935；最后普通推理为25297。没有HTTP400 Context超限拒绝、Host ContextBudgetError/413记录。
- modelContextWindow=31129是Harness有效窗口，vLLM配置32768；不能把累计313464 Tokens当成单次Context。
- 检查时8003仍监听；guard run-policy=manual、service_timeout_seconds=null；未出现此次service的CASE_TIMEOUT记录。smoke_limit/smoke_stale是启动自检，不能当实际内存事故。
- 运行清单74/74源码hash与当前一致，确实使用上一轮修复版本。

## 真正的执行拒绝

execution-contract.trajectory.jsonl:16、18、20的Observation：
- 模型allow_fallback=true，未指定provider；
- Shared Decision准确原因为authorization_unknown（回退授权未知）；
- 允许Google且allow_fallback=false的后续搜索成功，证明不是整个Web功能被禁用。
- 用户本轮原话指定Google，不含明确“禁止回退”；不能将本次精确拒绝原因写成明确禁止回退。
- 恢复结果给出allow_fallback=false、请求用户授权或报告阻塞等合法选项；恢复投影constraints_known=false/active_constraints=[]，而Host后续compatibility_guard仍保留web.provider=google。此为失败说明存在信息差，未证明Host约束丢失，不应据此扩大权限。

401/429是目标站点HTTP响应，不是Runtime据此禁止模型输出。
本轮没有外部政治事实核验，不认可模型经济/政治断言仅因来源标题存在。

## 证据仍然没有读完

以Fortune同一source_event_id WEB-LIVE-380c2003-8d34-4d5b-9c18-de893f58d5e6为例，实际供给：
- app-server-events.jsonl:3237：0–1159 / 6357。
- :3454：1159–2133 / 6357。
- :3644：1459–2433 / 6357。
最后一次没有使用上一份next_start_char=2133，而从1459开始，重读674字符。
这三个片段的覆盖并集只有0–2433，不是全文。不能把Capability内部申请3000字符与实际供给范围混同。
Business Insider最新供给:3645为0–1324 / 4764；旧快照/新快照不能仅凭URL自动合并版本。
相比上轮“完全不续读”，此次模型真实使用了两次缓存续读；但游标使用和完成研究仍PARTIAL。

## 客户端衔接缺口（源码证据）

scripts/h3_harness_interactive_repl.py：
- _wait_for:860–950消费事件队列、记录Raw Events、分发工具和显示回答。
- _request_turn:829起，超时保留pending Turn，并不取消原生Turn。
- main:1289–1299返回同步read_user_input等待stdin。
- run_turn:458起仅在新输入到达时短暂_resume_pending_turn(0.05)，未终结则拒绝新请求。
- /turn wait恢复消费同一Turn事件；/turn cancel向已知ID请求中断，ACK本身不能释放门禁。

因此420秒后“停止等待但继续保持原生Turn”与“同步等待stdin”组合，会暂停主线程的持续事件消费。
模型服务可能仍在生成；队列中的后续回答/工具请求/终结事件不会在空闲stdin期间持续处理。
这是已确认的代码级缺口；本次第二次压缩究竟产生了什么最终摘要，因流断开和缺少终结记录仍UNKNOWN。
不能删除pending门禁解决，否则会把新请求与旧Turn/Observation串在一起。

## 最小方向与即时操作

即时：若原Harness会话仍在pending提示，可输入 /turn wait，让同一Turn继续接收/处理事件。不要反复发“继续”作为新任务。
需要中止时用 /turn cancel，等待实际终结；若该Harness已关闭，以上控制命令无法恢复已结束进程，不能声称新会话自动恢复旧Turn。

最小修正候选：
1. 等待stdin期间仍服务已有Turn事件，将等待超时视为客户端提示，保留新请求隔离、明确取消和资源保护。
2. 状态展示区分生成、工具执行、Compaction、超时等待；不能以一次stdout沉默判模型停了。
3. Recovery说明应引用已知Google约束；不能把未知授权提升为允许。
4. 缓存续读继续使用真实next_start_char；不强制每轮调用工具，也不靠抬Context/取消安全保护解决。

本轮没有修改上述代码，亦没有以诊断作为新的行为验收PASS。
