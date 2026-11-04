# UAEA R1 — Information Dependency 最小建模与验证
日期：2026-11-03（Asia/Shanghai）  
结论：**R1离线观察边界限定PASS；整体PARTIAL。可以将研究重心转向R2最小问题定义，尚未实施R2。**

## 1. 最小模型与独立判断

复用R0的38个实体、22条关系及原记录定位，不改R0，不建立公共类、Pool、数据库或正式Schema。
仅在同一个已选历史运行中补取两次同内容Fetch作为反例。脚本不导入UAEA实现，
只读历史文件/SQLite，并在独立研究目录输出结果。

分类不是互斥枚举，而是几项分开的判断：

| 轴 | 含义 | 不等价于 |
| --- | --- | --- |
| new_external_event_at_origin | 受审计原始Host输入或实际执行观察发生过；身份按运行/种类/原生ID界定 | 每次回显都新增事件、信息内容全新、统计独立 |
| derived_information | 已知摘录/投影/模型生成的解释或提议 | 原文支持、真实、完整父依赖已知 |
| repeated_reference | 同一来源/Observation的再次表示；相同内容重访另加标记 | 必须删除重复事件、重复获得独立支持 |
| endogenous_model_record | Claim、Goal提议、Compaction、Action Proposal来自模型行为 | 可作为自身Goal的外部验证目标 |
| known_external_anchors / dependency_completeness | 记录可证明的已知来源锚点，与完整依赖是否已知分开 | 已列父节点穷尽真实推理 |
| statistical_independence | 本轮一律UNKNOWN，不计算 | “没有已知依赖边”或“ID/URL不同”证明独立 |
| additional_external_support | 派生/内生/传输记录不可充当新增外部观察；原始事件是否提供独立支持UNKNOWN | 一切记录都无价值或合法控制没有状态效力 |

external_target_candidate只是**对象种类上的候选**，不是R2样本已准入。
新外部事件也可受模型选行动/历史策略影响；执行观察不是自动外生于Goal的IID样本。
Host控制及采纳决定单独保留为状态/目的控制，不能冒充世界Evidence，也不被本研究撤销。

VERIFIED：以下具体记录的来源、复用、供给及事件发生。
DESIGN INTENT：未来研究仅按合法观察边界引用这些信息，保持模块独立。
HYPOTHESIS：该边界能改善Goal候选的未来观察预测评价；尚无效果实验。
UNKNOWN：模型实际使用、完整语义依赖、相关性/独立性、真实长期意图。
CONFLICT：用模型复述/确认措辞作为其自身Goal的外部支持，或用引用直接增权。

## 2. 三组真实案例

### D1：同一Observation多次表示，以及相同内容的两次真实访问

A运行：
/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/goal-compat-active-20261102T124823Z/bolt/harness/

- execution-contract.trajectory.jsonl:2的Observation
  execution:86d268b5d05de9e571727f20848a5926bc78862488432e21486ebddc4808ff5b
  对应app-server-events.jsonl:182的调用、:183的结果回显。
- model-http-audit.jsonl:5 /request/input/7供给该call的结果。
  R0已验证821字符摘录及内容hash；R1复核R0定位版本，
  将摘录、回显、投影关联到同一实际Observation，不产生三次外部观察。
- 原始事件可入观察候选；派生表示排除为“新增外部支持”。
  这只在离线序列生效，不是新增生产Runtime防重复计权机制。

C运行：
/home/wqkan_wsl/uaea-n1x/runs/h3-results/interactive-32768-20261102-065220/

- execution-contract.trajectory.jsonl:12、:32是两次实际web.fetch，
  原生调用分别在app-server-events.jsonl:179、:3171。
- Observation分别为：
  execution:43052826f60f04c88f08da7884ba3641ebb453e69b397251ee6a3305a35bdedc
  execution:edb2d687b366a8b1eeca01b98da0abfbde706f962ad5fefff9c5514ef991594b
- access ID分别为WEB-LIVE-2157d08c-33ee-4714-947a-58a9c140f22a、
  WEB-LIVE-76d82604-1fdc-4237-a045-2664db790ddf。
  访问时间分别06:55:23Z、07:11:01Z（2026-11-02）。
- URL相同，保存内容字节hash均为
  f88015fa68514a88b0243ba70a7d8fda59c4620b438548292377505a5cf4a1dd；
  两份历史body文件重算均一致，Host capability_called及不同原生call可核验。
