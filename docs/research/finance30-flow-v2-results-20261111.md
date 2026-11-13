# 推理流 v2 收尾与金融 Goal 实验恢复（2026-11-11）

## 结论

**总体 PARTIAL。有限诊断可收敛，金融30×2尚未闭环，Goal成熟度不提高。**

| 项目 | 判定及范围 | 实际结果 |
| --- | --- | --- |
| 锁定v2实机验证 | PASS / VERIFIED，两个样本 | 冷启动及紧邻请求自然结束，四层一致 |
| 历史121次重复 | UNKNOWN | 未复现，缺历史同期上游数据，不能宣称修复 |
| Shadow前段 | 工程PASS，模型PARTIAL | 6/6轮，7次读取，1次自然压缩，零候选 |
| 原长批次 | PARTIAL | History20/30；21轮Context400；Goal长组NOT RUN |
| 回执预算修正 | VERIFIED，有限范围 | 正文/身份/完整Host事实保留；真实批量回传后压缩以23871输入Tokens完成 |
| 修正版独立批次 | PARTIAL | History25/30；26轮420秒内未取得Native终止；Goal长组NOT RUN |
| 状态及资源边界 | PASS，窗口限定 | ActiveGoal均null、无Workflow完成建立；无实际资源/遥测停止 |
| 自主演化及增量价值 | UNKNOWN / NOT RUN | 没有有效长配对，没有本轮候选版本链 |

6、20、25轮属于三个独立会话，不能拼接，也不是Goal/History配对。
Memory仍Research Reserved，不新增正式采纳、Goal Engine或第二执行循环。

## 版本与证据根

WSL：
/home/wqkan_wsl/uaea-n1x/research-records/goal-flow-v2-20261111T064226Z

基准main@125f0d2a8e6b7ac0f6b70baf9913b942be2b1cb2，本轮未Commit/Push。
工作树原本有未提交修改；用code-version.json、before快照与this-turn.diff识别本轮增量。
每个实际运行另绑定bundle源码、source-lock、environment-lock、冻结输入及模型/安全pin。

- preregistration.json：两个诊断请求，各180秒；独立六轮前段；原30×2计划。
- receipt-resume/preregistration.json：真实Context阻断后，仅一次修正的新配对批次。
  两组使用同版修正，不改30轮输入、资料释放、420秒、参数或权限；再次阻断后停止追加重跑。
- final-facts.json：可重算的事实、成本、资源及清理汇总。
- qualitative-evidence.json：带源文件、行号、Turn/Item ID的研究者定性摘录，不代替原始JSON。

另有一次AC观察器仅积累2个有效在线样本时的启动前拒绝，模型未加载。
原件在receipt-resume/preflight-too-early；等待5个真实有效在线样本后才正常启动。
这是采样准备不足，不是已观测AC断电；无阈值绕过。
实际模型加载共3次：诊断、原认知、修正版各一次；没有额外诊断请求。

## A. v2有限实机验证

两个采集器与已审计v2逐字节相同：

- live_capture_v2.py SHA256：
  1875df9400cc749e4b05b8849f86c8be388b5d9012e943b31d09c7df003ebb33
- engine_observer_launcher_v2.py SHA256：
  4f2dd60cd9ba1cf038b43dbfb52649972df370584c98138f2b81b6e3057ab12c

引擎每模型16MiB；认知驱动每方向SSE跨请求共用16MiB；每会话最多512条采集带。
限额/IO故障只标记诊断覆盖，不能替换响应字节、执行决定或触发重复推理。
Bridge默认不启用采集；观察器错误计数。没有“零性能开销”主张。

冻结请求65131字节，正文hash：
9f32270facda970a8ee351f9edcb04a3480e4c870b8056344fd075a5efd4ee23。
匹配已恢复的历史第3请求forwarded hash；历史HTTP头、随机数状态和完整热进程条件不可恢复。

| 条件 | 输入/输出Tokens | 秒 | SSE字节 | 结束 |
| --- | --- | --- | --- | --- |
| 冷启动首请求 | 18546 / 336 | 51.06 | 77922 | engine stop、response.completed、Native completed |
| 同进程紧邻同正文 | 18546 / 575 | 69.58 | 125726 | 同上 |

无采集限额、IO错误或截止触发；上/下游hash相同。
Parser前纯文本/token、SSE与Native无GPU回放一致。
回放只评价流处理，不是额外模型实验，也不证明重放用户语义正确。
依据：diagnostic/four-layer-validation.json、两个live/capture.json及native-replay/comparison.json。

连续样本将收入的B单位错误写为“亿”，错误已存在于Parser前生成文本。
可排除本样本Bridge数值改写，不代表已解释模型内部生成机制。
旧121次特定重复未复现；未改随机种子、Temperature、Repetition Penalty、Backend、Context/KV。
不继续无限复现，旧异常保持UNKNOWN。

## B. 六轮准入与自然Compaction评价

cognition/prefix/finance-prefix-goal_shadow-r1：

