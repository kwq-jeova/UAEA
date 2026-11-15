# 研究资料可达性与 Context 容量联合评估 — 2026-11-13

状态：**总体 PARTIAL**。资料投影工程限定 VERIFIED；A完整财务章节已真实送达，但最终回答被研究驱动Compaction判据中断；B在明确缺失材料下合理UNKNOWN；C两个成品均有财务/完整性表述错误，**未证明Goal View决策收益**。没有扩大Context/KV/UMA、权限或正式采纳；未Commit/Push。

## 证据与批次

- A/B：evidence-context-20261113T082557Z。新Thread从真实A修订后的55,275B Journal（SHA e00a36df…32afa）恢复，4原版本/global head76fe…保持。
- C：evidence-context-C-20261113T093352Z，独立第二次模型加载，首次ON/OFF配对。A未重跑；原失败保留，不把两次加载拼成一个连续会话。
- 原HTML沿用前一真实资料捕获；研究者转成结构化章节，不将研究者任务或用户选择“金融领域”解释为用户个人持仓/偏好。
- fact-audit.json关联Native/Host、HTTP/SSE、Journal；document-delivery-audit.json核对源hash、selected hash、visible hash、范围和实际出站正文。原Journal与四版本不改。

## 根因与最小修复

1. **供给缺陷**：原通用JSON过预算fallback保留800字符content，文件读取成功、哈希正确却只送头部标题。不是64K容量不足的充分证据。
2. **Native第二次截断**：Python原上限按字符，Native还按UTF-8字节约束。首轮CPU新投影11998字符/12048字节仍被插入截断文本，破坏可见hash。现同一数字上限同时限制字符和UTF-8字节，不增加额度。
3. harness/document_projection.py只处理成功文档回执：保留身份/源hash/选区hash，按整行保留正文，列可见范围/hash、完整性/省略；正文优先于重复目录，必要身份放不下则拒绝。部分正文不称完整。
4. scripts/research/document_fixture.py保留article段落/表格、单位/多行表头/单元格顺序/span/HTML位置。NVDA15章8表、AMD29章17表；长表按原行拆分，重复原前12行明确标记。只覆盖识别的article结构，不宣称任意HTML全页无损；原HTML/映射保留。
5. goal_continuity.py严格验证新版doc标记/声明budget并精确重算；旧回执走明确legacy serializer。新版缺budget不得降级。Call/Step/Observation/来源校验不放松。
6. C隔离ResearchDocumentAdapter对选中正文回执，仅重复纯序列化选出能完整容纳正文的最小预算，仍≤12K，工具只执行一次，减少重复整目录。未改Goal工具/权限/执行循环。
7. A第五次restore是Host标记的Compaction请求，研究hook错误要求每次都有Goal View，本地502。独立C驱动现识别host_context_deferred_for_compaction透传summary，不强塞Goal/历史；下一正常请求恢复。CPU真实Harness路由1→0→1通过，**不证明真实模型压缩语义或自动来源恢复**。A未重跑。C只补1-based section ordinal说明，模型仍传0，Host原冻结fallback选root；未改Phase1。

## CPU及实际出站差异

同预算、同5条真实历史、真实Harness+CPU协议stub：
- 旧原大文档：NVDA/AMD各800字符。
- 新原大文档：8948/8828字符，明确partial。
- 结构化目录616/584字符，选中income正文2426/4817字符完整；源hash/行范围/日期/表头/单位关联。
- cpu-wire-v3确认Native工具结果与实际出站一致；stub不是Bolt，失败v1/v2仍保留。
- 最新8模块**108项CPU回归通过**；另存前一116项，不能相加。覆盖预算/Unicode/整行、原表映射、adapter、失败历史与Goal恢复连续性。独立代码/兼容审计另存。

## 实际模型实验

| 场景 | Native完成Turn | 完整模型响应 | 累计input / output Tokens | 真实读取 | 秒 |
|---|---:|---:|---:|---:|---:|
| A定位 | 0 | 4 | 131,886 / 1,233 | 15 | 316.95 |
| B不足 | 1 | 2 | 30,990 / 699 | 1 | 95.88 |
| C ON | 1 | 2 | 40,145 / 1,070 | 3 | 147.52 |
| C OFF | 1 | 3 | 61,486 / 1,838 | 4 | 252.70 |

11个真实响应HTTP framing完整、上下游SSE一致、generation均completed；**不等于11个用户任务正确**。每请求3072输出上限，无输出截断；每分支6次请求/420秒Turn/600秒watchdog预登记，未事后扩容救援。

