# N1X GPU56/Host72：隔离64K真实负载与历史64/64对照（2026-11-11）

**资源/容量限定PASS（VERIFIED），整体PARTIAL。56/72本轮安全余量明显更好，原生API长请求未见明显退化；Harness回放更慢且存在重复读取。**
建议保留56/72显式实验配置，提交后续长时稳定性验证评审；不自动切正式默认、不恢复30×2，不将资源收益当作Goal认知收益。

## 1. 授权适配、隔离与实际预算

- 按用户本轮明确批准，仅实验入口使用56GiB容量身份校验及gpu_memory_utilization=0.65。36GiB显式规划、1GiB KV、64K、单并发、Eager及全部资源停止规则不变。
- 原32K入口、历史64/64入口仍为0.6。已安装N1X策略仍要求64GiB，文件未改；新实验入口通过进程私有PYTHONPATH包视图，只替换一份56GiB校验策略，其余110个链接指向同一既有vLLM安装。
- 父进程与spawn子进程CPU探针均解析到实验overlay策略。真实引擎post_profile记录NVML总量56GiB且通过预算校验，和已安装64GiB策略不能接受56GiB的行为相区分。没有重建/升级Runtime或复制Agent Loop。
- 单时钟无模型Guard检查通过；GPU48GiB模拟停止及监控失效模拟停止均通过后才加载。模拟故障不计真实资源越界。
- 唯一一次加载，90/90分片，服务就绪116.09秒。actual_admission实际返回38654705664字节；post_profile再次确认budget36GiB、fixedKV1073741824、nonKV bound32GiB。
- 引擎KV逻辑容量109817 Tokens；理论1.68x，实际仍限制并发1。日志确认显式1GiB KV跳过自动内存Profiling，0.65没有用于自动扩大KV。
- 原生CUDA Total109.717GiB与NVML Dedicated56GiB分开保留，实际独立引擎预算仍为36GiB，不是仅靠利用率值宣称预算。
- 原GPU48GiB、Windows Available6GiB、WSL Available4GiB、Swap256MiB、采集2秒/新鲜度3秒全部不变。Commit仍为max(16GiB,20%Limit)：当前Limit91.481GiB，所以自动得到18.296GiB；历史16.696GiB对应旧Limit83.481，不是手工降低/提高阈值。

## 2. 硬件、版本和历史对照限制

当前NVML容量56GiB、DXGI Dedicated55.986GiB、Windows可见物理70.481GiB，符合GPU56/Host名义72。
vLLM0.32.0、Torch2.13.0、B12X1.5.1、FlashInfer0.7.0.post1、Codex0.163.0及固定本地Bolt权重不变。
驱动当前621.14、历史617.42；利用率数值的兼容差异已获批，但也必须披露。因此是独立新批次与历史对照，不是严格单变量A/B。
历史：/home/wqkan_wsl/uaea-n1x/research-records/capacity64-resource-20261111T115509Z
本轮：/home/wqkan_wsl/uaea-n1x/research-records/uma56-load-20261111T132628Z

DXGI诊断进程Local Budget109.717GiB、Nonlocal Budget0、Shared描述符54.481GiB；这些不是WSL可分配保证或整机使用量。实际PDH Shared另见资源表，不与Dedicated/CUDA相加。

## 3. 逐级冻结API请求

直接复用历史三个request.json，原始请求字节hash完全一致，usage输入及输出Token数也一致。没有改Prompt、采样、Model或输出上限192。历史金融内容仅为负载材料，可能含旧Claim，不作为新财务事实。

| 实际输入/输出Tokens | 历史64/64总秒 | 本轮56/72总秒 | 本轮首可见文本秒 | 完整性 |
| --- | --- | --- | --- | --- |
| 34017 / 38 | 38.58 | 38.20 | 34.71 | completed+EOF、JSON四键和UNKNOWN正确 |
| 40016 / 44 | 44.28 | 42.87 | 39.10 | completed+EOF、JSON四键和UNKNOWN正确 |
| 48016 / 31 | 51.18 | 50.45 | 47.62 | completed+EOF、JSON四键和UNKNOWN正确 |

