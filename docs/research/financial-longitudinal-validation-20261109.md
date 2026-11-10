# 历史金融多轮研究：自动化验证与认知边界（2026-11-09）

状态：**PARTIAL**。实验基础设施与限定来源恢复可以复用；没有证明额外Goal认知的决策收益，不接正式Goal/Memory采纳。

## 1. 真实输入与场景改编

原始输入来自两次人工会话的Semantic State快照：
- interactive-32768-20261105-053257：Intel财报、11月4日估值、模拟仓位、价格纠正、转Alphabet研究。
- interactive-32768-20261105-071627：Alphabet财报/估值、转Intel、两股比较、100%现金、Apple40倍PE疑问。

benchmark/longitudinal_dialogue/finance/historical-user-inputs.json保留原话、源文件、行号和SHA256；
scenarios.json逐项声明改编与新增干预，不将今天的合成参数倒写成原用户事实。

| 场景 | 用户轮次/每组 | 保留的连续任务与干预 |
| --- | ---: | --- |
| intc | 4 | 财报→历史行情缺口→模拟50/2→EPS修正1.25；研究目的保持 |
| comparison | 3 | Alphabet/Intel比较→100%现金模拟→现金至少80%；不虚构唯一买入排名 |
| apple | 3 | 核验40倍疑问及财政期间→模拟100/2.5→压缩后80/2.5并恢复来源 |

每个场景运行Relevant History（既有Goal Off）与Goal Shadow optional两组，共6个独立会话、20个用户轮次，
**不是一个连续20轮会话**。各自独立Sandbox/Codex Home/Host状态；两组同脚本、同财务摘录和工具预算。
交替部分顺序，未做统计重复/随机样本研究。提示直接要求区分假设/目标，不能据此声称自然Goal形成。

## 2. 来源与时间边界

