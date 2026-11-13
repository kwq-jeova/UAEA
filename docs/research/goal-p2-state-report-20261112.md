# P2 Goal 提交状态报告与反馈表达配对（2026-11-12）

总体 **PARTIAL**。原反馈组对“最近失败修订”与“历史成功form”发生错配；明确状态组正确报告拒绝/committed=false/未保存/head未变，但仍把旧head正文误当作失败提案内容。**不宣布完整状态报告PASS，也不新增反馈层。**

## 1. 独立材料、问题与实际供给

批次 goal-p1-p2-m3-20261112T093455Z/P2。采用前次六次拒绝中的**前两次失败后的真实请求时间切片**：goal-m2-branches-20261112T073526Z/B，model-http-audit sequence2。真实原Native失败调用：

| Call ID | 操作/目标 | 实际失败提案正文 | 真实结果 |
| --- | --- | --- | --- |
| chatcmpl-tool-a78d84a56e8cb702 | revise / 098ea60b1c3caf2ca410b22d | 长期跨公司研究AI产业投资机会 | CURRENT quote不合规；未接受/未提交 |
| chatcmpl-tool-a9d018f5e15dac09 | revise / 0cb6591e2475fdd96208bc87 | 完成Intel当前财报与估值分析 | 同上 |

完整目标ID均加goal-candidate:前缀。此处是旧失败分支的原始两个head，不是本轮P1的63a3/7a20修订head；P2不带入P1新交互，也不注入后来四次拒绝或后来的修订结果。

两组同一候选、历史、模型、工具/权限、采样和Context；只改变两个失败反馈文本，且同时追加相同的状态核对问题：说明最近两次提交、接受、committed依据、保存/head变化和未知；不发新提案/工具调用。问题未预填成功或失败答案，评价真值来自原生调用/Host Journal，不是模型自评。

- A：现有terminal_attempt_fact，含Call ID、FAILED、错误及执行失败标记。
- B：保留真实Call ID、revise、host_accepted=false、committed=false、拒绝原因、new_version_saved=false、heads_changed=false、当前head ID/原文及正确Host摘要。
- B为隔离的明确状态表达，**不是完整原始回执逐字直通**，也未补充实际失败提案正文。

[P2/source.json](../../../research-records/goal-p1-p2-m3-20261112T093455Z/P2/source.json) 链接经上轮修正版校验的冻结输入；[transport-cpu-tests.json](../../../research-records/goal-p1-p2-m3-20261112T093455Z/transport-cpu-tests.json)、[final-audit.json](../../../research-records/goal-p1-p2-m3-20261112T093455Z/final-audit.json) 独立确认仅反馈不同、问题相同、B的Call/操作/拒绝值/head哈希均真实。实际转发请求与冻结JSON完全一致，不以本地Adapter准备替代送达证明。

这是用真实历史失败请求做**单跳状态理解诊断**：复用原Bridge，真实Bolt输出，0新Tool调用、0Host提交，不是新多轮Harness状态维护或M3。当前追加问题是研究者诊断输入，不伪装成历史用户原话或已注册Goal操作。

## 2. 原反馈 A 的完整回答审读

全文 [P2/A/model-answer.md](../../../research-records/goal-p1-p2-m3-20261112T093455Z/P2/A/model-answer.md)，原始SSE/审计在 [P2/A/model-http-audit.jsonl](../../../research-records/goal-p1-p2-m3-20261112T093455Z/P2/A/model-http-audit.jsonl)。

**FAIL（最近事件身份绑定）**：模型列出原始两个候选的旧正文，使用历史form的committed=true、snapshot_status=saved作为这两次“提交”的说明；但问题问的是最近两个失败revise。这些true字段本身是真实历史值，错误在于**关联了错误的操作/Call**，不是凭空编造一个不存在的标志。

它也正确说当前head仍为旧内容、未保存纠正文本；最后却说“尚未提交新的修正”，忽略已发生但被拒绝的修订尝试。应区分未尝试、已尝试未接受、已接受未供给。

模型对长期持久性保持不确定，不能仅因这种谨慎判错；错误是旧成功回执与最新失败混淆，非“说UNKNOWN不够积极”。缺少显式committed字段时，承认无法直接确认是允许的。

## 3. 明确状态 B 的完整回答审读

全文 [P2/B/model-answer.md](../../../research-records/goal-p1-p2-m3-20261112T093455Z/P2/B/model-answer.md)，原始SSE/审计在 [P2/B/model-http-audit.jsonl](../../../research-records/goal-p1-p2-m3-20261112T093455Z/P2/B/model-http-audit.jsonl)。

