# Goal Hypothesis 可选语义通道：最小机制与真实负面结果

日期：2026-11-09；状态：**Research PARTIAL，未进入正式 Runtime**。
研究源目录：/home/wqkan_wsl/uaea-n1x/research-records/goal-hypothesis-20261109T101311Z/。
基准 HEAD：2d8d68d26ff97a4bf007895ebef02724890fa817（main，已有脏工作树，不能仅凭 HEAD 复现）。
本轮不 Commit / Push，不改变 Phase-1、Harness 执行所有权、正式 Goal / Memory 采纳或权限。

## 1. 问题与最小决策

此前 Shadow 的可选最终回答 JSON 通道反复出现 NO_GOAL_PROPOSAL。待检验问题是：
可否通过现有 Harness 的可选原生动态工具，实际观察非权威候选的形成及修订？
不是强迫每轮产出 Goal，也不是证明有来源的解释必然正确。

本轮增加隔离研究通道 --goal-channel sideband，默认仍为 legacy。
仅 Shadow 臂注册 goal_hypothesis；Relevant History 不注册、不注入候选视图。
两组使用相同用户脚本、来源与工具正文预算；Shadow 多出的通道/投影是处理变量，其成本单独报告。
主要脚本在第二轮有一次条件式邀请，因此也不能称为完全自发的自然形成实验。

**实际结论：尚未实现真实模型候选形成及跨轮演化。**
模型确实获得可选工具，但主批 Shadow 十轮与独立显式邀请诊断前三轮均没有调用。
不能用 CPU 人工构造的候选轨迹代替这一负面结果。

## 2. 实现边界与复用

| 文件 | 职责 |
| --- | --- |
| scripts/research/goal_hypothesis.py | 复用 GoalIntegration、Phase-1 GoalHypothesisRecord、RuntimeObjectRecord / Store；保留可撤销解释、当前原文身份及父版本 |
| scripts/research/goal_sideband.py | 在现有动态工具 RPC 中接收可选语义提案；不增加第二套模型或执行循环 |
| scripts/research/longitudinal_dialogue.py | opt-in 接线、逐轮候选状态留档及启动未返回时的进程清理回执 |
| scripts/research/goal_hypothesis_audit.py | 原生调用、原文 hash、父版本、出站投影、Observation 分离审计；无候选不能 PASS |
| benchmark/longitudinal_dialogue/test_goal_hypothesis.py | 生命周期、来源、非法采纳、错误语义反例及评价器空集负例 |
| scripts/research/README-goal-hypothesis.md | 运行与非权威边界说明 |

候选操作 form / maintain / refine / revise / withdraw 指**解释版本**变化，不直接断言用户真实 Goal 改变。
更新追加新版本并保留父 ID；多个解释与无解释均合法。
当前 quote 必须来自绑定到原生 Turn 的原始用户输入；历史引用校验来源 hash，并保留取消状态。
已取消输入可作历史依据，不能因此重新生效。Evidence 引用只能指向真实 Capability Observation，
但关联本身不证明语义支持。

候选投影为 untrusted，最多三个 head、八条输入索引，字符预算 4200；每轮最多两次、会话最多32个版本是上限而非配额。
语义调用回执不是外部执行 Observation，原生轨迹仍保留。
ActiveGoal 采纳禁用；不生成执行授权、Workflow 完成或可信 Memory。跨进程/跨 Run 恢复未实现。

## 3. 真实执行与中断，不能混算

固定模型 Revision 元数据 cf2effc5c4b794ee9fb8d34eab3d1d65ce64142f；
vLLM 0.32.0 / Torch 2.13.0 / B12X 1.5.1 / FlashInfer 0.7.0.post1。
沿用32K、单并发、1 GiB KV、36 GiB规划、64/64 UMA与既有独立资源保护。
模型全量权重 hash **未执行**。

