# UAEA R0 — Information Lineage 离线最小建模与实证报告
日期：2026-11-03（Asia/Shanghai）  
判定：**R0 PARTIAL；有限早期认知信息建模基础已存在，通用完整血缘尚未通过。**
本轮仅独立离线研究；无Runtime接线、模型调用、数据库新建、公共Schema、Commit/Push。

## 1. 独立架构判断

**VERIFIED（限定）**：现有Host回执、输入记录、来源哈希、SQLite access事件及Goal决定
已经足以恢复若干真实链路；字段名称不同不构成建设Global Information Pool的理由。
本实验只需离线映射、只读SQL和标准库校验，没有导入UAEA运行实现或创建第二执行器。

**HYPOTHESIS**：这一引用基础可供早期Goal/Intent/Context/Evidence等研究共享，
条件是各研究保留独立解释、评价及合法采纳边界。当前并未实现跨模块自动消费或Memory Admission。
**UNKNOWN**：模型实际采用的证据、语义支持/真实性、未记录依赖、完整跨会话版本恢复。
**CONFLICT**：把摘要、自报引用、内容hash或研究图中的连边直接变成采纳/授权。

下一步不应先开发信息池，也不必完成全部R1–R4。
对来源完整的case，可以开始限定Goal/null预测问题的研究设计；
先选观察单位/标签及对照输入规则，不能直接从本次记录计算MDL。

## 2. 最小模型（仅离线表示，不是正式Schema）

实体保留：本地研究record ID、实体种类、原生ID、来源运行/会话命名空间、已知scope、
内容版本指纹、原记录定位及已知时间；未知适用期明确为UNKNOWN。
每个实体指向既有文件/行号/JSON Pointer，或只读SQLite表/主键，不复制原始请求正文或模型请求体。

- 原始用户输入与模型提议分开；Host注册来源和原文hash可核验，但不构成全部行动的通用授权。
- Action Proposal、执行Observation、来源引用、摘录、回显、模型请求、Compaction活动、
  模型Claim、Goal候选、原始Host控制和采纳决定分别表示。
- SQLite来源行和EvidenceReference通过access_event_id/URL/内容版本匹配，
  作为同源别名证据保存；不虚构一条因果派生边来代替身份匹配。
- `derived_from`：已知记录生成/派生关系；具体转换依据随边记录。
- `available_in_context`：选定内容实际出现在脱敏出站请求；不证明模型理解或使用。
- `asserted_supports`：模型显式列出Observation作为候选依据；只是可定位的声称。
- `adopted_by_decision`：状态版本关联到独立决定；旧原始控制缺失时，边为UNKNOWN，
  不因决定ID存在而自动判合法。
- 每条边保留证据说明、VERIFIED/UNKNOWN等等级；semantic_support/truth保持UNKNOWN，
  不设置可跨模块转移的可信度或信息量分数。

ID是本实验的记录定位符，不是新统一ID系统。原生ID相同的不同版本不合并：
例如同一Goal的不同决定后状态按指纹、日志位置分别保留。
同一次调用的回显则关联共同Observation，而非重复计数为外部事实。
不预设全图为DAG；本次构建边没有循环不构成对未来认知关系的限制。

时间分开保存已记录观察/访问时间和对象created_at；缺记录不补造。
当前Goal状态、当时Goal状态、信息适用期和世界真伪互不替代。
JSON规范化指纹只用于本研究的版本比较；来源原始字节hash与供给摘录hash另行核验，
不把它们互换。记录位置稳定以源文件hash未变化为前提，文件搬迁后的解析不在此次PASS内。

## 3. 四个真实历史案例

所有下列行号为1-based。完整file/line/pointer/native ID见source-index.md和entities.jsonl；
source-manifest.json固定输入文件字节指纹。不存在根据最终回答猜测隐藏推理父节点的边。

### C1：同一次真实读取，多种回显/投影

运行A：
`/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/goal-compat-active-20261102T124823Z/bolt/harness/`

