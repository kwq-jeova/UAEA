# Goal 失败反馈表达独立对照：C1 无效条件与 C2 修正版（2026-11-12）

总体 **PARTIAL**。字段丢失为 **VERIFIED**；一次有效反馈对照未显示合法CURRENT引用恢复收益；保存状态理解 **UNKNOWN**（两组均只输出工具提案，没有状态回答）。不认定Structured反馈优于现有投影，也不认定现有反馈已充分。没有新的Goal提交、Host更新或M3行为。

## 1. 为什么需要独立比较

前批真实Host回执有ok=false、committed=false；经 [provider_history.py](../../harness/provider_history.py) 转换后，模型实际收到terminal_attempt_fact，保留失败与错误，但缺少Goal提交状态字段。旧报告已有追加勘误，不能继续声称原始完整回执已送达。见 [prior-feedback-audit.json](../../../research-records/goal-m2-current-feedback-20261112T083318Z/prior-feedback-audit.json)。

本轮B分支已经实际提交2个版本，新的问题是语义外推而非拒绝反馈；本C实验独立回答旧失败反馈问题，**不能用来解释或修复新B的目的抽象错误**。参见[M2修订报告](goal-m2-current-correction-20261112.md)。

## 2. 冻结材料与公平性

采用真实旧批 goal-m2-branches-20261112T073526Z/B 的 model-http-audit **sequence2**（两个初次失败后的实际Harness后续请求），在本轮模型运行前冻结。含原候选、原反馈、模型提案与旧Host状态，排除新B的输出和修订。

| 条件A | 条件B |
| --- | --- |
| 原转换terminal_attempt_fact | 真实Host事实的结构化反馈 |
| Call ID、FAILED、错误文本、execution_succeeded=false/result_available=false | Call ID、revise、rejected、host_accepted=false、committed=false、失败原因、head未变、无新版本、原head ID/原文/实际Host哈希 |

只替换2个历史失败反馈消息的文本；用户输入、模型、工具定义/Schema/权限、Context、采样、输出预算及其余历史内容均相同。当前quote规则不改。B增加明确状态和原head信息，输入成本相应增加；不是等Token信息量实验。

这是一跳**真实模型续接请求回放诊断**，复用现有Bridge与已冻结Harness请求。**不执行任何生成工具提案，也不建立第二套Agent Loop**。response.completed/function_call.status=completed表示生成结束，不是Host执行完成。该机制不能代替新的真实多轮Goal提交或状态读回测试。

## 3. C1 数据构造缺陷与保留

初批 goal-m2-current-feedback-20261112T083318Z/C 的两个请求完整结束，但离线校验发现，我构造“完整反馈”时用紧凑JSON计算了candidate_sha256；实际Host digest使用ensure_ascii=false、sort_keys=true的默认分隔符。两条head的ID/原文正确，4处重复摘要哈希错误。

- **FAIL（研究数据构造）**，不属于模型、正式Runtime或传输缺陷。
- 原冻结输入、响应、锁文件保持不变；不把它作为有效的“忠实完整状态反馈”比较。
- [C/feedback-integrity-audit.json](../../../research-records/goal-m2-current-feedback-20261112T083318Z/C/feedback-integrity-audit.json)包含错误哈希、真实哈希与原因。
- 原C1两组均继续生成历史quote工具提案，无状态回答；可记录原始现象，不能用有缺陷的B条件得出格式优劣。
- 原来的Goal纠正B不受影响；其2个Host接受、新版本和原文均已独立按实际Host digest复核。

为完成有效对照，另建新批 goal-feedback-control-fixed-20261112T085326Z，重新预登记**仅一次修正版A/B**。A保持原输入不变；B仅修正错误head哈希，采用实际Host digest。CPU先确认正确记录通过、C1错误摘要反例被拒；全部4处状态引用逐项核验，并验证A/B除2个反馈消息外完全一致。没有改Prompt、随机种子、采样参数或输出限制来追求PASS。见 [preregistration.json](../../../research-records/goal-feedback-control-fixed-20261112T085326Z/preregistration.json)、[pair-proof.json](../../../research-records/goal-feedback-control-fixed-20261112T085326Z/pair-proof.json)、[baseline-heads.json](../../../research-records/goal-feedback-control-fixed-20261112T085326Z/baseline-heads.json)。

## 4. C2 有效对照的实际结果

两组均一次请求、完整response.completed、HTTP framing通过、上下游字节相同、未触及采集预算或180秒期限。真实出站请求与各自冻结输入完全相同；B状态中的head摘要与Host记录匹配。见 [final-audit.json](../../../research-records/goal-feedback-control-fixed-20261112T085326Z/final-audit.json)。

