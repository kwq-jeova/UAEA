# Phase-2A vLLM Equivalence Analysis

> 目标：判断 vLLM 是否可以作为 Phase-2A 的 inference backend，而不破坏 Phase-1 runtime semantics。
>
> 注意：该文档现在属于历史分析记录。新的归因框架请以
> `docs/phase2a-equivalence-matrix.md` 为准，它把 backend、model artifact 和
> generation profile 拆成了三个独立实验。

## 1. Current Architecture

当前链路是：

```text
Frozen Phase-1 Runtime
  -> ModelBackend / ModelClient
  -> Backend implementation
  -> OpenAI-compatible inference server
```

实际数据流是：

```text
ModelBackend.generate(InferenceRequest)
  -> InferenceResponse
  -> ModelClient.chat() compatibility layer
  -> Agent runtime parse / guard
  -> ExecutionObservation
  -> SemanticObservation
  -> WorkflowArtifact
```

Runtime 只依赖 frozen contract，不应感知 backend 名称、HTTP endpoint、模型路径、vLLM 参数或加载细节。

## 2. Frozen Phase-1 Constraints

Phase-1 已冻结的核心目标是建立可靠的 Runtime Control Plane，而不是做模型能力增强。

冻结内容：

- workflow lifecycle
- Goal / Intent relation
- cursor execution model
- capability execution
- observation model
- artifact model
- failure handling
- L0-L6 benchmark logic

不能改的接口语义：

- `runtime.agent_runtime.Agent.handle(...)`
- `runtime.config.RuntimeConfig`
- `runtime.model_client.ModelClient.chat(...)`
- `runtime.tools.ToolRegistry.execute(...)`
- `runtime.tools.execute_capability(...)`
- `runtime.semantic_observation.ExecutionObservation`
- `runtime.semantic_observation.SemanticObservation`
- `runtime.runtime_objects.RuntimeObjectStore.snapshot()`
- `runtime.ledger.LedgerStub` 事件边界

冻结验证证据以 benchmark JSON 为主，不是单独一份文本 report。当前最关键的冻结证据是：

- `D:\UAEA-phase1-runtime-v1.0-verification-artifacts\data\benchmark_results\phase1_runtime_benchmark_20260804T075329Z.json`
- `D:\UAEA\runtime\phase1-runtime\docs\phase1_benchmark_closure_report.md`

## 3. Hardware Boundary

当前可用的运行边界是：

| 项 | 值 |
| --- | --- |
| OS | WSL2 Ubuntu 24.04 |
| GPU | NVIDIA RTX5090D v2 |
| VRAM | 24GB |
| Driver CUDA | 13 |
| Torch CUDA | 12.8 |
| vLLM | 0.26.x |
| Model | `DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4` |

vLLM 已验证：

- server PASS
- `/v1/models` PASS
- `/v1/chat/completions` PASS

参数分类：

| 参数 | 分类 | 判断 |
| --- | --- | --- |
| `VLLM_USE_V2_MODEL_RUNNER=0` | A 临时 workaround | 当前 vLLM 栈兼容开关 |
| `VLLM_USE_FLASHINFER_SAMPLER=0` | A 临时 workaround | 当前 sampler 兼容开关 |
| `max_model_len=16384` | B 硬件边界 | 24GB VRAM 下的可运行上下限 |
| `gpu_memory_utilization=0.7` | B 硬件边界 | 显存预算与安全余量 |

这组参数里没有明显的 D 类“架构设计要求”；真正的架构要求是 backend 必须留在 `ModelBackend` contract 后面。

## 4. LMF vs vLLM

### LMFBackend

LMFBackend 存在的原因有两个：

1. 它是 Phase-1 冻结时的生产模型路径。
2. 它与既有 LLaMA-Factory / 训练环境一致，支持 DS14B 的 4-bit 本地服务方式。

其加载方式来自 `D:\AI_Agent_FW\scripts\api\start_lmf_api.ps1`：

