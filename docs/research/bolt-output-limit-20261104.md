# Bolt输出Token上限检查（2026-11-04）

结论：**输出截断诊断PASS；2048在两次独立测试中足够；完整语义/建议质量仍PARTIAL。**
原11次历史实验不覆盖、不重评分、不混入本轮结果。正式Runtime/Harness/Goal及权限规则不修改。

## 1. 原始证据

原研究：/home/wqkan_wsl/uaea-n1x/research-records/historical-decision-value-20261104T072025Z/

| 原响应 | 输入 | 输出 | 总Tokens | finish_reason | JSON语法/要求字段 |
| --- | ---: | ---: | ---: | --- | --- |
| R530 | 1826 | 900 | 2726 | length | 字符串未结束，最后goal_vs_path被截断 |
| R952 | 858 | 453 | 1311 | stop | JSON可解析，但遗漏goal_vs_path |

R530原请求max_tokens=900，输出恰好900；可见正文1241字符/2487 UTF-8字节，
JSON错误在字符1122开始的未结束字符串。32K容量远未用满。
reasoning_content为空、usage.reasoning_tokens=0，与关闭Thinking配置一致；
没有证据表明隐藏推理耗尽了本次输出额度。

**VERIFIED**：这是请求级输出上限终止，不是32768 Context溢出、KV不足或Compaction。
R952不足900就主动结束，是字段遵循问题，不能由扩大预算直接解释或保证修复。
原11次结果：10个可解析JSON、9个要求字段齐全；唯一length为R530。
完整响应中最高输出856，仍接近900上限，说明900对这类冗长回答缺少余量。
原始usage/字符数/字段长度全部保存在original-output-audit.json。

## 2. 冗余检查

R530在why、门禁、未知项和最终总结反复叙述同一组事实：
32/90出现3次、WINDOWS_PHYSICAL出现3次、“采样”出现7次、“未能证明”出现5次。
not_established区域360字符，连同末尾总结占可见输出494字符。
重复计数仅作编辑线索，不是有效bit、统计独立性或认知价值测量。

合理压缩方式：最多两项行动，各保留一句动作、依据、门禁；
未知项2–3个短句；Goal/Path说明不再复述完整资源轨迹。
不能为简短删除安全约束，也不能在截断后猜测补齐JSON或语义。

## 3. 最小独立验证

新记录：/home/wqkan_wsl/uaea-n1x/research-records/bolt-output-limit-20261104T075655Z/
原payload、协议与两个新请求在调用前冻结hash：
- exact-2048：与R530请求完全相同，仅max_tokens900改为2048。
- concise-2048：在exact基础上追加通用简洁要求；这是提示变体，不能全部归为输出额度效应。
其余model、temperature0、seed42、Thinking关闭、32K/1GiB KV、36GiB规划与保护均不变。
仅2次API调用，无自动重试，无工具或建议实际执行。

| 本轮独立响应 | 输入 | 输出 | 总Tokens | 结束 | JSON语法 | 要求字段 |
| --- | ---: | ---: | ---: | --- | --- | --- |
| exact-2048 | 1826 | 566 | 2392 | stop | PASS | FAIL：缺goal_vs_path |
| concise-2048 | 1912 | 691 | 2603 | stop | PASS | PASS |

两者引用ID均可解析，未出现length；请求上限全部使用完的最坏合计分别3874/3960，仍远低于32768。
实际耗时58.64/70.61秒；没有扩容Context、KV或更换依赖。

**关键限定**：新输出与旧R530只共享前30字符，不是原截断文本的续写。
虽然temperature/seed一致，也不能据此假定逐字确定性；本轮未追查内容差异的底层原因。
两个新回答本身都少于900，因此不能用它们证明“这些具体新回答必须2048才完整”，
或把全部改善单因果归为扩容。旧900上限导致旧回答硬截断的直接证据依然成立。

