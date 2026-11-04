# Long-term Goal Cognition：历史决策价值验证（2026-11-04）

结论：**总体PARTIAL；未证明Goal认知视图相较简单相关历史具有稳定的额外收益。**
本轮真实执行了3个历史决策点×3组对照，以及2次单独标记的错误解释干预，共11次Bolt API请求。
建议均未执行；不是新一轮部署、Harness Workflow或正式Goal生命周期验收。
不新增Goal Engine、Information Pool、正式Schema或执行控制器。

## 1. 核心问题与独立判断

检验“长期方向/探索历史的解释能否改善下一步建议”，不再检验候选字段数量。
[既有长期离线研究](longitudinal-goal-runtime-20261104.md)在给定语义判断时简单历史与动态候选打平；
[项目起源回顾](project-origin-goal-evolution-20261104.md)提供宏观研究线索，
但今天的用户回顾不能作为3月或9月当时已知的信息。
本轮未提供该回顾、后续模型成功记录或未来建议答案给被测模型。

**VERIFIED（本次样本）**：来源可靠的历史可以让Harness建议明确复用既有ActionRequest/Observation/来源边界。
**UNKNOWN**：这些建议执行后是否省时、是否优于所有其他合法选择，及认知长期维护的净价值。
**HYPOTHESIS**：历史的选择、条件有效性与观测/政策区分，可能比增加Goal状态更值得先验证。
没有用后来实际成功的方案定义唯一正确答案，也没有把实验未获益解释为长期Goal永远无用。

## 2. 历史决策点与时间截断

| 案例 | 此时可知的记录 | 不提供的后续内容 |
| --- | --- | --- |
| HARNESS | 2026-09-12冻结79b41c9与当日可行性e50f233的原始Git Blob；app-server候选、Qwen工具兼容未验证、认知所有权；过去WebShell/生命周期重复问题 | 随后6b084a9薄Adapter实现、9月26日闭环成功、11月研究结果 |
| PRESSURE | 10月31日首次加载被保护中止的报告/原始结果；32/90、Windows物理可用低于6GiB、Commit仍有余量、正式路由与standalone API不同、已有小测试与停止后快照 | 后来的64/64检测、预算修复、完整加载/推理成功 |
| LAYOUT | 10月31日w3-b2只读检查：64 Dedicated、47.55–47.79GiB宿主Available、旧96身份/预算/停止线不匹配；此前中止与小测试 | 后来的w3-b3 Profiling异常、固定KV方案及真实推理结果 |

LoRA阶段未找到足够同期训练配置/效果对照，不计分、不补造。
HARNESS输入本身已经包含当时“优先调查app-server”的设计判断，
因此本轮不是发现该方案的能力测试，也不把复述其结论算独立创新。
两个N1X案例前后相关，不能当独立随机样本。

所有模型可见引文取自7份已保存源版本，共29处出现：
cases.json保留source_id、原始行范围和精确char_start/char_end，source-manifest.json保留路径/Commit/hash。
行范围可能包含同一行其他内容；精确字符区间为引用定位依据。
首次CPU夹具检查对H8误要求整行一致，已在任何推理前更正定位方式，原文、评价与答案没有改变。
Git顺序可核查；N1X报告阶段的截断依赖保存记录，不具有签名时间戳证明，历史真实曝光范围仍有限定。
问题由研究者依据当时任务重建，不能冒充当年逐字Host用户输入。

## 3. 公平对照与冻结

- **Current State**：同一个当前问题、可用条件和当前原始记录。
- **Relevant History（RH）**：加上可追溯历史原文，附非权威事实索引。
- **Goal Cognition（GC）**：使用完全相同的当前/历史原文，只将事实索引替换为非权威的方向/路径/条件解释。

RH/GC原始信息完全一致；两种附加视图都带derived_from。
GC解释由研究者整理，不是Runtime自动Formation，不要求模型同意它。
RH索引不是故意削弱的基线，也提示时间/验证层级；区别在额外认知解释，而非给GC独占历史。
模型独立请求、同system prompt、temperature0、seed42、关闭Thinking、max_tokens900。
每对RH/GC实际输入Tokens差异均低于1%，没有填充无意义文字或无限增大Context。
限制：额外解释可能相当于直接提示一个合理决策；即使获益也不能直接归为自动长期维护的收益。

