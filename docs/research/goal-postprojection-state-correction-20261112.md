# Goal 历史投影修复后的状态读回与纠正（2026-11-12）

总体 **PARTIAL**。用户已接受前一轮历史投影工程限定 PASS；本轮恢复真实 Bolt + Harness 行为验证，没有重新修改正式 Runtime 或 Goal 契约。

**评分更正：** 逐字段复核后，hypothesis 为 4/6 正确，2/6 将 quote 当成 hypothesis；target/committed 分别正确，但不能合并为完整字段绑定 PASS。原模型回答、Native、HTTP 审计未修改，旧评审快照已保留。独立纠正分支提出了目的忠实的 refine 草案，但又把历史目的原句用于 CURRENT quote，Host 正确拒绝，未保存新版本。M3 因前置条件不成立而 NOT RUN。

## 1. 冻结条件、独立分支和研究记录

首批：goal-postprojection-state-correction-20261112T122139Z。

- P2：克隆真实六次失败分支 Native Thread；Host Goal 使用原始已核验的两 head 基线。失败分支的 heads/versions 与原基线相同。额外旧反馈只作为 Native 历史，不声称完整恢复其全部 Host 输入状态；本分支不允许变更 Goal。
- B：独立克隆原始 goal-intent-lifecycle-20261112T031832Z/B，使用两个真实已保存候选；只给一次新用户纠正，首次 Goal 拒绝即停止。与 P2 不共享后续模型交互。
- M3：仅在 B 产生语义忠实、实际接受保存且成功投影的新版本后，才能继续同一 B Thread 的 Apple 任务。

当前源码含用户评审通过的历史投影修复，冻结 bundle、源码 SHA、实际工具 Schema、输入和判据均在启动模型前保存。56/72、64K、1 GiB KV、seq1、util0.65、Bolt/vLLM0.32/Codex0.163及原 Guard 不变。没有强制 Goal 生成、自动补发、自动改 quote、自动采纳或新 Agent Loop。

[首批预登记](../../../research-records/goal-postprojection-state-correction-20261112T122139Z/preregistration.json) /
[用户脚本](../../../research-records/goal-postprojection-state-correction-20261112T122139Z/scenarios.json)。

这些新反馈是研究者编写的实验输入，目的真值依据原始用户明确表达；不冒充用户新增的真实长期选择。

## 2. P2 首次运行：研究拦截错误，不评为认知失败

模型选择用已授权 read_section 读取新副本的 ledger.md。研究驱动误将“状态核对不变更候选”实现成“拒绝所有工具”，在实际文件执行和完整回答前抛异常。

这是 **研究执行器缺陷 / CENSORED**，不是 Host 拒绝 Goal，不是资源中断，也不能证明模型读错失败历史。保留该批请求、Native 调用和失败日志。

因此独立建立一次修复试验：

goal-postprojection-readback-repair-20261112T123257Z。

相同 P2 问题、冻结模型与来源、Goal 工具 Schema；仅修研究拦截范围：允许既有只读工具，仍禁止本分支变更 Goal；最多四个模型请求。CPU 反例确认只读调用委托现有 Harness、Goal 变更不进入 Host。没有新增权限，没有追加纠正反馈，没有重跑 B。

新分支最终没有选择工具，直接完成回答。因此不能声称“允许读取文件导致读回变正确”；新路径、当前时间及生成差异也使它不是严格单变量 A/B。这一次修复试验后没有继续调输入追求 PASS。

[修复试验预登记](../../../research-records/goal-postprojection-readback-repair-20261112T123257Z/preregistration.json) /
[研究拦截 CPU 反例](../../../research-records/goal-postprojection-readback-repair-20261112T123257Z/cpu-guard-regression.json)。

## 3. 完整 P2：字段绑定 PARTIAL（更正旧限定 PASS）

[完整回答](../../../research-records/goal-postprojection-readback-repair-20261112T123257Z/P2/model-answer.md) /
[事实审计](../../../research-records/goal-postprojection-readback-repair-20261112T123257Z/P2/factual-audit.json) /
[逐项完整文本判读](../../../research-records/goal-postprojection-readback-repair-20261112T123257Z/manual-review.json)。

实际出站请求包含六条完整失败 fact。原 Native 参数、Journal payload_sha256 和 Host 拒绝原因逐项匹配；模型按 Call ID 报告了正确目标和未保存状态，但正文栏只有 4/6 与实际 hypothesis 相同；第3、4项填入的是同 Call 的 quote。没有借旧 head 补填并不等于字段绑定正确。旧答没有独立 quote 栏，quote 准确性为 UNKNOWN。

