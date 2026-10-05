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

另外三份维护索引保留在 archive 原路径：[Harness](../archive/harness/README.md)、
[Phase-2A](../archive/phase2a/README.md)、[vLLM diagnostics](../archive/phase2a-vllm-diagnostics/README.md)。
主 startup/environment guide 在 [current](../current/environment/web-runtime-environment.md)，不在旧bring-up文档。

最新阶段状态以 [2026-10-05 checkpoint](../current/architecture/cognition-boundary-checkpoint-20261005.md) 为准。
各篇的旧计数、下一步和等待人工段落是当时记录；authority 最新人工测试仍未进行。
