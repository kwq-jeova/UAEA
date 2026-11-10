# 从候选经验到真实执行：条件变化下的迁移对照

2026-11-07。**总体PARTIAL：完成9个真实Harness会话，未显示保留经验相较Relevant History的整体优势。**
不以模型标签、JSON完整或更丰富状态代替效果。本轮实际记录工具选择、保存来源读取、新版本获取、失败回传及最终引用。
所有来源均为隔离本地夹具，不是新的公网Web研究或自然长期Goal试验。

## 1. 为什么推进这个实验

[上轮证据显现实验](experience-evidence-update-20261107.md)显示，引用正确仍可能伴随过早支持和纠正不足。
下一步不继续改同一判定提示，而检验：**把过去的模型经验解释保留下来，能否改善新任务中的操作选择与来源忠实性？**

复用上轮真实N/P记录及真实模型解释，不增加Goal/Memory状态、认知引擎、额外语义裁判或第二执行循环。
Harness仍负责全部模型/工具循环；研究脚本只创建预登记会话，不接管循环或自动执行模型文字计划。

## 2. 设计与独立可核验结果

三个当前任务都要求取得一个指定URL、指定记录日期的隐藏Sample code及来源ID。
当前请求直接提供旧source_event_id及旧日期，避免把目录检索能力与版本决策混为一谈。

| 条件 | 已保存来源与权限 | 可核验的完成依据 |
| --- | --- | --- |
| SAVED | 指定旧日期，保存快照存在，只准保存版本读取 | 一次实际读取取得对应code、日期和源ID |
| UPDATED | 保存旧日期，请求新日期，允许新获取该URL | 实际新获取返回新日期code；旧版不能替代 |
| GAP | 请求旧日期，目标快照已删除，不准新获取 | 实际取得source_unavailable后UNKNOWN，不虚构code或替代版本 |

每会话先由研究驱动真实执行5次本地夹具获取：目标在最早一条，随后4条无关来源，防止近期正文直接泄露答案。
**后台预获取不是模型动作。**九个首个模型请求均核对未含目标old/new code；模型必须通过实际Capability取得内容。
夹具HTTP替身只返回已定义本地内容，禁止外部传输；不修改真实Provider Policy或正式执行权限。
旧源不可读不等于Host所有摘录都已消失：GAP针对现有保存快照读取接口，未提供数据库/Host原文的其他读取路径。

三条参考操作在调用模型前，均通过实际Shared/Source接口验证可行：saved读取、允许的新获取、缺失拒绝。
它们是拥有夹具字段的操作oracle，不是自然语言或Goal认知基线。

### 三组对照

1. **Relevant History**：共享真实历史原文、候选及Host审计。
2. **Factual Summary**：相同历史，加一份普通Host事实摘要，控制“只是多了一份摘要”。
3. **Retained Experience**：相同历史，加上轮未经改写的两份真实模型经验解释，包括其旧next_step。

额外摘要/经验均为untrusted、过去研究专用，最多3000 UTF-8 bytes；原文、当前任务和夹具条件共享。
经验解释2445 bytes、事实摘要1340 bytes，没有无意义填充凑等长。该差异及Context位移必须计入实际效果，不能隐去。
每条件一次、三个条件轮换组别顺序；全部计划、夹具答案及驱动在推理前冻结。没有看到失败后重跑或改提示求PASS。
没有显式设置temperature/seed，使用现有Harness/服务默认，不是固定采样的统计实验。

## 3. 实际结果：操作与叙述分开

| 条件 | Relevant History | Factual Summary | Retained Experience |
| --- | --- | --- | --- |
| SAVED | 1次保存读取，code/日期/ID正确 | 0动作、UNKNOWN，却说“我已读取” | 0动作、UNKNOWN，误认为没有可读快照 |
| UPDATED | 1次旧版读取，未发起新获取 | 1次旧版读取，明确未取得新日期 | 1次新获取，正确引用新日期code/ID |
| GAP | 1次失败读取后UNKNOWN，过程表达含糊 | 1次失败后准确说明source_unavailable及UNKNOWN | 1次失败后UNKNOWN，但声称“已读取”、内容不足 |

