# Goal Continuity 三场景联合验证：独立审计意见

总体 **PARTIAL**。同意本轮结束并提交阶段评审；没有发现需要改变正式 Runtime、权限、Schema 或资源边界的新增阻断问题。A 获得单次跨会话显式纠正的正面证据，B 获得单次局部 Task 结束而长期候选保持的证据；C 的行为、成本和质量混合，尚未证明专用结构化 Goal View 的增量决策价值。

审计批次：/home/wqkan_wsl/uaea-n1x/research-records/goal-continuity-three-20261113T030425Z。

本审计读取冻结材料、完整原答、Native、实际请求与响应、执行轨迹、候选 Journal 和资源原始记录；未启动模型/GPU，未打开原 SQLite，未改变源码或原始实验记录。按主代理明确授权，仅写入派生的独立核验 JSON 和本意见。

## 1. 实验有效性和公平性：限定 VERIFIED

- 六分支均从同一 44,867 字节 Journal 开始，SHA256 为 a8d1973aad1aae9bb15af7d11ebbe8ecb52ad5635a898b32d8da0c75763fdd7f，使用六个不同的新 Native Thread。原版本在每分支逐字段保留。
- 普通 Relevant History 的 16 项内容，独立逐项核对原 Native 路径、行号、Thread、Turn 和正文/实参/真实回执，内容一致。五份冻结资料与原研究快照、当前 fixture 的哈希相同。
- 历史通过非权威普通消息提供，没有登记为 CURRENT，也没有重放为本轮执行。两组都保留既有 Goal 和成功回执；OFF 不是完全没有 Goal 信息。
- 两对真实首请求分别去掉 ON 当前专用视图，并且只在审计副本归一化新 Thread、Workflow/Task、Input、message/effective-state ID、Host 时间、client metadata 和匿名会话 home 后，剩余 JSON 完全相同。原始 wire 未改。
- 后续请求随真实行为而异。处理包含整个当前专用视图的长度、位置和显著性差异，不能声称只测试了抽象 Goal 语义，也不能将当前视图可见认定为模型内在采用。

只有两对、固定平衡顺序和同一持续引擎，不能建立一般统计因果效果。历史是预选的相关材料，不能由此证明自动相关历史检索能力。

## 2. 场景 A：跨会话受反馈修订，限定 VERIFIED

真实 Call chatcmpl-tool-98f84c205dd46177 对 ff2a010b338474f6ea3f66f5 提出 revise，使用本轮 CURRENT 原话，并通过 input_ids 同时关联当前纠正和原始历史目的。Host 保存 76fe2c341f981c349d539f56；父链、正文、内容哈希、回执和 canonical Journal 一致。第二个完整模型请求真正携带新 head，最终回答准确报告保存事实，并明确语义正确性尚未由 Host 证明。

候选保留了长期 AI 产业研究目的和可检验跨公司研究方法，没有把未表达的限制解释为“用户没有任何限制”。尾部重复解释维护要求，属于抽象冗余，不能机械判整个目的扭曲；抽象质量仍 PARTIAL。

这是明确纠正下的一次存在性证据，不是自然形成或自主维护成功。新 head 只在同 Turn 后续请求中验证，没有下一独立用户 Task 使用此新语义的证据。

## 3. 场景 B：局部 Task 与长期方向区分，限定 VERIFIED

模型没有新增 Goal 操作或版本，ff2a 当前 head 保持，回答区分 Intel 本轮停止与长期方向仍有效，并保留 candidate/非 ActiveGoal/语义未确证的边界。

“覆盖”旧候选的措辞可以指当前 head 被替代；实际旧版本未丢失，不能仅凭该词断言删除历史。末尾建议以后可通过 Sideband 标记 Intel 完成，提示 Task 状态和 Goal 生命周期概念仍有风险，但没有发生这种操作。

没有恢复或取消原 Thread 的 Workflow；Task 结束在此仅是用户当前语义和模型停止继续该局部研究。零维护调用是合理结果，不能作为能力失败，也不能证明一般 M4。

## 4. 场景 C：PARTIAL，增量决策价值 UNKNOWN

ON1/f1 在不新增读取的情况下，利用真实历史做出了新的比较和计算，因此不能按“零工具”判为没有行动。但其跨公司 EPS“规模溢价”、Apple 相对 Google 的错误排序、退款与 non-GAAP 混淆，以及资料限制扩大解释，构成实质性质量问题。收入比例及 Google EPS 同比的算术正确，不足以支持后续错误推论。

OFF1/f2 有四次真实读取、一条实际保存的 local 研究问题候选和两次字符串“None”参数拒绝。用户委托模型自行选择问题，故不能仅因题目由模型提出便断言完全无用户依据；但没有独立认可它为持续方向的证据，不能计作自然长期 Goal 形成成功。默认 local 没有变成 global，更没有获得正式执行权威。

