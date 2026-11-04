# Bolt真实Goal语义识别：受控中断与限定结果（2026-11-04）

总体 **PARTIAL**；完整真实实验 **BLOCKED（监控控制调用超时）**。
已完成一次模型启动和3次有效推理；第4次请求中断，另39次计划请求未提交。
**不能据此判断Bolt已具备可靠的Goal Change / Condition Change / Belief Update识别能力。**

## 1. 本轮实际范围及关键结论

- 真实Bolt通过既有受保护入口启动，90/90权重分片完成，服务约117.09秒就绪。
- 首组历史人工8轮，完整恢复原文/顺序并固定评价；完成前3轮语义识别。
- 新增反例、旧Fixture原文、更多历史及公平策略对照已冻结，**全部尚未推理验收**。
- 没有更改答案、自动重启、降低保护阈值、安装依赖或接正式Goal/Memory。
- 模型识别质量与Host权威契约分开：本轮直接调用API，没有真实Goal Admission/Reject流程。
  不能将研究隔离扩大成完整Runtime Contract PASS。

**当前可说的**：3个相近历史前缀中，输出未编造长期Goal或执行Observation，6处逐字引用可定位。
**当前不可说的**：目标明确改变、条件改变、认识修正、真实引用配错误summary、
重复/Compaction强化和跨轮泛化都通过。它们在本轮没有完成测试。

## 2. 环境、模型与实际命令

独立环境：/home/wqkan_wsl/uaea-n1x/nemotron-bolt/venv。
包元数据实测：Torch2.13.0、vLLM0.32.0、Triton3.7.1、FlashInfer0.7.0.post1、
B12X1.5.1、CUTLASS DSL4.8.0、Transformers5.19.0。
原Qwen环境未修改，其mem_utils.py仍匹配历史SHA256
54772815cecb6445485ff41bfeecf85082da6120c8e4615eff7066ddc544610e。

执行顺序：

```bash
bash /home/wqkan_wsl/uaea-n1x/nemotron-bolt/start-bolt-32k.sh --check
bash /home/wqkan_wsl/uaea-n1x/nemotron-bolt/start-bolt-32k.sh
python3 -u -B /home/wqkan_wsl/uaea-n1x/research-records/bolt-goal-semantics-20261104T000520Z/run_bolt.py
```

这些是本轮已执行记录，不表示建议在安全门禁未恢复时再次启动。
当前人工入口未变，实验脚本不是正式入口。

生效配置：64/64 UMA、32768 Context、单并发、Eager、固定1GiB KV、
36GiB引擎规划/32GiB非KV预留、B12X Linear/MoE、FLASHINFER Attention、
flashinfer Mamba、qwen3_coder及ultra_v3插件，127.0.0.1:8003。
设备规划、CUDA实际分配及Windows宿主边界分别保留，不将规划称作硬上限。

真实日志：模型加载报告21.5GiB、约69.04秒；KV容量96743 Tokens。
该容量的理论并发值不改变max_num_seqs=1；本轮未进行长输入压力测试。
请求使用temperature=0、seed42、max_tokens900、enable_thinking=false、reasoning_effort=none；
3个完成响应reasoning_tokens均为0。没有提供工具，不执行输入中的业务请求。

## 3. 历史8轮如何确定、恢复及限制

至少找到两组8轮：2026-10-28 agent研究对话与2026-10-30 INTC财报对话。
此前“第2、7、8轮”的描述，分别匹配10-28组指定Google、英文检索和逐篇阅读，
因此选它作为本轮主要8轮；不宣称它是“8用例”唯一可能所指。

主运行：
/home/wqkan_wsl/uaea-n1x/runs/h3-results/interactive-32768-20261028-010144/

每个原文来自semantic-state-snapshots.jsonl中保留的workflow_request_input.metadata.text，
并在app-server-events.jsonl找到**唯一、全文相等**的原生user回显。
只取原始文字，不使用snapshot中的topic、relation、Goal标签、模型答案或评价。
环境块、external_uaea投影和Compaction的协议role=user不进入首组输入。