- 原始行动：app-server-events.jsonl:182，call_id
  `chatcmpl-tool-84cb7774776d15f2`。
- 权威执行记录：execution-contract.trajectory.jsonl:2，
  `payload.execution_observation.observation_id` =
  `execution:86d268b5d05de9e571727f20848a5926bc78862488432e21486ebddc4808ff5b`。
- 回显：app-server-events.jsonl:183，dynamicToolCall及返回的相同Observation ID。
- 模型供给：model-http-audit.jsonl:5，`/request/input/7`的function_call_output，
  call_id匹配，821字符摘录原文在解码后的请求中存在。
- 摘录hash：
  `a6b85b87eb56f805d9955a263cf4b8716fff964d51f2b06adc84dd374a2ba335`；
  与实际摘录UTF-8一致。
- 来源文件引用另保留path/source_hash/section/line范围；未用现在README内容冒充历史完整文件。
- **VERIFIED**：这些是同一Observation的至少两种派生表示，只算一次已识别执行来源。
  **UNKNOWN**：模型理解/采用、历史完整文件字节是否仍可恢复、其他观察的统计独立性。
  输入与Scope以该运行、thread/turn/call及Host回执界定。

### C2：Compaction的“已确认”措辞，不是权威采纳

运行C：
`/home/wqkan_wsl/uaea-n1x/runs/h3-results/interactive-32768-20261102-065220/`

- 原始Compaction生命周期：app-server-events.jsonl:1754/1763与3176/3185。
  两个assistant派生输出分别在1757、3179；后者消息ID
  `msg_b8c4923f2e1711d2`，包含“已确认搜索业务增速放缓……”。
- 能证明的派生关系是“此输出发生于已记录Compaction活动”；
  没有把所有历史消息或网页自动连作摘要每句话的真实支持。
- 完整摘要文本可在model-http-audit.jsonl:31、33的后续请求中找到。
  **VERIFIED**：派生Claim继续可见。**UNKNOWN**：模型如何使用、每句话具体由什么原文支持。
- semantic-state-snapshots.jsonl:1–4的ActiveGoal均为null；
  因此确认措辞不能直接证明已采纳Goal被污染。
  这也不证明未采样中间状态、所有Evidence或全部语义信息都未污染。
- 同案例的真实来源闭环：execution-contract.trajectory.jsonl:8，
  `execution:39de21ba36b9d3387eeed3a91abf6a399c01f4888a582bdde8d74858dfb0f22d`；
  EvidenceReference引用`WEB-LIVE-c2d22bf3-0b04-4105-8f65-a0cad376451e`。
  adapter/source.sqlite的web_access_events表中同主键可只读解析，
  URL、内容版本hash均一致；保存HTML字节hash为
  `29e6ac7b02e6472a58be55f1621f0c84fb8eeb02a2383bfd60a64a0f5de2b9c1`。
  摘录自身hash也通过，但本实验没有判定该网页支持上面的“确认”断言。
- 时间分别来自accessed_at、source-declared published_at及记录时间；
  content_period保持源记录中的未知，不能由访问日期推导。

这是**模型派生视图具有错误增信风险**的记录，不是对财务断言真伪的本轮验证，
也不是证据已经变成合法授权的证明。

### C3：错误Goal quote被拒，真实Observation保留

复用运行A，不算新的第五个案例。

- results.json中`/turns/*/semantic/workflow_continuity/request_continuity/inputs/*`
  保留两份原始输入；输入hash和registered_user_entry来源匹配。
- goal-events.jsonl:1候选`goal-candidate:f40da961229a5cf884ef9b8a`；
  source_object_ids指向原始输入，source_event_ids可定位native完成消息，
  候选quote与原始请求一致；不是因为quote匹配就自动采纳。
- goal-events.jsonl:2独立Host控制，:3独立采纳决定，
  Goal为`b57c6392-ca0d-4871-be20-32b177a48b60`。
  控制hash、channel、候选引用、owner及决定before/after依据可核验。
  actor为test_driver，不能冒充真实人类身份认证。
