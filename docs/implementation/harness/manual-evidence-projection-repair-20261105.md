# 2026-11-05 人工测试其余问题收敛：Evidence / 历史 Topic / 关系提示

结论：限定 Contract PASS；Model Behavior 和 Research Workflow 本轮未测，不能宣布修复通过。
本轮没有启动模型、发起网络搜索/抓取、修改模型环境、安全保护或 Commit/Push。
CASE_TIMEOUT 生命周期修复沿用上一轮，本报告不将其重复计为新成果。

## 1. 问题与最小修正

- 成功 Fetch：保留 5000 字符整包上限，采用紧凑 JSON，删除重复 capability/tool、重复 EvidenceReference 投影；完整 Observation/引用保留于 Host，模型侧保留 URL、access_event_id、source_event_id、hash、实际范围和执行结果。
- Shared Decision：仅减少重复 schema/说明文字，保留 action/input/workflow/state/policy 引用、allowed、authorization、实际参数和参数来源；完整 Decision hash 对应 Host 原始决策。没有改变执行或授权判断。
- 正文 message 按实际供给范围生成：明确仍有未读保存文本，指出同一 URL/source_event_id、start_char=next_start_char 的缓存续读方式；到达保存提取文本末尾也不声称完整网页或语义支持已验证。
- 搜索：优先保留原有最多三条完整候选身份，再根据剩余预算供给摘要。此前仅尝试 120 字符或零摘要；现在上限 600、按预算有界降低。摘要保持原文前缀，省略用 snippet_truncated 表示，不将人为“field truncated”提示拼进来源文本。
- 原始后台/保留/模型可见数量、时间声明、Provider 与安全边界保留。候选可见不等于已读取正文或相关性已验证。
- 发现额外的字段口径问题：旧 evidence_extent.source_text_chars 实际来自快照 content_chars，HTML 时包含标记。本轮模型侧改名 snapshot_content_chars；提取文本总量仍用 source_excerpt.extracted_text_chars，两者不得混同。Host 原指标不改写。
- 旧 Topic 在模型侧明确命名 background.historical_topic；当前请求仍由 workflow_continuation.current_request 与当前原始输入提供。没有自行推断或采纳新 Goal。
- “未检测到关系词”不能证明任务切换：仅在非权威模型投影中提示 unknown。历史内部 legacy new_task 记录保留；没有更改 Phase-1 枚举、Workflow Owner 或约束作用域。已有显式任务边界函数被复用，使明确切换获得独立理由，不会也被投影成 unknown。
- 没有新增站点/政策/经济话题专属规则；模型未读取却作具体结论、无依据声称权限不足，仍需按模型行为评价。

## 2. 同一批真实 Observation 离线回放

来源：interactive-32768-20261104-235745 的 execution-contract.trajectory.jsonl。
真实历史记录不变；将记录的 Decision/Observation 重建为动态工具响应，比较修改前后投影。
这是离线重放，不是新的搜索、Fetch 或模型实际接收证明。

| 来源 | 原实际供给字符 | 修改后供给字符 | Capability 原摘录字符 |
| --- | ---: | ---: | ---: |
| Guardian | 712 | 1097 | 3000 |
| BBC | 1391 | 1719 | 3000 |
| Houston Public Media | 686 | 1083 | 3000 |
| PBS | 950 | 1337 | 3000 |

四篇仍未在单次响应中供给全文；保持预算，不通过抬 Context 获得完整性。
五次搜索均保留三条身份和非空摘要（此前四次三个摘要全为零）；原始命中数量没有因此改变。
每段输出 JSON 可解析、整包≤5000字符；前缀、供给 hash、游标和 temporal_facts 与相应记录一致。
Host 原 Observation、Decision 未修改，不用模型文字证明执行。

## 3. Shared 缓存续读闭环

- 复制历史 SQLite 到独立研究目录，原 SQLite、Canonical 轨迹、Raw Events 哈希前后不变。
- 复用真实保存的四份页面快照，禁止 HTTP；SharedExecutionBoundary → Capability → Observation → 动态 Tool Result 实际执行。
- 按实际供给 next_start_char 受控续读，Guardian 9段、BBC 4段、Houston Public Media 5段、PBS 7段。
- 拼接分别为 7712、6478、4367、8439 字符，等于原保存提取文本长度且完整提取 hash 一致。
- 每段 http_attempted=false、http_status=null、snapshot_http_status=200；没有制造新的网络观察或刷新来源版本。
- 这25段是脚本选择的受控续读，不是模型主动采取25次行动。段数仍有 Context 成本，不能据此要求每轮或每篇必须读完。
- ActiveGoal 保持 null；到达已保存提取文本末尾不能证明原网页完全获取、正文抽取无缺失或结论得到支持。

