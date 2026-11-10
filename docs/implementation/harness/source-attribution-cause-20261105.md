# Context 与来源错配：原始轨迹追踪及局部因果对照

日期：2026-11-05。限定结论：**PARTIAL**。已定位输入丢失与模型归属错误；没有证明通用恢复方案已修复，也没有修改正式 Runtime。

## 1. 证据范围与复现

原始实验目录：

~~~text
/home/wqkan_wsl/uaea-n1x/research-records/recovery-context64-20261105T082201Z/
  tool-replay-32768/
  tool-replay-65536/
  tool-replay-fixture.json
~~~

本轮独立记录目录：

~~~text
/home/wqkan_wsl/uaea-n1x/research-records/source-attribution-cause-20261105T123519Z/
~~~

关键文件：trace.py / trace.json 逐请求追踪；summary-*.txt 原样提取压缩摘要；design.json、stream-confirm-design.json 为调用前固定的局部对照；*-request.json、*-response.json、*-stream-events.jsonl 为实际请求与返回；availability-aware-evaluation.json 为重新分类结果；evaluate.py 为隔离评价器；checks.json、safety.json 为保护与不变性检查。SHA256SUMS 固定本轮产物，source-index.json 固定所分析原始输入。

可离线重复运行 trace.py、evaluate.py；causal_replay.py、stream_confirm.py 会调用模型，不能当成离线检查命令。它们不属于正式执行入口。

本轮沿用现有受保护 32K Bolt、固定 1 GiB KV、36 GiB 引擎规划，执行六个非流式探索及两个流式确认；所有局部请求小于 32K，未重跑完整长轨迹。没有执行网页访问或模型提出的工具动作。

## 2. 原始 Token / Context 对照

| 项目 | 32K 原实验 | 64K 原实验 |
| --- | ---: | ---: |
| Harness 有效窗口 | 31,129 | 62,259 |
| 自动压缩阈值 | 24,576 | 49,152 |
| 最大观测输入 Tokens | 27,068 | 49,762 |
| Compaction 次数 | 5 | 1 |
| 总回放秒数 | 718.624 | 513.162 |
| 实际工具回传 / 唯一 URL | 24 / 20 | 20 / 20 |

匹配实验没有 Context 溢出证据。64K 的容量收益成立于这条轨迹，不能从一次对照推导统计性能或证据质量收益。

**VERIFIED：**全部 24/24、20/20 工具实际回传正文，在 JSON 解码后与对应夹具正文完全一致；URL、source_id 和实际文本 SHA256 对应，没有在初次工具投影中剪掉目标锚点。原始夹具是嵌套历史工具/审计/模型 JSON，含其他 SRC 标识和旧研究内容，并非一般网页正文；其干扰特性限制外推。

## 3. 五组首次丢失位置与最终错误

目标是每组四个 URL 中第一个 URL 的 Record anchor。下面请求序号为 model-http-audit.jsonl 的请求顺序，行号从 1 开始，request n 的出站审计行是 2n−1。raw 行号指对应 app-server-events.jsonl。

| 组 / URL 后缀 | 正确 anchor | 初次真实回传 raw 行：32K / 64K | 32K 首次由存在变缺失 | 64K 首次由存在变缺失 |
| --- | --- | --- | --- | --- |
| 1 / replay/1 | SRC-7256c1531088 | 34 / 34 | request14，紧随 compaction request13 | request9，紧随 compaction request8 |
| 2 / replay/5 | SRC-5a70b26e2758 | 79 / 79 | request14，同上 | request9，同上 |
| 3 / replay/9 | SRC-ffe29390e1b4 | 169 / 124 | request14，同上 | request9，同上 |
| 4 / replay/13 | SRC-e5c018e2ecf6 | 225 / 169 | request17，紧随 compaction request16 | request9，同上 |
| 5 / replay/17 | SRC-cf28a2af0ea6 | 281 / 225 | 最终 request17 仍可见 | 最终 request12 仍可见 |

完整 call_id、输入 item 索引、每次存在性与来源文件见 trace.json。32K Compaction completed 的 raw 行为 108、156、212、268、324；64K 为 198。

