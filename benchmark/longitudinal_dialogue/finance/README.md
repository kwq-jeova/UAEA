# 历史金融研究的冻结回放

这三个场景改编自真实人工输入，来源及原话见historical-user-inputs.json。
这是明确改编，不冒充原会话的逐字完整重跑：
- Intel财报、指定日期行情缺口、模拟Forward P/E及假设修正。
- Alphabet/Intel比较、100%现金模拟及风险约束修改。
- Apple 40倍PE核验、模拟价格变化及两轮后显式Compaction。

共同估值截止为2026-11-04美国收盘后；系统时钟不改动。
官方财报原件于2026-11-09取得，发布声明早于截止，只暴露选定财报字段。
它们不是11-04当天已冻结的字节快照，不能证明当时页面未被事后修订。
本包没有已核验历史收盘价、交易日表、forward年度EPS共识或完整电话会议。
价格和年度EPS模拟值仅来自后续明确用户脚本，不属于市场事实，不执行交易。

financial-ledger.md是有出处的研究者摘录，不是完整网页/独立证据。原始官方HTML/PDF在实验记录中另存。
sources-manifest.json保留原件URI/hash；绝对原件路径可能需要从阶段记录恢复，不宣称全部原件已入Git。
通过真实document.read_section读取冻结文件；不将其叫作实时Google Search/Fetch。
如需实时金融验证，单独新批次记录，不与确定性回放合并。

## 执行

在已有完整UAEA仓库中，以未存在的外部目录准备：

    python3 -B scripts/research/longitudinal_prepare.py --scenarios benchmark/longitudinal_dialogue/finance/scenarios.json --output /absolute/new-study --snapshot --environment-lock /absolute/verified-environment-lock.json

随后传入新实验自己的已就绪guard记录运行：

    python3 -B /absolute/new-study/bundle/UAEA/scripts/research/longitudinal_dialogue.py --output /absolute/new-study --guard /home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/OWNED_READY_RECORD

离线评价（不会启动模型）：

    python3 -B scripts/research/longitudinal_audit.py --output /absolute/new-study --report /absolute/new-audit.json

使用现有32K、1GiB KV、36GiB引擎和全部保护；启动/停止仍由原guard负责。不要停止外部服务。
执行前及每轮核对source-lock，源码bundle不随工作树变化。
原始Git HEAD/dirty状态、模型Revision/config/index、Harness二进制及依赖版本另由环境锁和运行清单保存。
无.git的快照可能打印git查询警告；其版本依据是source-lock，不是伪造的干净Commit。
当前环境锁没有全量权重SHA256，不能宣称权重位级可复现；采样也沿用Harness默认。

财务数据包采用显式12000字符工具结果上限，只有此研究适配器变化。
原4000预算可截去整个数字段落，不能把读取成功或audit快照完整视为正文已完整供给。
既有32K/Host预算与权限不变；出站工具content的hash匹配必须另查，不用文件hash替代。
受控Compaction由现有thread/compact/start发起，等待原生完成后才发下一用户轮，不是自然窗口耗尽。
Evaluator将压缩原生Turn与脚本用户Turn分开核对，不能把压缩计成一轮用户完成。

模拟算术：50/2=25，50/1.25=40；100/2.5=40，80/2.5=32。
这些是预定义假设的参考运算，不是现实估值真值、唯一仓位、Goal标签或建议成功率。
正文事实、实际读取、模型声明、正式状态和研究完成必须分别审查。


2026-11-09独立审计收敛：Evaluator逐项核对原生用户消息、Turn及非空回答；
完整正文判定与真实Observation的call/observation ID、原section/file版本绑定，不能只检查结果自身声明的hash。
Goal投影必须是developer结构化块，并与出站manifest角色/位置一致；普通消息里的字符串不算投影。
无需要求正文的普通问答使用NOT_APPLICABLE，不强制每轮调用工具。
被Harness以unsupported call拒绝的提案也计入tool_attempts，分开执行成功、失败和未观察状态。
Runner的cleanup-observation.json记录实际退出与进程组状态；不再预写“已关闭”或Memory未采纳声明。
离线报告默认拒绝覆盖旧报告，请显式指定新的--report路径。原记录与旧判定保留。
