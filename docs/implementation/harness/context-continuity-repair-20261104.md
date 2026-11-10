# Context / Long-Turn 连续性最小修复（2026-11-04）

状态：**限定工程验证 PASS；Model Behavior / Real Workflow 待人工验收。**
依据：人工会话interactive-32768-20261104-131820；对应JSON审计已独立保留。
本轮未启动模型、关闭外部服务、修改依赖或资源保护，未Commit/Push。

## 1. 长Turn状态交接

修改scripts/h3_harness_interactive_repl.py：
- 外层等待超时后保留原始start请求、native Turn ID和原输入ID，不把超时等同完成/停止。
- 旧Turn仍active或身份未知时，新自然语言请求在prepare_turn之前被阻止，明确显示“未发送、未保留”，不能悄悄覆盖当前请求。
- /turn wait继续消费原Turn事件，不新增turn/start、不重发工具；/turn status显示最后观测状态。
- /turn cancel仅中断已识别的本会话Turn，等到对应终结事件才解锁；RPC ACK本身不算停止确认，身份未知时拒绝猜测。
- 迟到的Goal最终输出仍绑定原input_id；外来Turn终结不更新当前语义状态。
- 运行清单新增turn/user-input timeout和reasoning effort，生命周期写入turn-lifecycle.jsonl。
- 未创建第二套Agent执行循环；原Harness保留模型及工具循环。外部vLLM生命周期不变。

局限：超时后等待用户选择wait/cancel期间，不保证Host持续消费后续队列；这是明确的待处理状态，非后台完成承诺。
模型/进程断联且无法确认停止时保持阻止新输入，允许退出本Harness；不因“超时”自动停止外部模型服务。

## 2. 重复失败投影

修改harness/provider_history.py：
- 已确认失败的一对proposal/outcome仅在outcome位置投影一份terminal fact。
- 缺少outcome的拒绝仍保留proposal事实；不同call_id不合并，成功调用/结果不改。
- 原始消息、执行Observation及逐项hash审计保留；新增projection_effect说明何项合并。
- 本次真实历史最后请求离线回放：8份→4份，事实文本6950→3473字符；4个call的state/reason/observation/replayable一致，8项原始审计决定仍在。
- 回放用已保存的native rawResponseItem重建失败对，不声称是恢复原始wire bytes，也不宣称节省了同等比例Token。

没有新增“禁止模型重试”的认知规则。新call_id重复访问同一受限URL仍可能发生，需作为Model Behavior检查。

## 3. 有界正文续读

修改phase2/web_capability.py、phase2/web_context.py、harness/codex_dynamic_tools.py及统一入口工具声明：
- 沿用web.fetch；默认URL获取与原有900字符配置保留。
- 新增可选source_event_id、start_char、max_chars（1..3000）。
- 非零偏移必须提供同一运行数据库中成功页面的来源ID及匹配URL，续读同一份保存快照，不隐式重新联网。
- 检查快照位于本adapter目录、文件存在、原始hash正确；提取时也校验实际读到的字节。缺失或变化即拒绝，不用旧数据库摘录冒充原快照。
- 分段使用同一规范化提取文本坐标；返回文本hash、起止、总提取长度、提取文本hash和next_start_char。
- 工具输出仍受5000字符预算；请求3000不保证全部供给。若再截断，游标/hash按实际供给片段重算，防止下一次跳过未读部分。
- 缓存续读明确http_attempted=false、acquisition_mode=retained_snapshot、http_status=null，保留原snapshot_http_status及原观察时间。
- 保持Action/Observation和来源身份分离：新读取事件不等于新外部来源或独立语义支持；没有权限扩大或新Information Pool。

修改harness/semantic_state_adapter.py：
- Compaction恢复前缀仍有界300字符，但保留实际段落坐标和提取版本引用。
- 相同来源/版本/片段的重复恢复引用去重，避免占满三个恢复槽。
- 300字符恢复不冒充完整正文或完整历史；可通过来源ID续读本Run快照。

真实保存页面CPU回放：
- 经Registry→Shared Boundary→模型结果投影，NPR保存页面第900字符之后成功读取。
- 在现有5000字符输出预算中，中段实际供给947字符，next_start_char=1847。
- 再续读405字符；900+947+405=2252，拼接hash与完整提取文本hash一致，零新HTTP。
- “完整提取快照”不等于页面全貌、突破付费墙或来源语义真实。HTTP200挑战页仍由模型结合正文判断，不增加站点关键词规则。

## 4. 验证与范围

14个模块隔离运行：**230 PASS、0 SKIP、0 FAIL**，含21项新增定向测试。
覆盖timeout/迟到ACK/外来终结/取消确认/原Goal输入绑定、失败事实去重、快照版本/URL/路径/篡改/缺失、中文游标、预算截断、Shared读取、恢复引用与权威不变。
既有Web、Context预算、Goal、执行契约、版本及平台配置回归通过。
N1X/5090D共享实现，无模型专属语义规则；5090D只做离线公共路径回归，未在5090D实机运行。
前期新测试的HTTP fixture类型/方法名错误已修正；定向测试同时发现并修复了分段重复strip引起的游标偏移。没有修改标准让偏移通过。

源代码6个实现文件、2个测试文件：
- scripts/h3_harness_interactive_repl.py
- harness/provider_history.py
- harness/codex_dynamic_tools.py
- harness/semantic_state_adapter.py
- phase2/web_capability.py
- phase2/web_context.py
- tests/test_context_continuity_fix.py（新增）
- tests/test_harness_provider_history.py（调整一份终结事实的期望，继续校验原始审计）

## 5. 未解决的问题

- 模型自动续读、主动选择来源、因果推断及引用归属仍待真实交互。
- 未宣称修复Compaction摘要的语义错误；原始请求/执行记录独立保留，不让摘要自行提升权威。
- 旧Topic/Task Relation的语义判定、Google主题补造和Goal解释纠正未通过关键词补丁处理。
- 403/401/451和挑战页不绕过；连续无效重试仍可能来自模型。
- 本轮没有提高32K窗口、KV预算、推理输出上限或放宽安全阈值。
- 本轮不构成Goal Formation、正式语义撤回或长期建议价值PASS。

## 6. 人工验收及回退

使用全新Harness会话，保持Shared显式开启、Bolt External8003、Goal Shadow/optional，沿用受保护启动器。
详见[人工测试指南](context-continuity-manual-20261104.md)。旧会话未热更新，请退出后新开。
结果需要分别评价Contract、Model Behavior和Workflow；无需用户写JSON或手工编写工具参数。

本轮记录：
/home/wqkan_wsl/uaea-n1x/research-records/context-continuity-fix-20261104T135944Z

before/只保存本轮修改前文件；change.patch、source-hashes.json及回归日志用于审阅和回退。
回退应按本轮Diff逐项审查，不使用全仓reset/clean，不覆盖既有研究或后来用户变更。
