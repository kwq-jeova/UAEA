# HTTP framing审计与重复输出诊断（2026-11-11）

**总体PARTIAL。** HTTP消费判据限定PASS；本次单请求四层诊断PASS，但未复现旧121次重复，
旧异常首次出现于生成端、Parser还是流处理仍为UNKNOWN。**不建议据此恢复30×2长实验。**
本轮不修改Goal/Memory/权限，也不开展完整Goal对照；Audit Agent已独立复核，总体仍PARTIAL。

## 1. 证据与范围

B=/home/wqkan_wsl/uaea-n1x/research-records/transport-repetition-20261111T050056Z。
正式源码基准HEAD仍125f0d2a8e6b7ac0f6b70baf9913b942be2b1cb2；
已有工作树修改保留，本轮精确增量以B/before、current-turn.patch和changed-files.json为准。
不Commit/Push、不升级依赖、不改变Backend、采样、32K/1GiB KV、36GiB规划或执行权限。

旧失败原件：
/home/wqkan_wsl/uaea-n1x/research-records/context-resume-20261111T023249Z/long-repetition-case.json，
以及remaining-run/long/finance30-relevant_history-r1原生/HTTP记录。
旧Native输出3311字符、同一短句121次，420秒未完成；本轮不覆盖或改写。
网络切换中断发生于本轮实机请求启动前，没有因此重复发送模型请求；
本次实际模型请求只有一次，本地loopback通信不依赖外网资料。

## 2. A：framing消费契约修复 — VERIFIED / 限定PASS

生产者已有http_framing_complete，但harness/request_audit.py的transport_state此前未消费它。

本轮最小改动：
- 显式http_framing_complete=false，即使response_complete=true/HTTP200/计数相符也不能PASS。
- 完整成功要求http_framing_complete **布尔True**，同时保持EOF、无错误、字节类型/非负、
  received=forwarded、已知Content-Length相符及HTTP2xx要求。
- 缺失字段、None、字符串true或整数1不能视作已验证framing，旧“完整”记录保持UNKNOWN。
- 已明确transport_error或response_complete=false的旧记录仍可判partial，
  不为“历史兼容”抹掉已知失败。
- 没有增加SSE或模型理解裁判；HTTP完整仍不代表Native Turn/Workflow或语义正确。

定向回归：B/framing-tests.log，79项PASS。
新增6个消费判据反例，覆盖缺字段、显式false覆盖成功、非布尔值、
framing=true但EOF/计数不符、100/3提前EOF及HTTP/transport错误。
原loopback Content-Length100/实际3、合法chunk终止等测试继续通过。

较广限定回归：744项，742 PASS、2 SKIP，0 FAIL/ERROR。
沿用明确的10项旧个人语料缺失前提排除；未伪造语料或改Memory实现，不能称全项目无条件PASS。
测试中的正例补足真实framing证据，没有将负例批量改为成功。

历史原件只读重新分类见B/historical-reclassification.json：
- 旧capability-finance短组4条缺framing记录 -> 4 UNKNOWN。
- 上轮context-resume金融记录 -> 2 complete_success、1 partial。
原件hash保留，没有回填或覆盖旧字段。

## 3. B诊断设计：一条正文、四个边界

### 3.1 冻结正文恢复

原P0第3请求ID：9eaa2c64-46d1-4cc7-a482-16cf89f8d5d1。
脱敏快照并非原始字节：它规范化了JSON格式，还将
current_user_request.authorization_established字段脱敏。
根据固定生产者值及原消息hash恢复格式/该布尔值，再用**原整体forwarded字节SHA256**核对。

B/recovered-request.json共65131字节，SHA256：
9f32270facda970a8ee351f9edcb04a3480e4c870b8056344fd075a5efd4ee23。
最终所有消息hash和原forwarded整体hash一致；
见request-provenance.json（保留初始不匹配）、request-final-validation.json（最终零不匹配）。
原HTTP header集合未保存，不声称整个TCP/HTTP历史相同。

只发送这一条正文。不补发前两次请求或先前短会话，不重建旧进程的随机数/缓存历史。
相同正文及相同声明参数不等于相同随机抽样或完整引擎历史，这是不能据一次正常排除旧异常的原因之一。

### 3.2 资源与请求上界

B/preregistration.json：
- 最多1次实机模型请求；请求观察上限180秒、整个受控作业900秒。
- 预登记每层16MiB，但独立审计证实v1未完整执行该预算契约，详§8；本次实际文件均远小于16MiB。
- 不改Temperature、Repetition Penalty、max_output_tokens、Context/KV、seed或Backend。
- 截止时间只用于诊断客户端，部分响应不能伪装完整；没有重试或自动工具执行。

