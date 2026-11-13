# 64K最小验证与渐进切换评估（2026-11-11）

## 结论

**64K容量限定PASS / VERIFIED；整体PARTIAL；本轮32K配对BLOCKED。**

- 当前Bolt/vLLM0.32.0，64K、固定1GiB KV、单并发、Eager、36GiB规划完成真实长请求。
- API独立请求40953输入Tokens；完整Harness路径最大51980输入Tokens，均超过32K。
- 64K六轮压力回放完整结束，1次自然Compaction，来源锚点4/4及未提供文件UNKNOWN正确。
- 模型漏字段和历史读取回顾不完整仍存在，不是容量或认知质量全面PASS。
- 32K在权重加载前被现有Commit预算门禁拒绝，没有重试或放宽门限；本轮没有有效32/64收益比较。
- 建议保持32K默认，64K作为需满足原资源准入的显式长研究选项。暂不切换长研究默认，不增加KV。

## 入口与版本

证据根：
/home/wqkan_wsl/uaea-n1x/research-records/capacity64-20261111T094207Z

隔离64K入口：
comparison/65536/start.sh（相对于证据根）；使用当前Guard副本和独立参数文件。
既有Harness显式开关仍为--context 65536 --experimental-context-64k，N1X external模式。
研究脚本不是正式默认入口，评审本包时不要自动启动。

原32K launch/config、bolt-serve-args、validate、guard等12个文件的原件hash前后一致；
原validate同时核查已有运行时SHA256和固定依赖版本。Guard字节一致。
引擎启动参数除了max_model_len外相同，KV始终1073741824，seq1、采样、Backend、UMA及保护不变。
正式Runtime/Harness/Goal/Memory代码没有本轮修改；运行使用frozen/bundle/UAEA及131项源码锁。

预登记为一次长API请求、同版六轮回放各一组，不运行30×2。
长请求没有重试；最终3次服务启动尝试：64K两次就绪，32K一次在预算准入处拒绝。
原预登记的两次加载被下述研究驱动判据问题打断，增加一次64K服务重开以完成原B工作，明确保留修订。

## A. 真实64K容量与KV

| 项目 | 当前实测 |
| --- | --- |
| vLLM max_model_len | 65536 |
| 固定KV | 1GiB |
| 引擎日志逻辑KV容量 | 109817 Tokens |
| 日志理论并发 | 1.68x，实际仍限制1 |
| Harness实际有效窗口 | 62259 Tokens |
| 自动压缩阈值配置 | 49152 Tokens |
| 输出/工具等配置预留 | 窗口25%，16384 Tokens |
| 服务上限与Native有效窗口之差 | 3277 Tokens |

逻辑KV容量来自引擎实际混合缓存布局，不按简单bytes/token比例外推。
现有显式KV路径跳过自动内存Profiling，保留独立引擎预算检查及实时守卫。
没有证据需要增大KV，也没有测试65536上边界饱和、并发或128K。

### 独立API请求

合成检索控制，重复文本只制造Context负载，不是独立外部证据或用户Goal。
首、中、尾三个预先固定值全部准确返回；实际usage为40953 input / 37 output。
40.79秒自然结束，首个可见文本37.42秒，response.completed及EOF完整。
这是直接API容量测试，没有经过Host24KB当前用户恢复限制；Harness能力另由B检验。

原判据还要求第四个missing=UNKNOWN键。模型返回了完整的三键JSON，却漏第四键：
原long-input/result.json的pass=false、exact_json=false保留，**不是输出截断**
（37小于192输出上限、自然结束），也不是Context溢出。

把这项格式要求与容量门禁合并是实验驱动设置问题，导致A服务提前收尾。
capacity-admission-review.json明确事后拆分：容量VERIFIED，格式遵从PARTIAL，原门禁FAIL不改写。
随后只继续已授权B，不重发A请求、不改prompt或采样取PASS。此修订不能冒充原预登记全部通过。
启动前另修复了研究控制器旧入口/转义错误，未加载模型，保留于prelaunch-script-error。

