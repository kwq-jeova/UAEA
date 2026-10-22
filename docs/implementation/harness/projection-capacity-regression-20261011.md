# Pre-turn Semantic Projection 容量回归

Status: IMPLEMENTATION_NOTE
Role: Authority Separation 的局部容量回归修复，不是新的 cognition 阶段
自动与结构验收：PASS；本轮新进程人工验收：待执行
Authority Separation 整体仍为 PARTIAL

## 根因与有限修复

原用例为“仅使用 Google 搜索 AI agent，不要使用 Bing，不要使用 DuckDuckGo，禁止 fallback。”，
thread_id 使用 36 字符的真实长度。修复前未裁剪 payload 为 3096 字符，削减辅助 context 后
仍为 3033 字符，超过默认 2400 字符预算。异常发生在 App Server 请求前，原 REPL 未捕获，
因此可能退出并清理运行进程。旧投影 1395 字符是前次审计基线，不是新 authority contract。

只在原 payload 超预算时，共享所有 binding 中完全相同的 kind、owner、scope、strength、
authority_level、provenance。共享字段位于 semantic_binding_defaults；各 binding 的 item_id、
key、value、独立 promotion_basis 保留原样。展开规则是共享字段与单项字段的合并，单项优先。
不同来源、owner 或 scope 不会被合并；完整 metadata/native provenance 仍在 snapshot。
这些共享字段是原 metadata 的传输表示，不是新的 authority 默认值或 promotion policy。

io_contract 展开每条 binding 后，继续调用原 has_execution_authority，校验 USER_INPUT 来源和
promotion basis 的 input_id/key/value 一致性。缺依据、篡改依据、来源不匹配以及不允许的共享
字段不能增加权威。旧 inline binding 格式仍支持；原来已经在预算内的 payload 不改变。
模型可见的 application entry 保留共享字段和单项记录，不在传输时重新展开造成重复膨胀。
interpretation 仍走 untrusted entry，不能混入 execution constraints。

默认预算仍是 2400。原失败用例修复后完整 payload 为 2314 字符；拆分后的两个 semantic
context value 合计 2393 字符，四条 constraint 完整。预算仍计量 SemanticProjection 的 JSON
字符数，不是全部 additionalContext 的大小，更不是模型 context window/token 预算。
尚未压缩到预算内时沿用既有辅助 context 裁剪；完整解释记录仍保留在 semantic state。

## 真正超预算时的边界

- 不裁剪 qualified constraint、scope、authority 或必要 provenance 来勉强执行。
- 抛出专用 ProjectionCapacityError，携带 required_chars/budget_chars。
- REPL 只捕获这一容量异常，不发送 turn/start，不创建伪 TURN_COMPLETED，不关闭会话或 inference。
- 已接收到的输入和更新后的 semantic state 保留；不自动撤销指令，不回滚成旧权限。
- 清空本次 transport context，避免把旧 additionalContext 当作已送达的新投影。
- semantic-state-snapshots.jsonl 追加并 flush 一个本地 PRE_TURN_REJECTED 诊断记录，带 input_id、
  空 native turn_id、prior_turn_id、容量信息、app_server_requested=false 和 snapshot。
  snapshot.last_projection 是以前准备的投影，不代表本次送达或已经执行。
- 该诊断标签不属于 Harness event enum，不进入 POST_TURN，也不伪造 canonical Harness stream。
  诊断写入失败只显示异常类名，不使 REPL 退出。

大量独立来源/较长 identity 仍可能超预算。此时普通续问不会自动清除有效约束以绕过预算；
用户明确修订或撤销适用约束后，同一 thread 可继续，或者使用新 thread。
不保证任意规模的 semantic state 都能装入 2400 字符。

## 验证与未改变的 ownership

新增 13 项 targeted tests：原多约束用例、不同 provider/作用域、逐项无损展开、多来源不混淆、
模型可见 application/untrusted 分层、basis/source 篡改拒绝、普通投影兼容、跨 turn 持续、
容量耗尽不丢约束、不请求 Harness、不退出 REPL、不混淆旧 projection、合法修订后继续，
以及诊断 flush/写入异常保护。

相关 regression 136 项通过；full unittest 349 项中 343 项通过、6 项按既有条件跳过；
WSL 相关 tests 64 项通过。py_compile 和 git diff --check 通过。
静态 AST 对照确认 authority predicate、promotion basis producer、extraction、scope/relation、
effective view 与 action validation 未改变。provider history、responses bridge、dynamic adapter、
Web provider/capability、启动脚本未修改。没有更改 Core、8001/8002 参数、网络或授权规则。

最新既有 canonical artifact interactive-32768-20261011-072124 的 425 条记录/3 个 turn
只读校验通过，文件 SHA-256 未变；这不是新模型行为验收，没有新增 HTTP/model 请求。
原 Action Recovery 不稳定未修复，也不能由本轮自动测试推断为 PASS。
datetime.utcnow 的既有弃用提示不影响测试；本轮不扩大范围治理时间 API。

## 最小人工验收与停止点

新进程、新 thread 使用既有入口。若 8002 被旧会话占用，先在原 REPL 输入 exit，不启动第二套 inference。

```bash
cd /mnt/d/UAEA
bash scripts/start_h3_harness_interactive.sh --turn-timeout 420
```

一组两轮：

1. 仅使用 Google 搜索 AI agent，不要使用 Bing，不要使用 DuckDuckGo，禁止 fallback。
2. 继续查一个近期研究，论坛和商业发布资料都可以。

观察点：

- 第一轮应进入 turn/start，而不是容量异常/REPL 退出；第二轮仍可在同一 thread 输入。
- canonical trajectory 的 PRE_TURN_CONTEXT/raw turn/start 中四条 constraint 完整；共享字段
  展开后的 authority/scope/owner/input_id 与 semantic-state-snapshots.jsonl 对应。
- application 仅携带 qualified constraint；source preference/interpretation 若被投影，必须
  位于 untrusted entry；被预算裁掉的辅助信息仍可从 snapshot 追溯，不能变成执行禁令。
- semantic-promotion-audit.jsonl 中 binding item_id 与当前 effective view 对应；
  validation 应继续保持 Google 与禁止 fallback。合法搜索参数为 provider=google、allow_fallback=false。
- 模型若遗漏参数或拒绝重试，记录为独立 Action Recovery 问题；网络失败亦不证明容量修复失败。
- 两轮完成应各有真实 terminal event，不把本地 PRE_TURN_REJECTED 诊断当作 Harness 完成事件。

人工结果回来前，不关闭 Authority Separation 整体阶段，不进入 longitudinal cognition/Goal/Memory。