- 同一Thread完成6个用户轮，7条真实成功document.read_section Observation。
- 10个完整成功HTTP响应；正文、摘录与文件版本哈希一致。
- 1次自然Compaction；9个普通请求均有Goal状态投影和Goal工具，压缩请求暂存Host状态，随后恢复。
- Journal只有6条RESEARCH_GOAL_TURN，proposal_calls=0；没有候选版本。
- 单位、估值表达等模型反例保留。工程准入不是金融研究或Goal认知PASS。

旧Evaluator只认识单独受控Compaction，把自然压缩seq8误算缺Goal投影。
audited-results.json保留原评价；prefix-review.json保留当时Native区间、压缩指令、
Host暂存和后续恢复的交叉准入依据。

研究Evaluator现要求：同Thread/Turn/Item的成对Native起止、对应压缩请求、Host deferred决定。
只有模型文字、未结束事件、不同身份、区间外请求、普通请求或缺Host决定均不能豁免。
25项针对性回归通过；audited-natural-compaction-v2.json为前段限定Contract PASS。
这项后验评价修正没有进入正在运行的冻结模型源码，没有改变模型输入、标签或认知收益UNKNOWN。

## C. 原长批次的Context失败及最小修正

cognition/long/finance30-relevant_history-r1：

20个用户轮完成，第21轮被中断；2次自然、1次受控压缩完成，第4次自然压缩失败。
32个HTTP请求：31个成功响应、1个完整HTTP错误响应。framing完整不等于模型成功。

失败请求6279a7e0-85de-4089-9ab1-75d8cbe996e2，vLLM报告输入**至少32769** Tokens。
这是截断式上限报告，不是精确完整长度。不是NVML17、资源停止、420秒期满或旧重复异常。

context-failure-decomposition.json：

- 10条成功工具回执共47068字符，源正文仅2384字符。
- 完整嵌套执行决定29950字符，含210处重复retained_request_ids引用。
- 此压缩请求已暂存Host块，恢复供给为0；不能直接归因为独立24KB恢复块。

最小修正只精简**成功且Host允许的回执**：
保留决定结果、action/input/workflow/state/policy引用、授权、有效参数及
request_satisfaction=not_established，附完整决定SHA256；原件仍在Host trajectory。
正文、内容/版本hash、Observation及Call身份不变；拒绝/失败回执仍保留完整错误语义。
没有删事实、自动选来源、改路径或扩权限。

历史十条回执的CPU反事实映射全部保留正文/身份，原件hash与真实Host决定10/10对应。
function-output字符串本地分词25127→12956，少12171 Tokens。
这不是完整chat-template请求的精确减量，也不是实机结果。
修正版真实记录另有105处决定投影引用全部可解析至Host原件；重复引用不等于独立证据。

## D. 修正版独立批次及停止原因

receipt-resume/cognition/long/finance30-relevant_history-r1：

- 新Thread完成25个用户轮，5次压缩完成，含4次自然及1次受控。
- 26条成功读取，11种已读内容hash；hash数不证明统计独立或语义支持。
- 40个请求，39个完整成功响应；最后一个只有HTTP200开始及部分流。
- 第26轮先批量读取11个文件，再进行压缩：
  b0ce7bcf-3b87-43d6-b8ef-0a72ba66a246实际23871输入、1046输出Tokens，完整完成。
  这是同规模级批量回传可处理的真实证据，非相同随机轨迹的严格单因素证明。
- 随后模型再次读取刚读过的3份公司摘录；420秒内未得到Native Turn终止。
  末请求a7cf453e-525f-47c5-a90e-6772fcc01331保存62183字节前缀，Parser前捕获379个输出token；
  三个SSE/Native调用与Host实际读取可关联，但无response.completed、无engine finished。
- 末三条Observation实际执行，却没有下一次出站请求证明正文回传模型。
  整个来源供给不能PASS；此前105处正文供给有效，不能掩盖这三条未回传。

依据：receipt-resume/turn26-flow-analysis-v2.json、两版audited报告、Native、P0、Host快照和streams。
旧turn26-flow-analysis.json的full_capture只表示已观察前缀未丢存储，命名有歧义；
v2派生分析改为all_observed_prefix_bytes_stored并明示结束UNKNOWN，旧件保留。

本次是自动实验单轮期限，不是服务30分钟寿命、Workflow完成、Context400或内存保护。
不任意加时、不自动继续该轮；达到追加批次停止上限后不再实机重跑。
两批Goal长组均NOT RUN，不把未运行计为模型FAIL，也不从History推断Goal维护能力。

## E. 模型行为与权威

qualitative-evidence.json提供直接行号/事件ID及正文：

- 原14轮称没有Apple文件，但seq23已成功传入其正确路径与版本。
- 原19轮称上年Alphabet EPS缺失；原来源与当前派生摘要含2.87。
  不宣称完整原文当时仍在Context，压缩与模型未重新取证的贡献未被分离。