- **PASS（限定）**：两次真实事件、相同内容；保留两次事件及时间，不合并成一次访问。
  **UNKNOWN**：内容的新颖性/独立信息增益、统计独立性。
  不能因为ID不同算两份独立研究证据，也不能因为hash相同丢掉真实访问历史。

证据：origin-groups.json、real-revisits.json、R0 source-index.md。

### D2：Compaction供给不能升级为外部确认

复用C运行。R0实体定位原生Compaction开始/输出/完成：
app-server-events.jsonl:1754/1757/1763及3176/3179/3185。
第二份摘要消息msg_b8c4923f2e1711d2包含“已确认搜索业务增速放缓”，
在model-http-audit.jsonl:31、:33后续请求中原文再次出现。

- 可证明的是Compaction产生模型Claim，随后该摘要再次供给模型。
- 两次摘要均归为内生派生记录，不能计作新的外部观察或“第二次确认”。
- 摘要每句话的父来源、推断是否被原文支持、模型实际采用仍UNKNOWN。
  不从摘要措辞反推所有过去输入为已知依赖。
- R0记录的4份Host快照无ActiveGoal，不能把摘要的“确认”当作权威采纳，
  也不据此声称整个系统完全无污染。
- **PASS**：内生/外部观察边界及重复供给识别。
  **PARTIAL**：只能保留已有活动/供给关系，不能恢复逐断言完整支持链。

### D3：Goal候选及自己的后续复述，不能循环自证

复用A运行。goal-events.jsonl:1为候选
goal-candidate:f40da961229a5cf884ef9b8a；
原始模型提议与后续app-server-events.jsonl:437的模型输出具有相同summary。
R0中的两个模型记录分别是初始提议和后来的一次输出，不误算为两次后续复述。

- 在后续出站请求中可以同时找到原候选ID和摘要文字（candidate-visibility.json）。
  后来summary相同只证明字段一致；不能证明模型确实从此前候选复制、信念增强或内部采纳。
- Goal候选及两个模型输出均排除为外部预测目标；不能把“再次说了同一目标”算新增外部支持。
- 账本仅有一次原始Host控制/采纳决定；后续quote错用来源正文而被拒绝。
  本轮没有观察到因复述新增采纳决定；不等于模型内部没有强化或生产系统已实现MDL防自证算法。
- **PASS（限定）**：候选/内生复述不被离线模型循环计入外部观察。
  **UNKNOWN**：完整认知依赖、模型采用程度、潜在长期意图。

证据：goal-repetitions.json、candidate-visibility.json；具体定位从R0实体locator追溯，
不用最终回答猜测未记录Tool Call。

## 3. 可确认的观察子序列与UNKNOWN

candidate-sequences.json分别记录：

1. A运行原生顺序锚点10、169、183：
   两次registered_user_entry输入，再一次实际读取结果。
   输入来自受控test_driver，不冒充自然人自由交互数据。
   原生turn/start仅用作已绑定输入的顺序锚点，不当作精确Host输入时间。
2. C运行canonical顺序8、12、32：
   一个R0已核查Web观察，再两次相同内容的真实Fetch。
   工具结果受当时模型行动与查询选择影响，必须带行动条件使用。

共6个选定事件：R0的4个来源事件，加2次同内容重访。
这不是整个运行的事件总数，未列中间事件仍被省略。
两条流只在各自记录顺序内排序；跨运行总时序保持UNKNOWN，不按不同系统时钟强行合并。
不以记录数、事件数或来源族数冒充独立样本数或信息量。

不能作为新增独立外部观察的记录：
- 模型输出、Goal候选、Action Proposal、Compaction摘要；
- 同一Observation的摘录/回显/重复供给；
- 来源引用/SQLite副本、请求传输、状态快照和采纳决定本身。
  它们各自仍有来源、控制或审计价值，“排除”不代表它们无用/不合法。

不能确定是否统计独立：
- 已核验的新用户输入和执行事件，尤其同内容重访；
- 来源完整性未知、跨运行身份不明的记录。
  后者不因未知ID而自动准入新观察。

## 4. R0缺口是否阻碍本轮

- **PARTIAL但非阻断**：同hash Revision属于旧决定/状态变化，不是新外部支持；
  R1没有把它算成Goal演化或外部预测目标，不再展开修复。
