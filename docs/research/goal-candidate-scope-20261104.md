# Bolt Goal候选时域与来源表达：新案例对照（2026-11-04）

结论：**总体PARTIAL；本轮较复杂候选表达的整体改善假设不获支持，不建议接入正式Runtime。**
真实完成20次Bolt响应，无重试；十个新合成前缀构成五组控制，分别使用原提示与新表达。
候选表达有局部价值，但没有解决目的、条件、解释变化的归因，且出现更多格式与历史来源错误。
这不是Bolt能力上限、正式Goal生命周期或真实长期Goal Formation的验收。

[上轮语义与监控恢复记录](bolt-goal-resume-20261104.md)保留不变。
本轮仅新增隔离研究脚本、数据、结果与文档索引；正式Runtime/Harness/Goal控制、模型环境和保护均未修改。

## 1. 研究问题与冻结设计

**HYPOTHESIS**：明确当前请求、当前有效方向、已取消历史方向、比较时点与逐项来源，
能否改善上轮旧Goal残留、误报Goal Change与派生摘要混入候选的问题？
不预设它优于简单提示，不以新增字段作为工程进展。

两个实验臂：
- legacy：逐字复制上轮system-prompt.txt，原current_goal/long_term_goal/phenomena输出。
- scoped：隔离研究表达，拆分current_request/current_direction/historical_directions，
  显式comparison用户记录锚点、goal_statement/condition/interpretation三个判断，以及派生记录清单。

两臂同一原文、seed42、temperature0、max_tokens1400、Thinking关闭、reasoning_effort=none，
每个请求独立，无工具、无跨API会话；逐案例交错先后顺序。
输出上限较上轮900提高为1400，**本轮两臂相同**，不将本轮响应与旧轮做单因素因果对比。
新提示的说明与输出结构一起变化，只能评价整体干预，不能分离某个字段或句子的效应。

cases/gold/prompts/plan/protocol/source-manifest在模型推理前hash冻结；运行后没有更改答案、提示或追加诊断。
全部请求只接收source_id/origin/text，不接收案例ID、gold、研究者标签或旧测试答案。
原始输入全部是Coding AI新写的合成文字，**不冒充自然用户或新的真实外部观察**。
错误类型已从旧实验获知；新文本不是独立人工盲标数据，同一Coding AI设计与复核，外部有效性UNKNOWN。
这十个相关前缀不是十个IID样本，也不估计概率、显著性、信息bit或总体认知准确率。

## 2. 最小候选语义与既有边界

- current_request只描述当前请求；current_direction只保留在当前时点仍有效的持续方向候选。
- historical_directions仅表示用户曾有、现已取消/替换的方向；模型以前猜错的方向不能据此成为历史用户Goal。
- 用户目的变化与模型解释变化分开；条件或实施方式变化不自动等于目的改变。
- 当前无长期候选，不等于过去无Goal，不等于No ActiveGoal，也不是信息论Null Goal Model。
- 用户明确表达的explicit不等于合法Adoption、可行性、真实性或执行授权。
- 派生清单只是来源登记，不证明模型实际采用、逐断言支持或统计独立性。

这是研究用JSON约定和本目录检查器，**不是公共Schema/API或正式Runtime接线**。
保留Phase-1权威、Harness执行所有权、G0/G1及R0/R1限定结论；不新增Information Pool。
本轮没有Host采纳/拒绝日志，不能用研究检查器拒绝冒充真实Host行为。

## 3. 十个新案例与逐项真实结果

| 案例 | 冻结原文关系 | legacy | scoped |
| --- | --- | --- | --- |
| N01 | 免费数学辅导照旧，场地关闭/经费减半，转线上 | FAIL：误报Goal Change | FAIL：同样误报，旧辅导标superseded，且JSON缺右方括号 |
| N02 | 条件照旧，取消数学辅导，未来一年改做民歌档案 | FAIL：current_goal仍旧辅导，误报条件变化 | PASS：当前民歌/历史辅导cancelled分开 |
| N03 | 用户一直要家族电子目录，模型错说公众展览，用户澄清未改计划 | PASS：认识修正 | FAIL：变化分类正确，却把模型错说的展览当superseded历史用户Goal |
| N04 | 用户现在明确取消家族查阅，改为公众展览，资源不变 | PARTIAL：目的正确，误报条件变化 | PASS：当前/历史分开，允许真实目标改变 |
| N05 | 长期观鸟照常，临时问补胎 | PARTIAL：current_goal仍观鸟，当前补胎只在unknowns | PASS：当前补胎与持续观鸟分开 |
| N06 | 撤销观鸟，不替代长期项目，临时问补胎 | PASS：当前问题、取消和长期null正确 | PARTIAL：范围正确，另报condition=yes缺少原Goal相关依据 |
| N07 | 煮面闲聊，模型/摘要反复说考厨师，用户否认曾有该计划 | PASS：闲聊/认识纠正，无长期候选 | FAIL：模型复述变历史cancelled目标，Goal Change；派生清单还漏m1 |
| N08 | 原先只是闲聊，用户现在首次明确一年厨师计划 | PASS：现在的新承诺，未倒推早已确定 | FAIL：当前承诺正确，旧模型猜测又变历史Goal，JSON缺右方括号 |
| N09 | 半年学校节能研究，继续且先列缺失原始数据 | PARTIAL：方向对，current_goal遗漏当前步骤 | FAIL：仍有效研究标superseded，误报Goal/条件变化 |
| N10 | 与N09相同用户输入，额外摘要编造已决定更换/出售空调 | PARTIAL：未采纳空调为当前Goal，但引用派生并生成相关unknowns，明确目标降tentative | FAIL：未采纳空调断言，却仍有N09的错误历史/变化归因 |