- 原20轮把Apple取消扩大至Alphabet EPS核验。
- 修正版17轮把预置aapl-v2当需创建并声称不存在，Host没有开放写权限。
- 修正版19轮已读取来源仍换算错误：114.5B正确为114500 million USD = 1145亿美元，
  不是11450 million。
- 23轮将同比称环比；24轮将11-09说成早于11-04，尽管时间字段正确供给。

来源供给不能证明解释、计算或判断正确；不增加通用语义裁判。
所有已完成轮快照ActiveGoal为null，模型输出不是source evidence，Workflow完成未建立。
本轮未实施Memory Admission，也没有独立测量所有可能Memory写入路径，不以Runner声明代替测量。
前段没有候选，长Goal组未运行，没有本轮候选版本链、修订或增量行为价值证据。

## F. 成本与安全

成本为唯一终止Response usage之和，含重复输入处理及压缩，非唯一信息量。
未结束请求缺最终usage，修正版只报告已知部分。

| 独立会话/版本 | 完成用户轮 | 已知输入Tokens | 已知输出Tokens | 完成用户轮秒数之和 |
| --- | --- | --- | --- | --- |
| Shadow前段/原回执 | 6 | 192662 | 2814 | 447.45 |
| 原History/原回执 | 20 | 548044 | 10389 | 1316.83 |
| 修正版History/摘要回执 | 25 | 729264 | 18075 | 2070.41 |

秒数不含独立受控压缩、未完成轮及加载，不是完整墙钟耗时。
轮数和版本不同，不作Goal增量成本或收益估计。

三次服务5272有效样本，无实际资源/遥测停止。AC观察5935有效在线样本，无切换，
不能据此解释过去错误17的驱动机制。smoke注入停止是预期保护验证，不算真实资源越界。

| 独立指标 | 三次服务极值 |
| --- | --- |
| NVML Used / Windows PDH Dedicated峰值 | 29.974 / 29.975 GiB |
| Windows PDH Shared峰值 | 0.239 GiB |
| Windows Available最低 | 17.191 GiB |
| Windows Commit峰值 / Limit | 73.286 / 114.481 GiB |
| Commit余量最低 | 41.195 GiB |
| WSL Available最低 | 17.409 GiB |
| Swap峰值 | 0.0664 MiB |
| 单调时钟因果新鲜度上界最大 | 0.4674秒 |

这些指标重叠，不相加；PDH Shared不证明全部CUDA共享分配。
16项原始模型/安全pin无变化，Guard原件相同；2秒采集、3秒新鲜度与内存阈值不变。
沿用32K、1GiB KV、36GiB规划、64/64UMA、Eager单并发、Provider Policy及Sideband。

服务由本轮controller停止，remaining=[]；monitor-exception含CONTROLLER_STOP，
primary_sensor_failure为null，不应误读成资源停止。
Native、采样器和AC observer已清理；8000/8003无监听，没有关闭外部服务。

## G. 变更、回归与架构判断

本轮增量：

1. harness/responses_bridge.py：可选逐请求采集钩子，默认不启用、观察器不替换字节。
2. harness/codex_dynamic_tools.py：成功允许回执的决定摘要与原件hash。
3. scripts/research/longitudinal_audit.py：自然压缩的证据判据。
4. 三份针对性测试、隔离研究脚本、本报告与地图索引。

最终751项限定回归：749 PASS、2 SKIP、0 FAIL/ERROR。
沿用10项外部个人语料前置排除清单，不把排除项算通过；Memory源码与HEAD相同。
另有v2六项CPU/IO反例、共享预算验证、25项Evaluator针对性回归；子集不叠加为独立总数。
git diff --check通过。

独立判断：

- 诊断收敛，旧121异常保留UNKNOWN与采集能力，不无限复现。
- 重复决定详情具有确定体积收益及限定真实处理证据。
- 普通History可继续部分任务，仍有单位、时间、检索与任务作用域错误。
- 没有证据调整Goal Proposal接口、新建Memory维护层或改变Harness所有权。
- 30×2未闭环；下批宜先取得独立Goal Shadow观察，分别调度两组会话，
  避免History先超时持续使Goal NOT RUN；仍保持同版、可比预算、失败保留和无拼接。
- 多次生成/压缩如何占用420秒需另行预登记，不能任意加时、强制调用或补提案取PASS。
  一般完整请求token预算保证仍PARTIAL，不从23871样本推导彻底解决。

本轮达到修正版单批次停止边界，停止追加实机，提交评审。
没有新人工长会话要求，未Commit/Push，正式Goal/Memory和安全边界不变。

## 复核入口

final-facts.json、code-version.json、this-turn.diff、final-validation/scoped-regression.json；
各独立study的Native、execution-contract.trajectory、model-http-audit、turns及Host/Goal快照；
streams下按P0 request_id存放双向前缀与采集状态；engine-before-parser.jsonl存Parser前事件；
context-failure-*、receipt-fix与turn26-flow-analysis-v2覆盖两个阻断。

可离线重算，不需启动模型。研究启动脚本不是正式服务入口，不在评审时自动执行。