八轮原文恢复 **PASS（内容）**；来源身份追溯 **PARTIAL**：
旧记录没有现代host_input_origin登记证明，依据是Host保留请求+唯一原生回显+既有会话背景，
不能把协议role或文件hash当作独立身份认证。
另完整恢复10-30组8条与11-02组4条，共20条；三组都保留独立来源定位。

逐项结果：

| 用例 | 恢复原文 | 实际结果 |
| --- | --- | --- |
| H01 | 你可以联网搜索吗 | 完成；语义/引用限定PASS；无长期Goal或执行断言。 |
| H02 | 我想指定google站点，搜索：ai agent development | 完成；当前检索请求与细化标签正确；对是否希望搜索多余弃答，PARTIAL。 |
| H03 | 有没有更偏向研究性质的？ | 完成；研究方向保持；省略对象被解释成搜索方式，及多余搜索疑问，PARTIAL。 |
| H04 | 链接1主要讲了什么内容呢？有什么研究价值 | 请求已提交；安全保护中断，无完整响应，UNKNOWN。 |
| H05 | 仅仅只有原则吗？有没有其他类型的，更底层开发相关的 | 未执行，UNKNOWN。 |
| H06 | mindstudio这个开发的具体环境是什么样的 | 未执行，UNKNOWN。 |
| H07 | 有没有偏agent认知研究、多agent llm共享通信相关的？最好翻译为英文搜索 | 未执行，UNKNOWN。 |
| H08 | 请逐个阅读前三个链接，并总结告知我你对这些研究的判断 | 未执行，UNKNOWN。 |

详细snapshot JSON Pointer、原生行号/item/turn、输入字节hash见recovered-inputs.json；
每条进入模型的原文未经改写。模型收到的是带source_id/origin的原文记录列表，
不是旧Harness投影或历史模型解释。

“链接1”“前三个链接”和“这4点”的具体对象不从旧回答反向补造；
这会限制可判定范围，评价允许未知，不能用新推理捏造旧历史。

## 4. 输入覆盖与冻结反例

与上一轮8个预定义场景逐字比对，历史8轮与Fixture的原文重合为0。
这只说明字节不同，不证明语义独立或能力覆盖充分。

| 输入来源 | 准备数量 | 覆盖/重复性 | 实际完成 |
| --- | --- | --- | --- |
| 10-28历史人工前缀 | 8 | 同一agent开发研究主题，主要是细化/延续；缺少明确长期Goal替换与自由交流 | 3；第4个中断 |
| 上轮Fixture原文 | 8 | 只取short原文，丢弃facts、operation、标签与旧gold；4组关系配对 | 0 |
| 本轮独立合成 | 8 | 口述史资源变化/摄影展替换、跑步误解、自由聊天、读博错summary、重复派生、虚假读取、音乐假设 | 0 |
| 更多真实多轮前缀 | 3 | 网络修复后继续、缺失4点指代、Google财报研究；仅用户历史 | 0 |
| 历史派生摘要干预 | 1 | 原用户前缀加入明确标记的旧Compaction；单独报告，不作为纯人工输入 | 0 |

新案例包括真实quote搭配“已决定辞职留学”的错误summary、重复声称“已确定转行做医生”、
未提供Observation却声称读完网页，以及“假如以后做音乐、尚未决定”的条件设想。
它们仅是冻结的合成反例，不能写成已实测模型错误或通过。

cases.json、gold.json、protocol.json、system-prompt.txt、strategies.json、
request-plan.json及恢复来源在第一次推理前固定hash；
冻结清单frozen-before-inference.json复验一致，未根据模型输出改真值。
总计划43次：28基础前缀、12策略对照、3预选来源检查提示变体。
未提交的39次与已中断的1次均保持未测，不用离线旧分数补齐。

## 5. 实际3个响应的语义评价

评价依据是预先固定原文/可接受解释与Coding AI源文复核，
不是Bolt自评，也不是独立人类盲审。语义不明确处保留PARTIAL/UNKNOWN。