| 批次/会话 | 完成用户轮 | 真实文件读取 Observation | 候选调用 | 限定输入/工具契约 |
| --- | ---: | ---: | ---: | --- |
| paired/finance-relevant_history-r1 | 5/5 | 2 | 0（无此通道） | PASS |
| continuation/finance-goal_shadow-r1 | 5/5 | 2 | 0 | PASS；候选生命周期 UNKNOWN |
| continuation/engineering-goal_shadow-r1 | 5/5 | 2 | 0 | PASS；候选生命周期 UNKNOWN |
| continuation/engineering-relevant_history-r1 | 3/5 | 1 | 0（无此通道） | PARTIAL，中断 |
| diagnostic/explicit-goal_shadow-r1 | 3/4 | 0（非该场景要求） | 0 | PARTIAL，用户暂停 |

主实验18/20轮；独立显式邀请诊断3/4轮，**不计入主对照**。
两个完整金融会话各有一次受控原生 Compaction，正文 hash/实际出站供给检查 PASS；
这不是自然容量压缩，也不是已有候选跨压缩恢复 PASS。

保留的三类中断：
1. paired 首次 Shadow 因新工具缺少 canonical type:function，thread/start 即被拒，尚未请求模型。
   修正研究适配后使用新源码快照继续，保留该失败；原已完成基线未重跑。
2. 主批服务的有限自动实验期限为1800秒，工程基线第四轮遇到服务停止、连接拒绝；第五轮未执行。
   未归因为模型认知、Context溢出或资源不足，不改监控/延长期限来补齐结果。
3. 独立诊断第二次服务在用户暂停时停止，第四轮中断，不能计为模型失败。
   本次恢复只完成离线收敛，未重新加载模型或重复采样已完成回答。

paired-audit-resumed.json 包含原计划未启动项；不得把其四项与 continuation 三项相加称七个独立会话。
有效主结果选择与来源位置列于 evidence-summary.json、source-index.json。

## 4. 请求与语义行为证据

出站审计位于每个会话的 model-http-audit.jsonl：
Shadow 的 request_prepared 含 request_user_input / read_section / goal_hypothesis，
uaea.goal_state 为 developer 应用状态，候选视图为 untrusted，原始当前用户输入可定位。
桥接源码 harness/responses_bridge.py 在审计后用同一 body 调用 connection.request；
审计为脱敏视图并带原始/转发字节 hash，不等于模型已理解或使用这些信息。

诊断第一轮原生 Turn：
01a1bff5-09c4-7eb2-90fd-23a0fb761dbb；
最终模型 item：msg_a00b451f2f9cc15c。
输入明确写出样例长期目的，并请求有依据时调用工具；模型却称“目前可用的数据来源是仅剩的当前用户请求”，
继而答 UNKNOWN。第二轮能在普通文字中区分目的和 GPU 路径约束；第三轮仍以无外部来源为由不建立候选。
这是**已观察的错误解释/过度弃答行为**，不是 Host 真的要求外部证据或拒绝提案。
原生事件没有 goal_hypothesis 调用，因此也没有 Host 接收/拒绝此类真实提案的证据。
无法从其自述证明内部因果，不能据此断言 Bolt 一般性不具备 Goal 理解能力。

主批还观察到：
- 两臂最初将 $16.5B、$127.577B 错写为16.5/127.6亿美元，与冻结文本单位不符。
- RH 第三轮出现错误 P/E 算式，且建议取得截止日后的更新用于截止日比较。
- Shadow 第四轮给出模拟 P/E 40/24，末轮却把读取时间与发布时间混淆。
- 工程 Shadow 将“文件读取正确、模型推理错误”建议为重复文件读取去复现语义错误，验证路径不成立。
- 工程 Shadow 第五轮普通文字接受取消旧方向，但没有候选可供撤回。

这些是来源正确供给后的模型行为问题；没有因此建立错误的正式 Goal、可信 Memory 或执行事实。
普通文字描述目的/计划，不能被审计器事后转成 Goal Hypothesis。

## 5. 公平对照、成本和收益

只有金融5轮对照完整。两组各两次文件读取、一次受控原生压缩，均未产生候选：

| 指标 | Relevant History | Shadow sideband |
| --- | ---: | ---: |
| 累计输入 Tokens | 95,113 | 104,128 |
| 累计输出 Tokens | 4,013 | 3,928 |
| 累计总 Tokens | 99,126 | 108,056 |
| 已完成用户轮耗时合计 | 387.6秒 | 404.0秒 |