- **UNKNOWN但非阻断当前案例**：4个缺失控制来源均在旧V运行，
  与A运行已保留原始控制的Goal案例不同。声明来源不全则不能评价旧控制合法性；
  不补写原始命令，不推定非法，也不让它影响当前来源完整的观察序列。
- **UNKNOWN**：跨会话任意版本恢复、来源适用性及摘要逐断言父关系。
  这限制涉及这些记录的特定实验，不要求先统一全部Runtime对象或补齐全项目血缘。

## 5. 检查结果及原型边界

| 项目 | 判定 | 范围 |
| --- | --- | --- |
| 来源/记录版本定位 | PASS（限定） | 38个R0实体重读核验；继承R0已接受的类型映射 |
| 新事件 vs 再表示 | PASS（限定） | 共同Observation锚点；新访问但同内容的真实反例 |
| Compaction依赖完整性 | PARTIAL | 活动/供给已知，语义父来源未知 |
| 模型候选循环自证边界 | PASS（限定） | 内生提议/重复summary不计外部支持；不是模型信念检测 |
| 统计独立性/语义支持 | UNKNOWN | 不估计，不从ID/URL/文本特征判断 |
| 未知引用处理 | PASS（限定） | 旧缺失引用保留UNKNOWN，不准入外部样本 |
| R2可行性判断 | PARTIAL | 可开始最小研究问题定义；尚未训练/比较任何模型 |

r1_dependency.py在R0之上做离线映射，不修改R0或正式执行入口。
67项确定性记录/边界检查PASS、0 FAIL；其中包含38项R0定位指纹重验，
不能称作67个独立真实任务或Benchmark。
6项合成反例通过：新模型ID、摘要确认措辞、同事件新表示ID、跨run同ID、
不同URL/ID及内容特征不足以判断独立、未知身份不准入。
这些只检验保守准入/弃权规则，不是统计独立性或真实跨运行能力测试。
分类依赖受审计R0映射，不是面向任意不可信JSON的生产安全解析器。

复现：
python3 -B /home/wqkan_wsl/uaea-n1x/research-records/r1-dependency-20261103T122729Z/r1_dependency.py

classifications.json与real-revisits.json给出多轴判断，
candidate-sequences.json给出选定序列；
origin-groups.json、goal-repetitions.json、unknown-references.json提供案例依据；
source-manifest.json固定所有读入版本。
既有Host产物可信性是研究前提，hash只证明当前版本一致，不是签名或读取前历史真实的保证。

## 6. R2的最小准入建议

**可以将研究重心转向Goal Formation的最小可检验问题，无需完成全部R1–R4。**
R1提供的是足够可靠的有限观察边界，不是完整Goal理论或通用依赖图。

建议R2先定义“在时点t，仅用当时允许历史，预测下一次有来源身份的外部用户请求/任务关系”；
具体观测符号、标签/预测目标、编码规则尚待R2评审，不在本轮实施。
自然用户请求与test_driver研究提示应分层；本次受控Goal提议提示不能冒充长期意图真值。
工具结果另作为行动条件观察，不混入用户意图预测目标或当作对Goal的无偏验证。

仍需的最小前提：
- 明确候选Goal与Null模型的输入差异；当前任务、授权和可比预算保留，
  Null不等于active_goal=null，也不通过删光历史人为制造Goal收益。
- 固定t以前的可用记录，按来源锚点而非回显切分；同一来源的派生内容不能泄漏到未来目标。
- 外部目标及评价来源独立于Goal候选自身文本；不让模型输出/摘要充当真值标签。
- 预先声明行动选择/提示干预、未知依赖、缺失样本及时间顺序处理；
  只用来源完整的限定子集即可，不要求补全所有旧引用。
- 在开始数值比较前另行定义预测/编码方法及最低数据要求。
  现有67项契约检查不能替代样本规模、泛化、Goal识别质量或模型比较。

本轮没有计算有效bit、互信息、Evidence Weight、熵或MDL，
没有实现Goal Evolution、Memory Admission或Context信息瓶颈。
结论不是“已证明Goal优于Null”，而是“可以开始定义并验证这样的有限问题”。

## 7. 文件及修改范围

所有研究脚本、映射、检查及报告仅在本独立目录；仓库/冻结Runtime/Harness/G0/G1均未修改。
保留R0全部产物，不重跑覆盖R0，不启动Bolt/vLLM，不引入依赖，不Commit/Push。
最终指纹、复现及状态检查见final-verification.json、reproducibility.json。