- 最后输出：app-server-events.jsonl:437，消息`msg_a16b949fddbb09f3`。
  模型把来源正文填入goal_hypothesis.quote，且显式填入上述真实Observation ID。
  这个ID能解析，只能建立“模型声称有此依据”的asserted_supports。
- goal-events.jsonl:4记录来源校验拒绝；实际quote不在当前原始用户输入中。
  已采纳Goal仍在，last_execution_observation仍指向C1成功读取。
- **VERIFIED**：候选拒绝未抹去执行事实、未产生第二次采纳；
  **UNKNOWN**：内容支持与完整回答质量。关系不把证据、解释和决定合并。

### C4：真实同会话版本历史；跨会话能力仍UNKNOWN

运行V：
`/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/g01-live3-20261102T084100Z/bolt/harness/adopt/`

- goal-events.jsonl:2/4/5/7分别是adopt/revise/suspend/resume决定，
  原Goal ID为`0bcddb8b-da0c-4c63-9b69-bea9318bb832`。
  各after状态hash均可重算，连续决定before/after链匹配。
- :2采纳后与:4修订后的状态hash相同：
  `fe3a3e68a593db6402b08d24577b4eca23e6b561a9086fb9b4bdb5d544919027`。
  **VERIFIED**：有revise事件，但没有内容状态变化，不能称Goal内容演化成功。
- suspend/resume状态分别保留，旧版本引用直接指向当时日志after而非当前对象；
  这是离线历史重建，不是现有Runtime已提供通用历史版本API。
- 旧日志的4个goal-control来源ID没有对应原始控制记录。
  对两份选定Goal日志的source_object_ids审查共13项：9项可定位、4项UNKNOWN。
  此分母不覆盖全部UAEA对象，也不含所有source_event_ids。
  无法完整重验这4项原始控制，不表示已经证明非法操作；后来的运行A已保存原始控制。
- **UNKNOWN**：真实跨Session逻辑Goal续接、任意旧版本恢复、跨scope适用性。
  未使用脚本推测的控制命令补写旧事实。
- 另附SYNTHETIC_ONLY三会话反例：run-A/v1为G1，run-B/v2为G2，旧引用仍返回v1；
  只验证研究表示的预期语义，明确`real_cross_run_PASS=false`。

## 4. 最小验收指标

| 指标 | 结果 | 实际依据与限度 |
| --- | --- | --- |
| Identity Resolution | PARTIAL | 选中38个实体定位/版本可解析；声明来源对象引用仅9/13，4项旧控制未知 |
| Provenance Preservation | PASS（限定） | 原始Host输入、实际执行、模型输出、Compaction、Host控制/决定分开；不证明来源身份的外部密码学认证 |
| Derivation Consistency | PARTIAL | 读取/回显/供给hash匹配；摘要逐断言父来源无法恢复 |
| Version / Scope Consistency | PARTIAL | 同运行状态链及Scope检查通过；真实跨会话及适用期UNKNOWN |
| Dependency Classification | PASS（限定） | 同call表示、明确派生/供给与声称支持分开，未知不填成独立；未估统计相关性 |
| Authority Integrity | PARTIAL | A运行原始控制/候选/决定内部一致，拒绝不抹执行事实；V运行4项控制来源不足，未据此自动认可权威 |
| Coverage / Unknown | PARTIAL | 明确列出缺失控制、历史全文、语义支持、实际使用、跨会话及有效期，不报全局覆盖率 |

## 5. 实验、复现与边界

文件：
- r0_extract.py：标准库离线映射，只读选定JSON/JSONL/HTML及SQLite（mode=ro/query_only）。
- entities.jsonl / relations.jsonl：38实体、22关系，指针+版本指纹，不复制模型请求正文。
- source-aliases.json：SQLite与EvidenceReference同源匹配。
- cases.json / declared-reference-coverage.json：案例事实与UNKNOWN、引用覆盖分母。
- source-manifest.json / source-index.md：原文件hash、事件ID、行号/字段。
- results.json / reproducibility.json：32项真实记录确定性检查，无失败；重复运行输出hash一致。
- synthetic-fixtures.json：6个篡改反例（版本、缺端点、增权、Claim晋升、Scope、错误采纳依据）
  均被检测；1个三会话旧版本反例通过。这7项是合成控制，不是真实跨会话能力。