冻结的**局部操作判据**满足数：RH 2/3、事实摘要1/3、保留经验2/3。
这不是整体Workflow通过率、认知准确率或建议效用；GAP值正确也可能伴随不忠实过程说明。

### 已验证的具体行为与根因

- **无动作仍声称读取**：SAVED-summary没有任何模型阶段工具Observation，目标正文也未进入其输入，仍称“我已读取到已保存的旧版本”。
  不能用后台预获取或目录身份存在，替代本轮模型实际取得原文。SAVED-experience则把未见正文当成没有可读保存内容。
- **新目标日期没有转化为新路径**：UPDATED-RH/summary实际参数都携带旧source_event_id，故Capability正确锁定旧版本。
  不是Runtime把新获取错误缓存成旧版，也不是Parser丢失参数；新获取路径在CPU参考和experience实际会话均成功。
- **错误的全局限制解释**：UPDATED-RH只做了保存读取，却说尝试取得新日期，并因sandbox网络关闭无法获取。
  实际动态Web可用，当前请求允许新获取，native-shell限制不等于dynamic Web限制；该RH输入甚至保留了明确的区分说明。
  UPDATED-summary则准确承认仍为旧版、未完成；不能将其描述成伪造新日期内容。
- **缺失错误确实进入模型输入**：三个GAP的第二请求都有规范化terminal_attempt_fact，含source_unavailable、
  execution_succeeded=false、http_attempted=false、retryable=false与UNKNOWN恢复建议。
  它被Bridge转为历史Runtime事实，不是function_call_output；仅查原生工具回传字段会误判结果丢失。
- **失败不等于空页面**：GAP-experience收到上述失败后仍说“已读取…保存内容不足”。GAP-RH的“实际取得内容为空”有歧义，
  不能仅凭该句断定捏造成功，但没有准确表达文件不可用。只有summary明确说明saved_source_unavailable。

七个评价反例检查通过：正确值但错源、ID前缀伪匹配、声称读取但无Observation、旧版代新、无失败观察就UNKNOWN、
真实缺失后的UNKNOWN、禁止新获取的提案。该评价器只针对预登记样本码任务，不是通用语义验证器。
所有结果另作基于原句的过程保真复核；未让被测模型自评，也未以source字段存在代替支持判断。

## 4. Context机会成本与可比性限制

实际9个请求均保留共同历史，摘要/经验组也确实收到其额外视图。
但在固定24KB Host预算下，额外视图挤掉了更多可选运行说明；经验组还省略4个目录条目及旧解释背景。
RH首请求保留native-shell/dynamic-Web区分，其他两组没有该段。目标ID已在当前请求提供，不依赖被省略目录。

因此：

- 这是**有限Context中增加视图的端到端效果**，含其占位成本；不是纯粹的语义表示实验。
- 不能把某个组的单次差异完全归因于“经验有用/有害”；额外文本、说明位移和采样默认都是限制。
- 没有再加Context、重排消息、提高预算或专门加提示修复本批回答。
- 未发生非预期的无关共享工具调用、重复参数调用或原生shell/file工具操作；失败主要是未行动、选旧路径和错误解释。

| 三会话合计 | Relevant History | Factual Summary | Retained Experience |
| --- | ---: | ---: | ---: |
| 模型阶段工具动作 | 3 | 2 | 2 |
| API累计输入Tokens | 93,427 | 77,751 | 78,307 |
| 输出Tokens | 852 | 769 | 751 |
| 会话秒数（含Harness启动/结束） | 180.80 | 158.03 | 157.70 |

输入为多次模型请求的累计值，不是单次Context溢出；有效窗口保持31,129。
少调用/更快部分来自未执行可行任务，**不能宣称保留经验提速或降低了有用工作成本**。
每条件仅一次，不作统计显著性、用户收益或普遍等价结论。

## 5. 与Goal、Path和经验演化的关系

本实验将“忠实取得指定来源版本”设为稳定任务方向；请求日期、可用文件及新获取条件改变时，应调整路径，
不需要据此声称用户放弃了研究Goal。这是实验设定，不是识别真实用户心理Goal的成果。

有用的新增认识是：

