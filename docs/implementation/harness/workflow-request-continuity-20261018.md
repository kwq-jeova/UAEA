# 单 Workflow 请求保留与行动恢复

Status: IMPLEMENTATION_NOTE
日期：2026-10-18
停止点：完成本轮自测后，等待人工验收；不进入 Goal/Memory。

## 根因与边界

032826 人工 run 中第二轮要求探索网页，但没有生成 Action。
从 Step 派生的 `action_request_origin` 因此为空；这不是 Google、授权或线程恢复错误。
Step 是一次行动尝试的记录，不应成为保留用户工作请求的必要条件。

本轮不把所有输入解释成已采纳的任务。保留用户贡献只证明用户说过这些话，
既不构成新权限，也不证明具体行动适用、执行成功或请求已经完成。

## 实际实现与 ownership

- `harness/request_continuity.py` 使用 Phase-1 `RuntimeObjectRecord`，
  `object_type=workflow_request_input`、owner 为既有 Workflow identity，object ID 复用 input ID。
  保留 text、input/thread/turn/item/event provenance 与操作来源，不创建平行 executor。
- `semantic_state_adapter._apply_user_input()` 在模型调用之前保存用户输入，不依赖任何 Step。
  原生事件到达后补绑 native identity，不生成第二条独立请求或证据。
- Step 的 `request_context_input_ids` 关联行动发起时可用的输入上下文；
  `ExecutionObservation` 仍沿原 call/Step identity 关联，不能据此自动推断满足了所有请求。
- snapshot 的 `workflow_continuity.request_continuity` 包含原始输入记录、保留范围及
  `fulfillment=not_established`。assistant 自述、turn completion、失败和局部成功都不能把它变成完成。
- `workflow_continuation` 持续投影初始保留输入、较早的后续输入与最近输入摘要；
  请求文本保持 untrusted。当前用户输入仍完整进入 `turn/start.input`。
- 2400 字符预算和所有有效 Constraint 优先级不变；完整原文与身份仍在 snapshot/canonical。
  本轮不推断缺失的子任务、不规定 Search/Fetch 顺序、不解析普通 assistant JSON 来执行。

## 修订与取消的有限 contract

普通自然语言统一作为非权威贡献保留，系统不凭关键词判定其已经替换、取消或完成了任务。
为验证确定的用户生命周期，本轮仅在原人工入口增加显式控制：

```text
/request append <补充内容>
/request replace <替代内容>
/request cancel
```

此控制来自用户入口，不暴露成模型可自行授予的 dynamic tool。原始命令仍作为用户输入记录。
append 保留已有贡献；replace 将旧续接记录标为 superseded；cancel 标为 cancelled。
记录不删除，结束来源通过 `ended_by_input_id` 追溯。

取消后普通“继续”只保留为 context_only，不会重新激活旧请求。
用户可明确 append/replace 开始新的请求段。替换/取消不撤销或授予 Web provider/fallback 权限；
不清除已发生的 Action/Result，也不替代 Harness 对正在执行 turn 的 interrupt/cancellation。
旧执行事实可继续用于回顾，不能被当作新请求完成的证明。

**已知限制：任意自由自然语言的修订/取消理解仍未闭环。**
没有实现通用 request interpreter、supersession 推断或子任务完成判定。
晚到的用户说明与较早说明可同时保留为证据，模型负责解释；Runtime 不宣称所有 retained 输入都是当前有效指令。
这也是没有直接把 Task Evolution 或历史请求提升为 ActiveGoal 的原因。

## 自动与重放验证

- 新增 11 项：无 Step 连续保留、后续 Action/Result 关联、重复 native identity、追加、
  替换、取消后不复活、非权威自由表达、各类 terminal、task/thread 隔离、容量与来源。
- targeted 112 项 PASS；full unittest 386 项，380 PASS、6 skip。
- 032826 canonical 只读重放：7 轮，投影为 2197 / 2296 / 2361 / 2366 / 2340 / 2391 / 2379 字符。
  第二轮请求持续投影；最终仍为 1 次实际搜索、0 次 fetch，未制造虚假 Step。
- 离线重放只证明 Runtime 投影能力，不是模型改善的行为 A/B。

真实自测入口：