A用户只给公司/目的，不给正确片段编号。模型自行定位NVDA7、AMD14，在成功请求中取得完整income表、当期/上年同期营收、单位/报告期；送达限定VERIFIED。15次成功执行前11送达，最后4执行后触发hook失败，未进入新请求。最终答案CENSORED，不把“已读对”算“已研究完成”。

B诊断片段明确缺公司全名/单位/币种/期间/同期数。模型区分表面数字与不可比性、同比UNKNOWN，未据此精确排名；不证明对未提示缺失资料同样稳健。

C初始同一A checkpoint和普通Goal历史，仅关闭独立当前视图。ON先OFF后，单配对，Thread/身份/匿名路径不同，顺序未平衡。ON输入15,120→25,025；OFF13,064→22,971→25,451。

- 两组均传section0读root，回执明确partial（NVDA8924/35076字符、AMD8997/53960），却称完整阅读。OFF另读AMD7完整2915字符；不能把A正确章节送达拼入C。
- ON选择盈利/ROA检验，有实际算式，但声称的NVIDIA总资产44,044及AMD总资产57,327均未在C实际请求中供给，ROA缺乏依据；具体数字来源UNKNOWN，不能断言已定位为股东权益/总资产混淆。NVIDIA原件总资产320,272未供给；July25与已供July26矛盾。
- OFF选择增长/利润率比较，有实际算式，但表内经营利润率124%与自身66.2%计算矛盾，Non-GAAP表/算式也冲突；先称期间可对标后承认不同期间。
- 两组0Goal调用，4版本/global76fe保持，ActiveGoal空。未见新维护/净决策收益证据；Token更少不能抵消错误。

## 64K预算及成本核账

| 边界 | 实际值/含义 |
|---|---|
| 模型最大Context | 65,536，输入+输出受模型限制 |
| Harness有效窗口 | 62,259，不全是文件预算 |
| 自动Compaction阈值 | 49,152；A第四请求52,691未硬超窗，下一请求开始压缩 |
| 每次输出上限 | 3,072 Tokens，不是Context容量 |
| 单工具回执 | 原12,000数字上限，现同时约束UTF-8字节；子章可更小 |
| Host恢复块 | 24KB，独立于整请求/所有历史 |
| Goal View | 4,200字符；32是Thread可见版本限制，非Profile总版本 |
| 实验请求预算 | 每分支6次含压缩，不是工具次数或Context |
| KV/并发/UMA/util | 1GiB / 1 / 56-72 / 0.65；引擎KV容量109,817 Tokens |

/render在现有vLLM关闭scale-out下403，未开启新Backend功能。独立审计按原tag/item hash、真实Host bool与client_metadata原格式重建脱敏副本，**6/6 forwarded字节SHA匹配，同tokenizer+vLLM实际Responses转换/模板Token数与API usage相等**，未硬减7或用字符比例冒充Token。

以下为A/B实际请求的互斥语义跨度划分；模板/跨边界/普通历史余项见token-audit.json，各行完整分量和等于API输入。划分是成本解释约定，不证明模型使用Goal。

| 请求 | System/Developer | Tools定义 | Goal View | Goal历史 | 工具调用史 | 回执metadata | 文档目录 | 证据正文 | 当前Task | 总输入 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| f0/1 | 7532 | 1170 | 2027 | 1304 | 0 | 0 | 0 | 0 | 349 | 15232 |
| f0/2 | 7154 | 1170 | 2027 | 1304 | 161 | 2627 | 0 | 5367 | 349 | 23168 |
| f0/3 | 7151 | 1170 | 2027 | 1304 | 643 | 10532 | 7150 | 7400 | 349 | 40795 |
| f0/4 | 7160 | 1170 | 2027 | 1304 | 886 | 14577 | 10725 | 11407 | 349 | 52691 |
| f1/1 | 7266 | 1170 | 2027 | 1304 | 0 | 0 | 0 | 0 | 226 | 14638 |
| f1/2 | 7378 | 1170 | 2027 | 1304 | 77 | 1269 | 23 | 76 | 226 | 16352 |

A第4请求52,691输入中，目录10,725、回执metadata14,577，合计25,302（约48.0%）；证据正文11,407（约21.6%），当前Goal View2,027（约3.85%）。因此本样本更直接的容量负担是工具历史/重复目录，而非Goal版本数量本身。分类为成本跨度约定，不是可删掉同量Token且质量不变的预测。

角色分解另列rendered_role_tokens：Nemotron把tool_response包在user角色，developer合并system；两轴不可再相加。输出预留3,072单列，不算已用input。C分解见下表及独立终审，不套A/B。