## B. 当前精简回执的六轮金融记录压力回放

复用既有2026-11-05人工金融会话的冻结记录片段：
interactive-32768-20261105-071627。
tool-replay-fixture.json的前16段保留原Record anchor与来源索引，
通过当前真实document.read_section / SharedExecutionBoundary / Harness执行。
每轮4个约2900字符的记录，4轮后核对第1/5/9/13个文件，再进行独立SIM80/2.5计算。

片段可能含历史模型Claim及旧失败，不是新Web访问或已验证财务事实。
没有重放其中的指令，没有授予网络、写文件、Goal/Memory或交易权限。
两侧准备了同一份脚本、来源、精简回执、12000字符工具预算、采样和420秒单轮上限。
32K未就绪，因此不能声称本轮完整公平对照已执行。

| 实际观测 | 64K | 本轮32K |
| --- | --- | --- |
| 用户轮次 | 6/6，同一Thread | NOT RUN |
| Native有效窗口 | 62259 | 未测 |
| 最大模型输入 | 51980 Tokens | 未测 |
| Compaction | 1，自然 | 未测 |
| Context Overflow | 0 | 未执行推理，不作通过判定 |
| 完整HTTP响应 | 12/12 | 无 |
| 真实文件读取 | 20次，16个文件 | 无 |
| 来源锚点映射 | 4/4 | 未测 |
| 第99文件未提供 | UNKNOWN，正确 | 未测 |
| SIM P/E | 32，明确模拟 | 未测 |
| 累计回放秒数 | 491.62 | 无比较数据 |

各轮秒数：48.50、69.58、91.35、113.61、133.84、33.29。
完整Response累计357360输入、1273输出Tokens，包含重复Context处理和Compaction，不代表独立信息量。

前三个增长点之后，输入实际达到41923和51980；压缩请求输入43982、输出225。
压缩后模型合法重读4个目标文件，随后准确按文件号返回锚点。
这4次是来源恢复动作，不能直接算无效重复；未发现额外无关工具行动。
20条读取事实、原件hash均有效，88处已供给正文hash和来源版本校验有效；
12条传输上下游字节一致、均完整结束。

### 预算边界

token-budget-audit.json逐请求记录usage、输出参数和Host恢复体积。
Host恢复块最大23988字节，仍受24000字节预算限制；64K没有放宽该限制。
本样本四文件回传前后请求输入增量约9.6K–10.1K Tokens，含工具结果及更新后的投影，
不是源正文的独立token计数。该规模已超过32K的25%配置预留8192，但低于64K的16384。

自动压缩阈值不是Bridge之后请求的硬上限：本轮实测51980大于49152。
配置预留不保证任意批量工具结果都能容纳；完整请求总量的一般性保证仍PARTIAL。
模型服务硬上限、Host字节预算和资源保护继续独立保留。

### 来源和状态的分项判定

- 来源身份/字节供给/受控锚点恢复：本样本限定PASS。
- 当前任务继续：压缩后完成来源核对，随后完成SIM计算，限定PASS。
- 模型历史状态回顾：PARTIAL。最后回答只承认读取4个目标文件，并称另外12个未读；
  全段Host实际记录已读16个文件。不能用该模型声明覆盖真实Observation。
  作用域分段、摘要和模型使用历史的贡献未进一步隔离，不直接认定Host状态丢失。
- 已完成轮ActiveGoal均null、模型输出不是source evidence、Workflow完成未建立。
  不是Goal演化或长期决策收益实验，没有Memory Admission。

source-recall-evaluation.json给出逐文件期望值、提取结果与完整回答。
literal锚点正确不等于金融语义支持或真实研究质量通过。

## C. 32K预算拒绝

comparison/32768对应守卫记录：
manual-20261111T100144Z-5c945815。