**VERIFIED：**前四组首先发生的是压缩后模型输入缺少精确源值，并非初次 Fetch 错配或已证明的长窗口注意力失败。32K 早期摘要曾保留旧锚点，后续摘要逐次选择性丢失；64K 唯一摘要一次丢掉前 16 个精确 Record anchor/映射，保留较多嵌套历史分析及旧的“只回答 ACK”要求。Host 原始回执并未被摘要改写。

原生最终回答应重新分类，不能把 0/5 当作五次同类幻觉：

- **32K：**最终仅 ACK，属于当前任务未响应。不能统计为五次伪造来源。最终当前用户请求和 Host current_user_request 均为正确的新来源核对要求；旧 ACK 要求仍在历史/摘要。旧要求干扰是合理推断，内部决策原因 UNKNOWN。
- **64K 第 1 组：**错误给出 SRC-cf28a2af0ea6，实际是 replay/17；预期 replay/1 的值已缺失。
- **64K 第 2 组：**错误给出 SRC-b230908c4fc2，实际是 replay/18；预期 replay/5 的值已缺失。
- **64K 第 3、4 组：**UNKNOWN，与当时缺少原值相符，是允许的弃答。
- **64K 第 5 组：**错误给出 SRC-0ed394e98eff，实际是 replay/20；正确 replay/17 及其关系仍在输入。这里可以确认存在模型语义归属错误。

这三个错误 ID 都曾真实返回；真实性不等于组别绑定正确。模型为何选中这些近期值，无法从输出还原其内部依赖。

## 4. Host 投影、24 KB 和位置

代码依据为当前工作区 harness/semantic_state_adapter.py:557 recovery_sources 与 harness/responses_bridge.py:279 _bounded_blocks。

- recovery_sources 从当前 Workflow 的成功 Host 回执取经哈希校验的正文前 300 字符，按来源版本去重后只选最近 **3 个不同 URL**。压缩后这不是所有历史来源的完整恢复器。
- 最终恢复来源为 replay/20、19、18；旧组值无法靠这一近期选择规则自动回来。replay/17 另保留在原生历史/摘要中。
- 24,000-byte 限制会优先删可选说明，再必要时缩小正文。本次两条匹配轨迹 **没有 recovery_sources.text 的预算缩减，没有 24 KB 拒绝**；最终记录大小分别为 23,453 / 23,452 bytes，仅删 model、web_limits 可选说明。
- 较早“巨大用户粘贴包”的无效试验确实触发该限制，但不能混入本次工具回放的因果解释。提高 24 KB 也不会自动改变最近 3 URL 的选择规则。
- Host 恢复块追加在原生 input 后。最终当前用户 item 位于 32K index9、64K index19；其后分别为 15 个 Host 块。当前请求未被替换，但相对位置及旧任务文字可能影响显著性。

**UNKNOWN：**精确逐 Token 位置、lost-in-the-middle 的独立效应。附加 render 接口返回 403，已保存 render-unknown.json，没有绕过接口限制。审计可证明消息内容及顺序、API usage，不能推断模型实际注意了哪些部分。

## 5. 最小因果对照：保持预算，改变输入供给或顺序

使用捕获的脱敏最终请求，单条件单次调用。它们不是原始线上请求的逐字节重放，不以新结果覆盖旧实验。输出上限均 512 Tokens，实际 completed，未见输出上限截断。

干预 A 仅把现有 Host 块移至当前用户消息之前，不增加文本。干预 B 用真实 Host 回执的 128 字符原文前缀替换既有 recovery_sources，包含 URL、source_id、内容哈希与来源事件；五条按逆时间放置，未提供组号或答案列表，没有新增提示规则。它是**研究者知道目标后选择来源的 oracle 对照**，尚非自动检索实现。

| 非流式探索条件 | input Tokens | 候选文本正确归属 |
| --- | ---: | ---: |
| 32K 原最终请求 | 15,467 | 0/5 |
| 32K 仅重排 | 15,467 | 0/5 |
| 64K 原最终请求 | 27,626 | 1/5，另四组 UNKNOWN |
| 64K 仅重排 | 27,626 | 0/5 |
| 64K 补回目标源短摘录 | 27,257 | 5/5 |
| 64K 重排 + 补回源 | 27,257 | 5/5 |

