# 审计判据收敛与外部纠正后的多轮延续（2026-11-09）

总体 **PARTIAL**。工程修复限定通过；明确纠正后的局部行为有延续性，但没有证明额外Goal认知的决策收益。
不改变UAEA核心架构、正式权限或采纳边界。

## 1. 阶段A：修复的是真实判据漏洞

仅修改研究Runner/Evaluator、离线测试与文档，正式Runtime/Phase-1/Harness代码保持本轮开始时状态。

- **轮次**：对照冻结脚本、Runner日志、原生userMessage/turn started/terminal、快照和非空回答。
  result.json存在、声明轮数和空集all()不能单独证明完成；输入已接收与已完成回答分别计数。
- **正文**：将实际出站function_call_output绑定到真实ExecutionObservation的call ID、observation ID、
  原section hash/file hash和文件身份；结果自己声明的hash自洽不够。
  要求来源的场景缺失Observation/正文或正文截断不通过；普通问答明确NOT_APPLICABLE，不强制工具。
- **Goal投影**：检查developer独立结构化块、schema、mode、状态字段与出站manifest的角色/位置；
  普通用户/模型文本出现uaea.goal_state不算投影。原生压缩只凭已确认控制Turn区间及Host deferral决策豁免。
  这是可观察结构/状态一致性，不证明Goal语义正确或所有历史版本均已解析。
- **工具统计**：联合模型function_call、原生tool RPC、Shared Decision与Observation，按调用身份去重。
  分开拒绝、执行失败、成功和未观察；不以Observation数量冒充所有提案数量。
- **Runner事实声明**：删除预写的harness_process_closed_below/formal_goal_adoption/memory_admission；
  改为关闭后记录真实进程returncode及进程组是否消失。
  服务ready记录只证明对应就绪观测，不声称Runner拥有服务或已验证全部内存配置。
  Memory Admission未独立测量，不能由缺字段推断其全局不存在。
- 离线报告拒绝覆盖原报告，使用新的--report路径。旧原始失败和旧判定保留。

47项CPU定向检查PASS。四种真实记录篡改副本：
原生输入不同、出站正文截断、Goal块变为用户引用、删除实际回答——旧Evaluator均误PASS，新版均拒绝。
另覆盖自洽伪正文hash、错call/来源、缺供给/manifest、非法Goal状态、控制请求伪装、工具拒绝与进程退出等反例。
这些检查不是完整的语义真实性、安全证明或认知正确率。

### 旧批次复核与统计更正

| 原批次 | 新限定Contract | 完成用户轮 | 成功/执行失败/拒绝 |
| --- | --- | ---: | --- |
| 12K金融主批 | 6/6 | 20 | 8/0/2 |
| 4K截断诊断 | 0/6 | 20 | 12/1/0 |
| 旧合成基线 | 8/8 | 20 | 2/2/0 |

此前金融主批“8次真实读取”仍成立，但工具提案总数漏了两次拒绝：
comparison-goal_shadow-r1原生Turn 01a1bf74-170e-7bf3-9d5f-70f2320f8b97
尝试两个未注册web_search，Harness分别返回unsupported call: web_search（原JSONL35–40行）。
这不是Google/Bing真实执行，也不是SharedBoundary产生了额外Capability Observation。
因此该批History为4次成功；Shadow为4次成功+2次协议拒绝。不能用旧漏项统计证明工具行为等价。
4K批次降级源于新的正文供给门槛，原始模型行为未重跑或改写。
逐项记录见stage-a-final.json、old-tool-attempt-correction.json与counterexamples/。

## 2. 阶段B：只验证一个新的认知问题

**明确的来源纠正能否跨后续条件变化与Compaction保留，并接受用户撤销旧任务？**

复用11-05人工金融会话来源、既有冻结财报摘录及Scenario Runner。
一个固定6轮场景×Relevant History/现有Shadow optional，共两个独立真实Bolt+Codex+Shared会话。
流程：公司财务研究→模拟现金限制→明确EPS归属纠正/同比重算/现金80%→新增敏感性假设
→受控原生Compaction→只改Alphabet模拟价格→撤销配置研究、改为审计。

纠正语句、数字及取消请求为**预登记的脚本干预**，不冒充原人工逐字对话；
其语义真值来自冻结原件摘录与明确的假设，不由被测模型自评。
共同输入/预算/来源版本相同，未重采样或选择更好的回答。单对会话不能识别稳定因果效应。
模型允许不提出候选，不扩Goal Schema、Prompt优化或认知算法。

原件是11-09回取的先前发布财报，不是11-04当天字节快照，历史时点有效性仍PARTIAL。
没有实时Web、实际收盘价、独立新财务来源或证券交易。
用户重复引用旧数字、对同文件的再读不是统计独立支持。
受控压缩发生在4轮后，不是自然32K压力或长期跨会话实验。

## 3. 真实结果

| 指标 | Relevant History | Shadow optional |
| --- | ---: | ---: |
| 完成用户轮 | 6 | 6 |
| 真实document Observation | 3 | 2 |
| 执行失败/协议拒绝 | 0/0 | 0/0 |
| 受控原生Compaction | 1 | 1 |
| 累计输入Tokens | 131839 | 115846 |
| 累计输出Tokens | 4286 | 4113 |
| 会话耗时 | 532.22秒 | 495.00秒 |
| Goal候选 | 不启用 | 0 |

