# Goal 语义复核：自动验证边界与人工验收节点（2026-11-04）

结论：**PARTIAL；需要人工语义佐证，现已停止自动推进。**

## 本轮发现

- **VERIFIED（现有实现）**：semantic_interpretation.py:60–105验证原始请求、引用片段及模型事件身份，保存candidate；semantic_correctness=not_established。来源/引用通过不是语义正确。
- **VERIFIED（现有实现）**：goal_integration.py:102、183区分候选与显式Host控制。adopt/revise/switch/suspend/resume/reject不构成通用语义解释撤回接口；reject只针对待处理候选，不能当作撤回既有采纳。
- **VERIFIED（限定）**：先前维护实验的撤回在研究层由外部审查输入给出，失效后重放可恢复正确依据。它没有证明Runtime能自行发现“先前理解错了”。
- **UNKNOWN**：自然交互中模型能否区分用户改目标、条件变化与系统认知纠正；纠正后是否持续遵守。不能再用研究者预填语义标签证明。
- **DESIGN INTENT**：解释受到质疑不应抹除真实Observation、修改原始输入或倒写用户Goal历史；正式采纳和授权仍按原契约处理。
- **HYPOTHESIS**：保留原请求、错误解释和用户纠正的分离来源可能改善后续认知连续性；尚未证明现实建议收益。

没有新增语义判断器、自动撤回器或正式权威接线。

## 最小确定性检查

使用仓库原有按模块隔离的复现方式：
- python3 -B -m unittest tests.test_goal_integration：34项PASS。
- python3 -B -m unittest tests.test_harness_semantic_authority：15项PASS。

49项是既有确定性回归，不是49次真实认知识别。最初discover方式Goal模块因memory.sqlite_store导入错误未运行；随后原文档约定的按包模块方式正常通过。未改测试或依赖来绕过错误，不把未运行的discover计为PASS。

模式及退出方式已从当前入口/参数解析核对。端口检查时8000/8003均无监听；本轮没有启动模型/服务。

## 为什么现在需要人工

“我原本就是这个意思”和“我现在改变想法了”的语义真值属于真实用户，不能由被测模型、研究原型或代码字段自行赋予。
下一步先收集一段用户真实任务及自然纠正的可审查记录，再决定是否有必要实现解释复核/失效机制。
人工测试只验证已有模型交互与Shadow记录；不能验收尚未实现的正式语义撤回功能。

## 评判分开

| 维度 | 本轮结果 | 下一步所需证据 |
| --- | --- | --- |
| Runtime Contract | PASS（49项既有离线检查的限定范围） | 新会话的原始输入、候选、执行轨迹、出站审计 |
| Cognitive Behavior | UNKNOWN | 用户确认解释是否符合真实意图；纠正是否跨轮保持 |
| Information Integrity | PARTIAL | 用户输入/模型解释/工具Observation保持不同来源；不能由回答反推隐性依赖 |
| Formal Interpretation Withdrawal | 未实现，NOT TESTED | 需先评审独立解释失效语义，不能借用Goal reject伪装 |
| Long-term Recommendation Value | UNKNOWN | 自然决策及独立结果，本次短会话无法证明 |

可选候选没有生成，记NOT_TRIGGERED；没有真实误解，纠正场景记NOT_TRIGGERED；没有Compaction，不宣称压缩恢复PASS。
不以Turn completed、模型复述或口头“已读取”代替Workflow完成、工具执行或语义正确。

## 影响范围及证据

只新增本报告、人工指南与研究地图索引；不修改正式源码、模型/保护配置、冻结子模块。
原始离线记录位于：
/home/wqkan_wsl/uaea-n1x/research-records/goal-semantic-manual-gate-20261104T131528Z

source-index.json记录源码哈希，test-results.json及两份log保存实际测试。保留原有工作区变更；未Commit/Push。