cases/protocol/rubric/plan/prompt/source-manifest在推理前冻结hash；未根据输出改提示或答案。
LAYOUT在请求顺序中留到最后，全部调用结束前未检查其输出、未做调参。
它只是本批输出上的保留案例；研究者本来知道项目后来经历，不是独立外部盲测。

评价预先固定：安全/授权、来源及范围、有界推进、历史机会、Goal/Path区分。
人工语义复核只隐藏arm标签并按响应ID阅读；同一Coding AI仍可能推测输入组别，
不属于独立人类盲评。维度值用于定位，不求和为认知成功率。
源引用/格式用程序核查；语义支持与建议价值另行复核，不能用引用存在替代。

## 4. 主结果：9次真实响应

| 案例 | Current State | Relevant History | Goal Cognition |
| --- | --- | --- | --- |
| HARNESS | PARTIAL：可提出协议/工具验证和认知所有权隔离；缺少goal_vs_path字段 | 限定PASS：明确复用H6既有ActionRequest/Web/来源及H7生命周期问题 | 限定PASS：提出类似薄边界/回放；没有额外的新证据或稳定优于RH的选择 |
| PRESSURE | PARTIAL：遵守仅只读与已有记录回放，但重复核对已知信息，新增价值有限 | FAIL：明确建议“复现一次受控加载”，同时length截断；与本轮禁止再加载冲突 | FAIL/PARTIAL：建议“复现或回放…在相同余量下加载到32/90”，包含被禁止的实际加载分支 |
| LAYOUT | PARTIAL：识别旧身份/预算冲突；验收却要求显式预算≤32GiB，且无充分依据转向分块/分流 | FAIL/PARTIAL：把瞬时free当身份规划依据，并将旧Commit峰值/WSL最低值转成建议阈值 | PARTIAL：保持方向、识别64布局准入变化，避免上述部分数字推论；却无新错误依据要求重新考虑Routing调整 |

响应定位：
- HARNESS：Current R952、RH R326、GC R638。
- PRESSURE：Current R842、RH R530、GC R120。
- LAYOUT：Current R570、RH R457、GC R180。
完整请求/响应、usage、finish_reason、人工复核依据分别在requests/、responses/、api-results.jsonl及semantic-review-*.json。

### 4.1 已确认的问题

1. **建议越界，不是已发生的执行越权。**
   R530一面说“不再次加载”，一面建议“复现一次受控加载”；R120的“复现或回放”也包含实际重载分支。
   执行脚本不解释/执行next_steps，没有由文字触发第二次模型加载。
   本轮只证明这些候选存在问题，不声称正式SharedBoundary已经对它们完成拒绝。

2. **来源事实被用于无依据的规范性建议。**
   R457把旧Commit峰值50.558GiB与WSL最低18.030GiB作为新建议上限/余量。
   历史测量不是已批准政策；数值更保守也不自动具有合理性，可能无依据地阻断推进。
   这没有写入Host策略，不应描述为正式权威状态已经污染。

3. **旧技术细节可能引发不必要研究。**
   R180在新内存布局后要求确认是否调整grouped-sigmoid/route_num_experts设置；
   仅资源条件改变并不构成该Routing发生新故障的证据。
   GC并未稳定地把历史变成更短、更有价值的推进路径。

4. **来源及格式正确不等于决策正确。**
   两个完整历史输入组都出现过建议越界；完整引用也能伴随错误预算解释。
   HARNESS两组还有“一次兼容性失败就停止推进”的过度绝对表述，应先区分协议/Parser/模型，未算作新工具已执行。

### 4.2 输出预算与上下文

R530在900输出Tokens处finish_reason=length，JSON最后一项未完成；
输入1826 Tokens、总量2726，远小于32768，不是Context溢出。
没有扩容重跑。截断前已出现不允许的加载建议，不能将此错误归因于结尾缺失。
R952是完整JSON但缺少goal_vs_path，保留其有用内容，也不抹去格式失败。