这六次返回仅在 API 的 observable reasoning_text 通道，未产生用户可见 output_text。这里只分析可观察候选文本，不能宣称可见最终回答或完整 Harness PASS。

因此追加两次与原历史流式形式对齐的确认，保留相同输入及 512 上限：

| 流式确认 | input / output Tokens | 可见回答正确归属 | 秒数 |
| --- | ---: | ---: | ---: |
| 原 64K 最终请求 | 27,626 / 88 | 0/5：四次错配，第五组 UNKNOWN | 38.60 |
| 补回真实源短摘录 | 27,257 / 102 | 5/5 | 42.24 |

两次均为真正可见 message/output_text，status=completed，无工具执行。原请求的错误细节不稳定，不能用非流式单次结果代替历史原答。

**VERIFIED（限定干预）：**可供给的任务相关来源关系影响结果；补回源后输入反而减少 369 Tokens，在现有 32K 引擎即可正确绑定五组。单纯重排没有得到收益，不能合入作为已验证修复。

**未证明：**通用来源选择的正确性、重复运行稳定性、真实研究质量、改进适用于其他模型或普通网页。没有因一次 5/5 就宣称语义幻觉解决。

## 6. 本轮修改、评价修正及安全

没有修改正式 Runtime、Harness、模型环境或权限。只新增本报告及独立记录目录的追踪、对照、评价脚本。生产 bridge/semantic 文件与本轮 before/ 逐字节一致；此前工作区修改全部保留。

隔离评价器将 no_answer、appropriate_abstention、missed_available_value、wrong_attribution、correct_literal_attribution 分开。8 项定向反例/断言通过，覆盖“存在真实 ID 但归属错误”“缺失时 UNKNOWN”“可见时漏答”“ACK 非回答”“值猜对不等于有当前来源支持”等；该夹具评价器不是通用语义校验器，没有成为 Runtime 控制逻辑。原始实验报告和 JSON 不覆盖。

本次资源保护的阈值与监控失效模拟均 PASS；采样 Dedicated 峰值 28.89 GiB、Windows Available 最低 24.08 GiB、Commit 余量最低 45.75 GiB。未降低阈值，原有 15 项启动/Runtime 文件哈希、Phase-1 清洁状态及旧实验 JSONL 完整性检查通过。

已主动停止本轮创建的服务和采样器：guard_reason=CONTROLLER_STOP，remaining=[]，8000/8003 无监听。控制器因主动 stop 输出非零结束，不是本轮资源保护触发。不涉及终止外部服务。没有 Commit / Push。

## 7. 独立判断及下一步

- **Contract 供给 PARTIAL：**真实回执和原始文本完整，但压缩后的有界投影不足以回答任意未来细节问题。不能把“已保存”当“当前已供给”。
- **Model Behavior FAIL（原生本任务）：**32K 未响应；64K 三次错配，其中第五组在正确输入可见时仍错误。两组均不能算完整任务 PASS。
- **局部因果对照 PASS / 通用修复 UNKNOWN：**恢复相关来源可在既有预算内改善结果；oracle 选择不能直接部署成公共策略。
- **权威污染未见证据：**模型摘要/回答出现丢失与错配，没有证据显示原始 Host Observation、授权、Goal 或 Memory 因而被改写。

维持 **32K 稳定默认与 64K 实验入口**，固定 KV、安全策略不变。64K 可减少 Compaction 与回放耗时，但不能代替来源保留/合法恢复；本轮不支持再扩大窗口、KV 或 24 KB，也不支持默认消息重排。

下一步最小问题是利用已有来源事件、内容版本和保存摘录引用，验证**任务相关来源的有界、可追溯按需恢复**，而非恢复所有网页正文。模型可提出来源引用，Host 验证对应真实回执与版本；缺失且用户禁止工具时应 UNKNOWN。来源选择本身需要独立对照，不能硬编码“每组第一个 URL”或由研究者选择替代运行机制。

本轮无需再做人工长测。进入上述局部实现前先评审选择边界；不新增 Information Pool、第二套执行循环或自动权威升级。