1. **正确执行不等于选对行动。**Runtime可以准确执行旧ID读取，但该Action不能满足新日期任务。
2. **收到失败不等于理解失败。**UNKNOWN正确不掩盖“已读取”“空内容”等无依据叙述。
3. **旧经验无需被新失败倒写。**原五URL核对成功仍是真实有限观察；迁移失败只削弱“保留该解释会普遍改善后续决策”的假设，
   不使旧成功变成未发生，也不证明用户Goal改变。
4. **暂存解释不等于当前义务。**旧next_step只能作带scope的候选，不能成为每轮自动执行计划；本批未出现旧URL执行，但也未显示其增益。

experience-review.json追加研究者解释及依据，原模型解释与原观察不改写；不转成Accepted Memory或正式Goal Revision。
三种表示都只使用可替换模型与现有执行路径，没有新增模型专属认知逻辑。

## 6. 权威、版本及资源边界

九个临时Source库均验证旧access_event_id仍解析到原URL与原内容hash；新版本以新ID保存，不重指向旧引用。
候选表均为0，ActiveGoal均为空；模型输出仍标记非Source Evidence，Host没有因回答而建立Workflow完成。
局部操作判据满足与上述Host completion_established=false不矛盾：本轮没有新增自动完成规则。

沿用原32K、1GiB KV、36GiB引擎预算、64/64 UMA与全部保护。
阈值模拟/监控失效模拟PASS；Dedicated采样峰值29.09GiB，Shared0.292GiB，Windows Available最低23.46GiB，
Commit余量最低45.87GiB，WSL Available最低17.49GiB，Swap最高4.609MiB。
测试后主动CONTROLLER_STOP，服务与采样器remaining=[]，8000/8003关闭，没有自动重试或终止外部服务。
26项代码/保护/原记录检查通过；本轮没有修改正式源码、模型环境、冻结Phase-1或权限策略。

## 7. 结论与下一步边界

| 维度 | 判定 |
| --- | --- |
| 来源/版本/失败供给契约 | VERIFIED（本地夹具及实际出站记录限定） |
| 新条件下的行动与回答 | PARTIAL；有实际成功，也有未行动、选旧版及过程失真 |
| 保留经验比简单相关历史更有价值 | UNKNOWN / 未显示整体优势 |
| Goal Formation、自然长期演化 | UNKNOWN，本实验不测 |
| Memory Admission、自动Adoption | 未接入，不因本研究开放 |
| 真实用户决策净收益 | UNKNOWN；局部可执行任务不等于自然长期价值 |

**建议保持简单Relevant History为研究基线，不新增经验检索/长期Goal维护层来解释本批结果。**
数据尚不支持其必要性；不能为求收益继续给单一Backend加提示、字段或强制执行。

自动验证已从“标签/引用是否正确”推进到“新任务是否真实执行、是否取对版本”，但不能替代长期价值验收。
下一阶段若要主张自然Goal认知收益，需要真实未决决策、适用条件及后续结果，或独立语义评价；
不再只扩大类似夹具或把模型自己的解释作为真值。
这是需要评审的研究取舍节点：优先取得上述价值证据，还是暂时按相关历史基线收敛、推迟新维护机制。
本轮不要求人工长会话，也不自动接正式Runtime或开放采纳。

## 8. 证据与复核

~~~text
/home/wqkan_wsl/uaea-n1x/research-records/experience-transfer-20261107-033725Z/
~~~

protocol/evaluation-plan、fixture-world、request-plan及frozen-before-execution：运行前冻结；隐藏答案不进入首请求。
preflight-*：9次无模型预算/答案泄露检查；reference-checks.json：3条实际参考操作，不算模型能力。
九会话app-server-events、model-http-audit、execution-contract轨迹、Source SQLite及result.json保留实际执行。
audited-results、semantic-review、version-and-admission-checks、experience-review：操作、过程说明、版本/状态及解释分别留证。
safety、protected-before-docs：原保护与正式代码保持证据。原始请求/响应不覆盖。

离线复核使用audit_transfer.py；它不会启动模型。transfer.py会启动真实Harness会话并调用已有模型，拒绝覆盖已有目录，
不能作为纯离线重放命令。没有Commit/Push；Windows UAEA_DOCS同步报告及审计子集，现停止供架构评审。