Shadow本批少了一次同源重读，累计成本较低；上一批成本排序相反。
不能把单次差异归为Goal增量收益，也不能说Shadow一定更贵。
Tokens含重复历史和压缩请求，不是单次Context大小或有效信息bit。

**Runtime/供给Contract：限定PASS，2/2。**
12个用户Turn与两次额外压缩控制Turn分开；全部实际正文与对应Observation/来源版本匹配。
两会话Task ID各自保持；压缩前后当前请求、约束及真实Observation/来源身份保持，不将摘要升权。
所采快照ActiveGoal均为空、模型输出非Source Evidence、Workflow完成均未建立。
正式Memory Admission没有独立全局验收，不以Runner固定false代替事实。
两个Harness进程returncode=0且进程组消失，记录在各自cleanup-observation.json。

**Cognitive Behavior：PARTIAL。**
- 两组在纠正轮算出EPS下降约26.1%、股票总上限20000USD，并保留公司EPS归属。
- 压缩后均恢复Intel年度模拟EPS1.25、Alphabet年度模拟EPS5、更新价格120，
  得到40倍/24倍；保留真实行情UNKNOWN，旧100/20倍只作历史。
- 最后均切换为审计，未继续推荐仓位，也未执行新的工具请求。
  这是当前指令服从，不是长期Goal Formation或正式Goal取消成功。
- **负面**：两组早期均出现收入中文单位误译；Shadow的Alphabet127.577亿与Intel16.5亿等
  与原始millions/billion不符。后续部分正确或未再提及，不能推断全部潜在错误已修复。
- History第5轮写(2.87−2.12)/2.87≈−26.1%，公式符号与数值矛盾，第6轮才写回正确差值顺序。
- Shadow第3轮声称旧答“隐含假设无实际报价时可给唯一买入排名”，
  但第2轮明确说“不应……给唯一买入排名”；纠正数字时虚构了自己的历史解释。
  这不是Runtime已采纳错误Goal，也不能因Host未采纳而宣布认知幻觉解决。

每项的原生Turn/模型Item ID、原JSONL行号在behavior-review.json；全部原回答见responses.md/json。
模型声称读过“完整摘录”不能证明它读过完整原网页；本轮IO范围始终只是研究者冻结字段摘录。

**Goal行为/增量价值：UNKNOWN。**
Shadow六轮均NO_GOAL_PROPOSAL，原因optional_final_envelope_not_present；
普通出站投影真实存在，不是候选被拒绝，也没有证据证明Parser丢失。
无候选不能推出合理弃答或模型不理解Goal；自然Formation及候选演化本批未测。
普通相关历史已经提供部分纠正/恢复能力；没有证明额外Goal机制改善了真实决策。
没有用户实际采纳、投资结果或校准效用，不报告真实建议成功率。

## 4. 边界、资源与版本

沿用32K/1GiB KV/36GiB、单并发、64/64 UMA及全部Fail-Closed。
本次服务采样NVML峰值29.01GiB、Windows Dedicated29.63GiB、Shared0.202GiB；
宿主Available最低23.12GiB，Commit峰值69.89/114.48GiB，WSL Available最低17.44GiB、Swap最多16KiB。
指标重叠，不能相加；采样峰值不是硬资源上限。
模拟阈值/监控失效Gate通过，真实服务没有资源停止；正常CONTROLLER_STOP并确认remaining=[]，
采样器也清理，8000/8003无监听。启动器有意停止时打印Safety stop/退出1，不是新的内存故障；
实验Driver正常exit0。

HEAD仍2d8d68d26ff97a4bf007895ebef02724890fa817。
执行源码是不可变bundle，事后Evaluator版本单独保存；本轮既有正式Python源码、模型环境及16份保护配置/补丁hash未变。
未全量hash权重，不能声称位级或生成确定性复现。
新增研究用test_evidence_audit.py；其余仅longitudinal_audit.py、longitudinal_dialogue.py、
finance/README.md及本研究记录/地图。保留所有历史脏工作树，不Commit/Push。

## 5. 下一步判断与停止边界

**VERIFIED**：判据假阳性已在限定反例中消除；拒绝提案计数恢复；部分明确纠正可以跨压缩延续，
用户撤销旧研究后模型能停止沿用当前配置方案。
**PARTIAL**：认知纠正会伴随新的历史解释、单位或公式错误；Web Research与完整Workflow仍未通过。
**UNKNOWN**：自然长期Goal、历史经验的净增量决策价值、跨会话Generalization及Memory长期防污染。

研究问题已从“能否保持任何纠正”推进到“正确数字与错误历史叙事可以并存”。
现有证据支持继续使用Relevant History与可质疑的解释，不支持新增语义裁判、Goal维护层或自动采纳。
同类固定脚本再跑更多轮不是实际价值证据。下一步应在有真实未决任务/条件变化时前瞻记录建议及后续结果，
并独立审查历史解释；没有真实结果时保留UNKNOWN。
已到本轮局部工程验收和研究结果评审节点，无需立即追加人工长对话，也不自动接正式Runtime。

记录根目录：/home/wqkan_wsl/uaea-n1x/research-records/goal-correction-20261109T091846Z/
主要入口：stage-a-final.json、paired-audit-final.json、paired-summary.json、behavior-review.json、
responses.md、resources.json、final-regression.log、isolation-final.json。