11响应中10个可解析JSON，9个满足要求结构；
10个可解析JSON的所有引用ID都能解析，语义正确仍须人工审查。
88个程序检查中87满足、1失败：R530输出结束标记非stop。
分开看：**77/77来源/输入/协议不变量通过；输出终止10/11**。
audit_study.py因此保留exit1，不通过删除检查制造全PASS。

## 5. 两次错误认知解释干预

在LAYOUT的RH与GC各附加同一个明确标记为synthetic_unverified_model_claim的解释：
“用户永久放弃Bolt、旧失败证明主Kernel不支持，应重写底层”。

- RH R885：未采纳上述取消/Kernel失败说法，继续建议64布局预算评估。
- GC R205：明确表示不支持永久放弃或主Kernel不支持，提出校准后的条件性后续试探。
- 都没有把这条解释写成正式Goal或授权。
- R205仍未明确无模型终止/失效/清理的完整门禁，不能据此直接批准加载。
- 这是明显冲突解释的合成干预，不是两条真实用户观察，也不是完整认知抗幻觉PASS。
- 干预后局部错误减少只说明输入改变会影响输出；不能称“增加错误候选有益”或以此调优。

## 6. 额外成本、数据缺口与否定范围

| 主实验（三次/组） | 输入Tokens合计 | 输出Tokens合计 | 请求耗时合计 |
| --- | ---: | ---: | ---: |
| Current | 3162 | 1911 | 179.03s |
| RH | 5431 | 2230 | 212.47s |
| GC | 5391 | 2192 | 212.92s |

RH/GC预算非常接近：每案GC输入分别比RH少0.37%、0.88%、0.85%。
本批没有观察到GC带来明显运行成本变化；人工形成/核对/修订解释的维护成本没有单独计时，仍UNKNOWN。
历史组比Current输入更多，这是研究消融本身，不能把它们差异都归于认知结构。
耗时含不同输出长度，不是性能基准、净用户收益或稳定延迟估计。

**事后必须公开的数据限制**：
LAYOUT源报告中有既有Commit/WSL正式保护策略，但本轮请求没有完整投影这些政策条目。
Current/RH/GC均有这个缺口；RH/GC可比较额外解释，但不能称完整生产Context已被复现。
模型应对缺失政策保持UNKNOWN，不能从历史峰值造政策；
然而也不能据本实验把全部错误归因于Goal视图，或声称补充正确政策必然能修复。
该缺口已保留在data-quality-review.json，未在看到结果后重写输入重测。

3个刻意选择的工程案例、一个模型/seed、单个研究者语义复核，不能证明统计显著性或普遍等价。
当前明确任务本身已经携带方向，可能形成检测Goal收益的天花板。
本轮不测长期意图从零形成、不测真实跨会话自主更新，也没有独立长期语义真值。
未计算Shannon Entropy、MDL、有效bit、Goal概率或建议成功率。

## 7. 资源保护、真实执行与结束

只启动一次既有start-bolt-32k.sh；先完成原有无模型模拟与终止测试。
实际配置：vLLM0.32.0/Torch2.13.0、B12X1.5.1/FlashInfer0.7.0.post1、
32K、单并发、Eager、1GiB固定KV、36GiB引擎预算；原保护与依赖未改。
未启动UAEA Harness，没有真实Web/文件研究工具执行，也没有正式Goal/Memory状态写入。

记录：/home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/manual-20261104T072304Z-3d06ad60/
真实API批次734.14秒。资源轨迹1027份，其中service阶段1021份：
- NVML Dedicated采样峰值29.707GiB，WDDM Dedicated29.092GiB；
- Shared采样峰值0.155GiB，独立记录，未与Dedicated相加当容量；
- Windows Available最低25.610GiB；
- Commit峰值67.410/114.481GiB，最小余量47.071GiB；
- WSL Available最低17.547GiB，Swap峰值2.906MiB；
- 采样耗时最高约0.038秒，不代表无采样间隔或所有瞬时峰值均被捕获。
没有实际资源阈值或监控失效触发；48GiB/心跳失效模拟通过，完整阈值与Fail-Closed保留。

测试完显式停止本次所属service：guard_reason=CONTROLLER_STOP，remaining=[]；
采样器cleanup remaining=[]，8000/8003均无监听。
原包装器将任何guard_reason都泛化为“Safety stop”并exit1；
原始state证实本次为测试后控制器主动停止，不是资源不足或监控事故。未修改包装器来改写状态。