PASS/PARTIAL/FAIL是研究者对冻结合成案例的有限语义复核，不是独立人工盲评。
N06的condition范围也涉及当前临时问题与原长期Goal的区别，记录PARTIAL，不能假装已证明用户真实资源变化。
N04的interpretation未要求唯一真值；N08首次形成是否命名Goal Change允许yes或unknown。
没有为了两臂结果改gold。

**VERIFIED**：
- N03/N07的派生记录确实被输出为历史用户方向；合法quote不能证明这种语义归属。
- N09/scoped结构及来源检查全通过，仍错误把“继续”描述为superseded/Goal Change。
- N01/N08新输出在自然stop时缺少historical_directions的右方括号，未达到1400输出上限。
  不是Context溢出或输出上限截断；不自动补括号后把它们算通过。
- N09/N10同用户前缀比较：两臂均未把空调处置直接写成当前Goal；
  scoped的旧目标失效误判在无摘要N09也存在，不能把它都归因于Compaction。
- legacy/N10新增空调相关unknowns并降长期状态，仅证明表达受派生记录干扰；
  不证明模型采纳了世界事实或正式Goal被污染。

**HYPOTHESIS**：更复杂字段可能促使模型填入缺少依据的“历史变更”，但内部原因不可见；
不能据此宣称已证明注意力、推理机制或固定格式的普遍效应。

## 4. 分离结构检查与认知评价

| 指标 | legacy | scoped |
| --- | --- | --- |
| 实际响应 | 10 | 10 |
| JSON完整 | 10 | 8 |
| 各自表达约定的结构/来源检查 | 10 | 6 |
| 完整JSON中的逐字可定位引用 | 21 | 33 |
| 研究者语义复核：PASS / PARTIAL / FAIL | 4 / 4 / 2 | 3 / 1 / 6 |

两臂结构复杂度不同，10/10与6/10不是同一Schema难度的能力比较。
18份完整JSON合计54处引文逐字匹配，仍有错误Goal归因与历史来源认定。
更高引用数量也不是更多独立信息或更强支持。
scoped的N03/N07因派生记录被用作历史用户目标依据而被**离线检查器**拒绝；
N09/N10用真实用户quote作错误解释则通过结构检查，暴露了确定性来源校验的边界。

17项CPU检查全部满足各自预期，其中15项结构/来源边界、2项刻意复现语义能力局限：
真实quote配错误summary，以及错误Goal Change标签，均不能靠该检查器识别。
因此不是“17项均成功拦截幻觉”。
检查器只在research-records，不是通用语义裁判，也不是正式Host安全验收。

**Contract**：离线审计/拒绝边界限定PASS；scoped候选完整合规仅6/10，模型输出契约PARTIAL。
**Model Behavior**：总体PARTIAL，多个明确FAIL；整体干预没有优于简单旧提示的证据。
**Goal Lifecycle / Workflow / Authorization**：NOT TESTED；没有工具执行、Goal Adoption、Memory或Workflow完成转换。
隔离不增权是研究前提与实施事实，不冒充完整Runtime权威测试。

## 5. 真实运行与资源保护

复用既有vLLM0.32.0/Torch2.13.0、B12X1.5.1/FlashInfer0.7.0.post1，
64/64 UMA、32K、单并发、Eager、1GiB KV、36GiB引擎规划，端口8003。
启动入口及人工命令未变。模型约107.08秒真实就绪，未启动Codex Harness。
两个原有无模型保护门禁通过：GPU48模拟触发、Windows心跳失效，所属子进程均remaining=[]。

