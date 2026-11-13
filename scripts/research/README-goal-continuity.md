# 本地 Goal 连续性研究入口

这是 opt-in 研究工具，不接入正式人工入口。Harness 仍拥有 Agent Loop；不采纳 ActiveGoal，不开放 Memory 或执行权限。仅支持当前 Linux/WSL 单用户、本地文件系统和协作式单写者。

## 数据与 Scope

- 唯一候选权威为 profile/goal-journal.jsonl：保存原 Goal 事件、Host 回执、来源副本、Call/版本关系及显式 family Scope 绑定。
- writer.lock 只用于排他租约；每次写入预校验、追加并fsync。坏行、部分尾行、身份/父链/哈希不一致拒绝恢复，不回退为空状态。
- goal-research-state.json 是按 Journal 生成的每会话派生结果，**从不作为恢复输入**。
- Hashchain是本地完整性检查，不是签名/防管理员篡改，也不能单独发现整个合法尾部被删除的历史回滚。保留外部检查点/备份用于复核，不自动合并或修复。
- 旧版本、原Thread、原owner和来源身份不改写。新Thread只见显式绑定为global的family；local默认只在原Thread可见。
- 新form默认local。全局/局部是Host研究关联，不是模型从关键词推断的真值，不改变候选语义或授予执行权。
- 新Thread修订global时，新版本具有新Thread/当前Input身份，父版本仍为原真实版本。CURRENT quote仍只匹配当前登记输入；历史input_ids只是另一种依据，不替代CURRENT。
- 不恢复旧Workflow/Step为新执行，不把旧Observation重新发作工具结果。旧Evidence身份/关联留作历史。
- 原始Native文件缺失/变化时，视图标记unavailable/mismatch。保留的Host副本与候选不因此成为已证实事实；损坏canonical Journal则拒绝恢复。
- 当前视图4200字符、最多3head，历史/依据有界省略并标记。不无条件注入完整历史。
- 沿用原研究通道Thread可见集合最多32候选版本、单Turn最多2次接受的限制（不是Profile总版本上限；包含该Thread可见global family的历史版本和本Thread local版本，其他Thread不可见local版本不计入）；Journal目前16MiB、单条2MiB。达到限制即停止并报告，未建设无限长期维护或自动轮换/压缩。

## 开始空白研究 profile

在WSL仓库运行：

    cd /home/wqkan_wsl/uaea-n1x/UAEA
    PYTHONPATH=.:scripts python3 -B scripts/research/goal_continuity_session.py --profile ../research-records/goal-continuity-local init

此操作只创建空Journal，不制造用户Goal。已有经审查历史可用init --bundle 路径 --global-family 原始family根ID；只支持一次已审查bootstrap，重复相同导入无写入，不合并任意历史。不要将研究脚本目标当成现实用户已认可目标。

## 按次进行真实对话

先通过现有N1X受Guard保护入口启动服务；本脚本只引用已受保护服务，不启动/改变模型。资源/AC/遥测保护必须持续生效。

将用户本轮原话保存为UTF-8文本，然后：

    PYTHONPATH=.:scripts python3 -B scripts/research/goal_continuity_session.py --profile ../research-records/goal-continuity-local turn --output ../research-records/unique-session-directory --guard /home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/实际受保护运行目录 --input /绝对路径/本轮用户输入.txt

每次建立新Native Thread；Goal从同一profile恢复，普通旧对话不会自动迁移。模型/工具仍通过原Harness执行。当前研究入口仅有只读文档与Goal Sideband，不代替正式人工入口/Web能力。需要延续复杂Task时仍须提供相关历史/证据，不能把Goal摘要当全部工作上下文。实验Turn等待420秒只限此自动研究入口，不改变正式人工等待/Workflow生命周期。

运行后按原有方式停止owned服务即可；Goal不依赖GPU或进程持续存活。不要并发打开同一profile写者。不要手改Journal或派生cache来“修正”模型。

## 查看与显式研究关联

    PYTHONPATH=.:scripts python3 -B scripts/research/goal_continuity_session.py --profile ../research-records/goal-continuity-local view --thread 任意新Thread标识

新提案默认local；研究者确认需要跨会话观察该family时，显式绑定其最初form版本ID：

    PYTHONPATH=.:scripts python3 -B scripts/research/goal_continuity_session.py --profile ../research-records/goal-continuity-local bind-scope --family goal-candidate:真实原始根ID --scope global --basis "明确的用户表达/人工研究审查依据"

这是研究检索关联，不是认可语义或正式Goal采纳。将绑定改回local也不是withdraw；真正撤回仍由模型合法提案、Host保存新版本。

## 追加长期研究反例

    PYTHONPATH=.:scripts python3 -B scripts/research/goal_continuity_session.py --profile ../research-records/goal-continuity-local note --failure-class semantics --text "关联真实Turn/Call：模型把暂停Task错误解释为Goal完成；Host未变。"

分类：store存储/恢复，projection历史投影，semantics语义，reference工具/引用，conceptual建模假设，unknown未确定，none正面观察。注释不产生Goal版本或执行事实。记录成功也记录错误、遗漏及无法归因的样本；可使用CLI函数annotate的references关联ID。

## 后续阶段与停止条件

1. 本轮只验收跨进程/Thread保存、恢复、来源/版本一致性与一次模型读回。
2. 日常多次真实对话再观察形成、纠正、Task/Goal区分；不强制每轮提案。
3. 独立研究Context变化、Compaction和来源缺失；本轮短样本不能替代。
4. 公平Goal视图ON/OFF与Relevant History对照，才评价决策增益。

每次保留Journal检查点哈希、原生事件、HTTP审计、Goal视图、源码/配置版本和失败分类。新接口收益、长期规模、稳定自主维护和M5均不由存储测试PASS推出。需要正式接入、权限/Schema或容量变更时再评审。
