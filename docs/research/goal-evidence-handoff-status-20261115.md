# 2026-11-15：Goal、镜子与交接证据研究近况

本页是已有结果的进度同步，不是新模型实验或独立Audit AI验收。[报告文本副本与来源](evidence/handoff-goal-20261115/README.md)保留原失败和UNKNOWN；[本地历史清单](../archive/local-reports-20261115/README.md)供用户决定文件保留。

## 当前判断

| 事项 | 最新范围 |
|---|---|
| 用户意图归属 M1 | PARTIAL；长期目的、临时安排、资料使用边界仍会混写 |
| 受反馈纠正 M2 | 已有真实合法revise→Host保存→新head送达的限定存在性证据；不等于稳定自主维护 |
| 连续状态与后续行为 M3 | PARTIAL；跨Thread/进程/压缩继续执行成立过，时效安排、进度及证据使用仍不可靠 |
| 自主生命周期 M4 | UNKNOWN；自然调用存在，但忠实性和适时维护可靠性未建立 |
| 实际决策增益 M5 | UNKNOWN；镜子和Goal View均未证明稳定增益 |
| Memory | Research Reserved；不开放Memory Admission |

所有金融/采购方向、ROA例外和模拟配置是研究场景材料，不据此确认真实用户个人投资目的、偏好或交易授权。正式ActiveGoal仍不自动采纳。

## 1. Mirror阶段已收尾

Mirror v0.1按事先规则收为“没测成”。NextAction/Excerpt/Handoff没有稳定改善P014的季度期初缺口识别；P014诊断收住，不继续调提示。

真实HarnessMirror R1/R2每组一次：R1都算出SIM P/E=32、都未取得Apple季度EPS；R2普通组补读后得到Alphabet季度EPS并计算同比约−26.1%，镜子组停在截断回执。没有建立稳定任务收益，不能用单例反推镜子造成停止。镜子暂不正式接入，也不以此评价整个Goal机制。[原报告](evidence/handoff-goal-20261115/20261114_224717_HarnessMirror_Live/report.source.txt)。

## 2. 非权威候选权限与真实方向修订

[权限核对报告](evidence/handoff-goal-20261115/20261115_GoalPermissionClarity/report.source.txt)：既有GoalResearch规则允许模型提议修订非权威候选，不要求用户另说“保存”；正式ActiveGoal采纳是另一边界。CURRENT quote必须来自当前注册输入，历史目的可经合法input_ids支撑，不能互换。

答复后一次复盘没有促成提交；模型理解方向变更却再问确认，Host未拒绝过不存在的调用。随后加中性权限说明的独立样本真实revise：
76fe2c341f981c349d539f56 → bded94b910097623599608cb，真实Host保存并送达后续请求。文本转向企业AI算力采购和部署风险，仍混有“暂时不用再做ROA或估值分析”安排。只恢复AMD时，长期head未误改。不是严格随机因果对照，也不证明稳定自主维护。

## 3. 适用时间与完整任务的反例

[时间范围交接](evidence/handoff-goal-20261115/20261115_GoalTemporalHandoff/report.source.txt)：一次例外交接后被后移；持续解除暂停样本正确。两边Goal均未改，说明不能仅按head变化判输赢，也尚不能认定必须拆正式Schema。

[SupplierTaskHandoff v3](evidence/handoff-goal-20261115/20261115_SupplierTaskHandoff_v3/report.source.txt)：AMD→真实同Thread进程交接→NVIDIA→Intel及比较已执行完成。22个模型响应完整、38次读取、两次自然压缩。NVIDIA在说不算ROA后仍计算，最终早期收入及已读状态失真；Goal head/5版本未变。v1/v2中断独立保留，不拼接。

[最终交付局部重放](evidence/handoff-goal-20261115/20261115_SupplierFinalReplay/report.source.txt)：A因超窗无最终答复，B/C真实回查后收入正确，但仍有发布日期和来源缺口错误。不是完整原Host悬挂Turn恢复；删一句收工建议的因果作用未确定。

## 4. 已有证据与“来源没有”的区别

[两类缺口](evidence/handoff-goal-20261115/20261115_EvidenceAbsencePair/report.source.txt)：AMD债务7,079百万美元实际读过却被写成未披露；独立第三方部署报告确不在指定冻结文件，但模型未全文排除其存在。当前不可见、本次未核实、原材料没有须分开。

[正常可读摘要案例](evidence/handoff-goal-20261115/20261115_ReadableCompactionCase/report.source.txt)：ledger曾完整读取，摘要没保留读取动作，后来被说成“存在，未读取”。不能说摘要明示已读而模型无视。
[多次压缩资产案例](evidence/handoff-goal-20261115/20261115_ReadableCompactionAssets/report.source.txt)：AMD资产94,812在第一摘要中，第二摘要和最终输入丢失，最终被标“未读”；不能把第一摘要冒充最终所见。

## 5. 最新：交接时考虑未完成交付的小对照

[一屏报告](evidence/handoff-goal-20261115/20261115_HandoffDeliverableFocus/report.source.txt)及[逐字段派生记录](evidence/handoff-goal-20261115/20261115_HandoffDeliverableFocus/field-evaluation-compact.json)。

- 正确起点：v3第二次压缩前actual-compaction-request-12，早期证据仍在。A/B同模型、工具和3072摘要预算，B只加用户指定的一句话。实际出站已核实。
- A未生成正常摘要而输出Intel调用文本；接手23次成功读取仅涉及Intel/目录，前两家待收录，Intel数据进AMD列。
- B交接保留前两家收入、NVIDIA资产；4次读取目录/三家首页，收入/财季正确，但AMD资产仍写成源文未披露。最终模型status=incomplete、max_output_tokens=3072，不能因Native completed或HTTP framing完整判完整生成。
- 原NVIDIA收入96,221百万美元→B摘要96.2B→实际回读根节取得原数→最终96.2B，为保留且真实用上的具体链。AMD资产94,812已读却未被保留，误报来源缺失仍未解决；两组均遗漏，不能归因B挤掉。
- 迁移选点是原Phase1压缩后的新估值解释复核，上一小问已答完，弱于事先“仍待交付”的强条件。因此仅作旁证，不计合格迁移成功。A节号0失败后改1并成功读5份资料；B两次0被拒后没有成功新读取，靠摘要正确报告25/40/50，未见取证增益。
- 属于冻结Provider历史＋新Native Thread真实工具循环，不是原Native/Host全部状态原位恢复。旧调用不重执行，Goal heads/versions全部不变。
- 同一模型加载，四组各一次，无模型提示补跑。2086条服务样本全部有效，Commit最低剩余23.074GiB、离原停止线缓冲5.178GiB；owned模型已停。总体耗时主A/B均约12.3分钟，工具少不等于更快。
- 结论只有熟题局部覆盖改善；稳定、可迁移的证据使用收益未证明。未获本轮独立Audit AI认可，不能上调M3/M4/M5。

## 当前边界与后续研究位置

继续LLM proposes / Runtime validates；Harness拥有Agent Loop；候选非权威、不可自动获得执行权。未新增Goal/Memory Engine、自动纠错/采纳或SQLite Schema；不放宽CURRENT。56/72、64K、1GiB KV、单并发和原保护线保持。此次Git同步不启动GPU或新研究。

下一阶段需由用户根据记录决定：优先检验摘要是否忠实保留待交付所需的字段/来源和适用时间，或先改善来源缺口表述；不直接扩大Context/KV或把提醒接入正式控制流程。Goal预测/决定日志不能从以上结果推定已通过，真实可用决定样本仍需独立核对。
