# 能力投影、完整传输审计与金融长对照恢复（2026-11-11）

**总体 PARTIAL**。工程修复限定 PASS；短场景准入限定 PASS、模型质量 PARTIAL；
新长批次 History 13/30，Goal 长组 NOT RUN。未提高 Goal Cognition 成熟度。

## 1. 范围、版本及复现

本轮处理 Shell 能力虚报、预置 SIM 说明和 HTTP 完整传输判据。
未改变 Goal/Memory 采纳、执行权限、Provider Policy、模型依赖或资源门限。
Harness 仍拥有执行循环；研究控制器只按冻结脚本发送输入、等待和清理。

本轮原始记录：
/home/wqkan_wsl/uaea-n1x/research-records/capability-finance-20261111T010429Z（以下称 B）。
前一批 finance30-acstable-20261110T235223Z 独立保留，不与本轮拼接。
基准 HEAD：125f0d2a8e6b7ac0f6b70baf9913b942be2b1cb2。
用户原有未提交内容未丢弃。本轮增量以 B/before 为准，整个 HEAD Diff 不能归为本轮。

- B/input-lock.json：执行前307个输入/源码文件哈希，执行后全部匹配。
- B/short/frozen.json、B/long/frozen.json：分别10/20项锁定，均匹配。
- 新长组原金融场景、时间约束、SIM版本和释放时点保留，不改写原30轮用户文字。
- 会话保留 run-manifest、实际 config.toml、源码摘要、原生事件及 P0 审计。
- 隔离 bundle 无Git元数据，manifest的HEAD/dirty为null。外层HEAD、git-before.txt、
  逐文件hash及input-lock共同绑定版本，不能据null宣称工作树干净。
- 32K服务、1GiB固定KV、36GiB规划、Eager、单并发、64/64 UMA保持。
  Harness配置窗32768，原生Usage有效窗31129，自动压缩线24576。
- 资料为冻结官方摘录与明确标记的研究者SIM；未声称执行实时行情检索或真实交易。

## 2. 最小工程修复

### 能力投影 — VERIFIED（限定配置）

harness/io_contract.py 原硬编码 native Shell=True。现在使用实际Harness的
features.shell_tool / unified_exec，并独立描述sandbox模式：
关闭、启用但只读、工作区写入条件分别表达；缺少明确配置为UNKNOWN，不默认可用。
动态document/Web与原生Shell是不同执行面。

scripts/h3_harness_interactive_repl.py 将真实codex-home/config.toml及实际read-only模式
传入两条Context发布路径。本轮实机两个Shell flag均false，CLI只覆盖模型base_url；
实际P0显示native_shell.available=false。未增加工具或写权限。
单元测试覆盖关闭、只读、工作区可写及未知配置。

### 预置文件说明 — VERIFIED（隔离研究路径）

scripts/research/longitudinal_dialogue.py 通过现有AdditionalContext发布一个可替换的
uaea.research_fixture块：文件由研究驱动预置，只需已有只读工具读取，无需创建或修改。
只列当前已释放文件的路径、hash和可用轮次，不注入正文、数值或未来文件。
文件存在、目录展示、正文真正读取分别记录。冻结长脚本未改写。

短脚本还明确“已预置、无需创建”。短验证因此只证明
**能力修复 + 通用fixture说明 + 短脚本说明的组合条件**，不归因于单项修复，
也不证明模型普遍稳定。

### 完整传输审计 — VERIFIED（传输层）

harness/request_audit.py 与 responses_bridge.py 记录response_started、upstream_eof、
bytes_received、实际下游成功写入的bytes_forwarded、response_complete及transport_error。
先发transport_started，结束时再发transport_result。

完整HTTP成功必须有真实EOF、无异常、收发字节一致。HTTP200或收到部分字节不够。
BrokenPipe/ConnectionReset在响应后为partial；没有最终事件为UNKNOWN；
旧记录没有EOF/forwarded证据也为UNKNOWN。
HTTP完整转发不等于SSE语义成功、模型使用信息、原生Turn完成或Workflow完成。

harness/delivery_audit.py、Goal/Longitudinal审计据此区分投影准备、内容hash正确和完整传输。
部分传输不能通过供给门；后续一次失败不会抹掉此前已发生的有效完整供给。

B/historical-transport-reclassification.json另存旧批次重分类，不覆盖旧日志：
旧History36条、旧Goal8条缺新闭合证据，均UNKNOWN；
旧Goal请求9b8c3718-5ace-4e7f-8620-3b4229a25db4为BrokenPipe partial。
不否认另有原生完成事件，但不能继续将它们全计作完整HTTP成功。

## 3. 回归与反例

- B/scoped-regression.json：729项，727 PASS、2 SKIP、0 FAIL/ERROR。
- B/final-target-tests.log：最终针对性89项全PASS，含真实loopback TCP在HTTP200后复位的负例
  及正常EOF正例。