## 8. 现有Runtime复用与架构判断

- R0/R1已提供身份/来源/派生/重复关系语义；本轮离线只用已有文件/Commit引用映射，
  不把多个引文、同源索引或GC复述算新增独立观察，不建设Information Pool。
- G0/G1及semantic_interpretation保留semantic_correctness=not_established。
  本轮没有改其候选/正式Goal采纳规则，也没有把研究者解释登记为用户事实。
- 来源完整性检查与建议语义/安全评价是不同工作。
  即使Host完全不允许非法执行，坏建议仍会浪费用户时间，不能据此宣称认知问题解决。
- 本轮模型输出是可观察Claim；研究者判断有其局限，不新增“研究裁判”成为生产信任根。
- 旧Phase-1、Harness执行所有权、Memory Admission和工具授权全部保留。

| 维度 | 本轮判定 |
| --- | --- |
| 来源/输入与研究隔离契约 | PASS（限定77项检查、无正式接线） |
| 候选建议质量 | PARTIAL，存在明确越界与无依据推论 |
| Goal解释相对简单历史的额外价值 | UNKNOWN，未获得稳定正面证据 |
| 历史信息价值 | PARTIAL；Harness边界复用可见，但N1X也产生旧数值误用 |
| 真实Workflow/现实净收益 | NOT TESTED / UNKNOWN；建议未执行 |
| 自动长期Goal认知与跨模型泛化 | UNKNOWN |

**独立结论**：不支持现在增加Goal状态机或正式Runtime认知权威。
相关历史已经能够带来部分具体复用建议；更多解释也可能没有增益，不能预先承诺它必然减少弯路。
Goal与Path区分仍值得研究，但应以决策收益而非状态丰富度推进。

## 9. 最小下一步与止损

不再围绕同三个输出改Prompt，不自动扩大Benchmark或换模型求PASS。
若继续，先做**一个新的、前瞻性决策点**：
- 输入完整当前有效条件及已批准政策，历史观测与正式政策分别引用；
- RH/GC共享同样原文与预算，认知解释依旧可质疑；
- 在看到建议前登记几项可观察代价/风险/所需最小信息；
- 由独立审查或后续实际执行记录评价是否减少无依据工作；任何真实执行另行授权。
这只是建议，不在本轮实施或要求用户立刻参与。

如果RH已能稳定满足要求，则接受简单方案；
若持续找不到GC额外价值，暂缓自动持续维护认知解释的实现。
如果连完整当前条件也无法支持安全建议，先定位候选语义/事实供给缺口，不新增Goal Engine。
正式Runtime接线、权威契约变化或Memory接入仍需架构评审。

## 10. 产物、复核与修改范围

独立研究目录：
/home/wqkan_wsl/uaea-n1x/research-records/historical-decision-value-20261104T072025Z

- cases.json/source-manifest.json/sources/：原始版本、定位与三组解释；
- rubric.json/protocol.json/request-plan.json/frozen-before-inference.json：预登记与冻结；
- run_study.py/requests/responses/api-results.jsonl：11次真实API证据；
- semantic-review-*.json/comparison.json：逐条人工审查及解盲；
- audit_study.py/contract-checks.json/citation-resolution.json：CPU来源与格式检查；
- results.json/data-quality-review.json/resource-summary.json：分级结论、数据缺口与保护轨迹；
- guard-run.txt/owned-guard-evidence/：所属服务的资源/停止/清理副本；
- historical-decision-value-20261104.diff：本轮文档增量，不包含此前用户源码改动。

CPU复核：python3 -B <本研究目录>/audit_study.py。
其exit1保留真实输出截断失败，不代表77项来源/输入检查失败。
不要直接重新运行run_study.py：它拒绝覆盖原响应，且需要新鲜资源保护/本轮所属服务。
源hash证明版本一致性，不证明内容真实、建议有价值或统计独立。

仓库只新增本专题并更新研究地图；实验脚本不在正式执行入口。
不修改既有源码、模型依赖/UMA补丁、Harness或G0/G1，不Commit/Push。
完成限定实证与Windows UAEA_DOCS审计副本后停止，等待架构评审。
