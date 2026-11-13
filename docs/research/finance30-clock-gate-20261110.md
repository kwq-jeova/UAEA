# N1X时钟门禁定位与金融连续复测（2026-11-10）

**总体PARTIAL；已到资源安全判据评审边界。未完成30轮对照，不提高Goal Cognition成熟度。**

原批次 finance30-20261110T073104Z 的14轮保持原样。
本轮诊断：/home/wqkan_wsl/uaea-n1x/research-records/finance30-monitor-20261110T082511Z/。
新独立批次：/home/wqkan_wsl/uaea-n1x/research-records/finance30-rerun-20261110T083057Z/。
11项冻结输入文件及完整执行bundle哈希与原批次相同；新Thread、Home、来源目录及Journal，
未拼接旧轮次，未修改用户脚本追求PASS。

## 1. 监控最小修改与门禁

**VERIFIED applied**：仅独立启动资产guard.ps1、guard_ctl.py及对应SHA256 pins：
- 拆分LINUX_SAMPLE_OLD / LINUX_CLOCK_FUTURE / LINUX_SAMPLE_DELAY、
  invalid/run/sequence/value/读取失败等拒绝码。
- 拒绝前写入telemetry-rejections.jsonl：拒绝样本、最后有效样本、两侧UTC、
  Windows单调时钟、年龄、采样与读取耗时、当时Windows资源及具体条件。
- 保留primary_sensor_failure，再进入清理，不用最后CONTROLLER_STOP掩盖第一原因。
- Linux记录sample_start/end、单调时钟和publisher journal；失败仍写invalid并退出。
- 现有研究控制器识别Guard/launcher退出，停止后续组，保留primary-monitor-failure。

资源Reason函数逐字未变；其他原pins保持。48GiB Dedicated、6GiB Windows可用、
Commit余量max(16GiB,20%)、4GiB WSL、256MiB Swap、3秒新鲜度、
-1秒未来拒绝线和2秒采样预算未放宽。当前仍用常驻NVML，不调用nvidia-smi。
没有改vLLM、Torch、KV、Phase-1、Harness、Goal/Memory采纳或权限。

[补丁及独立测试](../implementation/harness/telemetry-diagnostics-20261110/README.md)；
完整before/after/pins在诊断记录中，可回滚但需检查后续修改，不能整体覆盖用户改动。

短时验证：
21项原生PowerShell注入PASS（含各时间/数值/序号和资源边界）；
7项既有Python回归PASS（含2.1/3.1秒迟到返回不得发布valid）；
invalid帧、冻结采集器两次专用无模型进程终止/子进程清理PASS；
原启动器资源阈值与心跳停止smoke PASS；
181秒真实无模型链路175样本，采集最大0.111秒，采样器remaining=[]。
以上是短时门禁，不证明偶发时钟问题已修复。

## 2. 新批次首次捕获的直接原因

**VERIFIED**：在2551个有效服务样本后，Guard记录LINUX_CLOCK_FUTURE。
关键原件：新批次primary-monitor-failure.json、
resource-review.json及其指向的guard/telemetry-rejections.jsonl。

| 字段 | 拒绝时实际值 |
| --- | --- |
| 判定Windows UTC | 1794302220.681 |
| Linux观察UTC | 1794302221.7236726 |
| sample_age_seconds | **-1.0426726秒**（触及<-1） |
| 当前/上次接收seq | 2546 / 2544 |
| seq观察单调间隔 | 1.032015秒 |
| valid | true |
| NVML query | 0.000282425秒 |
| 完整采样 | 0.000462908秒 |

本次直接原因是**跨系统UTC比较的未来时间判据**，不是2秒采样超时。
序号前进和查询很快，不独立证明数据真实年龄<=3秒；不能据此直接接受该帧。

停服后8组只读时钟括号测量，其中7组往返小于0.5秒：
Linux UTC位于Windows发送前/接收后的区间之外，
领先下界约0.668–0.679秒、上界约0.842–0.888秒。
这证实两侧绝对UTC不一致，未校准的差值不能直接解释为同一时钟下的样本年龄。
测量值不是永久校准参数，不回填到Guard，也不据此认为原样本已安全。
哪侧绝对时间正确、偏差由何种同步/虚拟化机制造成仍UNKNOWN。
原161612批次没有保存拒绝值，不能追认其也必然是未来分支。

有效服务样本峰值/余量：
NVML28.87GiB；Windows Dedicated29.24GiB；Shared0.227GiB；
Windows Available最低22.11GiB、Commit余量最低42.03GiB；
WSL Available最低17.44GiB、Swap峰值12288字节。
有效数据未见资源超限；不同内存域不相加，未记录间隔不承诺绝对无压力。
服务remaining=[]、采样器remaining=[]、Harness进程组absent。未自动重载。

监控判定：拒绝证据和Fail-Closed清理 **VERIFIED**；
长时间实验可靠性 **PARTIAL**；底层时钟偏差来源 **UNKNOWN**。
并非CASE_TIMEOUT、32K溢出或Goal推理失败（CASE_TIMEOUT未触发）。

## 3. 连续实验结果及范围