## 4. 自动化验证

21个定向模块共295项，0 FAIL。新增10项涵盖 Unicode/引号/换行供给 hash、非零续读、末尾范围、快照与提取长度、时间/授权保留、坏hash拒绝、搜索预算和历史上下文。
包括已有 Shared/Legacy、Goal、Compaction/Context Budget、恢复/失败回传、请求连续性及 Provider History 回归。
最后一次字段名称/省略提示调整后，受影响的3个模块40项重新通过；其余模块未受调整影响，采用同轮已保存结果。
8份真实历史 Semantic Snapshot 重新投影：当前请求、约束、Owner 与 completion_established=false 保持；缺少关系依据的提示为 unknown。

git diff --check 与修改文件 AST 检查通过；冻结 Phase-1 submodule 干净。
15项 Bolt 启动/环境 pin 与旧 Qwen UMA 哈希（合计16项）全部一致。
本轮未运行 GPU、调整监控或终止其他服务；最终8000/8003无监听。

## 5. 修改文件与回退

本轮正式源码仅：
- harness/codex_dynamic_tools.py：有界 Evidence 线格式、范围提示、摘要投影。
- harness/io_contract.py：历史 Topic 标识、无依据关系提示 UNKNOWN。
- harness/semantic_state_adapter.py：复用已有显式边界检查，避免明确切换被误标未知。

测试：
- tests/test_manual_evidence_projection.py：新增10项。
- tests/test_fetch_evidence_budget.py：长度字段名称断言更新。
- tests/test_harness_semantic_state_adapter.py：历史 Topic 名称断言更新。

完整前后 Diff 和本轮前文件副本保存在研究记录 this-stage.patch / before/。
工作区还包含前几轮未提交修改；回退应对照本轮 before 副本/patch 选择性恢复，不能 reset 或覆盖其他修改。
没有自动 Commit/Push，没有把模型/环境/运行记录添加到 Git。

## 6. 仍未解决、不能宣称 PASS 的问题

- 模型是否会使用缓存续读、读足证据并正确引用，UNKNOWN；本轮只是让实际范围和后续入口更清楚。
- 第3轮无执行依据的“没有X权限”，以及第6/7轮无新证据的确定性政策判断，不能靠投影格式保证消失。
- Compaction 可能错误概括来源或把推断描述为事实；本轮不将摘要质量修复等同于权威边界测试通过。
- 内部 Topic/legacy relation 仍是历史兼容字段，不代表已完成自然语言任务关系识别。
- 403保持真实失败，未绕过TLS、权限或提供者约束；本轮没有外部事实核验。
- 5000字符工具预算仍限制单段供给，读取很多页面仍可能触发正常Compaction。
- CASE_TIMEOUT手工生命周期超过30分钟、模型新上下文行为仍需实际人工验收；CPU/历史回放不替代它们。

## 7. 当前人工入口与最小验收

先启动模型，保留保护等待 READY（Lifecycle: manual）：

~~~bash
bash /home/wqkan_wsl/uaea-n1x/nemotron-bolt/start-bolt-32k.sh
~~~

另开WSL终端，使用新Harness会话加载修改：

~~~bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
bash scripts/start_h3_harness_interactive.sh \
  --profile n1x --context 32768 --vllm-mode external \
  --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x \
  --execution-contract shared --goal-mode shadow --goal-projection optional \
  --reasoning-effort none --turn-timeout 420 \
  --result-root /home/wqkan_wsl/uaea-n1x/runs/evidence-repair-manual
~~~

保持相同模型/工具，不要求强制每轮调用工具。最小三轮：
1. 指定Google且禁止回退，搜索一个可公开访问的主题，选择一篇文章阅读；未读完整时明确已读范围。
2. 要求从已保存片段的下一位置继续阅读，并区分文章原文、解释与未知事项。
3. 询问一个超出已有来源支持的问题，观察能否指出证据缺口或真实获取新证据，不编造权限/结果。

可在正常停顿与交互中让服务自然跨过30分钟，不需要额外压力。
若单Turn仍运行，使用 /turn status、/turn wait；需要中止用 /turn cancel，等待实际终结后再发新请求。
Harness退出保留外部模型生命周期；关闭服务用其模型启动终端Ctrl+C，由原保护清理。
本次下一步是人工行为验收，而非继续增加字段或话题规则。