| Call ID | 模型正文栏原样 | 目标末段 |
|---|---|---|
| chatcmpl-tool-a78d84a56e8cb702 | 长期跨公司研究AI产业投资机会 | 098ea60b1c3caf2ca410b22d |
| chatcmpl-tool-a9d018f5e15dac09 | 完成Intel当前财报与估值分析 | 0cb6591e2475fdd96208bc87 |
| chatcmpl-tool-b21dfc2c9aa2e545 | 我希望长期跨公司研究AI产业投资机会 | 098ea60b1c3caf2ca410b22d |
| chatcmpl-tool-8b034a9ece344047 | 另一个局部目的，是完成Intel当前财报与估值分析 | 0cb6591e2475fdd96208bc87 |
| chatcmpl-tool-ae8f596efc29972d | 用户希望进行长期跨公司研究AI产业投资机会 | 098ea60b1c3caf2ca410b22d |
| chatcmpl-tool-971f05e86a90bf4e | 用户希望完成Intel当前财报与估值分析 | 0cb6591e2475fdd96208bc87 |

目标完整 ID 均为 goal-candidate: 前缀。

模型还准确读回两个当前 head 的完整正文、ID、canonical SHA、form/candidate 状态，并说明未转为正式 ActiveGoal，失败修订没有覆盖旧 head。实际 Host 仍 2 heads / 2 versions；本次 0 Goal 调用、0 文件读取、0 新版本。

两个需要保留的表达问题：

1. “Host 全部返回 tool_failure”不够精确：tool_failure 是历史投影的通用 reason，原始 Host 错误是 CURRENT 引用要求。模型报告了正确具体原因，但未严格区分原始回执与投影摘要。
2. committed 栏写“未提交”，容易与“未尝试发起提案”混淆。它已明确列出六次实际提交正文，未否认调用发生；更准确应为“提案已发起，但未提交保存”。失败 fact 的 current_head=UNKNOWN 与独立 Host 当前 heads 是两种供给范围，回答列出了两者，但没有充分说明区别。

**更正后的逐 Call 结论：** hypothesis 4/6 正确；b21dfc2c9aa2e545 的实际 hypothesis 是“长期跨公司研究AI产业投资机会”，8b034a9ece344047 的实际 hypothesis 是“完成Intel当前财报与估值分析”，两条回答都误用了同 Call 的 quote。target 6/6、committed 6/6；quote 未单列，UNKNOWN。前两条真实 hypothesis 与 quote 恰好相同，字面匹配也不能证明模型区分了二者。总体 P2 为 **PARTIAL**，撤销旧“完整绑定限定 PASS”。旧评分错误源于以全文包含关系代替带字段标签的归属核对；后续必须以同 Call 下的具体字段比较。

## 4. B：目的忠实草案出现，但受反馈保存闭环 FAIL

用户反馈指出：资料需求、查询和临时条件是模型工作需要，不是用户长期目的；未知约束不能擅自判定存在或明确不存在。没有提供标准候选正文，没有指定操作或参数。

唯一真实调用：

    Call ID: chatcmpl-tool-81aeeb81a19d032c
    operation: refine
    candidate_id: goal-candidate:098ea60b1c3caf2ca410b22d
    hypothesis: 长期跨公司AI产业投资机会研究是全局范围目标
    input_ids: [input:f4e32d18-219d-4c3e-83ab-6b89201fee81]
    quote: 长期跨公司研究AI产业投资机会

**有利的语义观察：** 草案保留用户原有跨公司 AI 投资研究目的与全局范围，去掉模型补资料待办；未将“没有依据”写成“用户没有任何长期限制”。refine 作为修正理解的操作本身可以合理，不因未选择 revise 判错。

**确定失败：** quote 是历史用户目的原句，不是 CURRENT 本轮纠正的精确子串。历史目的依据正确不代表它可以充当当前操作触发依据。实际出站 Schema 明确包含 CURRENT 要求；不能再将此失败解释成工具说明完全未送达。

Host 回执：ok=false、committed=false、Quote must come from CURRENT original input, not model/summary。目标指向真实 head，Host 没有版本绑定或传输拒绝；没有证据要求放宽 CURRENT。

按预登记，第一次拒绝后停止，未补发、未替换参数、未给第二次用户反馈。原 2 heads / 2 versions 不变。没有完整最终回答，不能宣称本轮模型在收到完整失败反馈后又虚称成功；其后状态报告是 **NOT OBSERVED**。

[原生调用与 Host 回执](../../../research-records/goal-postprojection-state-correction-20261112T122139Z/B/goal-wire-receipts.jsonl) /
[引用与保存事实核验](../../../research-records/goal-postprojection-state-correction-20261112T122139Z/B/factual-audit.json)。