三档均无Context Overflow、length截断、传输错误或异常重复。此小样本未见原生长请求明显性能退化；轻微耗时差不证明GPU56更快，也没有足够重复测量估计稳定吞吐或统计置信区间。

## 4. 六轮真实Harness压力回放与负面行为

- 同一Thread完整6/6，实际最大输入53196 Tokens，超过32K且达到约52K目标。有效窗口62259，声明65536，自动压缩阈值49152。
- 预留16384 Tokens按服务窗口计算；按Native有效窗口剩余13107，供工具结果/Host恢复/压缩/输出共同使用，不是每项独立配额。单条回执12000字符不是整批Token上限；Host24KB限制未放宽，最大恢复块23988字节。
- 14个Harness HTTP请求均complete_success、上下游字节一致、采集预算未超限；加3个直接API共17个完整推理请求，不含tokenize/health。历史同一基线为11+3=14，不拼接为新批次。
- 实际36次成功read_section、16个不同原件；全部原件hash有效，104处重复供给的正文hash及版本一致。重复记录不是独立新观察。
- 本次目标file1/5/9/13锚点4/4正确，file99未提供且UNKNOWN正确；SIM80/2.5=32并标明模拟。字面来源核对成功不证明财务研究质量或通用语义支持。
- 第一轮Compaction前已完成16个文件读取；压缩后模型再次调用工具读取全部16个文件。这16次是可追溯的重复执行，不能计作新信息或隐藏为成功。
- 第二次Compaction后，为当前来源核对重读4个目标文件，属于有目的的恢复动作；共20次重复引用中这两类行为必须分开。
- 两次Compaction完整结束：输入/输出分别45638/1129及45256/547 Tokens。第4轮348.77秒，未超原420秒Turn上限；没有因耗时长而调参或重试。

| 回放观测 | 历史64/64 | 本轮56/72 |
| --- | --- | --- |
| 累计回放秒数 | 511.64 | 805.58 |
| 用户轮次 | 6 | 6 |
| Compaction | 1 | 2 |
| 真实读取 / 不同文件 | 16 / 16 | 36 / 16 |
| 请求输入Tokens累计 | 326691 | 425966 |
| 输出Tokens累计 | 1830 | 4324 |
| 目标来源映射 | 1/4 | 4/4 |

累计Token含重复Context和压缩，不代表有效信息量。回放变慢与不同模型行动轨迹、额外读取/压缩、输出增加并存；前四组原始工具调用各输出362 Tokens，历史为158，因为这次生成绝对文件路径。不能将整段耗时增加直接归因GPU容量缩小。

重复读取由原始模型响应提出，Host按既有权限真实执行。摘要/Context投影/模型行为的贡献未做进一步消融，不把它简化成某一组件的唯一根因，更不在此扩展Goal或语义纠错架构。

各轮秒数：63.23、83.99、107.26、348.77、158.97、42.22。Task在压缩后继续并完成核对/SIM，但执行效率PARTIAL；ActiveGoal保持null、模型输出未升级为source evidence、Workflow正式完成未建立。

## 5. 全程资源极值

下表分别取各独立批次的service采样，包括加载及所有负载、排除故障注入；不是瞬时峰值保证，也不是同一宿主背景下的严格因果实验。

| 采样指标 | 历史64/64 | 本轮56/72 |
| --- | --- | --- |
| NVML Used峰值 | 28.739GiB | 28.522GiB |
| PDH Dedicated峰值 | 28.737GiB | 28.519GiB |
| PDH Shared峰值 | 0.189GiB | 0.174GiB |
| Windows Available最低 | 28.140GiB | 36.878GiB |
| Commit已用峰值 | 63.345GiB | 62.282GiB |
| Commit余量最低 | 20.136GiB | 29.199GiB |
| 距Commit停止线最小缓冲 | 3.439GiB | 10.903GiB |
| WSL Available最低 | 17.396GiB | 17.582GiB |
| Swap峰值 | 0.141MiB | 0.137MiB |

