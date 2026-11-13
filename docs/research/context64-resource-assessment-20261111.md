# 64K Context初步验证与64/64资源评估（2026-11-11）

**总体PARTIAL；容量VERIFIED，来源恢复失败保留。建议：64K可用但Commit余量偏紧。**
保持32K默认、64K显式实验、1GiB KV、64/64 UMA，不重启PC、不改任何停止阈值。
不建议现在切换长研究默认或扩大负载；56/72的收益UNKNOWN，本轮不提出重启要求。

## 1. 环境、准入与实际参数

- 当前Nemotron Bolt74B本地权重，vLLM0.32.0 / Torch2.13.0 / B12X1.5.1 / FlashInfer0.7.0.post1；NVIDIA驱动617.42；实际选择的Harness为codex-cli0.163.0。
- 开始时WSL处于Stopped，本轮只启动WSL并检查，没有重启PC、改变WSL配置或UMA。
- Windows原生初始Commit：16.507/83.481GiB，剩余66.974GiB；Available约47.84GiB，WSL约20.56GiB，Swap0。GPU NVML空闲约62.53GiB；PDH Dedicated约1.46GiB，Shared约0.05GiB。
- 原公式：剩余Commit减36GiB规划后，必须大于max(16GiB,CommitLimit/5)。停止余量16.696GiB，冷启动需剩余>52.696GiB；本次满足，额外规划缓冲14.277GiB。
- 现有无模型Guard检查通过；正式启动前GPU48GiB停止和失效心跳Smoke均通过。注入故障是模拟，不是设备实际越界。
- 隔离参数：max_model_len65536、max_num_seqs1、Eager、fixedKV1073741824、显式引擎规划38654705664、nonKV reserve34359738368、chunked prefill256。采样/Backend未调。
- gpu_memory_utilization仍0.6；固定KV路径不按它自动计算KV，现有独立N1X规划检查仍实际返回36GiB，budget-decisions记录准入和post_profile。不是靠利用率值宣称硬限制。
- 仅一次加载，90/90分片；服务就绪104.08秒。固定KV1GiB、引擎逻辑KV容量109817 Tokens；日志理论并发1.68x，实际仍限制1。
- 954个AC观察样本均online，0次切换；未发生NVML17或监控失效。

## 2. 有效窗口及预留

| 项目 | 实测/配置 |
| --- | --- |
| vLLM窗口 | 65536 |
| Harness声明/实际有效窗口 | 65536 / 62259 |
| 自动Compaction阈值 | 49152 |
| 阈值至服务窗口的配置预留 | 16384 Tokens |
| 阈值至Native有效窗口 | 13107 Tokens |
| Host恢复块 | 上限24000字节，实测最大23910 |
| 单条工具回执 | max_output_chars12000；不是整批上限，也不是Token数 |
| 独立长请求输出上限 | 192 Tokens |

窗口配置相容：Harness有效窗口保守低于服务窗口，不要求二者数值相等。25%预留由工具结果、Host恢复、压缩和输出共享，不能解释为独立输出配额。本轮每批四条工具结果，完成请求输入增量分别9653/9691/9924/10206 Tokens（含更新后的投影，不能当作纯正文Token数）；单条字符限制没有提供整批Token硬上限。Harness实际出站未增加max_output_tokens覆盖；本样本完整结束，不证明任意批量工具结果/任意输出都必然能容纳。Compaction阈值也不是Bridge后输入的硬上限。

## 3. 渐进式请求（全为本轮新记录）

冻结历史金融记录用于制造负载，混入单独标明的合成检索控制；旧模型文字不是新财务事实、授权或独立证据。使用/v1/responses，记录原始SSE、usage与自然完成状态。

| 真实输入Tokens | 输出Tokens | 首可见文本秒 | 总耗时秒 | 完整性/控制项 |
| --- | --- | --- | --- | --- |
| 34017 | 38 | 34.91 | 38.58 | completed + EOF，四键JSON及UNKNOWN正确 |
| 40016 | 44 | 40.00 | 44.28 | completed + EOF，四键JSON及UNKNOWN正确 |
| 48016 | 31 | 48.22 | 51.18 | completed + EOF，四键JSON及UNKNOWN正确 |

三档均超过32K，无Context Overflow、length截断或异常重复。单样本输入增长伴随延迟增长，不能由三次短输出测出稳定生成速度，也没有当前32K配对速度收益。首文本延迟约35–48秒、六轮中个别轮超过2分钟，是否符合实际交互要求仍属PARTIAL。

## 4. 真实Harness六轮压力回放

- 复用前次冻结六轮脚本和16个来源片段，源自interactive-32768-20261105-071627；不启动新联网研究或完整30轮Goal对照。
- 6/6同Thread完成，累计511.64秒；每轮47.62、67.94、90.61、113.13、168.44、22.86秒。
- 真实最大输入52296 Tokens，无超窗；1次自然Compaction，压缩请求44234输入/1019输出，完整结束。
- 11个Harness请求均complete_success，原始上下游字节一致，采集预算未超限；16次真实读取、16个不同文件，全部hash有效；80处重复供给的正文hash/来源版本检查通过。这80处不是80次独立观察。
- 压缩后没有新增read_section调用。来源核对：file1正确；file5、file9给UNKNOWN；file13误用file8的anchor；file99未提供且UNKNOWN正确。已知来源仅1/4正确，本样本来源恢复FAIL。
- 缺失第99来源的UNKNOWN是合理的；第5/9来源原件仍可通过只读工具取得，模型未实际恢复，因此不能将其UNKNOWN视为研究任务已完成。
- 错误首次见于第10个模型响应：上游capture 3ef02796-94ae-4257-b21b-227252812d19，已生成错误file13绑定，下游字节一致；不是Bridge重复/改写输出。
- 第9个压缩响应保留了按原顺序排列的16个anchor列表，但没有逐文件明确绑定表；第10请求中四个目标anchor仅见于该摘要。明确绑定的弱化与模型不重读/误归属并存，单一根因未隔离，不能断言只是窗口或模型问题。
- 第6轮SIM80/2.5=32正确、明确标为模拟；但声称目标anchor已完成不能代替实际正确核对。全部16文件确已在前四轮读取，任务的读取事实与来源归属正确性必须分开。
- ActiveGoal保持null；模型输出未升级为source evidence；Workflow完成未建立；不评价Goal演化或Memory收益。