这次是模型证据用途/参数绑定失败，不是新发现的 Runtime Bug。草案正确不能替代真实保存；过去两次合法 revise 的操作证据仍保留，不因本次失败抹除。

## 5. 传输、成本与安全

完整 P2：1 个真实模型请求，response.completed / HTTP framing 完整，上下游 SSE 字节相同。API usage：input 25,884 / output 1,535 / total 27,419 Tokens；Native Turn 167.413 秒。无 Compaction、无 Context Overflow、无输出截断证据。

首批 P2/B 各有一个真实提案请求，但被研究停止提前结束，未取得完整 HTTP 终态和 API usage。它们不是成功完整响应，成本 **UNKNOWN**，不能填成 0。真实 Native Tool Call 和 Host 接受/拒绝证据可独立使用。不能把本轮 1 个完整响应与前两条局部响应算成 3/3 完整。

| 服务批次 | 有效 service 样本 | NVML 峰值 GiB | Shared 峰值 GiB | 最低 Commit 余量 GiB | 最低停止线缓冲 GiB | 最低 WSL 可用 GiB |
|---|---:|---:|---:|---:|---:|---:|
| 首批 | 175 | 28.647 | 0.154 | 24.081 | 5.785 | 17.625 |
| 读回修复批 | 257 | 28.735 | 0.206 | 24.149 | 5.853 | 17.650 |

两次引擎均报告 KV 容量 109,817 Tokens，固定分配仍为 1 GiB；没有改 UMA、Context、并发或采样配置。AC 启动年龄和探测返回合计均小于 3 秒，观察器身份有效，结束均 error=null。遥测单时钟最大确认上界分别约 0.119 / 0.128 秒。

所有服务按研究控制器主动 CONTROLLER_STOP 结束，remaining=[]；不是资源越界、NVML 故障或安全绕过。手工生命周期 Guard 因主动停服返回非零 launcher 退出值属既有行为，不能误算硬件故障。Native 进程组均已退出，服务端口已关闭。启动中的 guard_smoke_limit/stale 是既有安全注入，资源统计只取 case=service，未把模拟高值混入真实峰值。

原始历史 6 件文件及 3 个 Native 副本的源 home 哈希未变；SQLite Schema 未改。只新增隔离研究批次、报告和进度索引。无 Commit/Push。

[资源与保护证据](../../../research-records/goal-postprojection-readback-repair-20261112T123257Z/resource-summary.json) /
[原件不可变性](../../../research-records/goal-postprojection-readback-repair-20261112T123257Z/source-immutability.json)。

## 6. 里程碑与架构判断

| 项目 | 本轮结论 |
|---|---|
| 已评审历史投影修复 | 保持限定 PASS；真实模型请求实际收到完整失败事实 |
| P2 字段绑定 | PARTIAL：hypothesis 4/6，2条 quote 误填；quote 未单列 UNKNOWN；target/committed分别6/6 |
| M1 用户目的与待办归属 | PARTIAL；本次 refine 草案有利，不代表全覆盖 |
| M2-A | 保留限定通过，语义 PARTIAL |
| M2-B 受反馈保存与忠实性 | 本分支 FAIL：草案忠实，但 CURRENT 引用错误、0 保存 |
| M3 | NOT RUN：没有合格已保存修订，未运行 Apple 后续任务 |
| M4 自主生命周期 | UNKNOWN |
| M5 相对 Relevant History 决策价值 | UNKNOWN，未开展匹配对照，不报告收益 |

现有 Schema 已有合法 CURRENT 修订成功历史，当前也能表达目的忠实草案；没有证据证明必须新增字段、Goal Engine、自动修订器或语义裁判。主要未闭环环节缩小为：**历史目的依据与当前纠正触发依据的区分，能否正确转成合法提案。**

下一步建议仍保留 Sideband，在独立小规模研究中只检验证据用途理解及实际参数绑定；任何工具说明改善须核对真实出站，不能再次把本地定义当成送达。不扩充 Runtime 校验规则，不自动把 quote 改成当前输入，不回到完整 30×2 长实验。只有忠实候选真实保存并投影后，才进入 M3，再研究 Relevant History 增量。

本轮原始模型试验已结束，不重跑。2026-11-12 字段归属复核修正了本报告和 manual-review.json，原评价字节快照保留于新纠正批次 before/，原模型回答/Native/HTTP/Journal 不变。逐字段真值与读出值见 ../../../research-records/goal-field-understanding-correction-20261112T130408Z/old-evaluation-correction.json。M3/M4/M5不提升；新限定验证另立批次，不与旧结果混算。
