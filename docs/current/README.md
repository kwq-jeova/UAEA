# Current Baselines

Status: CURRENT
Role: 当前基线导航；无独立新 contract

## 最新状态：2026-11-13

[Goal Continuity三场景](../research/goal-continuity-three-scenarios-20261113.md)总体PARTIAL：M2显式跨会话纠正/保存/送达限定VERIFIED，B长期Goal保持；M3仍PARTIAL，M4/M5 UNKNOWN。C仅比较结构化视图相对相同历史/回执的增量，尚未证明决策收益。Memory Research Reserved，正式采纳关闭。

N1X隔离研究为56/72、64K、1GiB、单并发、util0.65；原保护与32K回退保留。详见[本次Git检查点](../implementation/checkpoints/goal-research-checkpoint-20261113.md)。下方按日期保留当时状态；旧“待修/未运行”不覆盖最新结果，冻结契约与研究成熟度分开。

| 正文 | 当前有效范围 | 不应推断 |
| --- | --- | --- |
| [2026-10-05 信息边界 Checkpoint](architecture/cognition-boundary-checkpoint-20261005.md) | 最新阶段状态、有限 authority contract、验证等级与停止点 | 最新 authority 人工 NOT TESTED；不是 Goal/Memory baseline |
| [Boundary Integrity Audit](architecture/boundary-integrity-audit-20261002.md) | semantic state/authority/result/evidence/bounded identity | 不保证模型开放行为或长期 cognition 已验收 |
| [Harness Runtime Baseline](runtime/harness-runtime-baseline-20260926.md) | generic execution/runtime CLOSED | 不恢复 Phase-1 generic runtime；末尾为历史 |
| [2026-10-22 Harness 双版本升级](runtime/harness-upgrade-20261022.md) | 默认 v0.163.0、保留 v0.154.0，构建/回归/回退 | 不代表模型行为或 cognition 已闭环 |
| [Web 私有环境](environment/web-runtime-environment.md) | 当前 proxy/secret/startup | smoke 不等于 model-mediated acceptance |
| [SQLite Source/Evidence closure](evidence/sqlite-source-evidence-closure.md) | source history/EvidenceReference | 非 Memory Store，旧测试数量和 next slice 属 checkpoint |

[总入口](../README.md) · [研究基础](../research/README.md) · [历史证据](../historical/README.md)


## 2026-11-12 独立研究进度导航

Goal研究最新进度见[研究阶段索引](../research/README.md)与[研究地图](../research/research-foundation-map.md)。
历史恢复仅案例限定PASS；Step–Observation绑定缺口待修，M2尚待独立读回/纠正验证，M3未闭环，M4/M5 UNKNOWN。
这不是正式Goal/Memory采纳或Runtime架构升级，原有冻结职责与授权边界保持。

## 2026-11-12 研究进度补证（不变更正式契约）

[Goal恢复绑定与M2分支阶段报告](../research/goal-m2-branches-20261112.md)：恢复限定PASS；准确全文读回单样本PASS、归属PARTIAL；明确纠正6次拒绝且虚称保存，M2-B FAIL；M3未运行，M4/M5 UNKNOWN。批次 goal-m2-branches-20261112T073526Z。详细范围及下一步提交架构评审。

## 2026-11-12 Goal M2 研究补证（正式契约不变）

[M2真实修订/语义门](../research/goal-m2-current-correction-20261112.md)与[失败反馈配对](../research/goal-m2-failure-feedback-20261112.md)：真实2次接受和准确保存报告VERIFIED，语义外推未解决，M2 PARTIAL；M3未运行、M4/M5 UNKNOWN。保留旧失败、未Commit/Push，提交评审。

## 2026-11-12 P1/P2限定研究补证（正式契约不变）

[P1/M3准入](../research/goal-p1-faithfulness-20261112.md)：3独立输入无合格新候选，M3未运行。[P2状态报告](../research/goal-p2-state-report-20261112.md)：原反馈有事件错配，明确反馈只改善部分结果字段，提交正文关联仍缺失/补填。M1/M2语义及P2仍PARTIAL，M4/M5 UNKNOWN。保留失败，未Commit/Push，提交评审。


