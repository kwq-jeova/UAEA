# 稳定AC条件下恢复金融30轮对照（2026-11-11）

**总体PARTIAL：History完成30轮；Goal Shadow完成3轮、第4轮未结束。完整双组对照仍未取得。**
本次没有NVML17、遥测拒绝或已证明的资源越界。停止原因已经转为模型工具用途/恢复行为及实验单轮等待期限，不能再归为供电、Context、KV或Goal保存失败。

## 1. 实验来源及安全：VERIFIED（本次窗口）

记录：/home/wqkan_wsl/uaea-n1x/research-records/finance30-acstable-20261110T235223Z/。
守卫：/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261110T235528Z-bef5ed29/。
批次名使用UTC；本次客户端日期为11月11日，金融研究时钟仍明确冻结为11月10日，估值目标11月4日。

冻结的30轮用户脚本、资料字节、来源开放时点、执行bundle与判据沿用上批，未为失败改题。
旧14/20轮批次全部独立，没有拼接。新建两个Thread、Home、Sandbox和Journal。
167项输入/源码/配置快照结束后哈希仍匹配。运行依赖冻结bundle，不以HEAD替代未提交源码身份。
32K/1GiB固定KV/36GiB引擎规划/Eager/单并发/64-64 UMA、Provider Policy均未改。

启动前做一次120秒无模型检查：111次有效采样确认、清理通过。
正式guard.ps1与guard_ctl.py哈希分别为：
032755d91acf805037907220eb1541de58a0ac061e73c96f1d71c4d65b0ef4aa；
614ebbd12e7095824017f60c96b46ae19bad910ea368e0902fc7a594496224a6。
它们与上轮验证安装版本一致，没有重做或放宽时间门。

新增隔离的只读Windows GetSystemPowerStatus日志：
2674个有效样本均AC=1，观察约2701.59秒；最大观测间隔2.333秒。
没有主动拔插实验。离散采样不能排除采样间隙瞬态，也不能证明NVML17的驱动机制或AC因果关系。

全次守卫2360个标记均唯一匹配新采集/确认；最大因果上界0.2451秒、Linux采集0.1185秒，
2秒/3秒及全部资源门限保持，telemetry-rejections为空。
资源有效样本峰值/余量：
NVML29.048GiB、Windows Dedicated29.048GiB、Shared0.213GiB；
Windows Available最低21.899GiB、Commit余量最低43.536GiB；
WSL Available最低17.403GiB、Swap峰值77824字节。不同内存域不相加。

研究控制器因Native Turn未结束退出，再请求停止owned模型；
guard旧包装字符串写“Safety stop…supervisor=CONTROLLER_STOP”，但primary_sensor_failure=null、
无资源停止原因、无遥测拒绝。该包装文字不能覆盖真正第一原因。
服务、两组Harness、采样器均确认退出；8000/8003无监听，电源观察器收到stop并正常结束。
本次未触发1800秒CASE_TIMEOUT；420秒是冻结自动实验的单轮等待期限，
不是人工入口超时、模型服务生命周期或Workflow完成条件。人工入口没有被修改。

## 2. 实际完成、工具及压缩

| 项目 | Relevant History | Goal Shadow |
| --- | --- | --- |
| 完成用户轮次 | 30/30，同一Thread | 3/30；第4条真实输入已发送但未完成 |
| 实际唯一工具调用 | 4次read_section | 3次read_section + 1次goal_hypothesis |
| document Observation | 4成功 | 1成功（目录）、2失败（读取文件夹） |
| Goal尝试/提交/版本 | 通道off，不作自然行为评价 | 1次自然选择的无效尝试；0提交、0版本 |
| Compaction | 1自然 + 第20轮后1受控 | 0，后续未运行 |
| 来源身份/字节判据 | 限定PASS | 目录字节限定PASS，不代表财报正文已读 |
| 完整摘录进入成功HTTP请求 | 56次供给 | 8次目录供给 |
| 后续Goal演化/增量价值 | 基线 | 未建立/UNKNOWN |

供给次数不是新的独立Observation。原始Evaluator结果保留；
分类attempt视图可能重叠，不能把semantic_proposal_rejected和rejected_before_capability
对同一call_id相加成两个真实调用。独立审计按原生call_id去重。

History第20轮受控压缩完成，前后Phase-1状态及document_observations逐值相同，
Workflow完成标志都false；不能把整个Snapshot不同直接判为语义污染。
但是第21轮后，按既有完整摘录审计没有发现原始工具正文再次完整供给，模型也没有重读。
Host保留来源/观察不等于正文一直在模型Context，更不等于模型正确使用。
第28轮遗漏已实际读取的Apple摘录，不能宣称证据恢复与读取回顾完全PASS。

模型正式收到的9个Goal组成功HTTP请求均包含goal_hypothesis定义；
不是“工具未送达”。第6–9号成功请求均含本次拒绝原因，
有request_id/transport_result/http200/bytes_received佐证。
这些是桥出站与传输证据，不是服务器token化审计或模型理解证明。

## 3. 首个自然工具尝试与失败链：VERIFIED

Goal组第4轮，用户只给出SIM价格50 USD、FY2027 EPS2、计算P/E并注明版本路径，
**没有明确邀请调用Goal工具**。本轮确实不再是“零自然调用”，但不能升级为自然候选形成成功。

原生call_id：chatcmpl-tool-ab9966177d49d860；
native turn：01a1c803-58b4-7603-b463-74470c29e7ac。