- 覆盖forged complete、字节不一致、无EOF、旧HTTP200、连接前失败、fixture替换、
  正文不偷渡和真实生成配置。
- 首次完整发现套件原样保留在B/full-regression。10项Memory测试缺旧个人语料/附件：
  tests/test_resources/UAEA_phase-1-benchmark-phase.json，以及
  tests/test_resources/chatgpt_personal_selected_2026-08-24。
  未补造、修复或隐瞒；限定套件逐项列明排除，不能表述为全项目无条件PASS。
- 真实配置相关期望测试已更新。Memory源码未改；Phase-1子模块干净。
- 最终git diff --check另存，无Commit/Push。

## 4. 两个短场景：真实Bolt + Harness

固定的合成控制，4个独立Thread，总计10个用户轮次。
语义标准来自冻结脚本与确定性计算，非被测模型自评。

| 场景 / 组 | 完成轮数 | 实际读取 | 指定结果 | Goal状态 |
| --- | ---: | ---: | --- | --- |
| SIM更新 / History | 2/2 | 2 | v1:50÷2=25；v2:50÷1.25=40 | 无候选、无提案 |
| SIM更新 / Goal Shadow | 2/2 | 2 | 同上，标明SIM与版本 | 无候选、无提案 |
| 持续方向改变 / History | 3/3 | 1 | 理解投资机会→可审计研究方法，随后读取v2并计算40 | 明确未提交/未保存 |
| 持续方向改变 / Goal Shadow | 3/3 | 3 | 同上，含一次多余重读 | 明确未提交/未保存 |

原始证据在 B/short/<id>/app-server-events.jsonl、execution-contract.trajectory.jsonl、
model-http-audit.jsonl；逐轮答案/调用在B/short-evidence.json。
17/17请求有完整传输闭合；普通P0各有一个fixture块、Shell=false；
8次成功只读Observation，正文供给审计PASS，无创建/写入工具尝试。

**限定准入PASS，不等于认知PASS。** Goal组没有形成种子、修订或生命周期。
本轮只能验证合理不提交及状态诚实。
History SIM将EPS从2降到1.25写为下降40%，正确37.5%；
History方向场景P/E分母措辞不准，但50/1.25=40正确。
保留为Model Behavior反例，不增加金融规则或通用语义裁判。

原生累计Usage（不是独立账单或收益估计）：

| 组 | 两场景总Token | 其中输出 | 文档读取 | 完成轮次等待时间合计 |
| --- | ---: | ---: | ---: | ---: |
| History | 90,288 | 1,361 | 3 | 209.855秒 |
| Goal Shadow | 124,330 | 1,806 | 5 | 282.664秒 |

只有一次小对照；Goal多34,042 Token（约37.7%），没有显示增量行为价值。
不足以推出长期负收益或接口优劣。B/short-review.json保存有限准入理由。

## 5. 新金融长批次：PARTIAL

History在同一Thread完成13/30，第14轮已发送但未获原生terminal。
Goal长组 **NOT RUN**。未拼接旧批次、未自动重试。

- 1次自然Compaction。
- 9次真实read_section：3成功（ledger、Intel官方摘录、Alphabet官方摘录），6失败。
- 成功来源/摘录hash及释放时点一致；6个已释放文件字节/版本匹配。
- 18个HTTP请求完整转发，最后第19个只有transport_started、无最终闭合，UNKNOWN。
- 最后观察累计Usage为333,755 Token，输入326,976/输出6,779。
  包含中断前累计事件，不能当成30×2成本对照。
- 前13轮仍有单位换算、财务解释和文件计划措辞错误，未转为Runtime通用纠错目标。

### 第14轮失败链

B/compaction-path-case.json提供原始文件、行号、request/call/turn ID。

1. Compaction生成的派生handoff summary出现sandbox/ledger.md、
   sandbox/sources/official-intc.md、sandbox/sources/official-googl.md。
2. 压缩后P0 sequence18，request_id=b2550c3e-e53a-4616-bff6-e121f9e87414，
   同时含正确的Host filesystem根、fixture绝对路径/hash及Shell=false；
   HTTP完整转发67854字节。不是仅“准备注入”日志。
3. 随后模型六次按sandbox/...读取ledger、official-intc、official-googl、
   intc-v1、intc-v2、paper-cash-v1。Shared保留失败，没有生成成功读取或完成事实。
4. 冻结Sandbox._candidate将相对路径基于sandbox_root解析，
   多出的sandbox前缀指向.../adapter/sandbox/sandbox/...。
   read_path对不存在/不可读路径的通用错误为outside allowed files。
   这不是新Provider拒绝、不是需要写权限，也不构成扩大允许目录的依据。
5. 请求19虽保留正确Host引用与失败回传，仍无最终传输/原生终止。
   控制器因本轮未结束停止研究，并清理自己拥有的服务。