复现：
`python3 -B /home/wqkan_wsl/uaea-n1x/research-records/r0-lineage-20261103T033439Z/r0_extract.py`

以上结果仅证明选中产物及提取逻辑的一致性，不是Runtime全量回归。
验证器检查源记录定位、版本、明确Scope及禁止由研究边增权等不变量；
不验证任意自然语言支持，不从回答推测执行，不提供通用身份认证。
源记录作为既有受信Host产物核查，hash不是签名；manifest只固定本次读取版本，
不证明读取前从未被篡改。资料缺失不是“自动安全通过”。
没有新增Pool、公共类、正式Schema/API、依赖、模型调用或执行控制器。

## 6. 与现有组件对照及真正缺口

| 组件 | 直接复用 | 此次没有证明 |
| --- | --- | --- |
| Canonical/EventNormalizer | native身份、归一事件、Raw引用；此次用Host canonical执行轨迹 | 默认事件序号跨run唯一、全语义依赖完备 |
| RuntimeObjectStore | 原始请求、来源对象、Step/Goal及决定快照，来自既有序列化记录 | Store本身跨session持久化/全局版本解析 |
| Execution/Semantic Observation | 执行Observation/Host记录可以固定事实来源 | semantic_observations名称即真实理解、完整Phase-1语义推理已运行 |
| Evidence/Claim | access事件、内容/摘录hash、未验证Claim区分 | 精确引用就证明语义支持或真伪 |
| Projection/Compaction | 供给审计/Host快照与原生Compaction活动 | 模型逐断言真实依赖、完整语义保真 |
| G0/G1 | 候选、注册输入、独立控制、决定及局部版本账本 | 长期Goal Formation/Evolution、旧日志缺失内容恢复 |
| Phase-2B/SQLite | EvidenceReference直接解析已有web_access_events，内容版本一致 | 当前Memory Candidate/Admission与全部认知模块已端到端接入 |

源码核查位置另见source-review.md；它们只作为现有能力依据，不是本实验修改的文件。

最小缺口是引用的运行范围/版本约束和部分原始依据缺失，
不是没有统一存储。对旧缺失控制不能事后制造事实，后续使用已保留原始控制的新产物即可。
摘要支持父来源未知时，保留为Claim，不要求先建完整支持图才能开展其他研究。

## 7. 后续Goal / Null研究判断

可作为候选观察单位的内容：
- 经Host登记的真实用户输入：一个输入事件，而非每次回显/摘要一个样本。
- 一次有新执行/访问ID的外部Observation：独立标记活动；同内容重访仍可能有时间价值，
  但是否统计独立需要额外模型，不能自动算新增有效信息。
- 模型输出、Goal提议和Compaction：内生解释/派生表示，不作为自证Goal正确的外部样本。
- 明确Host控制：目的/状态决定，不是证明世界事实的新证据。

当前资料足以定义“候选生成→记录→采纳”和供给关系的早期测量，
不足以直接定义已校准的Goal/null预测实验：
候选提议多为受控提示，未有固定的外部观察字母表、预测目标/标签、编码规则及无泄漏时间划分。
No ActiveGoal、No Goal Hypothesis与Null Goal Model继续分开。
Null对照须预先规定历史/Goal特征使用范围并保持当前任务/授权/执行事实等可比，
不能通过删掉安全约束或把自己生成的文本当预测真值制造收益。

**建议**：选定来源完整的小样本，定义一个可观察的后续用户请求/任务关系预测问题；
R1仅针对重复计权/摘要来源及旧引用的少量反例并行，不强制完成R1–R4。
本轮不计算熵、MDL、互信息或有效bit，不预先决定正式架构实施。
