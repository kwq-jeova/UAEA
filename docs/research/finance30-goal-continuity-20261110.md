# 真实金融对话改编的30轮连续Goal研究（2026-11-10）

**总体 PARTIAL：脚本及离线门禁完成，真实连续对照被遥测Fail-Closed中断。**
这不是Goal机制失败或30轮验收通过。保留Sideband，不新增协同层。
原始记录：/home/wqkan_wsl/uaea-n1x/research-records/finance30-20261110T073104Z/。

## 1. 来源与预登记

**VERIFIED**：原始人工会话 interactive-32768-20261105-053257、interactive-32768-20261105-071627，
分别29、34条Execution Observation；共16条原始用户消息，已核对Semantic Snapshot的输入身份、
原文件SHA256/行号、原生userMessage/Turn绑定。详见场景historical-user-inputs.json、
scenario-provenance.json、实验historical-tool-index.json。

前15轮按原顺序改编/合并这些问题，后15轮为研究者扩展，**不是原始30轮人工对话**。
benchmark/longitudinal_dialogue/finance30/保存脚本、逐轮来源、官方摘录与模拟版本。
用户原话包含“不会参考”“只看推理”，不能把真实长期Goal金标设为投资获利或某种风险偏好。
第26轮目的变化是明确标注的模拟研究条件，不代表真实用户修改了长期Goal。

冻结研究时点11-10 00:00 +08:00；历史估值目标11-04纽约收盘，
该日交易日/价格未核验。官方文件于11-09保存，文档声明发布时间更早，
**不证明11-04当时可获得同一字节版本**。其严格历史适用性UNKNOWN。
复用Intel/Apple HTML及Alphabet PDF快照，原件哈希一致；Alphabet数值复用此前审计摘录，
本轮未独立重新提取PDF表格。无新增市场联网数据、未来数据回填或真实交易。
SIM价格、年度EPS、10万美元纸面现金和后续约束均为研究者假设。

预登记：3轮显式引用类型控制；Relevant History/Goal Shadow各一个新Thread连续30轮；
同脚本/来源/模型/权限/12000字符工具回传预算；Goal组不预设种子、不强制提案；
各组第20轮后一次受控原生Compaction，自然Compaction独立统计。
短控制650秒、双组连续研究6000秒、总作业7200秒，仅约束本研究；
模型服务使用既有manual生命周期，内存和遥测阈值完全不变。
本次未达到这些作业期限，停止不是CASE_TIMEOUT。

## 2. 最小工程范围

仅隔离研究设施：
- longitudinal_prepare.py：可选max_turns（2–30，默认10不变），冻结分轮开放的只读资料版本。
- longitudinal_dialogue.py：不可覆盖的按轮资料释放、释放记录、版本清单；
  研究者可在完成轮次间停止，不能把部分脚本标为全量通过。
- longitudinal_audit.py：按确切文件身份匹配多来源版本，不能仅凭自报哈希接受未知文件。
- test_long_finance.py：6个反例/回归；finance30目录为冻结场景及来源映射。
资料开放是研究事件，不是工具Observation。工具真正读取后才产生Execution Observation。
算术参考与来源映射位于模型沙箱外，不注入金标。
冻结bundle单轮超时420秒，两组相同，不修改人工入口、模型依赖或资源配置。
执行源码以source-lock.json/frozen.json绑定，HEAD 125f0d2，明确保留dirty工作树身份；
不是声称Git HEAD已完整包含本轮实现。未Commit/Push。

## 3. 真实执行结果

| 项目 | 实际结果 | 判定范围 |
| --- | --- | --- |
| 显式短控制 | 3/3用户轮，5次原生Goal尝试，全拒绝，0候选 | Runtime拒绝限定PASS；合法恢复未发生 |
| Relevant History | 同一Thread完成14/30，第15轮失败 | 连续实验PARTIAL |
| Goal Sideband | 未启动，0轮 | NOT_RUN，认知及增量价值UNKNOWN |
| Compaction | 2次自然完成；第20轮受控项未执行 | 不能声明受控恢复验证通过 |
| 文件读取 | 8次真实成功，4个不同文件 | 来源/摘录哈希限定PASS |
| Context正文 | 65次对应8个Observation的完整呈现 | 重复供给，不是65次独立观察 |
| 不支持的工具 | 1次apply_patch被执行前拒绝 | 未写文件，不当成成功执行 |
| 来源版本 | 已释放6个不可变文件，后续版本未提前创建 | 选定回放范围PASS |
| 自动回归 | 118 PASS | 离线契约，不代表Goal语义通过 |

