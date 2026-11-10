# 2026-11-05 人工研究循环审计

会话：interactive-32768-20261105-021615。
结论：Research Workflow未完成；模型反复提出信息采集，Compaction与Host进度投影存在可证实缺口。不是同一call被Runtime重复调度，不是上下文全部丢失。
本轮只读诊断与报告，没有修改运行代码、启动模型、新搜索、停止用户服务或Commit/Push。

## 1. 执行规模

- 5条真实用户输入，4个Turn completed，最后Turn未见终结。
- 79个不同call_id、79条对应Execution Observation。
- Search：36成功、3超时、2校验拒绝；Fetch：19网络成功、7缓存续读成功、6次403、4次404、2次execution_unknown。
- 同一AllInvestView URL重新联网获取9次，另有6次缓存续读。9份HTML原始hash不同，但提取文本hash完全相同、均1912字符。因此不能将这些记录自动计作新的独立内容证据。
- 精确参数重复主要发生在Fetch：同一AllInvestView max_chars=3000请求出现7次。Search query经常换词，不能将近义查询机械认定为完全相同；可确认的是持续围绕旧EPS/财报/价格信息采集。
- 本次9次Compaction均有completed；未见Context超限拒绝。最大已完成模型inputTokens=25376。
- 74/74份运行源码hash匹配当前文件，manual无任务时限配置生效。

最后一轮用户要求建仓判断；随后模型新提议14次工具请求、经历两次Compaction，尚未给出最终回答。取消无限等待不是解决重复采集的方法。

## 2. 最强的压缩前后对照

同一source_event_id WEB-LIVE-53714896-31e0-4da0-ae0d-391df87fce9f：

| Raw Events行 | 事实 |
| --- | --- |
| 5126 | 实际供给0–1557 / 1912字符 |
| 5134 | 缓存续读供给1557–1912；has_more=false、next_start_char=null |
| 5150 / 5159 | Compaction开始 / 完成 |
| 出站请求47、input[8] | 摘要仍列“Fetch AllInvestView full page (already partially fetched)”为待办 |
| 5210 / 5222 | 模型提出新的call，从网络重新获取该页，再供给0–900 |

这证明已供给的保存提取文本被后续摘要重新表达为未读完；并不证明网页真实全文已获取、事实核实完毕或模型实际理解了文本。
在更早的相同URL版本，也出现了完整1912字符分段供给后的重新抓取。

## 3. UAEA投影缺口

- recovery_sources只恢复最近三段、每段前300字符。请求47恢复了0–300与1557–1857，并分别has_more=true；这些字段准确描述恢复片段本身，却没有同时明确此前实际供给已覆盖0–1912。
- 这不是篡改原始Observation，也不是Host授权状态污染；是“现在重供给的片段”和“历史实际读取覆盖”未明确分开。
- Semantic Projection预算收缩从source_coverage.sources末尾删除，导致保留早期Reddit/Moomoo URL，较新的AllInvestView读取身份未出现在该覆盖列表中。请求47只列早期Reddit。
- provenance摘要supplied_excerpts=0，而Raw Events存在26份成功Fetch/续读的合法文本hash/范围。当前Host保守计数没有接上实际线格式片段，不能把0解释为模型从未收到正文。
- source_coverage是URL/获取状态统计，不是已读取范围、内容支持或Workflow完成判断。
- 代码入口：harness/semantic_state_adapter.py:542起(recovery_sources)、:1104起(预算收缩)；harness/evidence_provenance.py:49–63(供给判定)。

因此，Runtime保留了来源与任务，却没有可靠地向模型表达“哪一版本哪些范围已供给”。这是具体工程缺口，不需新增Goal Engine才能修复。

## 4. 仍有独立的模型行为问题

- 三次相同Vantage请求均403，且发生在同一次Compaction间隔内；说明压缩不是所有重复的唯一原因。
- 当前原始用户请求及workflow_continuation.current_request确实进入最后普通请求，不能说建仓问题根本没送到。
- 模型在明知多项数据已收集时，反复承诺“再获取完整内容、再交叉验证”，没有给出有界判断或明确不可验证项。
- 摘要一边写verified，另一边又列同页待取；来源一致/页面取回不证明财务数据真实或独立验证。
- 最后一份完整估值回答还存在内部量纲不一致：165亿美元与165B混用。此处只检查回答内部一致性，不进行外部股票估值或投资建议。
- 不能根据日志反推模型隐藏推理，也不能证明只要修正投影就会停止循环。真实行为效果仍UNKNOWN。

## 5. 中断状态

turn-lifecycle.jsonl仅有wait_interrupted，未见interrupt_requested、terminal_confirmed或最后Turn终结。
因此现有记录证明用户中断了等待，未证明原生任务已经取消。若原会话仍开着且要停止，应在原会话/turn cancel；不要自动杀外部模型服务。
本轮没有替用户发送取消，也不声称后台一定仍在执行。

## 6. 最小修正方向

1. 复用现有Observation与Tool Result，分别保留Capability取得范围、实际模型供给范围、恢复块当前片段；按source_event_id与内容版本合并已供给覆盖，不按URL猜测。
2. 将最新相关成功/失败/已读覆盖优先放入有界恢复，而不是保留最早URL。保留来源hash和省略声明，不增加无限Context。
3. 模型重提同URL/同参数时提供既有来源、范围和失败事实提示；允许真实刷新、合法重试，不把相似查询一律禁止，也不自行接管模型研究策略。
4. 明确当前请求并非要求无限获取所有发现URL；已有数据不足时允许限定结论或明确缺口，不将模型自称verified当事实。
5. 用本例压缩前后原始线格式离线验证，再用同任务真实模型检查是否改善；Contract与Model Behavior分别验收。

当前建议优先修正“已读覆盖/恢复表达”，不恢复固定任务超时、不单纯加长Context，也不扩大Goal/Memory架构。