## 5. 全程服务资源极值

采样极值包含加载和三个API请求及六轮回放，不含故障注入的伪数值；不是瞬时峰值保证，各内存域重叠，不能相加。

| 项目 | 全程实测 |
| --- | --- |
| NVML Used峰值 | 28.739GiB |
| Windows PDH Dedicated峰值 | 28.737GiB |
| PDH Shared峰值 | 0.189GiB |
| Windows Available最低 | 28.140GiB |
| Commit峰值/Limit | 63.345/83.481GiB |
| Commit余量最低 | 20.136GiB |
| 距原Commit停止线最小缓冲 | 3.439GiB |
| WSL Available最低 | 17.396GiB |
| Swap峰值 | 0.1406MiB |
| 有效service样本 | 727，失效0 |
| 单时钟因果新鲜度最大上界 | 0.109秒 |
| Linux采集最大耗时 | 2.617毫秒 |

三个长请求期间NVML峰值约26.29–26.31GiB，Commit最低余量分别22.421/22.435/22.449GiB；本次输入增大未伴随持续资源增长。全程更紧的Commit缓冲出现在加载阶段。不能由此保证更长会话没有泄漏、瞬时峰值或更高工作区需求。

原GPU48GiB、WindowsAvailable6GiB、Commit max(16GiB,20%Limit)、WSLAvailable4GiB、Swap256MiB、采样2秒/新鲜度3秒全部不变。Shared计数不能证明所有CUDA共享分配均已覆盖；Windows物理/Commit保护仍独立生效。

收尾为主动CONTROLLER_STOP，owned进程和采样器remaining=[]，Native进程组absent，8000/8003无监听。原Guard会把该手工结束写为Safety stop异常，但primary_sensor_failure=null、resource_stop=null、没有遥测或内存故障；保留原日志，不把它当成真实保护触发。

## 6. 判定与建议

| 问题 | 判定/证据范围 |
| --- | --- |
| 64K启动、真实>32K、1GiB KV | VERIFIED / 限定PASS |
| 本轮资源保护和传输完整性 | VERIFIED / 限定PASS |
| Compaction自然触发、压缩请求完成 | VERIFIED |
| 压缩后来源映射和任务语义完成 | PARTIAL，来源核对1/4，失败保留 |
| 相对32K是否减少压缩/超窗/延迟 | UNKNOWN，本轮没有32K配对，不拼接旧数据 |
| 长时稳定性/64K窗口边界饱和 | UNKNOWN，未测试小时级会话或65536上边界 |
| 56/72是否改善实际安全余量 | UNKNOWN，未更改/重启/对照 |

选择“64K可用但资源余量偏紧”：保留64/64和显式64K入口，32K继续默认。现有1GiB KV足够本次负载，无扩容依据。GPU Dedicated并非当前最紧约束，Commit缓冲和压缩后的来源使用更值得关注。

不建议凭本次容量结果立即安排56/72：尚不能把重新分配的物理内存直接等同于Commit改善；现有Guard和准入还明确绑定64GiB布局，变更需独立评审。无需本轮重启PC。

容量证据支持后续限定稳定性验证的可行性，但应先评审仅3.44GiB最小Commit缓冲和来源失败，再决定是否追加。当前不扩大负载、不启动30×2、不切换正式默认。

## 7. 复现、变更与证据

证据根：/home/wqkan_wsl/uaea-n1x/research-records/capacity64-resource-20261111T115509Z

隔离入口：65536/start.sh；progressive.py为三档API测试；capacity_driver.py复用现有ScenarioApp与Harness，未新增Agent Loop。run-experiment.py只允许一次加载，无失败重试。

preregistration.json / input-lock.json / frozen/source-lock.json绑定协议、来源、脚本和131个当前源码文件；harness-version.json记录实际二进制版本，环境和模型元数据见final-summary.json。12个原启动文件和131项正式源码hash前后未变；git diff --check与研究脚本compile通过。未重复运行全量回归，不沿用其PASS数作本轮新结果。

新增内容仅隔离研究脚本/证据、本报告和研究地图索引；不修改正式Runtime/Harness/Goal/Memory或模型依赖，不Commit/Push。原历史批次不覆盖。

progressive/*/{request,events,result}.json及raw.sse：三档真实usage和完整性；
65536/replay/{model-http-audit,app-server-events,execution-contract.trajectory}.jsonl：原生执行与出站来源；
source-context-slices.json / source-recall-evaluation.json：负面来源案例及期望映射；
final-summary.json / token-budget-audit.json：资源、窗口、Token与回执；
preflight-guard.json / 65536/owned-service.json：Guard原始路径，含采样、保护Smoke和cleanup。

完成本轮初步评估后停止，提交架构评审。
