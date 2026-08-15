# UAEA Phase-2A Equivalence Matrix

> 目标：把 migration 验证拆成三个独立实验，避免把 backend、model artifact、generation profile 混为一谈。
>
> 当前权威更新：Phase-2A 从 migration mindset 转为 platform abstraction mindset。
> C 实验是最终迁移验证；A/B 实验是诊断实验。

## 1. 实验切分

### Experiment A: Backend Equivalence

固定模型 artifact，只比较 backend。

```text
same checkpoint
  -> transformers / HF loading path
  -> vLLM backend path
```

关注点：

- prompt rendering
- tokenizer input view
- generation config
- stop / eos behavior
- output structure
- semantic observation generation

这里的比较对象是：

- LMFBackend / HF 4-bit path
- VLLMBackend / vLLM engine path

但前提是同一个 model artifact。

### Experiment B: Model Artifact Equivalence

固定 runtime/backend，只比较模型 artifact。

```text
same backend
  -> HF 4-bit checkpoint
  -> AWQ / compressed-tensors checkpoint
```

关注点：

- tokenizer identity
- config compatibility
- quantization behavior
- generation stability
- semantic drift

这里比较的是模型 artifact，不是 serving engine。

### Experiment C: Full Migration Equivalence

比较完整生产路径。

```text
LMF original path
  vs
vLLM production path
```

这是最终关心的实验，但它同时改变：

- serving engine
- model artifact
- generation profile

因此它不能作为根因定位实验，只能作为最终系统等价性实验。

## 2. 当前已知事实

### Phase-1 frozen baseline

- Phase-1 runtime 已冻结
- `ModelBackend` contract 已存在
- `Runtime` 不应感知具体加载方式

### LMF baseline

LMF 原始生产路径为：

```text
LMF API Server
  -> transformers / HuggingFace loading
  -> DeepSeek-R1-Distill-Qwen-14B
  -> 4-bit loading
```

已知特征：

- 生产路径稳定
- 能生成 semantic observation
- 能生成 `COMPLETE` Artifact

### vLLM baseline

vLLM 生产路径为：

```text
vLLM API Server
  -> vLLM Engine
  -> DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4
  -> compressed-tensors / Marlin WNA16
```

已知特征：

- `GET /health` PASS
- `GET /v1/models` PASS
- `POST /v1/chat/completions` PASS
- `POST /v1/completions` PASS
- `L0-02` PASS
- `L0-01` FAIL (`finish_reason=length`)
- `L1-02` FAIL (`semantic_observation_event` / Artifact 未生成)

## 3. 当前实验状态

| Experiment | Status | 说明 |
| --- | --- | --- |
| A. Backend equivalence | PARTIAL | backend contract 已通，但 semantic output 仍有分歧 |
| B. Model artifact equivalence | UNKNOWN | 当前还没把模型 artifact 变量单独隔离出来 |
| C. Full migration equivalence | PARTIAL | vLLM path 可跑通，但 semantic equivalence 未闭环 |

## 4. 当前 benchmark 缺口

当前 benchmark 还缺这些诊断字段：

- rendered prompt
- token ids
- tokenizer metadata
- generation config
- detailed stop reason

因此当前只够判断：

- transport 是否通
- contract 是否通
- output 是否大致对齐

但还不够判断：

- 为什么同一 task 在不同 backend 上进入不同 semantic output 路径

## 5. 建议的 Inference Trace Record

建议在 backend adapter / benchmark 诊断层增加：

```json
{
  "backend": "lmf|vllm",
  "model_artifact": "hf-4bit|awq|compressed-tensors",
  "tokenizer": "tokenizer identity or path hash",
  "rendered_prompt": "...",
  "input_tokens": 0,
  "input_token_ids": [],
  "generation_config": {
    "max_tokens": 0,
    "temperature": 0.0,
    "top_p": null,
    "top_k": null,
    "stop": [],
    "enable_thinking": false
  },
  "output_tokens": 0,
  "finish_reason": "stop|length|error",
  "latency_ms": 0.0
}
```

### Why this matters

这个记录不是为了让 benchmark 变复杂，而是为了让后续 migration 可以定位到底是：

- prompt 差异
- tokenizer 差异
- generation 差异
- stop 条件差异
- 模型 artifact 差异

## 6. 当前阶段建议

1. 先把 Experiment A 做成可重复的 backend-only trace 比较。
2. 再把 Experiment B 单独隔离成 artifact-only trace 比较。
3. 最后才做 Experiment C 的完整迁移等价性结论。

## 7. 当前结论

现在不能直接说：

```text
vLLM 导致 semantic 差异
```

更准确的说法是：

```text
当前 full migration 结果出现 semantic 差异
需要拆分 backend / artifact / generation 三个变量后再归因
```

## 8. Platform Abstraction Update

Phase-2A 当前抽象目标：

```text
Cognitive Runtime Freeze
  -> Inference Runtime Abstraction
  -> Replaceable Inference Backend
```

### Experiment A: Backend Equivalence

固定变量：

- model artifact
- tokenizer
- generation config
- prompt content
- benchmark case

比较变量：

- HF / transformers backend
- vLLM backend

目标：

```text
Same model artifact + same tokenizer + same generation config
  -> compare serving engine behavior
```

判定面：

- rendered prompt 是否一致
- input token ids 是否一致
- finish reason 是否一致
- output structure 是否满足 Runtime semantic contract
- semantic observation / artifact 是否生成

### Experiment B: Artifact Equivalence

固定变量：

- Runtime
- backend
- tokenizer policy where possible
- generation config
- benchmark case

比较变量：

- HF 4-bit checkpoint
- AWQ / compressed-tensors checkpoint

目标：

```text
Same backend + same generation config
  -> compare model artifact behavior
```

判定面：

- tokenizer identity
- model config compatibility
- quantization behavior
- semantic output stability
- Artifact status distribution

### Experiment C: Production Migration

真实生产路径：

```text
LMF original path
  -> LMF API Server
  -> transformers / HuggingFace loading
  -> DeepSeek-R1-Distill-Qwen-14B
  -> 4-bit loading

vLLM production path
  -> vLLM API Server
  -> vLLM Engine
  -> DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4
  -> compressed-tensors / Marlin WNA16
```

目标：

```text
Real migration validation
```

限制：

Experiment C 同时改变 engine、model artifact、quantization format、
generation profile 和 chat template behavior。因此 C 的失败不能直接归因
为 vLLM engine 问题。

## 9. Required Trace Fields

后续 A/B/C 都应依赖 `InferenceTraceRecord`，至少包含：

- backend
- model_artifact
- model_version
- tokenizer
- rendered_prompt
- input_tokens
- input_token_ids
- generation_config
- output_tokens
- finish_reason
- latency_ms
- error

详细设计见：

```text
docs/inference-trace-layer-design.md
```

## 10. Current Status

| Validation Surface | Status | Note |
| --- | --- | --- |
| Transport | PASS | vLLM API 已响应 |
| Backend contract | PASS | `InferenceRequest -> InferenceResponse` 已通 |
| Phase-1 freeze | PASS | Runtime 核心不改 |
| Semantic equivalence | NOT PROVEN | `L0-01` / `L1-02` 仍失败 |
| Backend-only equivalence | NOT PROVEN | 需要 Experiment A |
| Artifact-only equivalence | NOT PROVEN | 需要 Experiment B |
| Full migration equivalence | PARTIAL | 需要 Experiment C 完整闭环 |