### 3.3 四层观测

1. **引擎输出进入响应Parser之前**：
   B/engine_observer_launcher.py进程内包装现有SimpleContext/ParsableContext.append_output，
   记录RequestOutput.text和token_ids，再以原对象调用原函数，返回原结果。
   CPU身份测试见observer-cpu-check.json；没有改site-packages。
2. **vLLM原始SSE正文**：
   观察原HTTPResponse.read1返回字节，不编辑或重发；保存live/upstream.sse。
3. **现有Bridge下游字节**：
   同次请求保存live/downstream.sse，核对全体字节/hash。
   独立CPU碎片写入测试见byte-observer-cpu-check.json。
4. **真实Codex Harness的无GPU回放**：
   native_replay.py将同一份捕获SSE提供给独立原生Harness会话，
   仅一次本地fixture响应，没有模型调用或工具权限；保留app-server-events.jsonl。
   SSE解码只拼接output_text.delta，不再把done/完整item重加一遍。

隔离启动说明：
- 正式启动脚本/模型环境不改。isolated-launch/guard.ps1与原版逐字节相同。
- 隔离副本只改workload入口链接，以及用相同vLLM CLI参数启动进程内observer；
  资源/心跳/时钟/终止逻辑不变。差异完整保存在isolated-launch.diff。
- 原16项模型/安全pin最终均匹配；原资源上限不因诊断放宽。
- 观测可能改变时序，不能将“参数/返回对象不改”扩大为零扰动或统计等价证明。

## 4. 实际观测 — VERIFIED（仅本次正常路径）

模型实际记录：
manual-20261111T054916Z-0c88fb33。

| 层级 | 证据 |
| --- | --- |
| 唯一API response_id | resp_a90afd29ef755a9a |
| 引擎request_id | resp_a90afd29ef755a9a_0 |
| 引擎类/PID | SimpleContext / 829 |
| 引擎观测 | 303个chunk，303个token IDs，421字符；位置连续 |
| 实际输入Token | 18546（本次真实第3请求正文的token化结果） |
| 结束 | finish_reason=stop，SSE response.completed |
| 耗时 | 46.050秒，未触及180秒 |
| SSE正文 | 上游/下游各72246字节，逐字节相等 |
| SSE SHA256 | b3b76cba074434dddbf3820c8abbe17e7c684d984bc849b8235ff98ef543b39c |
| 文本 | Parser前文本=SSE delta文本=Bridge文本=Native回放文本 |
| 文本SHA256 | 178326169d862600167cf362cb06cda900dfe6fb1292444a78f3d574c04a6497 |
| 重复短句 | 四层本次均0次；旧121次未复现 |
| CPU token解码 | skip_special_tokens解码与引擎文本一致 |
| Native回放 | 1.899秒，Turn completed；0次GPU请求、无重复放大 |

原始/对比文件：
- engine-before-parser.jsonl：引擎原始text/token_ids，首尾理由。
- live/upstream.sse、live/downstream.sse、live/model-http-audit.jsonl、live/capture.json。
- sse-comparison.json：事件类型、逐item delta、done文本独立记录。
- token-decode-check.json：本地tokenizer hash及纯CPU解码。
- native-replay/app-server-events.jsonl、comparison.json。
- layer-comparison.json：ID、hash、位置、usage和层级归因汇总。

Native回放中的Usage是同一SSE自带字段，不能重复计作第二次推理成本或另一次模型行为。
Replay输入只用于流处理验证，不能作为真实用户Goal/Workflow研究样本。

## 5. 未解决的根因与语义反例

### 已证实

- 本次引擎Parser前输出没有重复；SSE解析、Bridge转发与Native拼接没有新增重复。
- Bridge没有复制或丢弃本次响应正文。
- HTTP审计明确记录framing完整，符合修正后的消费判据。
- 新回答存在财务单位错误：来源16.5 billion USD被写成16.5亿美元。
  错误已在Parser之前出现，后续层如实保留。该错误不是HTTP修复责任，
  本轮不添加金融规则或第二个语义审核器。

### 仍UNKNOWN

旧121次输出的**最早层级不能从现有记录恢复**：
旧资料只有Native deltas与吞吐/资源日志，缺少同次引擎原始text/token_ids及上游SSE。
本次正常样本不能倒推旧异常一定来自模型，也不能据此排除偶发Parser/流处理问题。

未复现不等于已修复；没有证据支持新增重复惩罚、裁剪模型输出、换Backend、
调KV/Context或建立认知纠错层。本轮没有这样的修改。
也没有将旧原生部分输出人工伪造成“旧原始SSE”。