简洁变体unknowns从5项变3项，并补齐字段，但691比另一条566更长；
只能说明本次字段完整，不能声称输出总量/耗时下降或通用提示已被优化。

## 4. 认知与格式分开评价

- exact-2048引用A8的“不重复测试”历史，却建议对同一已通过测试做重复独立复核，并称其唯一最小验证。
  JSON可解析没有消除来源语义误用，且字段仍缺失。
- concise-2048保留“不再次加载”，但仍反复要求复核已经审查的Routing，缺少新故障依据。
  它没有证明实际建议质量超过原对照。
- 未将这两条改写成原Relevant History组的新结果；原R530仍为length、JSON失败及建议越界。
- 这不是Runtime正式校验、自动修复或Goal状态采纳实验，不因研究隔离就宣称模型安全正确。

## 5. 建议配置

对当前“关闭Thinking、两项短建议、结构化输出”的实验：
- **max_tokens=2048**作为下一次新实验的保守输出上限，不要求模型写满。
- 约600–1000 Tokens作为软性简洁目标；依靠内容组织而非硬截断达成。
- 保留32K Context、1GiB固定KV、原vLLM与全部资源保护。
- 保持finish_reason、实际usage、JSON解析、必需字段与语义支持分别核验。
- 若length或缺字段，明确记录失败；不默默补JSON、不自动无限续写或将修复样本混入原对照。

**2048足够的范围**：本轮两个短任务响应。
**UNKNOWN**：任意长研究回答、开启Thinking、多来源长引用或跨轮摘要是否足够。
目前没有理由直接提高到4096；若任务确实需要更长结构，再独立论证3072/4096并重新预留Context。
现有请求在2048上限下仍有至少28808 Tokens空间，不需要改32K服务规格。
本轮只提供独立请求文件和建议，不改原研究默认值或任何正式入口。

## 6. 资源与清理

复用已验证start-bolt-32k.sh，仅一次模型启动。
48GiB模拟提前停止与Windows心跳失效清理均通过；真实测试保持Fail-Closed。
264个联合样本、258个service样本，采样极值：
Dedicated NVML29.107GiB、WDDM29.141GiB，Shared0.151GiB；
Windows Available最低26.226GiB，Commit峰值67.517/114.481GiB、最小余量46.964GiB；
WSL Available最低17.590GiB、Swap峰值2.906MiB。
这些不是瞬时最大值，Dedicated与Shared未作为独立容量相加。

服务记录：/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261104T075746Z-5ed1af47/
测试后主动停止，service.guard_reason=CONTROLLER_STOP、remaining=[]，采样器remaining=[]。
包装器仍将该主动停止通用显示为Safety stop/exit1；没有改写原日志。
无真实资源阈值或监控失效触发，最后8000/8003无监听。

## 7. 可复核产物与影响范围

- original-record-manifest.json：原研究全部文件hash，最终逐一比对，无覆盖。
- original-output-audit.json、redundancy-review.json：原usage、格式和可见冗余。
- payload-exact-2048.json、payload-concise-2048.json、frozen-before-inference.json：独立请求/控制。
- run_probe.py、responses/、api-results.jsonl：两次真实运行证据。
- analyze_probe.py、probe-analysis.json、semantic-review.json：离线复核及明确能力边界。
- resource-summary.json、guard-run.txt、owned-guard-evidence/：资源与所属进程终止证据。
- final-verification.json：原记录、仓库源码与受保护环境哈希检查。
- Windows UAEA_DOCS中提供审计报告与完整独立记录副本。

只读复核可运行python3 -B <本目录>/analyze_probe.py，不会重新调用API或修复输出。
不要直接重跑run_probe.py：它拒绝覆盖结果，且依赖本轮所属新鲜保护会话。
仓库、正式Runtime/Harness/Goal/权限和模型依赖均不修改；不Commit/Push。
本轮检查和2次最小验证完成，停止。
