# 2026-11-05 人工会话：时间与第二研究对象授权核查

会话：interactive-32768-20261105-053257。
本轮只读分析已有JSON及源码，不改运行代码、不发新模型或Web请求、不停止服务、不Commit/Push。
74/74份运行源码hash匹配当前修复版本。不得据用户体感将研究事实质量记为PASS。

## 时间：传递成立，理解与证据使用未通过

- model-http-audit.jsonl第1个请求已包含 current_date=2026-11-05、timezone=Asia/Shanghai；后续普通请求仍包含相同环境信息。
- 用户明确的11月4日收盘要求确实进入当前请求。工具accessed_at是UTC，和Asia/Shanghai显示相差8小时不构成时钟错误。
- 第18至21个模型请求中的压缩摘要还明确保留“当前日期：2026-11-05”。
- 搜索结果保留了原始来源日期与标签性质：首批Intel结果含2025年标题，Google结果含2019年报道、2023/2025电话会议，以及2026年2月资料。年份在query中出现不保证后端所有候选属于该年/季度。
- Runtime没有把这些日期改成2026Q3；来源日期均标search_provider_label，content_period仍unknown，须由模型核对。候选可见不能当作期间符合或语义支持已验证。
- 模型在未取得11月4日价格依据时先判断估值；后续自行使用24–26美元“模拟参数”，该价格不是工具Observation。它虽标明模拟，却没有沿用用户要求的实际行情时点。
- 回答还存在独立的量纲/算术问题：16.51B曾写成16.51亿；16.54B与16.51B的差额是30M，模型写成300M。此处仅核查回答内部一致性，不验证现实财报或行情真伪。

因此：Clock/Timezone Delivery PASS；Temporal Evidence Fidelity PARTIAL/FAIL。
不能认定Runtime把当天日期传错，也不能将缺乏行情证据的问题通过“再提醒一次今天日期”视为解决。
本会话未跨天，没有证据证明是长会话时钟刷新问题。

## 网络：没有因Intel换成Google/Alphabet而失去搜索权限

Google/Alphabet研究Turn：01a1aa46-2d1c-7ab0-8d51-e10017229b6c。

- 先有5次Google搜索真实成功：execution-contract.trajectory.jsonl的Observation行32、34、36、38、44。
- 同期insiderfinance Fetch成功；Yahoo Fetch的404来自目标URL，非授权拒绝。
- 随后3次模型提案仍provider=google，但把allow_fallback设为true：
  - action_id chatcmpl-tool-a4eda5d60448cbcf
  - action_id chatcmpl-tool-8acd3ee697b2903c
  - action_id chatcmpl-tool-b0529ccfa55a541f
- Shared Decision拒绝原因准确为authorization_unknown，缺少的是provider_switch回退授权；不是整项web.search无权限。对应Canonical Observation行46、48、50，实际Tool Result在Raw Events:6077、6080、6082。
- 回传已列合法恢复：provider=google、allow_fallback=false重新请求，或询问回退授权；模型没有采用这一合法重试。
- 模型随后在Raw Events:7603/8217把局部拒绝扩大为“当前环境实时网络受限”“本会话网络未激活”，与此前成功记录不符。
- 第1个用户输入的Google provider约束仍在Host。所有阶段同一Workflow owner，但新GOOGL请求确实注入；未见对象切换导致权限状态被撤销。

Permission Decision限定PASS；Model Recovery/权限解释FAIL。
不应扩大授权或默认把模型显式true改成false以消除拒绝，也不需要用户重新授予笼统“联网权限”才能合法Google搜索。

## Runtime可以改进的确定性表达

现有拒绝恢复字段scope=unspecified、constraints_known=false、active_constraints=[]，而Host保留web.provider=google。
这是失败表达缺少已知上下文，不证明Host约束丢失。它可能加剧误解，但不能证明是模型误判的唯一原因。

最小方向：

1. 将失败作用域明确表达为“本次回退提案”，保留已知Provider约束和合法重试参数。
2. 区分“基础只读Web能力可用”与“额外Provider回退尚未授权”，仍由当前策略重新校验。
3. 不新增Google专属关键词，不静默修改显式提案，不自动扩大权限。
4. 日期方面优先验证模型是否忠实采用已有时点与来源期间；不凭此次会话新增时间语义解析器。

## 另两项问题

- 模型把uaea.recovery_sources上下文块当成recovery_sources/*.md目录，臆造3个路径进行document.read_section，继而把路径失败当网络限制证据。Raw Events:6176–6179的文件失败不能证明Web权限不可用；摘要没有提供真实存在这些文件的依据。
- 4次Fetch使用max_chars=5000，超过工具Schema的3000上限；Canonical仅记录execution_unknown/ValueError，而非清晰的参数校验提示。这是可局部改进的错误表达，不应误判成网络拒绝。

用户最后输入的是turn/cancel，它被作为普通用户消息送入原生Turn（Raw Events:8235），不是控制命令。
正确命令是 /turn cancel（前导斜杠、空格）。最新生命周期只有wait_interrupted，不能据此宣布已取消原生Turn。

## 当前判定与后续

- 时钟/时区传递：PASS。
- 合法Google搜索执行：PASS。
- 未授权回退拒绝：限定PASS。
- Runtime失败作用域/非法参数表达：PARTIAL。
- 模型时间证据使用、局部失败恢复与环境解释：未通过完整验收。
- Research Workflow：不能因Turn completed或模型声称“交叉验证”宣布PASS。

当前人工入口与不限时配置未改变。本轮无需用户立刻重复测试；建议下一步先收敛上述确定性错误表达，再进行同任务跨对象回归。
