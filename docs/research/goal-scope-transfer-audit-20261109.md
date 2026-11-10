# Goal 取消作用域与供给审计：限定复核

日期：2026-11-09。**总体PARTIAL**。两项评价器修复PASS；旧显式生命周期保留PASS；
新无工具邀请对照零候选，长期Goal状态演化UNKNOWN。
源记录：/home/wqkan_wsl/uaea-n1x/research-records/memory-goal-models-20261109T125740Z/

## 1. 两项局部修复

仅修改 scripts/research/goal_hypothesis_audit.py 与对应离线负例，不改Goal运行通道或核心Harness。

1. **撤回后旧版本再现**：
   旧检查只核对ID、内容hash与“晚于自身提交”，不知道请求时已提交的后继版本。
   新检查按每个请求时间重建已提交版本前沿：被后继取代的旧版本不能再作为当前heads出现。
   正确展示withdrawn后继允许；旧版本仍可存在于历史工具回执、Journal及原始来源中，不能误判历史本身非法。
   缺少时间关系保持UNKNOWN，不能无条件PASS。
2. **准备与传输**：
   request_prepared只证明准备了body；现在必须关联同request_id的唯一transport_result，
   要求2xx、有响应字节、无已记录传输错误且时间顺序正确，才计为限定供给证据。
   缺失回执、ID错配、BrokenPipe、503、0字节均不计成功。
   HTTP回执仍不证明完整SSE已被模型处理或模型采用了信息；原生Turn完成另外审计。
   prepared构造合法与transport状态各自报告，不把网络失败误判为内容本身错配。

依据旧真实金融request sequence 6构造内存中篡改反例（不改原件）：
- 在真实withdraw提交后，把旧candidate原样放回heads；旧评价器valid=true，新评价器false。
- 只保留合法准备请求、不给传输回执；旧评价器计入供给，新评价器UNKNOWN。
详见 audit-counterexamples.json。

**117项CPU回归PASS，0FAIL**。旧三份真实版本用新审计器复审仍PASS：
financial form投影成功序号4/5、withdraw序号6；engineering form序号5/6。
原来的缺参拒绝→模型补正能力保留，没有为了获得PASS放松Schema。
这是对评价器的修正，不是发现或宣称Runtime真实复活了旧Goal。

## 2. 新的Scope真实对照

固定原文、Relevant History/Goal Shadow各3轮，单次受保护Bolt服务：
1. 长期AI产业跨公司投资研究，当前Apple估值只是子任务，读取冻结ledger。
2. 只取消Apple子任务，明确长期方向不取消，不重启其他股票研究。
3. 再讨论AI产业共同信息缺口，可引用Apple经历但不重启估值。

原文不提goal_hypothesis、不要求任何候选操作；保留原有可选工具说明。
这检验**未显式邀请工具提交时的选择**，不是完全无语义线索：用户已经明确说长期/子任务。
没有人为禁止UNKNOWN，没有强制提案，没有改Schema/Prompt变体重试。
实际服务采样：NVML峰值29.76GiB、Windows Dedicated29.16GiB、Shared0.26GiB；
Windows Available最低23.03GiB，Commit最低余量44.63GiB，WSL可用最低17.48GiB。
无资源阈值触发；结束后控制停止及监控清理均remaining=[]，8000/8003无监听。不同内存口径不可相加。
资料为既有研究者冻结摘录，非实时行情、真实交易、真实用户投资结果。

使用32K、1GiB KV、36GiB规划、单并发、64/64UMA及原保护。
源码127文件bundle冻结；当前默认及64K实验入口未变。
服务：
/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261109T125909Z-1d958682
（与本轮 owned-service.json 对应。）

| 结果 | Relevant History | Goal Shadow |
| --- | ---: | ---: |
| 完成用户轮 | 3/3 | 3/3 |
| 真实文件Observation | 1 | 1 |
| Goal工具调用/候选 | 0/0（无通道） | 0/0 |
| 限定基础设施/正文供给 | PASS | PASS |
| 累计输入Token | 46,355 | 51,115 |
| 累计输出Token | 1,174 | 1,731 |
| Compaction | 0 | 0 |

Shadow输入约+10.3%；累计量不是单次上下文，实际Harness有效窗口31,129。
样本小、基线先行、没有候选干预，不能估计Goal机制的决策收益或一般性能。
模型普通文字不是正式候选，零候选生命周期仍是UNKNOWN。

## 3. 可观察行为与负面证据

- 两组都将Apple估值取消与长期AI方向保持区分开，并允许已读资料作为历史背景。
- Shadow第二轮承认“继续抓取其他公司财报”是实施计划而非核心长期方向，
  依据用户新输入修正了普通文字解释；没有生成可审计的refine/revise操作。
- 第三轮两组都提出跨公司需要核验的方向，但未实际执行新检索，不能宣称研究完成。
- 两组仍误写Apple收入单位；Shadow还错写Alphabet单位。
  这些是相对已完整供给ledger的模型错误，本轮不开发金融纠错器。
- 没有候选可撤回，不能用“未发生撤回”证明系统已能保护一个现存的长期候选。
  旧真实显式候选只覆盖特定比较Scope，不足以证明跨Task/长期身份。

原生调用、出站请求与回复可在 scope/*/app-server-events.jsonl、model-http-audit.jsonl定位；
完整独立评价见 scope-audit.json。普通回复可被研究者比较，但没有被脚本升级成Goal事实。

## 4. 对Memory研究的约束

旧实验的取消对象与新例子不同，不能事后改写为“只取消Task却撤回全局Goal”。
需要区分：
- 候选描述当前比较任务，被取消时撤回可以合法；
- 候选描述更广方向，明确仅取消子任务不应自行扩大撤回Scope；
- 候选本身误解Scope时，应修正解释而非虚构用户历史变化。

经历可重新被线索引用，与任务恢复、记忆正式采纳或执行权限独立。
新对照为此提供了普通语义响应的有限证据，不是新的Memory/Goal生命周期实现。

## 5. 结论和下一节点

**VERIFIED**：评价器反例被检出；旧显式版本仍能在成功传输请求中定位；
新6轮真实完成、两次文件读取和普通Scope解释连续。
**PARTIAL**：模型可区分给定明确Scope并修正部分自身表述，但仍有来源数值错误。
**UNKNOWN**：自然候选形成、长期候选跨Task状态、真实Memory再激活与增量决策价值。

不再为了获得候选重复Prompt或启动模型。
如评审继续Goal实验，最小问题是“一次明确建立的较广候选，在取消子任务后如何保持或修正”，
与“直接取消该较广方向”成对；只在必要时明确初始接口，后续不强制每轮调用。
本轮不接入自动Goal/Memory采纳，不新增Scope分类器或第二套循环。

Memory理论候选与竞争方案已完成比较，详见
[Memory数学与生命周期研究](memory-mathematics-goal-lifecycle-20261109.md)；
到达核心理论方向评审节点，停止后续实验，不Commit/Push。
