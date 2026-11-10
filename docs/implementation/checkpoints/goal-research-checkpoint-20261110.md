# UAEA工程与Goal研究Git检查点

日期：2026-11-10。只执行本地提交，不Push，不启动模型，不新增功能。
基点：2d8d68d26ff97a4bf007895ebef02724890fa817。
这是多轮工程/研究的阶段保存，不是完整Workflow或Goal Cognition验收。

## 提交范围

按相关性分为三个提交：
1. Harness/Web：当前时间与局部错误语义、已保存来源分段恢复/历史供给、
   Source ID不可变性、手工等待与未终止Turn身份、对应测试和历史报告。
2. N1X：常驻NVML监控补丁归档、V1/V2验证边界及回退依据。
   本机启动资产位于仓库外；本提交保存可审查patch，不复制vLLM环境/权重。
3. 研究：既有多轮Scenario Runner、离线审计、opt-in Goal候选通道、
   小型合成/历史改编Fixture、Goal/Memory研究报告与研究地图。

不提交unused投影日志、模型、环境、原始大JSONL、数据库、私人语料或凭证。
既有工作区历史保留；Phase-1子模块仍固定1f311291df027baceca40779643e5107b9eb6fb3。
原始实验轨迹及源码bundle仍在各报告指向的仓库外research-records，不声称Git包含全部实机重放材料。
实验记录中的旧HEAD+脏树hash是当时证据，不能改写为本次新Commit。

## 本次必要检查与限制

- Python AST/JSON解析、相关Markdown相对链接、源码/文档Diff空白、候选文件尺寸及凭证形态扫描通过。
  原样归档patch中的一行空白上下文会触发外层Git空白告警；该字节不改写，patch反向dry-run通过，单独记录例外。
  唯一命中是原有本地user:key负例URL，不是真实凭证。
- 当前可用夹具主回归：667项，665 PASS、2个可选vLLM CPU测试SKIP、0 FAIL/ERROR。
- 独立研究套件：83 PASS。
- 另外10个旧SQLite/语料测试依赖.gitignore排除、当前机器缺失的私人导出资料：
  测试保持不变，未算PASS，原全量失败日志保留。准确测试ID/路径见旁侧JSON。
  对应语料导入/引用函数与基点AST一致；本轮Source变更不涉及这些导入函数。
- 仅修正四处过时测试断言：近期来源排序、历史call/result合并为单事实、
  可见候选结构化计数（同时覆盖当前/legacy表面）、两次Context比较时固定Host时钟。
  没有通过降低来源/权限/Goal判据来获得PASS，也没有新增Runtime改动。
  另清除一个测试文件末尾多余空行，AST一致，不改变已执行研究套件的逻辑。
- 正确的完整发现入口需要-t .，否则tests/backend与tests/memory可能遮蔽正式同名包。
  完整入口仍要求私人夹具，不能宣称完整677项全部通过。

本轮检查与原失败日志：/home/wqkan_wsl/uaea-n1x/research-records/git-checkpoint-20261110T011442Z/
机器可读记录：[检查范围](goal-research-checkpoint-20261110.json)。

## 必须保留的研究状态

Web Research为PARTIAL；自然Goal形成、候选自主演化与实际决策增益仍UNKNOWN。
最新措辞对照5会话30轮没有Goal提案，不得将空生命周期或Turn完成当作认知闭环PASS。
Memory数学研究ResearchReserved，不开放ActiveGoal/Memory自动采纳。
真实NVML负载是V1；V2仅迟到拒绝经CPU与无模型测试，不冒充V2完整模型验收。

回退优先使用对对应提交的git revert，保留后续历史，不使用破坏性reset/clean。
Git回退不会自动修改仓库外N1X启动文件；其回退须停服后另按对应pins/patch核对。