f2 没有最终回答。四个实际模型 HTTP/SSE 响应均完整，随后本地 502 和 Native 五次重连后失败。停止与冻结四请求上限相容，但原始局部异常文本没有记录，且 super 恢复先于上限检查，具体原异常和上限是否唯一原因仍 UNKNOWN。最终答案质量 CENSORED；预算内任务未完成和已经发生的参数/候选行为可以独立评价。不能将其当成 ON 质量优越的完整对照，也不能重标为上游网络、资源或 Context 故障。

OFF2/f4 确有读取和计算尝试，但 EPS/总营收不是无量纲收益率，收入单位错误且混用会计口径，金融检验质量 FAIL。免责声明不能修复无效指标。

ON2/f5 的主要数字、单位以及两项 EPS 比例计算更忠实，但“净营收比率”标签、未给出的收入增长前提、11-09/11-04 顺序倒置等仍错误。应保留这些反例；不能因保留 UNKNOWN 就判全部推理正确。

两对成本不能合并成简单的效率优势。特别是 ON2 为 55,474/1,335 输入/输出 tokens、186.7 秒，OFF2 为 53,737/1,119、164.8 秒；ON2 输入更多且更慢。ON1/OFF1 的完成状况和行动路径不同，也不构成等质量效率对照。

## 5. 执行、来源及状态边界：限定 VERIFIED

独立重新计算并保存了逐项检查：

- 12 个实际模型响应均为 response.completed，HTTP framing 完整，上下游 SSE 字节相同；不等于 12 个任务成功。
- 13 次本轮读取逐 Call、Decision、Observation、Native 回执、正文和文件哈希一致。旧历史读取没有重复计作新执行或新独立外部证据。
- A 和 f2 的两个新版本由真实调用保存；f2 两个拒绝调用没有额外版本。成功保存是结构/来源/状态事实，不是语义裁决。
- 六分支 ActiveGoal 均为空，原有记录保持；没有观察到权限或正式采纳提升。原有来源合法性不等于解释受到支持。
- 六 Native 进程组均清理为 absent。源码 136 项、安全 pins 15 项在独立核验时匹配。
- 本轮无 Compaction，最大单请求输入未超过 32K，不能由固定使用 64K 推广为本轮验证了长 Context 或压缩收益。

A、B、C 是独立分支，不能拼接成“A 修订后被 B/C 使用”的新 M2→M3 轨迹。Global family 绑定来自研究操作者，不计模型自主 Scope 推断。

## 6. 资源证据：限定 VERIFIED

独立从原始 service 样本重算：983 条有效采样、1090 条有效在线 AC；NVML 峰值约 28.837 GiB，Shared 峰值约 0.277 GiB，Commit 最低余量约 23.285 GiB，距离原停止公式的最低缓冲约 4.989 GiB。结果与主报告汇总一致。

服务正常 CONTROLLER_STOP、remaining=[]。启动 smoke 注入与真实服务观测分开，没有本轮实际资源超限或遥测失败证据。本轮约 1051 秒观测不是长期稳定性证明；未发现需要放宽原保护的理由。

## 7. 结论与研究建议

阶段报告、manual-review、cost-summary、resource-summary 与本次原始证据相符，未发现必须阻断归档的结论越界。正式结论保持：

| 维度 | 独立判定 |
|---|---|
| Runtime Contract / Information Integrity | 限定 VERIFIED |
| M1 用户意图归属 | PARTIAL，局部委托和持续目的仍有语义歧义 |
| M2 明确纠正 | 限定 VERIFIED；抽象质量 PARTIAL |
| 新 A head 的下一独立 Task 行为 | NOT RUN，不由 B/C 补足 |
| M3 一般后续行为 | 保留 PARTIAL |
| M4 自主生命周期 | UNKNOWN |
| M5 超过相同 Relevant History 的决策价值 | UNKNOWN |
| 整体 | PARTIAL |

建议保留已验证的隔离持久化和 Sideband，不新增维护层、通用语义裁判、subject 字段或第二套循环。若继续研究，可在某个已纠正分支真正接下一独立 Task，采用有独立正确性标准的行动评价，并继续允许简单历史已足够这一结论。不应通过重写提示、重跑删失样本或制造强制工具调用追求 PASS。

既有 32 版本上限是当前 Thread 可见版本集合，不是 Profile 总量；16 MiB Journal 等研究预算仍在。Hashchain 不提供任意合法前缀回滚防护。上述限制没有被本轮结果消除。

可复核派生检查：
/home/wqkan_wsl/uaea-n1x/research-records/goal-continuity-three-20261113T030425Z/audit-independent-checks.json
（SHA256 9764e7fa4423b97a3cf9fc8bd11004e194474a652341f771bb696af0e427a61d）。

审计不要求追加模型实验。本轮可以停止并提交架构评审。