**限定PASS（结果维度）**：正确报告两次未接受、committed=false、新版本未保存、head未变；没有虚称更新成功，也未实际再次提案。

**FAIL/PARTIAL（提案内容与事件绑定）**：它把长期旧head正文“需从本地摘录之外查找更多资料，并在候选中保留”列作被拒提案。真实失败提案却是精简目的文本“长期跨公司研究AI产业投资机会”。原始旧文字最初form已经成功，不能把它当成最新失败revise内容。第二次笼统称相同，未清楚按真实Call ID报告。

所以不能以几个false字段命中或最后一句“没保存”给完整PASS；也不能把明确状态格式认定为普遍更优。两组各一次，仅有描述性的部分差异。

## 4. 可验证的信息供给缺口与模型责任

**VERIFIED**：两组当前模型请求都没有保留这两个失败Call的function_call参数绑定；对应反馈也没有submitted_proposal/arguments/hypothesis等实际提案正文。原始Native有这些字段，仍可审计；见 [final-audit.json](../../../research-records/goal-p1-p2-m3-20261112T093455Z/final-audit.json) 中P2.feedback_visibility。

这不表示目的文字完全未出现——原用户表达可能有相同词句；缺少的是**特定Call ID → 实际提交内容**的可见关联。明确B中的current_heads.hypothesis是旧保存对象，并非submitted hypothesis。

- 供给缺口：通用失败历史投影丢失实际提案关联，完整“提交了什么”不能直接读取。
- 模型责任：缺少可见绑定时应保留UNKNOWN，不能用旧head正文补填。
- **HYPOTHESIS**：字段布局、role/前缀和历史成功回执可能影响了事件选择；本配对不能分离它们或证明内部因果。
- 不能把全部错配只归为模型，也不能把补齐字段当作语义误读必然消失。

## 5. 结果矩阵

| 子问题 | A 原转换反馈 | B 明确状态 |
| --- | --- | --- |
| 最近失败修订 vs 历史成功form | FAIL | PARTIAL，结果正确、正文仍错配 |
| 接受/committed/新版本/head | 旧true回执归错事件；旧head识别正确 | 限定PASS，本单样本 |
| 实际失败提案正文 | FAIL，应该标明可见性不足 | FAIL，仍拿旧head补填 |
| UNKNOWN的合理使用 | 部分谨慎，但不能弥补事件误配 | 某些字段直接可见；正文缺失未保持UNKNOWN |
| 新工具调用/正式状态变化 | 0 / 0 | 0 / 0 |
| 完整状态报告 | FAIL本配对样本 | PARTIAL |
| 真实Goal纠正 / M3 | NOT RUN | NOT RUN |

A input/output=20,903/926，B=21,531/574 Tokens；增加明确反馈628输入Tokens。两组均完整response.completed、framing通过、上下游字节一致，未触180秒限额。服务端输出上限按剩余窗口动态决定（两组输入长度不同），实际输出均不足1K，未出现length截断；没有调采样或输出上限来选优。单次耗时不是格式性能统计，详见原capture.json。

## 6. 最小兼容性建议，不在本轮实施

输入Schema的quote/input_ids/candidate_id已能表达来源及修订，不需要新增正式subject、对象或Goal Engine。

若继续收敛状态报告，优先审查**现有失败投影中的事实保留**，而不是增加第二轮LLM或自动语义纠错：

1. 保留Call ID、operation、target candidate/version与实际提交内容的有界原文或可解析引用，明确这是提案，不是事实或权限。
2. 同时保留真实receipt与当前head引用；旧form成功不能代表后续revise成功。
3. 不以当前head正文替代失败提案正文，不自动改quote或补发。
4. 原记录不可变但可以追加研究版本；不可正式采纳不等于不能提交研究候选。说明需用实际出站审计验证。
5. 这些只证明身份、状态和执行事实，不证明候选语义真实、长期有用或获得授权。

该建议可复用现有投影和来源机制，不需要核心架构重构。由于涉及正式历史反馈行为，本轮仅提出证据与兼容方案，**未修改provider_history、正式Schema或权限**。不能因A本样本不完整，就认定必须增加新反馈层；B也未全面通过。

## 7. 里程碑与停止

P2从上轮“无状态回答所以UNKNOWN”推进到可复核状态报告：部分错误能定位到具体事件/正文错配，但整体仍PARTIAL。P1无合格已保存修订，因此[M3未运行](goal-p1-faithfulness-20261112.md)；M4/M5 UNKNOWN。保留全部失败，一次固定配对后停止，不再调整问题追求PASS，不安排人工长会话。