| 维度 | 实测结果与限制 |
| --- | --- |
| Goal Understanding | H01/H02 PASS；H03 PARTIAL：方向基本保留，但“偏研究性质”被解作搜索方式；原文省略宾语，不据此判确定性错误 |
| Change Attribution | 3/3符合各自宽容的标签范围；均为同一方向的询问/细化，未覆盖三类真正变化 |
| Unsupported Inference | 未发现已确定长期Goal或外部事实的无依据断言；仅此3前缀 |
| Semantic Support | 6/6 quote逐字存在；H03完整语义支持PARTIAL，不能用quote匹配代替内容理解 |
| Abstention | H01 PASS；H02/H03 PARTIAL：对是否希望/需要执行搜索提出多余疑问 |
| Historical Consistency | H02/H03保留同一研究方向；H01单轮UNKNOWN；复杂切换/摘要传播尚未测 |
| Authority Integrity | PASS仅限研究隔离；0工具执行/0Goal采纳；未测试当前候选在正式Host中的拒绝路径 |

H02当前请求正确识别“指定google搜索ai agent development”，
但unknowns又写“用户是否允许或期望我执行联网搜索”；
H03也写“用户是否需要执行搜索”。
这是**过度弃答、语义请求与执行条件混淆的迹象**，不是未经授权操作，也不是已观察到真实Agent停滞。
原文已有搜索意向；本实验不执行工具不应被误作用户未提出行动要求。

可考虑的最小非侵入性改善（**HYPOTHESIS，未测试**）：
分别表达“用户已提出什么要求”“是否存在可用工具/合法执行条件”“真实执行了什么”。
不能靠Google关键词默认、替模型补执行事实或自动放宽授权解决。
本轮冻结的source_check提示也尚未执行，不能称改善已验证。

3个响应总输入1557 Tokens、输出469 Tokens；总壁钟约63.96秒，
输出Tokens/总响应时间约7.33/s，包含输入处理，不是纯decode测速。
单次14.55、24.14、25.27秒；没有流式TTFT测量。

## 6. 混淆分析与公平基线

四现象不被当作互斥枚举。已完成数据只支持：

- 无明确长期Goal：3个相关前缀均long_term_goal=null；
- 当前任务细化：H02/H03均输出task_refinement；
- Goal Change / Condition Change / Belief Update：**本轮0个相应实测真值案例，UNKNOWN**。

不能用“未发生错误Goal Revision”推导模型能识别真实Revision；
也不能把3个递增历史前缀当作3份独立长期能力证据。

上轮Fixed/Separated的16/16输入包含人工语义，**不与本轮原文识别做准确率对比**。
本轮另预定义Fixed Explicit与Separated的原文策略对照，保证相同来源、工具和输出契约；
它们是提示/表达方式对照，不是已训练不同认知模型。
Current Only是明确的历史消融，输入较少时允许无法识别，不能据此制造“Separated必胜”。
这些策略请求均未执行，排序与收益UNKNOWN。

## 7. 资源保护中断：证据与未解释部分

本次模型运行目录：
/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261104T000852Z-e1fb827a/

启动前no-model CHECK通过；阈值模拟和stale-heartbeat无模型子进程终止均通过后，才开始service。
保护维持：Dedicated48GiB、Windows Available6GiB、Commit剩余max(16GiB,20%)、
WSL Available4GiB、Swap256MiB、监控新鲜度3秒、控制调用截止时间及Fail-Closed。

**VERIFIED**：
guard.ps1的Linux metrics控制调用超过2500ms，记录
“Control timeout metrics; workload state unconfirmed”；
Windows心跳随后不再更新，独立guard_ctl监督器以WINDOWS_SENSOR_STALE终止模型组，
exit_code=-15、remaining=[]。第4次API请求收到RemoteDisconnected，无完整响应。
8000/8003无监听，GPU compute PID列表为空；不是仅凭前端退出判断清理成功。

| 采样指标 | 实际观测 |
| --- | --- |
| GPU NVML / WDDM Dedicated峰值 | 29.30 / 29.30GiB |
| WDDM Shared峰值 | 0.203GiB；不能与Dedicated相加当容量 |
| Windows Available最低 | 24.37GiB |
| Commit峰值/Limit；最小剩余 | 68.33/114.48GiB；46.15GiB |
| WSL Available最低 / Swap峰值 | 17.55GiB / 约0.0098GiB |
| 成功完成的采样最大耗时 | 0.327秒；不包含失败的metrics调用 |
| Windows native测量最大耗时 | 0.0164秒；本次不是CIM查询路径 |
| 停止后采样 | GPU约2.02GiB，Available26.06GiB，Commit41.04GiB |

