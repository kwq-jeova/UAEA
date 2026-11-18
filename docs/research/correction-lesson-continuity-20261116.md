# 一次纠正到下一任务：候选教训最小连续性

2026-11-16。**通路限定 VERIFIED；实际帮助 PARTIAL，不能默认开启正式Memory。**
批次：lesson-continuity-native-20261116-v1。16个真实Harness新任务、2个真实纠正输入，34个HTTP响应完整。

## 实际实现与边界

新增 scripts/research/correction_continuity.py 的 LessonStore / LessonAdapter / LessonApp / app_for。
不是修改默认交互入口，也不是第二套Loop。显式opt-in入口内部完成提案保存与新任务检索/投影；研究脚本不读取候选正文来拼接请求，也不指定候选ID；只为审计读取快照。教训送达由项目App负责。

复用 memory.candidate.MemoryCandidate、ScopeHypothesis、EvidenceReference、memory.sqlite_store 现有Schema。
每Profile一个SQLite权威库；JSONL为审计，不是第二套可修改候选状态。来源为UAEA用户Input身份，原生Thread/Turn/Call另行保留；不把Input ID冒充原生Turn ID。
claim=工作教训；scope=何时相关；validation_requirements单项=最多一次可选低成本核查；provenance=derived。
legacy extraction_confidence固定0仅满足现有结构，不作可校准概率、可信度或检索权重，模型视图不投影此值。

correction_lesson工具只在run_correction明确入口开放提交，校验当前原文quote、实际输入/Thread/Turn、重复Call、单次纠正一条候选。
所有候选open、不可覆盖；没有隐藏、关闭、删除或Goal采纳操作。缺失/损坏来源、冲突身份安全拒绝。
新任务run_turn默认找回：纯通用字符二元片段重合、阈值2、top1；这是未经校准的工程启发式，绝不是语义真值或行业分类器。
视图包含选中候选、纠正原话、来源身份、完整候选ID清单。未选中不等于删除。仅支持最多一次已有只读工具核查，不授予新的工具权限；不由Runtime替模型判断材料够不够。
**一步限制没有被行为普遍遵守**：7/8启用样本读取多份文件。工具总预算与基线同为6次Provider请求/1536输出Tokens；本轮未用硬编码语义规则替模型拦截哪些读取是“多余”。

## 使用入口

WSL仓库内，以 PYTHONPATH=.:scripts 导入：
```python
from research.correction_continuity import app_for, LessonStore
from research.longitudinal_dialogue import check_guard
check_guard(owned_guard)  # 已有监督器需持续维护原资源/电源保护；本入口不启动模型
app = app_for(profile_db, output_dir, workspace, lesson_view=True)
try:
    app.start()
    app.run_correction(user_correction)  # 用户明确纠正入口，不是普通回答自动抽取
finally:
    app.close()
# 结束旧进程后，以同一profile新建app_for(...):
# app.start(); app.run_turn(new_task); app.close()
```

app_for自动扫描已有Markdown文件首标题提供目录；两类场景没有改代码、加行业关键词或指定正确文档。
实验关闭lesson_view仅用于对照，数据库候选仍存在。日常普通主入口尚未自动启用此研究路径。
不开放正式Memory Admission或Active Goal；未改SQLite Schema、Goal工具契约、Provider Policy或Phase-1边界。
两次纠正是研究者构造的SIM用户输入；调用、Host保存与跨任务请求真实，不伪造纠正前的模型错误事件或真实用户长期偏好。

## 行为结果：每题每条件2次

| 任务 | 基线正确 | 启用正确 | 成功读取次数（基线→启用） | 非必需读取（基线→启用） |
|---|---:|---:|---:|---:|
| 必须可用 | 0/2 | 1/2 | 4→6 | 2→4 |
| 只需到货 | 2/2 | 2/2 | 0→4 | 0→4 |
| 正式采用数量 | 2/2 | 2/2 | 6→6 | 4→4 |
| 草案当时数量 | 2/2 | 2/2 | 6→6 | 6→6 |

合计6/8→7/8；成功读取16→22，非必需12→18；启用组另有1次无效README路径尝试。
一次基线书面追加确认“是否需要查验收条款”，启用未追问，但替代为本来不需的读取；工具追问均0。
非必需读取只按完成当前事实问题的最低必要证据计成本，不把合理对照一概判为错误。
第一对必须可用样本出现错→对；第二对两组都错，不能宣布稳定因果收益。
启用组失败原话：“按条款12月8日完成安装调试验收，可在12月7日开始投入使用”。相关候选和源条款都已送达。
草案/定稿分别用D1=120、F1=80作答，两组均正确。材料是终端配置数字，验证的是版本来源错误类型，不宣称已证明所有行业通用。
8/8启用新任务找回对应候选；但在第二个纠正入口，只有采购候选时误匹配并送达了采购教训（重合3）。这是一条明确的检索边界反例。
第二条模型候选还自行写入“采购/部署”范围；one_check混入“本轮材料已足够”的当轮结论。原文保留，未自动修正。它们可能影响迁移，当前未证明是具体错误原因。

## 验证与限制

2条真实提案均Host保存；原话/quote/原生Call/SQLite逐字段一致。旧Harness进程关闭，新任务Thread不同。
16个独立分支的候选、来源、证据及关联表均与共同checkpoint完全一致，候选始终2条open，没有隐藏或改写。
38次成功读取的正文/Thread/Turn/Call与后续HTTP逐条一致；失败路径不计已读。
所有原生最终答复完整。1182条有效服务采样，Commit最低余量22.364GiB、距原停止线4.468GiB，AC持续有效，无实际资源停止，模型已停。
保留56/72 UMA、64K、1GiB KV、单并发、utilization=.65以及全部原保护。

新增CPU最终16项PASS；既有Candidate8项PASS。旧SQLite26项中16通过，10项因本地缺对话/附件夹具失败，原始日志保留，不改既有测试/源模块。
真实实验源码已冻结code-as-run；结束后增加CURRENT文本/待处理输入/原生绑定完整性/空白字段/单纠正单候选防御校验。
这部分最终CPU16项通过；最终代码在临时数据库副本重放，8个有效新任务视图与实际HTTP视图完全一致。未改提示、工具Schema或检索规则，未重跑模型。
不是假称最后加的边界保护也经过了新的真实模型测试。它们只拒绝无效输入；有效样本的通路和行为证据仍来自as-run版本。

## 下一步判断

已经接通：显式纠正→模型提案→可追溯持久化→独立任务自动找回→实际送达→工具与交付记录。
尚未建立：可靠的相关性边界、仅需一步的使用、稳定少错/少问/少做。暂不默认开启正式主入口。
先处理低相关候选被硬送和教训混入当轮结论，再研究模型已看到正确条件却推荐相反；不扩大Context、Schema或新增认知引擎。
Goal M3仍PARTIAL、M4/M5 UNKNOWN；不能用教训接通代替长期Goal决策收益。
完整原始证据在research-records/lesson-continuity-native-20261116-v1；Windows评审副本UAEA_DOCS/20261116_LessonContinuityNative。
未Commit/Push。