```bash
python3 scripts/h3_workflow_continuity_probe.py --scenario request --turn-timeout 420
```

此探针仅替代键盘，仍使用现有 source-owned Harness、独立 CODEX_HOME、
local Qwen/vLLM、ToolRegistry、真实 Google/fetch；不强制工具调用计划。
结果须根据新 artifact 单独判定，不以助手文本作为执行成功证据。

### 本轮真实自测结果

artifact：
`D:\UAEA-runtime\h3-results\workflow-request-continuity-20261018-034618\interactive-32768-20261018-034619`

- 4 轮同一 Workflow，全部完成，canonical validation PASS。
- Google search：`call_b1194cef8fd05292`，严格 Google、no fallback、HTTP 成功，3 个 citable 来源。
- fetch：`call_bde7722c108e3737`，实际获取 `https://note.com/citizen211/n/n13cbfc0c9320`，
  result/observation/access identity 保留；Step context IDs 包含第一、第二轮用户输入。
- 第三、第四轮没有新调用。最终 discovered=3、fetched=1、unattempted=2；completion 未被模型自述改变。
- 实际 pre-turn semantic 投影为 2242、2360、2335、2337 字符，authority separation 与预算保持。
- 最终回答正确列出已获取的第一来源及剩余两个，但“仅找到链接”段落又泛称没有读取这些链接，
  局部表述仍不严谨；不能把 Runtime 事实链通过等同于模型 grounding 全面通过。
- 本次第二轮直接成功发起 Action；没有制造真实缺失 Action 的 A/B。
  无 Step 请求持续性的证据来自新增自动测试和原 032826 七轮只读重放，不冒充真实恢复成功。
- app-server 与 8002 正常停止；8001 未启动或修改。未调整网络、timeout、授权、模型或 Core。

阶段判定：请求保留/身份/投影及真实执行关联 PASS；通用模型行动恢复与自由语言修订仍 PARTIAL。
`py_compile` 与 `git diff --check` PASS；WSL targeted 112 项 PASS。
仓库文本与本轮 artifact 的实际 credential 字节检查：1354 个文件、0 处命中；不输出 key。

## 人工验收

入口不变，先完成普通四轮，不需要使用控制命令：

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

### 用例一：请求先存在，行动可晚到

1. “仅使用 Google，禁止 fallback。搜索三个与 OpenAI Agents SDK 和 Model Context Protocol 相关的公开来源。”
2. “选择其中一个，实际读取网页，并研究它对本地 agent runtime 接口设计的帮助。”
3. “继续。”
4. “总结实际取得的证据和尚未完成的工作。不要把搜索摘要说成已读取网页。”

检查 `semantic-state-snapshots.jsonl` 的 request_continuity：第二轮即有稳定 input identity，
即使没有 Step；后续 projection 的 untrusted request_history 保留此请求。
若模型生成调用，Step 的 request_context_input_ids 应包含此前请求，结果按 call ID 关联。
若模型仍只打印 JSON，则 fetched 必须仍为 0，fulfillment 不能成为 completed。
以 adapter trace、canonical tool event 和 execution outcome 核对模型声明。

### 用例二：有限的追加、修订与取消

同一会话依次输入：

```text
/request append 还需要比较调用取消机制
/request replace 不再逐个阅读网页，先基于已有证据比较接口；不能确定的内容单独列出
/request cancel
继续
```

检查旧请求保留事实但状态已 superseded/cancelled，新续接投影不把旧请求列为当前工作。
最后“继续”不能使旧请求恢复 retained；原有 Google/no-fallback Constraint 不因这些操作消失。
这只验收显式控制，不把它宣传成任意自然语言修订理解通过。

## 仍未解决

请求投影正确不保证 Qwen 产生真实 function_call；证据计数正确不保证模型停止虚构已阅读。
若 Runtime 输入/执行/观察链已完整，而模型仍不执行，应记录为模型行动或 grounding 的限制，
不通过更多 Semantic State 规则、放宽授权或自动执行普通 JSON 来追求当前 case PASS。
当前请求状态在既有运行进程内跨 turn 保留，snapshot/canonical 保存可追溯事实；
本轮未实现或验收重启后自动重建该语义状态，不把 artifact 留存等同于运行状态恢复。