**本轮不存在有证据支持的重复输出确定性修复。**
实质完成的是HTTP判据修复、可复核的四层观测与一次无GPU端到端回放。
生成重复风险尚未合理排除，长期稳定性仍UNKNOWN。

## 6. N1X保护与清理

151个服务期资源样本、157条publisher记录，未见telemetry-rejections或NVML17；
267个有效被动电源样本均AC在线。
Dedicated峰值约29.448GiB；Shared约0.145GiB（独立计数）；
Windows Available最低21.952GiB；Commit剩余最低42.255GiB；
WSL Available最低17.593GiB；Swap峰值12KiB。这些域不相加。

原48GiB GPU、6GiB Windows、Commit、WSL/Swap、2秒采集、3秒有效期、单时钟一次性确认
和Fail-Closed均保留。正常结束后仅停止本批拥有的模型/采样器。
monitor-exception中的Safety stop为CONTROLLER_STOP包装，primary_sensor_failure=null；
不是本次资源越界。最终remaining=[]、Native进程组absent、8000/8003无监听。
有限窗口不升级为长期驱动或监控稳定性PASS。

## 7. 修改、回退及下一步

正式源码仅transport_state消费framing字段；4个现有测试文件更新/补反例。
研究采集/回放/隔离入口均在B，不成为正式推理入口；无新依赖、新Agent Loop、
Goal或Memory功能。Phase-1子模块保持干净。

本轮增量见current-turn.patch、changed-files.json；回退只核对B/before及这些hunks，
保留用户之前未提交内容和全部原始失败，不reset/clean。
本报告与研究地图追加索引，原历史记录不改写。

| 问题 | 判定 |
| --- | --- |
| HTTP framing审计 | VERIFIED / 限定PASS |
| 本次四层传输/解析一致性 | VERIFIED / 限定PASS |
| 旧121次重复的首次层级 | UNKNOWN |
| 重复输出风险已消除 | 未证明 |
| 新财务回答语义正确 | PARTIAL，单位错误保留 |
| 恢复30×2金融Goal对照 | 暂不建议 |
| Goal架构变更依据 | 没有新增证据 |

本轮已交Audit Agent独立复核，详§8。
后续若继续诊断，应维持本次观测并预先定义少量请求的warm-state/冷启动对照，
而非正常一次就重启长实验；数量、资源及推理参数须明确，不追求测试到PASS。
暂不需要人工长会话，不自动开展新一批模型实验。


## 8. 独立Audit及采集器修正

原始独立报告位于B/audit-agent-review.md、audit-agent-review.json、audit-agent-tests.log。
父Agent不改写这些报告。Audit总体PARTIAL，确认HTTP限定PASS、正文恢复/本次四层限定PASS，
旧121次根因及风险消除UNKNOWN，明确不足以恢复30×2。

Audit补充发现并以无GPU反例确认v1诊断代码的三项缺陷：
1. **P2**：下游直接write，无16MiB硬限额；16777217字节纯内存run反例下，
   上游限额标志触发但下游仍保存16777217字节。
2. **P3**：Tape跳过超限块后仍可写入后续短块，limit5、abcd/XY/z得到abcdz，
   不是原流的连续prefix。
3. **P3**：Observer的capture_limit marker本身可超过剩余空间；limit1时写51字节。

本次实际up/down各72246字节、engine124327字节，没有触及限额、marker或IO错误。
Audit独立重算数据确认上述缺陷**未使本次四层比较失效**；
也不能因为本次未触发就称v1预算契约PASS。

原v1、已锁定input-lock和全部实机原件原封不动。
新建独立live_capture_v2.py、engine_observer_launcher_v2.py，仅修日志预算/故障路径：
- 双向文件硬上限；超限只保留连续prefix，不会稍后恢复拼接。
- 截断/IO错误时完整prefix证明为None，存储状态不冒充HTTP或模型完成。
- Observer预留marker；IO前保守计入预算，写/flush异常锁存error并停止后续写入；
  原模型append输入、text/token和返回对象保持不变。
- Audit再次发现“flush写后报错、不更新bytes”反例，修正后独立验证仅113字节、
  error=OSError、后续不再写，身份保持。
- B/test_capture_budget_v2.py的6项CPU回归PASS；Audit另有纯内存双向run和marker边界复核。

**v2只有CPU限定PASS，未用于任何实机请求，未替换原入口。**
本轮没有追加GPU“验证到通过”。复现材料应在新的独立目录准备，不可对现有原件就地重跑。
正式Runtime修改仍只有framing消费判据及相应测试；本节不是新的推理或采集架构授权。
