# N1X单时钟确认与金融30轮恢复（2026-11-10）

**总体 PARTIAL；负载下GPU遥测可靠性 BLOCKED；30×2 Goal对照未完成。**
本轮按“监控异常停止、不得自动重试”的边界结束。没有新的人工长会话需求，不提高Goal Cognition成熟度。

## 1. 证据位置与批次隔离

- 监控隔离验证：/home/wqkan_wsl/uaea-n1x/research-records/singleclock-20261110T122425Z/
- 新金融批次：/home/wqkan_wsl/uaea-n1x/research-records/finance30-singleclock-20261110T130307Z/
- 本次守卫：/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261110T134344Z-a4b0608b/
- [监控实现、Diff与测试归档](../implementation/harness/telemetry-single-clock-20261110/README.md)
- 上轮20轮及其时钟拒绝：[历史报告](finance30-clock-gate-20261110.md)。更早14轮、上轮20轮与本轮14轮是三个独立批次，未拼接。

新批次165个执行输入/源码/环境与监控快照被锁定，结束后全部哈希仍匹配。
用户脚本、来源、原判据、32K/1GiB固定KV/36GiB引擎规划/Eager/单并发未改。
前15轮是历史人工问题的改编/整合，后15轮是研究者扩展；不是30条原始人工历史。
研究时钟11-10，11-04估值适用性仍UNKNOWN；11-09资料快照不自动证明11-04字节可用。
未运行公网行情查询、Provider回退或真实交易。Researcher模拟值不视为市场事实。

## 2. 单时钟修复与独立验证：限定PASS

**VERIFIED**：Windows以Stopwatch记录T0（早于本次Windows采集），
发布绑定guard Run、sampler Run、递增seq与随机nonce的标记。
Linux先读取、验证并消费该标记，再实际查询/proc和常驻NVML。
Windows在T1校验返回的相同标记，仅接受T1−T0≤3秒且Linux完整采集≤2秒的有效数据。

一次性、错Run、重放、倒退、失败、丢失和迟到均Fail-Closed。
等待期间发现上次响应不会消费、重采或刷新原期限。两侧UTC仍供审计，不作为跨系统年龄。
所有原有内存门限及资源Reason函数逐字未变；独立心跳和owned进程清理保留。
没有恢复旧缓存，也没有自动重试NVML查询。

| 验证 | 实际结果 |
| --- | --- |
| Python采集器CPU反例 | 10项PASS |
| Windows消费者CPU反例 | 16项PASS |
| 实际IPC及专用CPU进程故障 | 7种PASS，均停止并清理；没有模型 |
| 正常短IPC与UTC±1小时注入 | PASS；只改测试帧，不改系统时钟 |
| 真实无模型持续验证 | 3000.874436秒、2734次唯一完整确认，PASS |
| 持续验证最大确认/采集 | 0.7410859 / 0.229901485秒 |
| 验证后安装及正式smoke | PASS；GPU48GiB模拟与心跳失效清理通过 |

仅在上述验证通过后，替换独立启动资产guard.ps1、guard_ctl.py及其SHA256 pins。
config、NVML实现、服务生命周期、vLLM/模型环境与系统设置未修改。
既有N1X模型启动准入的额外UTC检查没有绕过，本次正常通过实际加载。
应用守卫不是CUDA硬分配上限，有限无模型PASS不等于所有负载下持续可用。

## 3. 实际负载证据与新的停止原因

### 3.1 旧时钟误判路径获得实际反证

**VERIFIED（本次有限区间）**：1502个成功确认均有匹配的issue→新采集→ack链，
无重复消费，最大确认0.3611862秒，最大完整采集0.217201520秒。
其中6次Windows−Linux UTC差小于−1秒，最低−1.291306496秒；
这些帧仍凭独立的本次因果新鲜度证明通过，而不是放宽UTC容差。
见causal-chain-audit.json、old-future-rule-examples.json及原journal。
哪一侧绝对时间正确、底层时钟偏差成因仍UNKNOWN。

### 3.2 首个异常是NVML API错误，不是时钟拒绝

monitor-exception.json保存的primary_sensor_failure：
- code：LINUX_SAMPLE_INVALID。
- detail：NVML memory status 17。
- request_seq/nonce：1503，绑定本次guard及sampler。
- Linux错误采集耗时：0.104177298秒，未超过2秒。
- Windows读取时因果上界：0.1646453秒，未超过3秒。
- invalid帧未被接受；采集器退出，模型随后终止，未重试。

本机实际/usr/lib/wsl/lib/libnvidia-ml.so.1的nvmlErrorString(17)返回：
“GPU access blocked by the operating system”。
只做错误字符串解码，未启动NVML查询或新模型测试；库哈希见nvml-error-decoding.json。
这证明API返回了OS阻止访问的错误，**不能证明**是权限变更、驱动重置、WSL升级、
显存越界或Compaction导致。底层原因UNKNOWN。
22:07:57–22:11:57 +08的Windows System日志读取61条，
指定Display/nvlddmkm/WHEA等Provider过滤无匹配；不据此宣称驱动健康。