共有156份资源样本、157条Windows心跳。完整统计见resource-summary.json。
停止后宿主指标未完全恢复到启动前，不能宣称所有内存立刻归还；无额外清缓存/重启。

**UNKNOWN**：
超时发生在wsl.exe→Linux Python/nvidia-smi控制调用边界，
现有记录不足区分WSL启动/IPC抖动、nvidia-smi延迟、调度或短时负载影响。
不能据此归因为Commit耗尽、CUDA OOM、CIM故障或Bolt语义失败；
成功采样有充足余量，也不证明缺失时间段所有风险均可排除。
后续postflight一次metrics成功，只说明该路径恢复过，不等于稳定性已验收。

冻结实验停止规则禁止监控失效后自动重启。本轮遵守，不更改超时或安全阈值绕过。
monitor-exception.json、service/state.json、final-cleanup.json、心跳与资源原记录均保留。

## 8. 权威、来源与复现边界

真实推理走本地OpenAI-compatible API；不是完整UAEA Harness/G0-G1交互验收。
客户端没有工具分发、Goal控制或Memory写入代码，模型提议只作为研究结果。
因此正式Host拒绝当前错误候选 **NOT TESTED**；
不能将不存在的接线当作Runtime成功拒绝。

既有G0/G1真实错误quote拒绝、Observation保留及合法决定不等于语义正确仍可作为历史基线，
但没有在本轮新响应中重演；详见[上轮实验报告](dynamic-goal-experiment-20261103.md)。
Compaction/复述不是新外部支持、来源≠语义支持≠真实性≠授权的原则保持不变，
本轮不估计统计独立、模型内部依赖或熵。

归档：
recovered-inputs.json与historical-source-manifest.json固定输入来源；
requests/、responses/、api-results.jsonl固定已提交请求和实际响应；
automatic-checks.json只做结构、标签范围及逐字引用检查；
semantic-review.json单独记语义评审，execution-coverage.json逐项列未测。
手动审阅不将模型自己的Confidence或标签作为唯一真值。

需要本机完整运行记录才能重新解析历史；Windows副本用于审计。
run_bolt.py拒绝覆盖已有响应日志，且启动/真实重放必须先恢复安全门禁；
本轮不附带自动再次加载或继续调用。

## 9. 最终判定与下一步最小建议

| 验收项 | 判定 |
| --- | --- |
| 原人工8轮文本及顺序恢复 | PASS（内容）；PARTIAL（旧身份登记） |
| 与Fixture区分、来源隔离、冻结评价 | PASS（限定） |
| 真实模型启动与首3次推理 | PASS（限定） |
| 完整语义/反例/多轮/基线验收 | BLOCKED / UNKNOWN |
| 可靠候选语义输入、动态Goal信息论建模前提 | UNKNOWN；证据不足以批准为语义基线 |
| 安全停止与进程清理 | PASS（实际中断） |
| 模型幻觉整体受控 | UNKNOWN，未被本轮证明 |

**回答核心问题**：目前不能根据这3个相近前缀认定Bolt足够可靠。
观察到的主要语义问题是过度弃答及请求/执行条件边界含糊；
但Goal Change、Condition Change、Belief Update及错summary的主失效机制仍未测，
不能用本次监控阻断给模型判能力FAIL。

下一步先局部定位现有metrics控制链路的延迟，保持阈值和Fail-Closed，
通过无模型监控/终止门禁后，再对冻结数据的剩余40个未完成项继续受控测试。
已完成3项保留为原结果；不要把重复运行当新的独立支持。
监控修复及再次启动不在本轮自动执行，需提交架构/安全评审；无需用户手工编写测试或进行对话验收。

在语义观察可靠性未明确前，不引入MDL、Bayesian、Goal Entropy或建议概率；
本轮无概率模型，也未计算任何有效bit。暂不接正式Goal Evolution或主动建议。

本轮仅新增隔离实验脚本、数据、日志索引和研究报告，并更新研究地图；
未修改Phase-1、Harness循环、Goal Adoption、Authorization、Memory Admission、依赖或系统设置。
旧工作区历史保留；无Commit/Push，完成后停止。