输入成本约增加9.5%。累计 usage 包括多次请求，不是单次 Context；耗时合计不含加载和独立压缩控制。
单对、固定先后顺序、不同源码 bundle（局部接线修复）且没有候选介入，不能估计因果效应或真实收益率。
相对 Relevant History 的候选利用价值、自然形成能力、长期决策收益均 **UNKNOWN**。
本批没有证据支持建设维护层、增加状态算法或将新入口切为默认。

## 6. 自动验证、资源与可回滚性

最终104项 CPU 测试 PASS（offline-tests-final-v2.log），覆盖来源/版本/撤回/冲突、
合法 quote 配错误解释仍保持未验证、原生回执适配、非法采纳拒绝、语义调用不成为外部事实。
它们证明限定实现约束，不证明真实语义工具调用或候选演化已发生。
最初单独运行旧测试时因 Python 路径顺序导入失败；初始化现有研究入口后联合运行通过。
原失败日志保留，没有修改依赖解决。

评价器修正：无候选的完整或不完整会话，lifecycle_contract_status 均为 UNKNOWN；
有候选但会话不完整为 PARTIAL；有实际权威/来源违反则 FAIL，不再 all([]) 得到 PASS。

真实服务采样（排除模拟保护触发）：
- 第一服务 NVML GPU峰值28.83 GiB；Windows Dedicated峰值29.46 GiB、Shared峰值0.27 GiB；
  Windows Commit峰值69.78 GiB、最小余量44.70 GiB；Windows Available最低23.23 GiB；
  WSL Available最低17.48 GiB。
- 第二服务相应GPU峰值29.04 GiB；Windows Available最低23.12 GiB，Commit余量最低44.75 GiB。
这是采样极值，不保证捕获瞬时峰值，各口径不可相加。
保护烟测为模拟48GiB/失效触发，不能误报为真实资源超限。
两个服务均已停止、目标进程清理回执 remaining=[]；本次恢复检查8000/8003均无监听。

原基线Python hash对照仅既有 scripts/research/longitudinal_dialogue.py 改变；
核心 Harness / Phase-1 / Memory源码不变，锁定模型配置、启动器与Codex二进制六项hash保持一致。
研究新文件单列于 research-changes.patch，旧脏工作树保留。
回退仅停用 opt-in sideband（默认legacy）；如撤销本轮Runner改动，应对照 before 快照局部还原，
不能 reset/clean 清理其他历史工作。正式人工入口没有改动。

## 7. 架构判断与下一节点

- **VERIFIED**：可选工具及来源状态真实送出；既有文件执行及正文供给正确；CPU候选版本和权威隔离通过。
- **PARTIAL**：最小研究通道已建立，但真实形成/演化目标未达成，工程基线会话不完整。
- **UNKNOWN**：真实模型候选质量、候选跨压缩恢复、跨运行恢复、增量决策价值。
- **CONFLICT（观测行为）**：把缺少外部财报/外部文档事实当作不能保留用户已表达目的的必要条件。
- **HYPOTHESIS**：可选通道选择/模型语义混淆影响生成；日志不能分解二者因果。

本轮到达“重要负面结果需评审”的停止点，不再反复调整 Prompt、强制 tool_choice 或由 Host 从文字编造候选。
建议保留 opt-in 原型与 Relevant History 基线，**暂不扩展 Goal/Memory 维护层**。
下一项需要评审的选择：是否开展一次可替换 Backend / 独立语义提案接口的最小功能对照，
先区分“不能表达候选”和“选择不调用可选工具”，而非继续扩大现有状态结构。
额外模型调用或改变正式候选入口应另行评审；本轮不实施。
无需新增人工长会话，也没有任何真实投资建议或交易。

## 复核入口

- 根目录：预登记、源码/模型锁定、主批与诊断分离、中断及保护记录。
- source-index.json：每个原生调用/回答的行号、Turn/Item ID，每个出站请求的序号和hash。
- evidence-summary.json：有效会话选择、成本、判断及资源极值。
- paired-audit-resumed.json / continuation-audit-resumed.json / diagnostic-audit-resumed.json：完整离线审计。
- research-changes.patch：本轮源码变化，独立于旧工作树改动。