| 项目 | 真实结果 |
| --- | --- |
| Relevant History | 同一Thread完成20/30轮；第21轮未完成，按基础设施中断删失 |
| Goal Shadow | NOT RUN，不能统计为零自然候选或失败 |
| Compaction | 2次自然；第20轮后受控原生Compaction完成，共3次 |
| 压缩后行为 | 第21轮真实读取目录并进入后续请求，但回答未完成；完整行为UNKNOWN |
| 工具执行 | 10次document.read_section成功，无提案操作 |
| 冻结来源 | 8次财报/目录清单内读取；另2次项目脚手架README |
| 资料版本 | 已按轮开放9个不可变文件；第22轮SIM v3未开放 |
| Goal生命周期/增量价值 | NOT RUN / UNKNOWN，不能由History表现替代 |

冻结Evaluator的document_delivery为 **FAIL**，原因是两次默认生成README未预声明在
financial fixture manifest，保留原结果，没有放宽判据重算PASS。
独立事后核验分开记录：两次README实际存在且文件/摘录哈希一致，
但不能当作财报来源；其余8次清单内读取与版本/范围匹配。
独立检查用真实Native userMessage与冻结脚本绑定未完成第21轮，
没有把该轮当成完成，也不把原检查器无法映射其轮号误报为未来资料泄漏。
见independent-source-review.json；不是全项目来源契约通过。

**Cognitive Behavior PARTIAL（仅History基线）**：
- 第11、16、17轮按用户SIM值计算40、40、32倍；明确区分年度假设与季度实际。
  未读取这些SIM文件时，只能归因为用户输入/历史恢复，不能声称文件取证。
- 第18轮正确核算现金>=80000、单公司<=20000，保留全现金模拟，无真实交易。
- 第20轮取消Apple子任务、继续其他科技研究，未把Task取消等同全部研究结束。
- 来源与单位仍出错：Intel营收有16.5亿美元/16.5百万美元等矛盾；
  Alphabet EPS从2.12误归为2.10，并在第19轮核验时用2.10-2.87=-0.77继续传播。
  Apple收入114.5billion→1145亿美元换算正确。
- 来源可见性不能简化：第6轮真实读入Alphabet2.12；第8轮输入仍含2.12但原完整段已退出；
  第19轮原段与2.12均不在当前Context且未重读。后续错答不能一概称为
  “完整正确来源仍在输入、模型却忽略”。引用来源可恢复不等于模型实际恢复。

原生累计usage（含受控压缩与未完成轮）：input563454/output21032；
不是独立计费审计，Goal组成本和相对收益NOT RUN。
所有已完成基线终态ActiveGoal仍null，Workflow completion未建立。
未独立审计所有Memory写入通道，不用固定声明充当全局无Memory事实。
本轮无Goal/Memory采纳入口或交易能力变更。Memory保持Research Reserved。

## 4. 需评审的最小替代方案——尚未部署

不建议将未来容差从1秒加大、删掉检查，或仅凭seq前进接受数据。
缓存/传输若延迟5秒但持续交付递增序号，接收端“最近见到新seq”仍不能证明数据<=3秒。

建议复用现有心跳/采集器，建立**同一Windows单调时钟下的因果采样确认**：
1. Windows在T0发布不可重放的采样标记n。
2. 已验证代码顺序的Linux采集器先读n，再采WSL/GPU，返回n与run/seq。
3. Windows在T1收到；要求T1-T0<=3秒，保持2秒采样预算及原有全部资源门限。
4. 缺确认、错误run/标记、回放、超时或无效计数继续Fail-Closed；启动前先完成门禁。
因果顺序T0<=采样<=T1可给出年龄上界，不依赖两侧UTC相等。
必须用真实IPC轨迹和故障注入证明采集顺序，不能信任帧自述的“fresh=true”。

隔离原型causal-freshness-proposal/timing_proof.py仅检验条件算术，
11项合成反例通过；**未证明设备IPC，也未接入启动器**。
不可从该PASS推导可部署、安全保护或Goal认知已通过。

这改变了安全观测契约：以前因UTC超前被拒的帧，只有获得独立因果新鲜度证明才可能接受。
因此按用户本轮“若必须调整资源安全策略，停止并提交人工评审”要求，暂停实际加载。
**待评审具体项**：是否批准在隔离监控分支实现上述因果门禁、
完成无模型实链路/停止回归后，再启用一次全新30轮对照批次。
资源数值门限、模型配置、正式Goal/Memory和执行权限均不申请扩大。

## 5. 工程结论

VERIFIED：拒绝分支、低采样耗时、跨侧UTC偏差、20轮/三次压缩/真实读取、清理事实。
PARTIAL：监控长期可靠性、History研究行为与来源覆盖。
UNKNOWN：历史故障确切分支、时钟偏差底层来源、自然Goal形成/维护和增量价值。
NOT RUN：本批Goal Shadow、完整30×2对照、替代门禁设备实现。
不据此改变Goal Proposal Interface或上调Goal成熟度。
无需新的人工长会话。保留全部旧/新失败，不Commit/Push，不自动重试。
