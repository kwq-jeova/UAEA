# 2026-11-05 历史供给覆盖与 Compaction 恢复修复

限定 Contract PASS；Model Behavior / Research Workflow 本轮未测。没有重新执行股票搜索、抓取页面或模型推理。
本轮仅修复已有执行/证据投影，未新增Goal Engine、Information Pool、执行控制器或模型专属规则，未Commit/Push。

## 根因与修改

此前 Shared Host 保留了 Capability 取得的摘录，但没有将实际工具结果的较短片段接回供给记录。
压缩恢复只重供给300字符，且缺少独立的历史范围；模型摘要又把已供给的文本描述为未读完。
来源列表预算收缩还会删掉后面的近期URL、保留最早URL。模型也存在与压缩无关的重复失败请求，因此不认定这是唯一原因。

本轮：

1. 复用现有Step.action，新增局部source_delivery元数据，不改原host_execution_receipt或outcome。只有规范化Tool Result回显与真实Host凭据匹配，才记录历史供给。
2. 校验调用/Turn身份、成功执行、来源ID、原始内容hash、提取文本版本、供给文本hash、前缀和范围。取得3000字符但实际只供给1000字符，不会把余下2000字符计为已供给。
3. 回显重复不重复计数；错误hash、范围、身份、缺少Host凭据、模型自称已读均不能新增供给记录。
4. 历史范围按当前Workflow内的source_event_id + content_sha256 + 提取文本版本合并，重叠只计一次，空洞不算完整；与当前恢复片段的start/end/has_more分开。
5. historical_supply.saved_text_fully_supplied仅指保存提取文本已在工具结果中供给，不证明网页完整、模型已理解、内容真实或任务完成。
6. 最新同URL快照的提取文本与旧版本完全相同时，可引用旧版本供给记录same_extracted_text_as；不合并版本、不计作独立验证，也不阻止合法刷新或重试。
7. recovery_sources仍最多三个近期URL、每段最多300字符。预算缩短当前恢复文本时，重算当前范围/hash，历史覆盖独立保留。
8. source_coverage优先保留近期Fetch尝试，再按最近发现排序；失败事实也保留。仅采用可观察执行顺序，不添加语义相关性规则。
9. 成功回显一到达即刷新恢复上下文；supplied_excerpts计数现在能够引用已核对的较短片段。Legacy没有被强制升级为Shared，也没有获得额外权威。

## 真实历史回放

原始会话：
/home/wqkan_wsl/uaea-n1x/runs/unbounded-manual/interactive-32768-20261105-021615

以原Canonical Host Observation为取得凭据，逐事件处理实际Tool Result；只在隔离研究状态中重建，不改原文件、不发HTTP、不重新执行Capability。

- 26份成功Fetch/续读工具回显恢复为26份可校验供给记录；此前摘要supplied_excerpts=0。
- 9次Compaction结束后重建下一次普通模型请求；恢复块均在现有24000字节预算内，最大20748字节。这不是模型Token计量。
- 关键案例Raw Events:5126供给0–1557，:5134供给1557–1912；:5159压缩完成后，重建第47次请求仍包含历史范围[[0,1912]]、saved_text_fully_supplied=true、next_unsupplied_start_char=null。
- 同时保留恢复摘录本身较短的当前范围。原始模型摘要中的“仍需全文”未被改写成Host事实；新投影提供独立执行依据。
- 同一案例的预算来源列表优先保留AllInvestView与Digrin，不再只列早期Reddit/Moomoo。
- 原始会话文件hash未变，ActiveGoal仍为空，Workflow完成依据仍未建立。

这些是修改后代码对真实历史记录的离线回放和拟发送请求重建，不是已经让真实模型收到新投影、更不是循环问题已通过实机验收。

## 自动验证

26个隔离模块共349项回归，0 FAIL。新增14项覆盖：

- 取得不等于供给；精确短片段和未见余文的隔离。
- 完整/部分/重叠/空洞范围；重复回显幂等。
- 坏hash、错误身份、缺失凭据、取得内容变化与畸形payload拒绝。
- 模型文字不能制造读取事实。
- 同提取文本不同快照只建立引用，不合并版本；内容改变不继承完整性。
- 旧Workflow供给不自动成为新Workflow供给。
- 恢复文本预算收缩不改变历史进度。
- 近期Fetch优先于早期发现URL。

最终Scope收敛后，受影响的5个模块100项重新通过；其余采用同轮已保存结果。
Python AST、git diff --check通过；冻结Phase-1 submodule干净；16项受保护环境/启动/旧Qwen UMA hash一致。
没有修改模型依赖、UMA补丁、监控阈值、人工不限时设置或Codex Core。

## 修改范围

- harness/evidence_provenance.py：校验回显、局部供给记录和范围投影。
- harness/semantic_state_adapter.py：接入规范化结果、区分历史覆盖与恢复文本、限制Scope。
- harness/workflow_continuity.py：来源展示的执行时间顺序。
- harness/io_contract.py：历史供给与当前恢复视图的解释边界。
- harness/responses_bridge.py：缩短恢复文本时同步范围，不触碰历史覆盖。
- scripts/h3_harness_interactive_repl.py：结果回显后及时发布更新。
- tests/test_source_reading_progress.py：新增14项定向回归。

研究目录指针：
/home/wqkan_wsl/uaea-n1x/research-records/reading-progress-repair-current.txt

该目录保留before/、this-stage.patch、replay_history.py、historical-replay.json、回归日志与hash。
工作区含前几轮未提交成果；回退应只对照本轮Diff和备份，不覆盖其他修改。

## 人工验收与剩余问题

检查结束8000/8003无监听；本轮未发出停服命令。下一次先用既有模型入口启动，再使用新Harness会话。
旧会话不热更新，也不自动恢复到新进程。

模型入口：

~~~bash
bash /home/wqkan_wsl/uaea-n1x/nemotron-bolt/start-bolt-32k.sh
~~~

另开WSL终端：

~~~bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
bash scripts/start_h3_harness_interactive.sh \
  --profile n1x --context 32768 --vllm-mode external \
  --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x \
  --execution-contract shared --goal-mode shadow --goal-projection optional \
  --reasoning-effort none --turn-timeout 0 --user-input-timeout 0 \
  --result-root /home/wqkan_wsl/uaea-n1x/runs/reading-progress-manual
~~~

复用同一研究任务即可，重点观察压缩后是否复用保存版本、是否反复从头获取、是否能说明未验证项并进入限定结论。
不强制每轮工具调用，不把减少调用次数本身当质量PASS；合理复核、刷新和重试仍允许。
已供给不等于模型实际理解或采用；不会自动纠正财务量纲、时间含义、语义支持或研究推理错误。
如果仍反复采集，应结合新出站审计区分投影缺失与模型未采用证据，不能继续用模型专属规则掩盖。
需要真正停止原Turn时使用/turn cancel并等待终结；Ctrl+C只返回控制提示。