| 维度 | A：原转换反馈 | B：结构化真实状态 |
| --- | --- | --- |
| input Tokens | 20,796 | 21,424 |
| output Tokens | 386 | 398 |
| 耗时 | 56.08秒 | 56.06秒 |
| 模型生成提案（未执行） | 2个refine | 2个revise |
| parent选择 | 原真实head | 原真实head |
| quote | 历史长期目的及Intel局部目的 | 历史长期目的及Intel局部目的 |
| quote属于当前原始纠正 | 0/2 | 0/2 |
| Host执行 / 新版本 | 0 / 0 | 0 / 0 |
| 状态说明回答 | 无 | 无 |

A使用当前纠正input_id，但quote仍是历史目的；B使用历史purpose input_id，quote也仍来自历史。不能把更换input_ids视为解决CURRENT触发引用；两类来源用途不可互换。

B长期草案包含“不自行增加长期约束”，与主B的“不需要任何长期限制”不同；但它是未执行草案，不能冒充已修订Goal，也不能由这一个差别证明反馈导致更好语义质量。

完整输出见 [C/A/decoded-result.json](../../../research-records/goal-feedback-control-fixed-20261112T085326Z/C/A/decoded-result.json)、[C/B/decoded-result.json](../../../research-records/goal-feedback-control-fixed-20261112T085326Z/C/B/decoded-result.json)；原SSE、请求、HTTP审计仍保留。未自动提交、未模拟接受，也未为取得状态回答追加提示。

## 5. 结论的边界

- **VERIFIED**：转换确实丢失Goal回执字段；修正版结构化字段实际正确送达。
- **FAIL（本对照的合法恢复观察）**：两组生成的quote仍不属于CURRENT原始纠正，未观察到字段更完整便解决引用选择。
- **UNKNOWN**：模型能否正确报告“已提案/被拒绝/未保存/原head仍有效”。本次两组选择再次提案，没有状态说明输出；不能从无回答推断它们已经理解或继续虚称保存。
- **UNKNOWN**：哪种反馈普遍更优。仅一个有效配对、非统计重复，操作refine/revise不同不自动代表优劣。输入多628 Tokens、输出多12 Tokens；约0.02秒延迟差没有性能推论意义。
- **NOT RUN**：真实工具后续接受/拒绝以及跨轮Task；本诊断不应用输出。
- 不重复测试直到产生状态回答或PASS。本有效配对完成后停止，C1失败与C2结果都保留。

## 6. 资源、成本与正式边界

两个服务批次分开记录：主批B+C1约480.49秒，修正版C2约237.19秒，均主动CONTROLLER_STOP；不是资源保护失败。各自只启动一次模型，**本轮合计2次启动、6个模型请求**（B2+C1两次+C2两次）；不隐去C1无效条件的成本，不合并为一次运行。

| 指标 | 主批B+C1 | 独立C2 |
| --- | ---: | ---: |
| 有效资源采样 | 460 | 225 |
| NVML峰值 GiB | 28.565 | 29.031 |
| PDH Dedicated峰值 GiB | 29.039 | 29.029 |
| Shared峰值 GiB | 0.132 | 0.195 |
| Commit最低余量 GiB | 25.808 | 25.648 |
| Commit停止线缓冲最低 GiB | 7.512 | 7.352 |
| WSL最低可用 GiB | 17.634 | 17.723 |

全部AC样本有效在线；单时钟、Fail-Closed、GPU/Commit/WSL阈值不变，56/72、64K、KV1GiB、util0.65、单并发不变。所有服务/采样器/AC正常清理，端口清空。资源曲线见 [resource-series.csv](../../../research-records/goal-m2-current-feedback-20261112T083318Z/resource-series.csv)、[resource-series.csv](../../../research-records/goal-feedback-control-fixed-20261112T085326Z/resource-series.csv)；不是持续稳定性证明。

正式Schema、CURRENT要求、Goal/Memory采纳、Provider Policy、SQLite及Phase-1不变。只是隔离研究代码和事实反馈文本对照，不把模型输出当授权或执行事实。

## 7. 下一步

当前没有足够证据决定替换Sideband或合入新的反馈格式。事实投影应尽量保留Goal提交状态，**这是信息保真要求，不是语义质量已改善的实证结论**。后续如专门测失败状态理解，应预登记一个两组相同的“只报告真实状态”任务，而非事后强求当前一跳续接产生回答；不得把这种任务混为合法工具恢复或M3。

主线仍是目的解释的忠实性：先避免把纠正操作的元要求变成用户永久偏好，再按M3准入条件验证真实新Task。不增加语义裁判、自动补发或Memory层；本轮停止提交评审。
