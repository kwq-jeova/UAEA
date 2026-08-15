# UAEA Phase-2A Backend Equivalence Matrix

> 目的：先建立差异矩阵，不改代码，不改 frozen contract。

说明：

- `PASS` = 已验证一致
- `PARTIAL` = 只验证到部分场景
- `DIFF` = 已确认存在差异
- `UNKNOWN` = 当前没有直接证据，暂不下结论

| Layer | LMF | vLLM | Status | Note |
| --- | --- | --- | --- | --- |
| API contract | PASS | PASS | PASS | `ModelBackend -> InferenceRequest -> InferenceResponse` 已对齐 |
| Runtime injection | PASS | PASS | PASS | backend 由 Phase-2A 注入，Phase-1 不感知具体后端 |
| Model loading | PASS | PASS | PASS | LMF 走 LLaMA-Factory；vLLM 走 OpenAI-compatible server |
| Endpoint topology | `8000/v1` | `8001/v1` | DIFF | 端口与服务进程不同，属于 backend 配置层 |
| Prompt template | PASS(文档基线) | PARTIAL | DIFF | vLLM 额外注入 `chat_template_kwargs.enable_thinking=false` |
| Generation config | PASS(文档基线) | PARTIAL | DIFF | vLLM 当前代码对 temperature 做了下限约束 |
| Stop condition | PASS(文档基线) | PARTIAL | DIFF | vLLM 在 `L0-01` / `L1-02` 上出现 `length` |
| Input token ids | UNKNOWN | UNKNOWN | UNKNOWN | 当前 benchmark 未记录 token ids，只记录 token counts |
| Output structure: L0 semantic output | PASS(文档基线) | PARTIAL | DIFF | vLLM `L0-02` PASS，但 `L0-01` length 截断 |
| Output structure: L1 semantic observation | PASS(文档基线) | FAIL | DIFF | vLLM `L1-02` 未生成 `semantic_observation_event` |
| Artifact pipeline | PASS(文档基线) | FAIL | DIFF | vLLM `L1-02` 没有 Artifact 落盘 |
| Failure handling | PASS(文档基线) | PARTIAL | DIFF | transport contract 一致，但语义失败路径不同 |
| Observation metadata | PASS | PASS | PASS | 两边都能携带 backend/model/usage/latency |
| Artifact schema | PASS | PASS | PASS | 当前不改 Artifact schema |
| Benchmark closure | PASS | PARTIAL | DIFF | Phase-1 scripted closure 已冻结；vLLM 仍在收敛 |

## 现阶段结论

目前可以确认的不是“vLLM 不能接入”，而是：

- backend contract 已成立
- runtime contract 未被破坏
- semantic equivalence 仍未闭环

换句话说：

```text
backend 可替换
semantic output 仍需 AB 证明
```