**VERIFIED**：错误路径在模型派生摘要和后续调用中，正确Host引用已送达，
失败已回传。**HYPOTHESIS**：模型优先沿用了摘要路径。
不能恢复隐藏思维依赖，不能断言摘要是唯一原因。
没有证据证明权威Goal/Evidence被污染，没有Context溢出或资源越界证据。
这是派生Context/模型工具恢复反例，不是已证明的Goal架构冲突。

### 实验配置偏差

B/preregistration.json写自动单轮420秒，实际Runner硬编码180秒且本轮command未覆盖；
manifest与turn-lifecycle均记录180秒。
这是本轮实验设置疏漏。另存B/postrun-deviation.json，不改写冻结原件。

准确结论是：错误路径连续读取后，**180秒未完成**；
不能声称永久卡住，也不能与旧420秒批次直接比较完成率/耗时。
这不影响六次调用和P0证据，但限制最终恢复能力的否定。
人工入口生命周期、超时和安全保护未修改。
本轮没有延长期限反复跑至PASS；未来复现必须先明确实际等待值，独立建批。

## 6. 资源保护与清理

实际守卫：
/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261111T012050Z-26ea1dcb。

先完成约61秒无模型验证、56次有效确认，再运行短场景与长组。
原单时钟一次性确认、2秒采集预算、3秒有效期及资源门限未改。
B/resource-review.json记录服务窗口1681次采样、1687条publisher记录；
无telemetry-rejections、无NVML17。
被动AC观察1945样本均有效且在线。有限窗口稳定不证明驱动长期无故障。

| 实测（同一守卫加载/短/长服务窗口） | 值 |
| --- | ---: |
| NVML占用峰值 | 29.489GiB |
| Windows Dedicated峰值 | 29.489GiB |
| WDDM Shared峰值（独立计数） | 0.179GiB |
| Windows Available最低 | 22.365GiB |
| Commit剩余最低 | 42.909GiB |
| WSL Available最低 | 17.487GiB |
| Swap峰值 | 12KiB |

这些内存域不能相加。GPU48GiB、Windows6GiB停止线，以及独立Commit、
WSL/Swap/监控失效保护全部保留。

monitor-exception.json含“Safety stop”包装文字，但实际supervisor=CONTROLLER_STOP、
primary_sensor_failure=null。结合Native wait_timeout→runner failure→controller stop时序，
第一原因是研究等待到期，并非资源越界。
service-stop.json及metrics-cleanup.json的remaining=[]；
会话cleanup-observation记录Harness进程组absent，最终端口/进程观察见cleanup-final.json。

## 7. 修改范围、回退与架构判断

本轮必要改动：
- harness/io_contract.py、scripts/h3_harness_interactive_repl.py：配置驱动的能力投影。
- harness/request_audit.py、harness/responses_bridge.py：真实传输阶段、EOF、字节计数。
- harness/delivery_audit.py、scripts/research/goal_hypothesis_audit.py、
  scripts/research/longitudinal_audit.py：严格消费闭合证据。
- scripts/research/longitudinal_dialogue.py：隔离研究fixture可用性块。
- 相关现有测试与新增tests/test_capability_transport_closure.py。
- 本报告、研究地图追加索引。

未修改Goal提案生命周期实现、Phase-1、守卫或模型环境。
工作树其他修改属于先前阶段，见git-before。
B/current-turn.patch与changed-files.json提供精确本轮增量及前后hash。
回退应按这些hunks和B/before核对，只撤销本轮修改，不覆盖用户旧修改、
不destructive reset，不将冻结实验副本当正式入口。

| 维度 | 判定 | 限定依据 |
| --- | --- | --- |
| 能力及完整传输契约 | PASS / VERIFIED | 配置、P0、真实断流反例、限定回归 |
| 两个短场景准入 | PASS（限定） | 10轮读取/指定P/E/状态诚实；组合条件 |
| 模型计算/语义质量 | PARTIAL | 算术、单位和措辞反例 |
| 长Workflow | PARTIAL | History13/30；14未终止；Goal长组NOT RUN |
| Goal自主形成/演化 | UNKNOWN | 短组无候选，未完成长配对 |
| 相对Relevant History价值 | UNKNOWN | 短组无增量证据，长配对未取得 |

保留Sideband、32K默认/64K实验和全部安全边界。本轮不支持新增Goal Engine、
替换提案接口或开放文件权限。
当前主要阻塞是压缩后路径恢复，以及实际实验期限与登记不一致，
不能继续当成Goal能力负面结论。
建议先固定实际等待值，基于本次真实压缩前后片段进行一次独立小范围路径恢复对照；
只有在正确Host引用和错误派生摘要并存时能恢复，才值得再消耗完整30×2。
不需要人工长会话，没有要确认的真实投资/Goal事实。
本轮停止供阶段评审，保留失败，不自动重跑，不Commit/Push。