停止后postflight又遇到未消费的1503标记，记录UNCONSUMED_CHALLENGE；
这是拒绝新采样的次生事件，不能覆盖此前保存的NVML首因。
1503个issued、1502个成功ack及1个明确invalid是预期的失败轨迹，
**不能**将计数不相等改写为全部成功。

### 3.3 资源与清理

有效服务样本1497个，峰值/余量：
- NVML GPU峰值29.517GiB；Windows Dedicated峰值28.908GiB；Shared峰值0.191GiB。
- Windows Available最低21.777GiB；Commit剩余最低42.707GiB。
- WSL Available最低17.453GiB；Swap峰值12288字节。

失败时新的NVML值不可得，不能使用上一帧伪造当前GPU数据。
已有有效样本没有达到内存门限，**不证明失效时段绝对没有资源风险**。
本次不是已证明的显存超限、KV/Context溢出或CASE_TIMEOUT。
服务remaining=[]，采样器remaining=[]，Harness进程组absent，8000/8003无监听。
终止后的CONTROLLER_STOP是执行停止结果，第一原因仍为NVML错误。

## 4. 金融连续实验：PARTIAL，Goal对照NOT RUN

| 项目 | 实际证据 |
| --- | --- |
| Relevant History | 1个Thread，14/30轮完成；第15条真实输入已送入但未完成 |
| Goal Shadow | NOT RUN；未建立Thread，不能统计为零自然提案或Model Behavior FAIL |
| Compaction | 2次自然contextCompaction完成项；第20轮受控压缩未到达 |
| 实际工具Observation | 10条：9成功、1目录读取失败 |
| 来源/版本 | 9次成功读取的源文件、摘录哈希匹配；6个开放文件保持不可变 |
| 正文供给 | 67次完整摘录供给，均关联HTTP200且bytes_received>0的传输记录 |
| 正式状态 | 14个完成快照的ActiveGoal均null、Workflow完成均false；模型输出不作来源Evidence |
| Goal生命周期与相对收益 | NOT RUN / UNKNOWN |

正文进入成功传输请求不等于模型实际使用或解释正确，更不是服务器token化审计。
原始Evaluator对History来源供给给出限定PASS，但因轮次未完成，整体基础设施契约不通过。
它对未启动Goal组输出缺失Observation的FAIL；保留原件，研究判定必须是NOT RUN，
不能把“未运行”算作模型失败。本轮没有改判据或补齐缺轮。

局部行为与负例均保留：
- 第4轮真实读模拟文件，50/2=25；第11轮50/1.25=40，未重读v2，不能声称文件取证。
- 第6轮真实读Alphabet资料后正确报告季度EPS2.12，并保留历史价格/年度共识UNKNOWN。
- 第8轮比较表错误写“万亿USD，万股”；第14轮将Apple114.5 billion USD错写成114.5亿美元。
  不能用来源哈希正确或同段其他数字正确掩盖这些语义错误。
- 第13轮真实读取现金假设，反复读取同一内容并把目录交给read_section导致一次失败；
  最终完成回答，保留$100000、100%现金、零成交的SIM状态。
- 保留原回答、native turn ID、事件行号及实际调用；没有将文本建议视为真实买入或执行完成。
- 用户Goal/Task变更的后半段尚未到达，不能据此评价自主Goal演化。

原生累计usage：input425476/output8317（包括压缩与未完成轮的记录范围）；
不是计费审计，也不能与未运行Goal组比较成本。
Goal理解、操作选择、候选状态及长期决策价值均未得到本批新证据。

## 5. 修改范围与下一步评审

**已完成**：独立监控脚本/pins、隔离CPU/IPC/持续验证、一个新冻结实验批次、
失败归因、来源/轮次/传输及进程清理审计、研究与代码证据归档。
没有修改Phase-1、Harness执行循环、Goal Adoption、Memory Admission、Provider Policy、
模型依赖、Context/KV、系统内存或时钟配置。Memory仍Research Reserved。
工作区已有变更保留，不Commit/Push。

**VERIFIED**：本次标记链与UTC解耦、50分钟门禁、负载中的旧UTC误判避免、
NVML错误返回、Fail-Closed和清理。
**PARTIAL/BLOCKED**：持续GPU遥测可用性及完整30×2实验。
**UNKNOWN**：OS阻止NVML访问的底层原因、自然Goal维护和相对Relevant History收益。
**NOT RUN**：本批Goal Shadow及后半段认知对照。

建议下一阶段只定向排查NVML17：核查负载下接口/OS事件及可用的独立GPU观测依据。
不能仅因错误很短就重用旧样本、自动重试直至成功，或将Windows Dedicated与NVML口径
未经验证直接互换。若考虑有界恢复，须先证明独立安全观测及原3秒/2秒门禁，
涉及安全观测策略变化应评审。当前不建议再次加载长实验，更不修改Goal架构。
保留因果守卫的Fail-Closed能力；不恢复已知存在UTC误判的旧实现追求连续性。

本轮按用户停止条件提交评审；无需人工长会话。