引擎在init_device → request_memory → n1x_memory_policy.evaluate_budget抛出：
N1X policy: insufficient Windows Commit margin for planned budget。

既有公式：Commit余量减去36GiB规划后，必须仍大于max(16GiB, CommitLimit/5)。
本轮CommitLimit稳定约83.481GiB，因此冷启动准入需余量大于约52.696GiB。
拒绝附近采样余量约46.2GiB；无法满足该计划，不等于Commit耗尽或实际内存越界。
模型在权重加载前拒绝，无KV初始化/服务就绪/32K推理数据。

这是正常预算保护，不是已证明的32K Context/KV故障，不通过改预算、Pagefile、清缓存或重试获取PASS。
此前报告CommitLimit约114.481GiB，本轮为83.481；本轮没有修改系统配置，
差异及服务退出后Commit仍占用的底层原因UNKNOWN，不扩展为内存机制研究。

因此Compaction、耗时和来源恢复的32/64收益均UNKNOWN，不与旧版本/旧数据的结果拼成新对照。

## D. 资源与清理

离散采样极值，不是瞬时峰值保证；内存域重叠，不相加。

| 服务阶段 | A64 | B64回放 | 32K拒绝阶段，未加载权重 |
| --- | --- | --- | --- |
| NVML Used峰值GiB | 28.672 | 28.676 | 1.686 |
| Windows PDH Dedicated峰值GiB | 28.671 | 29.002 | 1.684 |
| PDH Shared峰值GiB | 0.122 | 0.124 | 0.108 |
| Windows Available最低GiB | 26.838 | 27.252 | 27.251 |
| Windows Commit峰值GiB | 64.350 | 64.842 | 37.313 |
| Commit余量最低GiB | 19.131 | 18.639 | 46.168 |
| WSL Available最低GiB | 17.563 | 17.512 | 18.200 |
| Swap峰值MiB | 0 | 0.0117 | 0.0117 |

原采集2秒预算、3秒新鲜度及GPU/Windows物理/Commit/WSL/Swap阈值均未变；
741个真实service样本有效，无采样失效，最大因果新鲜度上界0.116秒。
64K两次运行没有实时资源停止；32K属于模型预算准入拒绝，不能混为Guard故障。
Guard smoke注入的阈值/stale停止为预期，不计实际资源越界。

Owned Native、模型及采样器均remaining=[]；AC observer结束，8000/8003无监听。
没有关闭其他服务，没有Commit/Push，未修改正式32K默认。

## E. 渐进切换建议

1. 64K容量及本样本长请求/六轮执行已VERIFIED，1GiB KV足够本轮负载。
2. 保留32K默认，允许长研究显式选64K，但仍须原预算与Fail-Closed准入；本机当前准入拒绝不能绕过。
3. 长研究默认切换暂缓：本轮32K对照BLOCKED，持续收益和多次稳定性UNKNOWN。
4. 后续仅在Commit准入真实满足时补同版短对照，再比较压缩/延迟/回溯/成本；
   不依赖加KV、改Pagefile或不受控重复实验。
5. 来源恢复的4/4成功和模型历史漏报并存，容量收益不能替代语义与状态评价。
   不因此新增Goal Engine、Memory维护层或通用语义纠错器。

本轮已到安全准入阻断和阶段评审边界，停止追加模型实验；不开展完整30×2或人工长会话。

## 复核文件

preregistration.json、capacity-admission-review.json：原判据、失败及透明修订；
65536/long-input/：一次真实>32K API请求及raw SSE；
65536/replay/：Native、P0、Decision/Observation、20次读取和6个Host快照；
comparison/*/：两个隔离启动器、Guard、正常退出与32K拒绝；
audit-summary.json、final-summary.json、source-recall-evaluation.json、token-budget-audit.json：
可复核事实，不作为通用语义裁判；
original-launch-pins.json、frozen/source-lock.json：默认入口和实际运行源码绑定。