本轮选择确定性冻结文件IO，不同时开展实时网络研究：
模型通过现有document.read_section真实读取ledger.md；**不是模型执行Google Search或web.fetch**。
研究者在2026-11-09通过HTTPS取得三份官方财报原件并保存原字节、URI、HTTP200和SHA256：
[Intel](https://www.intc.com/news-events/press-releases/detail/1786/intel-reports-third-quarter-2026-financial-results)、
[Alphabet](https://s206.q4cdn.com/479360582/files/doc_news/2026/Oct/28/attachments/2026q3-alphabet-earnings-release.pdf)、
[Apple](https://www.apple.com/newsroom/2026/11/apple-reports-fourth-quarter-results/)。

只提供声明发布时间不晚于11-04截止的选定财报字段；但这**不是11-04当天保存的字节快照**，
不能证明页面从未事后修订，历史时点真实性为PARTIAL。原件获取时间、声明发布时间、报告期间、估值截止日各自保存。
无已核验的11-04收盘价/交易日表、forward全年EPS共识或完整电话会议记录，必须UNKNOWN；
没有根据星期几推定交易日，没有实际证券交易。

financial-ledger.md是研究者有出处的摘录，不是完整正文或新的独立来源。
模型无法联网，不能因本次UNKNOWN判断正确就声称真实行情获取通过。
季度EPS与全年模拟EPS分开；Apple财政Q4与自然季度分开。
量化参考由独立十进制计算产生，不由被测模型自评：25→40、40→32；
现金80%意味着股票合计最多20000USD；2.12相对2.87下降约26.13%，不是72.1%。

## 3. 必要工程修正与复现

仅修改隔离研究代码、Fixture和文档：
- scripts/research/longitudinal_audit.py：逐项核对预期轮数/原用户文本/原生Turn ID/完成状态/Host快照，不以result.json存在或空列表all()通过。
  同时区分文件、完整section及1000字符receipt摘录的hash范围，另核对实际出站工具正文，读取成功不等于正文完整供给。
- scripts/research/longitudinal_dialogue.py：实际Sandbox根目录与研究投影对齐；原配置cwd正确但投影仍指源码根，导致错误文件路径。
  修正只在研究子类，未扩大Sandbox。复用现有原生thread/compact/start；控制Turn不计入用户轮次。
- scripts/research/longitudinal_prepare.py：复制独立源码bundle、源文件/模型配置/Harness/脚本hash、Fixture及计划；
  执行前及每轮检查源码锁。没有把脏工作树伪装成干净Commit。
- benchmark/longitudinal_dialogue/test_contracts.py及finance/：负例、3组历史改编、独立来源索引与复现说明。

HEAD：2d8d68d26ff97a4bf007895ebef02724890fa817；运行使用124文件的不可变源码bundle，不受后续工作树编辑影响。
环境：Python3.12.3/aarch64、vLLM0.32.0、Torch2.13.0、B12X1.5.1、FlashInfer0.7.0.post1；
模型下载Revision cf2effc5c4b794ee9fb8d34eab3d1d65ce64142f；Harness rust-v0.163.0。
环境/模型config/index/Parser/启动配置的hash分别归档；**未进行全量权重hash**，不能声称位级或输出确定性复现。
依赖安装与模型配置均未改，保留32K/1GiB KV/36GiB、64/64 UMA及原保护。

23项CPU定向检查PASS，git diff --check通过。
两份真实历史篡改回放（同时删末轮、清空全部轮次但保留result文件）在旧Evaluator均误PASS，新Evaluator均拒绝。
此前合成批次用最终Evaluator复核为8/8会话、20轮完整。

原生压缩的评价还发现一项误报：Shadow的压缩控制请求按既有Host决策将状态保留在带外，
不应要求它携带普通用户Turn的Goal投影。初版审计5/6留档；
修正仅凭已完成原生压缩Turn时间区间+Host deferral决策识别控制请求，普通请求仍严格检查。
缺普通投影、伪造压缩文字、无原生完成证据、时间区间不符均有负例，不用关键词豁免。
最终离线评价6/6，不改变任何真实模型输入或重跑回答来求PASS。

## 4. 正式批次与诊断批次分开

主批次：finance-dialogue-adequate-20261109T082916Z（完整路径见文末）。

先前4K工具输出上限会把1217字符section中财务段落截掉；
文件/Observation正确、审计记录完整，仍不能证明模型拿到正文。
该限制批次完整20轮单独保存，不与主批次混合。
主批次仅将研究Adapter的两组工具结果预算统一为12000字符，原Host/模型预算不变。
实际22次出站工具正文呈现均与完整section hash相符；其中重复出现在历史请求不算新读取，
**真实Capability Observation只有8次**。

此外，最初来源根目录异常批次保留；一个排队的12K单轮探针在首次服务有意停止时被中断，
它曾真实读取，随后Provider不可达。原始错误完整保留，既不声称没执行，也不纳入认知准确性。
未使用这些诊断中的响应择优替代主批次。

## 5. 主批次结果：三个层级分别判断

| 指标 | Relevant History | Goal Shadow optional |
| --- | ---: | ---: |
| 完成用户轮次 | 10 | 10 |
| 真实document Observation | 4 | 4 |
| 原生受控Compaction | 1 | 1 |
| 累计输入Tokens | 168362 | 178638 |
| 累计输出Tokens | 3503 | 4087 |
| 会话耗时合计 | 508.17秒 | 566.03秒 |
| Goal候选 | 不启用 | 0（10条NO_GOAL_PROPOSAL） |

Tokens为原生累计计费/usage计数的会话末值相加，含重复历史和控制压缩；
不是单次Context长度，也不是有价值信息bit。Shadow该次输入多约6.1%、耗时多约11.4%，
受生成随机性/长度影响，不能推成稳定性能效应。

**Contract：限定PASS（6/6）。**
全部用户轮次、工具结果与实际出站正文可关联；每会话Task ID保持；
两组压缩前后constraints/task/current_input/effective_state、真实来源计数及最近Observation保持。
model_outputs计数2→3是压缩生成派生输出，不是新增Source Evidence。
ActiveGoal均为空、model_output_is_source_evidence均false，Workflow完成均未建立；没有把Turn完成当研究完成。

**Model Behavior：PARTIAL，存在明确FAIL。**
- Intel两组均保持行情UNKNOWN，模拟25→40并更新假设；个别“盘前/收盘后”、用户输入/模型自设措辞仍偏。
- Shadow comparison首轮在**完整来源已供给、压缩尚未发生**时交换两公司数字，第二轮延续；第三轮修正部分值但将Intel指引错误归给Alphabet。
- History comparison保留主要来源身份，却把同比EPS下降错算为72.1%，并一度将访问日期11-09当截止日。
  修改现金约束后，一面承认40%股票不满足80%现金，一面仍称40000股票+60000现金（80%）可行。
- Apple两组压缩后均真实重读文件、恢复2.5的模拟年度EPS、得到32倍，保留FY2026Q4/季度EPS2.10与行情UNKNOWN。
  History组仍将114.5 billionUSD译为114.5亿美元，存在十倍单位冲突；Shadow最终局部正确不代表整组研究通过。
- 多轮超过用户150/200字限制，增加成本；不以格式/长度正确冒充语义正确。

每项结论的原生Turn ID、模型Item ID、原始JSONL行号见behavior-review.json与responses-for-review.json/md；
没有根据最终回答反推隐藏推理依赖。

**Goal Behavior / 决策增益：UNKNOWN / 未观察到增量。**
Shadow投影确实进入普通出站请求；10条日志均为optional_final_envelope_not_present，
不是提出后拒绝，也不是已确认Parser丢失。不能仅凭无候选判断合理不提或协议失败；
本批未自然形成长期Goal，不能检验完整候选演化。
普通连续历史已能完成部分修正/恢复；没有证据支持增设经验维护层或自动采纳。
真实投资决策价值、真实网页研究完成、长期建议净收益均UNKNOWN。

## 6. 资源与清理

主服务全生命周期采样（含加载）：
NVML Dedicated峰值29.11GiB；Windows GPU Dedicated峰值29.12GiB、Shared峰值0.264GiB；
Windows Available最低22.99GiB，Commit峰值69.37/114.48GiB，Commit余量最低45.11GiB；
WSL Available最低17.37GiB，Swap最多16KiB。不同域重叠，不能相加。
前一诊断服务另表保存，NVML峰值29.65GiB、宿主Available最低22.00GiB。

两次服务启动前模拟阈值/监控失效闭环通过；真实服务没有资源保护触发。
完成后只停止自有服务，CONTROLLER_STOP，remaining=[]；采样器也remaining=[]，8000/8003无监听。
启动器对有意停止仍打印Safety stop/退出1；这是控制器正常收尾，主实验驱动exit0，不能误报内存事故。
16份既有受保护配置/补丁hash未变；正式Runtime/Harness/Phase-1代码与本轮开始时一致。

## 7. 下一步与复现入口

建议先评审来源归因、单位/算术与约束执行这些真实失败；继续以Relevant History作为可撤销基线。
不因增加历史状态而工程化Goal层，不通过强制候选或更多同类重跑追求PASS。
无需本轮再安排长人工会话；若要研究实际建议价值，仍需独立真实结果/人工评价，不能用本脚本代替。

源码入口：benchmark/longitudinal_dialogue/finance/README.md。
主记录：/home/wqkan_wsl/uaea-n1x/research-records/finance-dialogue-adequate-20261109T082916Z/
关键文件：source-lock.json、environment-lock.json、posthoc-evaluator-version.json、
audited-results.json、comparison-summary.json、actual-tool-exposure.json、behavior-review.json、
responses-for-review.json、resource-summary.json、final-tests.log。
旧20轮复核/负例/4K批次/中断探针引用另行保存，原始记录不覆盖。
本轮不Commit/Push；保留原有未提交变更，不自动接正式Runtime。
