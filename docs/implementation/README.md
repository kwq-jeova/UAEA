# Implementation / Maintenance Notes

Status: IMPLEMENTATION_NOTE
Role: 局部维护导航，不决定 architecture ownership

| 正文 | 有效用途 | 历史限制 |
| --- | --- | --- |
| [Inference Trace Layer](inference/inference-trace-layer-design.md) | legacy backend的token/config/stop与trace分层 | 旧主调用/首轮实施计划不是当前Harness待办；不是App Server trajectory |
| [SQLite Python Environment](environment/python-environment.md) | stdlib隔离与SQLite smoke说明 | Windows路径/版本/空表状态是当时观察，不启动新Memory subsystem |
| [Web Network Observability](web/web-network-observability-phase1.md) | 实际请求的open/header/read、SSL/proxy/timeout诊断 | 不宣称逐阶段DNS/TLS可见，不改retry/timeout；Phase1停止点为历史 |
| [Failed Attempt Recovery](harness/failed-attempt-recovery-20261003.md) | factual history 与 provider-safe projection、同thread恢复证据 | 不删失败事实，不改Core；不是Google end-to-end验收 |
| [Rejection Recovery Observation](harness/rejection-recovery-observation-20261004.md) | 两层恢复投影、surviving constraints、真实Qwen合法HTTP重试 | recovery PASS不等于自然语言action initiation或完整Web acceptance已CLOSED |
| [生成与工具解析诊断](harness/generation-parser-diagnostics-20261004.md) | bounded pre-parser生成、stop/finish、Hermes入参/结果/异常的独立观察 | 显式启用，不修parser；fixture不是实际Qwen生成，需新人工run定位 |
| [模型可见观察边界](harness/model-visible-observation-boundary-20261004.md) | 执行事实、开放式原因、证据范围、授权作用域与恢复投影 | 不新增错误分类；投影通过不等于模型行为验收通过 |
| [Semantic Promotion Shadow Audit](harness/semantic-promotion-shadow-audit-20261005.md) | semantic item、constraint surface、projection、validation snapshot 的诊断旁路；最新 terminal 补验 PASS | 不判断自然语言正确性、不授予权威；正文保留早期待验状态 |
| [Semantic Authority Boundary](harness/semantic-authority-boundary-20261005.md) | retained interpretation 与 qualified execution constraint、投影与 validation 的共同边界 | 仅沿用已有 Web directive recognition，不宣称完整理解或 Goal 已实现；等待人工 probe |
| [投影容量回归修复](harness/projection-capacity-regression-20261011.md) | 2400 字符预算内共享重复 metadata；超预算时保留约束并局部拒绝、不退出 REPL | 原修复由 095353 七轮人工 artifact 确认；本轮续接改动仍待人工；不修旧 Action Recovery |
| [单 Workflow 事实续接](harness/single-workflow-continuity-20261011.md) | 复用 Workflow/Step、按调用去重、turn receipt、bounded continuation 与真实三轮自测 | Runtime 事实链 PASS；模型证据使用 PARTIAL；待人工验收，不进入 Goal/Memory |
| [单 Workflow 来源覆盖](harness/workflow-source-coverage-20261018.md) | 不同 eligible URL 与实际 fetch 结果关联、未获取来源计数、请求续接与原子省略 | 真实三轮计数核对 PASS；待人工验收；不代表完成研究、不规定工具计划 |
| [请求与行动依据续接](harness/workflow-request-basis-20261018.md) | 历史行动请求来源、实际搜索 query、短追问后的 bounded continuation | 来源覆盖已人工 PASS；本轮仍待新人工验证；不推断 ActiveGoal 或自动确认缩写含义 |
| [请求独立保留与行动恢复](harness/workflow-request-continuity-20261018.md) | 不依赖 Step 的用户贡献、既有 input identity、bounded history 与显式修订控制 | 032826 暴露行动请求来源的前置依赖；本轮不宣称自由自然语言修订或模型 grounding 已闭环 |

另外三份维护索引保留在 archive 原路径：[Harness](../archive/harness/README.md)、
[Phase-2A](../archive/phase2a/README.md)、[vLLM diagnostics](../archive/phase2a-vllm-diagnostics/README.md)。
主 startup/environment guide 在 [current](../current/environment/web-runtime-environment.md)，不在旧bring-up文档。

最新阶段状态以 [2026-10-05 checkpoint](../current/architecture/cognition-boundary-checkpoint-20261005.md) 为准。
各篇的旧计数、下一步和等待人工段落是当时记录；2026-10-11 容量回归修复以
[局部修复说明](harness/projection-capacity-regression-20261011.md) 及后续人工 artifact 为准，
不据此宣称 Authority Separation 整体关闭。2026-10-11 随后的只读重放及真实单工作流自测，以
[单 Workflow 事实续接说明](harness/single-workflow-continuity-20261011.md) 为准；已能完成真实三轮，
模型结论的证据充分性仍为 PARTIAL，等待人工验收。
2026-10-18 人工记录后的来源覆盖改进以 [来源覆盖说明](harness/workflow-source-coverage-20261018.md) 为准；
只补当前 Workflow 的事实与续接，不据此启动 Goal/Memory 或宣布完整认知闭环。
后续 `interactive-32768-20261018-030440` 已确认来源覆盖事实 PASS，研究推理仍为 PARTIAL。
本次增量与停止点见 [请求与行动依据续接](harness/workflow-request-basis-20261018.md)。
032826 人工验收 PARTIAL 后的独立请求保留增量见 [本轮说明](harness/workflow-request-continuity-20261018.md)。