实际提案：
- operation=form；
- candidate_id="intc-assumptions-file"；
- hypothesis="用户要求在 assumptions/intc-v1.md 中记录 SIM 假设 P/E 计算结果"；
- quote关联了当前用户SIM指令。

Host拒绝：“form needs new hypothesis and null candidate_id”。
没有保存版本，也没有后续版本投影；terminal heads=[]、versions=[]。
这里拒绝的是新建候选参数，不是证明该Goal语义真假。
即使修正null，也不能因此认定“记录文件”就是合理的长期Goal。

随后模型：
1. 没有纠正候选并重试，而是反复说要创建文件；
2. 两次把assumptions目录交给read_section，均收到Is a directory；
3. 继续描述apply_patch/shell创建计划，没有真实写文件Tool或权限；
4. 达到原有420秒等待期限，Native Turn仍未确认结束；
5. Runner没有发送第5轮或自动“继续”，停止整个研究并清理模型。

assumptions/intc-v1.md实际上已由研究驱动按冻结计划在第4轮开放，
不是模型写入。存在这个文件不能证明模型完成写操作。
两组都只有只读文档能力；Goal工具保存候选，不是通用文件记录API。

**语义/行为失败**：候选内容描述当前文件操作，缺少长期目的抽象；
将Goal记录与文件写入混淆；收到失败后没有采用现有合法途径完成本轮。
**契约限定PASS**：非法参数没有写成版本、没有扩大权限或写文件，没有文字自动采纳。
**HYPOTHESIS**：版本路径措辞、只读夹具的预置状态表达、工具用途解释可能共同影响选择；
单次失败不证明Sideband本身不可用，更不能证明新增协同层更优。

## 4. History的连续行为与负例

基线已经能从用户输入保持部分方向/约束：
- T20取消Apple子任务，仍保留其他公司的待核验事项；
- T22使用新SIM EPS1.00，50/1.00=50，并保留旧版本区别；
- T26在文字上转向可复核财务方法；公司作为样本；
- 但T29只复述/计算已有SIM版本，没有实际新Tool，未证明完成一个有增量信息的核验动作。

明确负例，不以格式或来源哈希掩盖：
- T1把16.5B写成16.5亿美元；
- T5首句称已取得真实价格，后文又称未取得，状态表述矛盾；
- T19 Apple114.5 billion USD的单位换算错误（正确为1145亿美元），虽Alphabet EPS差−0.75正确；
- T25将P/E描述为EPS÷股价，与其其他轮price÷EPS计算矛盾；
- T27引用official-apple.md别名而非实际official-aapl.md；
- T28没有准确回顾已读取Apple摘录，且把来源/模拟版本与“已保存候选”混在一起。
  “长期目的已更新”也应区分对用户新指令的理解与真正Host候选版本，不能单凭一句话认定状态写入。

Goal组第一轮只读目录，却误说无财报正文；实际原文文件已开放、目录也列出三个来源。
可确认没有尝试读Intel正文，不能说正文读取被Runtime拒绝。
这不等于所有财报正文已进入模型而被忽略；Goal组只得到目录供给。

## 5. 成本及公平性

| 范围 | History | Goal Shadow |
| --- | --- | --- |
| 原生累计input/output | 617744 / 12256（30轮及压缩） | 114406 / 2386（含未完成第4轮） |
| 共同完成前3轮input/output | 63993 / 988 | 50581 / 1101 |
| 共同前3轮用户等待合计 | 161.76秒 | 149.16秒 |

不能拿30轮与3轮的整组总成本比较效率。
Goal前3轮少读财报、完成内容不同；较低input不是Goal效益证据。
固定顺序、一个repeat、History先运行与冷启动/采样差异均是限制。
未得到有效Goal候选，不能测量“维护候选”相对Relevant History的因果收益。
本批新增的是自然无效尝试及明显失败负担，不是长期认知收益证明。
没有用Token数、Confidence或重复次数计算有效bit、Goal概率或建议成功率。

33个完成快照ActiveGoal均null，Workflow完成均false，模型输出未标作来源Evidence；
这是本路径可观测边界，不是全局Memory Admission审计。Memory仍Research Reserved。

## 6. 独立结论与最小下一步

- 环境/安全：VERIFIED，限定窗口PASS；未复现NVML17，不证明AC就是其原因。
- 执行/候选权威：限定PASS，拒绝、错误回传及真实空状态可追溯。
- History连续研究：PARTIAL，30轮完成但语义、算术及行动仍有失败。
- Goal自然形成与修订：PARTIAL（出现无效尝试）；有效自然候选及演化未建立。
- 完整30×2、公平后续维护比较、决策增量价值：UNKNOWN/未完成。
- 无证据要求改变UAEA+Harness核心架构、开放写权限或新增Goal/Memory层。

建议先针对本次一个反例做有限的“任务措辞—工具能力—提案用途”研究条件审查，
明确预置SIM版本、模型计算/展示及实际文件写入的区别。
若另开实验，应预登记新的统一条件并对两组同步修改；
不要将本轮History30与改题后的Goal30拼成公平成功对照。
也不要只修正candidate_id=null便宣称Goal认知修复，或给Goal工具增加文件写入用途。

本轮不再以相同条件反复模型重试。保留Sideband已验证通道及Relevant History，
无需人工长会话；提交此负例及未完成对照供阶段评审。
没有修改正式Runtime、Harness、Goal/Memory采纳、模型、安全阈值或人工入口。
仅新增隔离电源诊断、审计和控制器的观察器清理；不Commit/Push。