C五个真实请求也已逐项/整请求hash与API Token闭合；合计11/11请求核账。首请求去独立Goal视图后，只正规化本轮生成身份/时间/路径，原历史ID与内容保持，二组内容相同。顺序效应/单配对仍保留。

| C请求 | 证据正文 | 目录 | 回执metadata | Goal View | 总输入 |
|---|---:|---:|---:|---:|---:|
| ON/1 | 0 | 0 | 0 | 2027 | 15120 |
| ON/2 | 5452 | 22 | 3931 | 2027 | 25025 |
| OFF/1 | 0 | 0 | 0 | 0 | 13064 |
| OFF/2 | 5452 | 22 | 3881 | 0 | 22971 |
| OFF/3 | 6848 | 22 | 5227 | 0 | 25451 |

C首请求ON/OFF实测相差2,056 Tokens；在同一ON请求上CPU反事实仅删独立View为2,032，余差来自独立身份/时间/路径的tokenization。该CPU反事实不是额外真实模型请求，不计入行为或成功率；低Token不能证明研究质量相等或有Goal增益。


容量风险：
- 原20→5条精确历史选择，独立BPE14,660→2,725，保留原目的/A纠正/Call/Host/最终回答，原20留存。不是模型摘要，不是API总量改善的单因素证明。
- A输入15,232→52,691，工具历史/重复目录/root与子章重叠带来增长，不只是新正文。没有同source+section完全重读，不代表零重叠浪费。
- 12K回执压掉正文时，整体Context仍有余量；扩窗不能替代供给修复。
- 实际A4存储/3可见版本视图3,289字符、独立BPE1,976；另真实6版本原localThread有5可见版本，3,599字符/2,138BPE，已省3历史/1来源。有界成本依赖**明确省略，非无限完整**。
- Journal零提案仍记录新输入并增长。Profile16MiB/行2MiB存储限额与Context不同；当前小样本不能证明长期无限容量。
- 本轮真实模型未完成自然Compaction后恢复：A止于summary发送前，C未触发。CPU故意删Goal/source摘要后Host仍重供当前Goal，**不证明财务证据摘要保真**；后续须区分Goal重投影与正文重读，不把摘要升级Evidence。

## 安全与完整性

| 资源 | A/B服务批次 | C服务批次 |
|---|---:|---:|
| 有效service采样 | 832 | 473 |
| NVML峰值 GiB | 29.428 | 28.901 |
| WDDM Dedicated/Shared峰值 GiB | 28.927/0.280 | 28.900/0.268 |
| Commit最低余量/距停止线 GiB | 21.090/2.794 | 21.520/3.224 |
| Windows Available最低 GiB | 30.530 | 31.613 |
| WSL MemAvailable最低 GiB | 16.899 | 16.758 |

两批monitor-exception.json在收尾记录CONTROLLER_STOP且primary_sensor_failure=null，不是运行中遥测故障。两批单时钟nonce/序号、AC和新鲜度有效；Swap峰值16KiB，原门限不变，正常控制停服、无残留子进程。smoke GPU48GiB/stale注入为预定保护验证，非真服务越线。最窄Commit缓冲2.794GiB仍为正，不支持无界扩负载/长期稳定性承诺。锁140/143源码、5,618/5,613输入及各15原保护pin一致；HEAD仍2b3edfc。A/B→C有协议/glue差异，不宣称严格单变量修复收益。

## 研究判断

- **VERIFIED（限定）**：来源目录/章节可达、实际正文/省略/hash保真、历史兼容恢复、A自主完整表送达、B明确缺失的UNKNOWN，Host权限/版本/状态保持。
- **PARTIAL**：完整资料利用/任务完成、C财务解释及当前Goal适用性。A研究hook删失，C忽视partial。
- **UNKNOWN**：自动压缩后证据语义保真、长期Goal增长的认知质量、结构化Goal净决策价值；未解决历史偶发重复根因。
- M1 PARTIAL；M2沿用显式纠正存在性；M3总体PARTIAL；M4/M5 UNKNOWN，不上调。

不支持增加Goal/Memory Engine、金融语义裁判或扩Context/KV。现有Sideband足以表达本次状态，资料供给与认知收益分开。下一步优先一次完整可见表头/分母的有限跨任务检验，以及修正研究Compaction路由后的真实恢复。冻结资料/预算，不批量30轮或反复Prompt找PASS；在有效成品可比后再研究Goal视图对受限普通历史的增量。

独立Audit Agent终审joint-independent-audit.md及C/independent-audit.md总体PARTIAL，无剩余阻断性实现/报告问题；核验11/11实际请求、Token、原状态与公平性，保留模型负面样本。限定测试结束，保留可证伪失败，提交评审，不需要新的人工长会话。