Commit Limit由历史83.481到本轮91.481GiB；最低余量增加9.064GiB，停止线缓冲增加7.464GiB。
这是当次资源改善的事实。算术上余量差来自Limit多8GiB及观测峰值已用少1.064GiB；但较低峰值的原因及驱动/后台差异贡献UNKNOWN，不能作单一硬件因果断言。
本轮1025个有效service样本、失效0；单时钟新鲜度最大上界0.119秒，Linux采集最大4.696毫秒；1111个AC样本全online，0次切换。未出现真实资源越界、NVML17或遥测Fail-Closed。

本轮结束为主动CONTROLLER_STOP、owned模型与采样器remaining=[]，Native进程组absent；8000/8003无监听。Guard原日志把该主动结束写为Safety stop，但resource_stop和primary_sensor_failure均null，不能当成资源失败。

## 6. 分层判断与建议

- **资源分配收益 VERIFIED / 限定PASS**：观察到更大的Windows物理余量和Commit缓冲；Dedicated占用仍远低于48GiB提前停止线，Shared未明显增加。
- **64K推理能力 VERIFIED / 限定PASS**：同字节三档长API及53,196 Tokens真实Harness请求完成，1GiB KV足够本轮，未观察明显原生API性能退化。
- **长任务执行效率 PARTIAL**：多一次压缩、重复读取及更多输出带来更长回放；不能宣称56/72让整段研究更快。来源恢复成功有额外执行成本。
- **长期适用性 PARTIAL / UNKNOWN**：仅一次约18分钟服务运行，不证明小时/天级稳定性；未做电源拔插，不证明驱动异常消失。

建议选择“本轮资源层面56/72明显优于历史64/64，值得进入下一阶段长时稳定性验证”，同时保留端到端Workflow PARTIAL、驱动与轨迹差异。不是认定所有任务或正式配置全面更优。

本轮不再扩大负载、不修改32K默认、不自动开展30×2。当前56GiB硬件如需运行，应显式使用此实验入口；原64/64启动原件保留用于对应硬件布局回退，不能把其原有64GiB身份检查当成已适配当前56GiB。

## 7. 变更、复现与证据

15项原启动/监控/已安装策略原件hash未变，131项正式UAEA源码hash未变；输入锁无变化。原32K和历史64K参数仍0.6，本实验独立0.65。未Commit/Push，未改BIOS/UMA/Pagefile/WSL配置。

实验入口：65536/start.sh；只设置本进程树PYTHONPATH，退出后不污染其他入口。overlay-links.json记录110个只读链接，唯一策略副本及应用Diff随包提供；默认安装没有需要回滚的改动。脚本依赖当前已有模型/venv，评审时不要自动启动。

仅做相应compile、父/子模块隔离、原Guard smoke、真实负载及源hash/传输审计，未复跑全量回归，不沿用旧测试计数作为本轮结果。

主要证据：
- adaptation.json / applied-isolated-adaptation.diff / overlay-probe.json：限定适配和隔离证据。
- 65536/engine-verification.json / Guard budget-decisions.jsonl：实际36GiB规划、1GiB KV、NVML56。
- frozen-requests/*/request.json / progressive/*/{events,result}.json / raw.sse：与历史字节一致的三档请求。
- 65536/replay/：原生Turn、P0出站/传输、实际Observation和Compaction。
- comparison.json / source-recall-evaluation.json / interim-output-costs.json：分项比较和负面行为。
- final-summary.json / token-budget-audit.json / final-integrity.json：资源、Token及原件不变性。

本轮完成后停止，提交用户评审；不自动切换正式入口或进行后续长时实验。