短控制首轮有意请求错误引用，得到3次“Evidence must reference actual Capability Observation”，
另有2次null candidate参数错误；它不是纯净的单变量自然恢复实验。
第二轮仅声称“已准备调用，等待Host回执”，没有原生重提；第三轮正确说明heads为空，
但只复述了Host保留的部分失败记录，不能当作完整调用次数。
不得将此显式控制记为自然Goal形成，亦不能以其混合失败证明接口不可用。

Relevant History已观察到：
- 第1轮真实读取目录/Intel资料；第2/5轮把16.5 billion USD误写成16.5亿美元
  （应165亿美元）。后续又正确写16.5B；未证明已系统纠正旧结论。
- 第4轮读取SIM v1，P/E=25；第11轮依据用户提供的新年度假设正确重算为40，
  并区分官方季度EPS。未读取v2文件，不能声称该结果来自文件恢复。
- 第6–12轮能保持部分公司归属、假设及真实报价缺口；选举/政策未读证据时保留UNKNOWN。
  仍有“均不符冻结时点”的表述错误：11-04历史适用性与11-10研究可用性被混淆。
- 第13轮保留10万美元全现金的模拟状态，没有交易执行凭据。
- 第14轮Apple任务只给框架，未读取已存在的Apple资料。
  Apple路径在出站请求2–14可见、15–25不再可见；ledger.md引用仍在。
  **文件存在不等于本轮模型收到正文**。它可以重读目录发现资料，却未行动；
  来源可恢复与模型主动恢复是不同问题，未证明新的确定性Runtime缺陷。

以上为非盲的事后人工代码审阅（Coding AI），不由被测模型自评制造真值。
目标、条件、路径变化及实际决策区分力的后半脚本尚未执行，不得补填认知成绩。

## 4. 中断根因与安全证据

**VERIFIED直接触发**：实验归档guard-monitor-exception.json
记录 active=service、message=Linux metric timestamp stale or invalid。
guard.ps1:63的条件为Linux样本age>3秒、age<-1秒或sample_seconds>3秒之一。
被拒绝的具体样本/当时比较时钟没有写入日志，具体分支及底层调度、采样、时钟或读取原因
均为 **UNKNOWN**；成功样本很快不能证明失败样本也正常。

时间线（UTC）：
- 08:04:33.051：最后记录的有效Windows服务样本；
- 请求24仍收到HTTP200/235239字节；第二次原生Compaction完成；
- Windows异常路径清理模型，后续请求25 ConnectionRefusedError，
  第15轮于08:04:35.737原生failed；
- 研究控制器终止后续阶段并再次确认清理。最终service/state的CONTROLLER_STOP
  是清理结果，不能覆盖较早的Windows遥测异常原因。
未证明KV越界、32K溢出、GPU超限、模型崩溃或Goal推理失败；未自动重载。

1894个有效服务样本（包括加载）：
NVML峰值29.53GiB；Windows Dedicated峰值30.09GiB；Shared峰值0.272GiB；
Windows Available最低20.56GiB、Commit余量最低40.63GiB；
WSL Available最低17.47GiB、Swap峰值12288字节。
这些是不同内存域，不能相加。有效样本未见资源越界，不证明未记录时间绝对无压力。
拒绝失效观测并停机的Fail-Closed有效，但持续遥测可靠性仍为PARTIAL。
已运行的短控制与基线两个Harness进程组均确认absent，模型remaining=[]、采样器remaining=[]，
8000/8003无监听；外部服务未关闭。14个基线终态ActiveGoal均null，Workflow完成未建立。
未独立测量所有Memory持久化路径，不以声明性字段保证全局无Memory写入。

## 5. 成本、结论与下一步

原生累计usage：短控制input 88040/output 2457；
基线含失败轮压缩input 447981/output 10854。已完成14轮耗时1357.43秒，
控制器含加载/短控制总计1917.21秒。usage为Harness原生累计报告，非独立计费审计。
Goal组未运行，**不能计算两组收益或成本差异**。

- VERIFIED：历史来源绑定、冻结脚本、8次读取及正文供给、拒绝与清理事实。
- PARTIAL：连续金融Workflow、遥测长期可靠性。
- UNKNOWN：自然Goal形成、维护/修订、后续使用、相对Relevant History的额外决策价值。
- 未产生支持替换Sideband、新建Goal Engine、协同层或Memory维护层的证据。

本轮停止，不安排人工长会话，不修补后重跑到PASS。
下一最小阻塞是遥测拒绝原因的可观察性：应先保留拒绝样本、
Windows读取/判定时刻、Linux时间与序列、读取耗时，再用隔离故障注入区分过期/未来时钟/
采样失败；不放宽3秒或内存门限，不直接归因为NVML超时。
待安全条件可靠后，复用此冻结脚本和完整失败轨迹，分别标注新执行及旧失败；
不得把未执行Goal组记为零自然候选或接口障碍。