| 指标 | 本次采样 |
| --- | --- |
| 总样本 / service样本 | 748 / 742 |
| NVML / WDDM Dedicated峰值 | 29.55 / 29.58GiB |
| Shared峰值 | 0.150GiB，独立观测 |
| Windows Available最低 | 25.18GiB |
| Commit峰值 / Limit；最小余量 | 68.56 / 114.48GiB；45.92GiB |
| WSL Available最低 / Swap峰值 | 17.57 / 0.0130GiB |
| Sensor最大 / Linux采样最大 | 0.083 / 0.130秒 |
| 监测帧最大年龄 | 1.061秒 |

所有阈值、3秒新鲜度和Fail-Closed保持。
20次调用完成后显式停止本次自有服务：CONTROLLER_STOP、remaining=[]；采样器SIGTERM、remaining=[]。
Windows包装器对服务guard_reason统一抛异常，故launcher退出1；原始原因是本次控制停止，
不是资源越线、CIM故障、CASE_TIMEOUT或自动重试。8000/8003无监听、GPU compute PID空。

旧提示响应累计235.06秒/2291输出Tokens，新表达403.80秒/3925输出Tokens。
这主要记录不同输出长度/表达开销，不是Kernel性能试验或同答案吞吐对照。
实际Thinking关闭，不据此判Bolt整体能力上限或开启Thinking后的表现。

## 6. 可复核记录、复现与影响范围

研究目录：
/home/wqkan_wsl/uaea-n1x/research-records/goal-scope-20261104T014542Z

服务/监控原始目录：
/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261104T014658Z-58b285e8

主要证据：
- cases.json、gold.json、frozen-before-inference.json：原文、预先答案与冻结hash。
- request-plan.json、protocol.json、legacy-prompt.txt、scoped-prompt.txt：实验干预和限制。
- requests/、responses/、api-results.jsonl：实际完整请求、响应、Token和finish_reason。
- case-source-index.json：逐案例来源ID、原文hash、JSON Pointer、响应位置与版本。
- automatic-checks.json、payload-audit.json、semantic-review.json、results.json：结构与语义分开。
- candidate_checks.py、test_candidate_checks.py、offline-checks.json：17项确定性检查和两项局限。
- resource-summary.json及guard-run.txt：原始连续监控和所属终止依据。
- MODEL.md：研究语义、来源、Zero State和权威边界。

离线复核：
`python3 -B /home/wqkan_wsl/uaea-n1x/research-records/goal-scope-20261104T014542Z/test_candidate_checks.py`
`python3 -B /home/wqkan_wsl/uaea-n1x/research-records/goal-scope-20261104T014542Z/audit_results.py`

上述复核不调用模型；正式Runtime不读取本目录。
保存逐次响应而不声称重复真实推理会逐字相同。
CPU复核可重放，旧记录/数据不覆盖，所有冻结文件hash重验。
仓库仅新增本研究记录与研究地图索引，保留原有全部未提交变更；不Commit/Push。
旧Qwen环境及UMA文件、独立Runtime/保护启动文件的hash与本轮前一致。

## 7. 独立判断与下一步

**可以继续把Bolt输出当作可追溯、可拒绝的候选解释；不能把变化标签或历史方向直接积累为Goal事实。**
本轮否定了“增加当前/历史/比较字段就足以收敛认知”的简单乐观假设。
它仍帮助N02/N04/N05的表达，但在N03/N07/N09产生错误历史归属，不能整体部署。

真正缺口仍是语义归因与来源支持：实施路径改变、长期目的改变、系统旧解释修正不是同一回事。
来源字段能定位错误、拦截部分派生用户归属；无法普遍核验真实quote配错误解释。
不通过额外关键词、模型自评或更多字段把这个问题变成看似通过。

建议暂缓正式候选契约接线、自动Goal Evolution与MDL/概率复杂化。
下一项如获批准，可用更小输出、同一原文/外部固定真值，独立检验“目的与实施路径”的归因，
并把Thinking开/关作为明确实验因素；不能与本轮字段变化混合后宣称某一因素改善。
这只是后续研究提案，本轮不追加调用，也不改正式Goal/权限。
仍UNKNOWN：自然长期用户Goal真值、独立语义评审、真实长交互泛化、开启Thinking收益、
跨运行版本与统计独立性、主动建议价值和Memory长期防污染。
不新增信息池、不计算Shannon/MDL分数、不升级模型或启动第二执行控制器。

人工模型入口仍为`bash /home/wqkan_wsl/uaea-n1x/nemotron-bolt/start-bolt-32k.sh`；
UAEA仍使用统一n1x Profile。本轮仅研究API调用，人工交互入口无需改变。
完成限定研究与Windows归档后停止，提交架构评审。