```powershell
& $script:UAEA_LMF_API_CLI api `
    --model_name_or_path $script:UAEA_MODEL_PATH `
    --template $script:UAEA_LMF_TEMPLATE `
    --infer_backend $script:UAEA_LMF_INFER_BACKEND `
    --quantization_bit $script:UAEA_LMF_QUANTIZATION_BIT
```

对应环境里，模型配置是：

- model path: `D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B`
- template: `deepseek3`
- infer backend: `huggingface`
- quantization: `4`
- endpoint: `http://127.0.0.1:8000/v1`

### VLLMBackend

VLLMBackend 的定位不是替换 Phase-1，而是替换 inference backend 实现。

当前 contract 一致点：

- 输入：`InferenceRequest`
- 输出：`InferenceResponse`
- 元数据：backend / model / finish_reason / usage / latency_ms

vLLM backend 的差异只应停留在 backend config 内：

- `base_url`
- `model_name`
- timeout
- API key
- vLLM 启动参数

Runtime 侧不应直接看到这些字段。

## 5. Model Output Path

当前模型输出进入 Runtime 的路径是：

```text
Backend response
  -> ModelClient.last_response / last_finish_reason / last_usage
  -> Agent._inference_metadata()
  -> semantic_observation_event payload
  -> runtime_objects.record_workflow_artifact(...)
```

这意味着：

- `InferenceResponse.metadata` 可以进入 semantic observation event
- artifact schema 不需要改
- backend 元数据属于 observation payload，不属于 artifact schema

## 6. Current Benchmark Result

### Frozen baseline

- unit tests: `22/22 PASS`
- Phase-1 scripted benchmark: `PASS`
- frozen Phase-1 closure: `24/24 PASS`
- real-mode L6 baseline: `5/5 PASS`

### vLLM benchmark

当前结果：

| Case | Result | 现象 |
| --- | --- | --- |
| `L0-02` | PASS | vLLM backend 可完成最小 read 场景 |
| `L0-01` | FAIL | `finish_reason=length`，两次 `chat_answer` 都被截断 |
| `L1-02` | FAIL | `finish_reason=length`，未生成 `semantic_observation_event` / Artifact |

失败文件里能看到：

- `L0-01`: 两次调用都走到 `finish_reason=length`
- `L1-02`: planner call 也被 `length` 截断，最终没有结构化 semantic output

## 7. Root Cause Hypothesis

优先级判断：

1. **prompt template / structured output mismatch**，概率最高  
   证据是 `L1-02` 没有产出可解析的 semantic package，而不是 transport 失败。

2. **generation parameter problem**，概率较高  
   `L0-01` 和 `L1-02` 都是 `length`，说明当前生成预算或采样配置没有稳定终止结构化输出。

3. **checkpoint behavior difference**，中等概率  
   同一任务在 LMF 与 vLLM 路径上可能出现不同的输出收敛性，尤其是 AWQ + vLLM 的组合。

4. **serving / runtime contract problem**，低概率  
   原因是 `/v1/models`、`/v1/chat/completions`、backend contract tests 都已通过，问题更像生成语义而不是服务连通性。

## 8. Recommended Next Steps

建议顺序：

1. 先保留 frozen contract，不改 Phase-1 架构。
2. 用同一组 case 对照 LMFBackend baseline，确认差异是不是只出现在 vLLM 路径。
3. 检查 vLLM 的 prompt template、chat template、stop 行为和 sampling profile。
4. 只在 backend config 层调整 generation 参数，不把参数下沉到 Runtime。
5. 若结构化输出仍不稳定，再把问题归类为 checkpoint / backend compatibility，而不是 Runtime semantics 回归。

结论先行：

> vLLM 目前已经证明可以承载 Phase-1 的 transport / contract 层。
> 但要证明它能作为 Phase-2A inference backend，还需要先把结构化输出稳定性补齐。