## 2026-11-12 Goal 失败历史工程补证（正式契约不变）

[失败提案投影收敛](../research/goal-failed-proposal-history-20261112.md)：Call→实际参数/正文→同Call结果完整关联；64项CPU及真实Codex无模型出站核验通过，独立工程审计限定PASS。未加载GPU或重跑M2/M3；模型失败状态理解仍需重验，M3 NOT RUN，M4/M5 UNKNOWN。原先的投影缺口不再作为模型能力不足的单独证据；Goal/Memory/执行权限不变。


## 2026-11-12 Goal 历史事实真实读回（正式契约不变）

[投影后P2/M2研究](../research/goal-postprojection-state-correction-20261112.md)：字段复核更正：hypothesis 4/6，2/6把quote误填正文；target/committed分别正确不等于完整绑定正确。P2改为PARTIAL，撤销原完整绑定PASS；原实验不重跑。一次独立纠正产生目的忠实refine草案但CURRENT引用错误，Host拒绝且无新版本；M3未运行，M4/M5 UNKNOWN。研究驱动误拦只读工具的原试验保留并单列，不计为认知失败；无正式Runtime或授权变更。


## 2026-11-12 Goal 字段评分更正与限定验证

[新A/B及M2进度](../research/goal-field-understanding-correction-20261112.md)：旧hypothesis4/6已更正并保留旧评审；新A quote4/6，其余三字段6/6，仅单次读回样本。B实际revise仍误选历史quote，Host拒绝、未保存；当前与历史依据用途选择仍未闭环。拒绝后的模型报告CENSORED，M3未开展，M4/M5 UNKNOWN。无正式Runtime/Schema/授权改变，不Commit/Push。


## 2026-11-13 M2 合法忠实纠正样本与M3后续行动

[历史失败明细消融](../research/goal-history-ablation-m2-m3-20261113.md)：一个显式反馈下的Goal修订完成合法保存、真实新head投影及后续跨公司读取。M2仅限定存在性通过；M3总体PARTIAL，新head的因果作用和M5仍UNKNOWN。消融有额外ID/时间/条件路径差异，不宣称严格因果。无正式采纳、Memory或权限扩大，原评分器问题已归档。


## 2026-11-13 Goal当前视图增量研究（正式契约不变）

[相同纠正checkpoint的ON/OFF配对](../research/goal-view-increment-20261113.md)：当前结构化视图相对普通历史/回执的增量仍UNKNOWN。两组保留长期方向但各有缺陷：OFF返回Intel且优先级论证不足，ON暂停Intel却未落实当前核验并误报完成。Host未提升正式状态；总体PARTIAL，M3未升级、M4/M5 UNKNOWN。保留现有Sideband，不依据一对样本建设维护层或改变架构。

独立Audit Agent已复核本批次：总体PARTIAL，可归档限定研究；没有证明当前视图增量决策收益，不支持新增正式机制。


## 2026-11-13 Goal连续性研究（非正式Runtime基线）

[本地Journal与跨会话恢复](../research/goal-continuity-20261113.md)：隔离研究工程限定PASS，真实新Thread准确读回；后续讨论过度弃答，整体PARTIAL，M3未升级、M4/M5 UNKNOWN。未把历史候选自动采纳、旧Workflow恢复或Memory开放。正式人工入口/Schema/执行权限不变。长期研究使用方法见scripts/research/README-goal-continuity.md；本轮完成后暂停。


## 2026-11-13 Goal连续性三场景（研究，不是正式运行基线）

[跨会话纠正/保持/行动选择](../research/goal-continuity-three-scenarios-20261113.md)：A一次真实忠实核心revise保存/新head送达，B结束Intel局部Task而保持global；六分支独立、不拼接认知链。C两对当前结构化视图ON/OFF仍混合并有金融/日期错误及一个删失，M5 UNKNOWN；12响应完整不等于任务正确。M2限定存在性、M3 PARTIAL、M4 UNKNOWN；无正式采纳/权限/Runtime变更。32候选版本是Thread可见集合上限，非Profile总上限。资源安全正常停止，无Commit/Push，提交评审。
