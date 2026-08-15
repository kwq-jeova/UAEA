# UAEA Phase-2A vLLM Migration Context Manifest

> 目标：恢复 Phase-2A vLLM migration 的当前工程上下文与技术基线。

## 1. 项目归属

- 项目：UAEA (Unified Autonomous Evolution Architecture)
- 当前工作副本：`D:\UAEA`
- 远端仓库：`https://github.com/kwq-jeova/UAEA.git`
- Phase-1 冻结子模块：`runtime/phase1-runtime/`
- Phase-1 冻结版本：`v1.0.0-phase1-runtime`
- 冻结 commit：`de0ecb0e8837c848f842a996fa2dad1c93666f2f`

## 2. Phase-1 冻结位置

Phase-1 已冻结的核心边界：

- workflow lifecycle
- Goal / Intent relation
- cursor execution model
- capability execution
- observation model
- artifact model
- failure handling
- L0-L6 benchmark logic

冻结原则：

```text
Runtime 不依赖具体模型加载方式
Runtime 只依赖 ModelBackend contract
```

冻结接口侧重点：

- `runtime.agent_runtime.Agent.handle(...)`
- `runtime.config.RuntimeConfig`
- `runtime.model_client.ModelClient.chat(...)`
- `runtime.semantic_observation.ExecutionObservation`
- `runtime.semantic_observation.SemanticObservation`
- `runtime.tools.ToolRegistry.execute(...)`
- `runtime.tools.execute_capability(...)`
- `runtime.runtime_objects.RuntimeObjectStore.snapshot()`
- `runtime.ledger.LedgerStub`

## 3. 当前硬件与运行环境

| 项 | 当前值 |
| --- | --- |
| OS | Windows 11 + WSL2 Ubuntu 24.04 |
| Python | 3.12 |
| GPU | NVIDIA RTX 5090 D v2 |
| VRAM | 24GB |
| Driver CUDA | 13 |
| Torch CUDA | 12.8 |
| vLLM | 0.26.0 |

## 4. 模型与启动边界

当前模型：

- `DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4`
- `model_type: qwen2`
- `max_position_embeddings: 131072`
- `quantization: compressed-tensors`

当前运行口径：

- 不要强制使用 `--quantization awq`
- 让 vLLM 按模型配置自动识别量化路径

当前已验证的部署边界：

- 模型类型：`qwen2`
- `max_position_embeddings`: `131072`
- 当前服务边界：`max_model_len=16384`
- 当前显存预算：`gpu_memory_utilization=0.7`

当前口径下，这个模型不是传统 `--quantization awq` 运行方式。当前 vLLM 服务依赖模型配置的自动识别路径，服务侧不应强行覆盖成传统 AWQ 运行参数。

### 已验证的 vLLM 启动形态

脚本：

```text
/opt/uaea/scripts/start_vllm_ds14b.sh
```

稳定环境变量：

- `CUDA_HOME=/opt/uaea/vllm_env/lib/python3.12/site-packages/nvidia/cu13`
- `VLLM_USE_V2_MODEL_RUNNER=0`
- `VLLM_USE_FLASHINFER_SAMPLER=0`

稳定服务参数：

- `--served-model-name ds14b-awq`
- `--dtype half`
- `--max-model-len 16384`
- `--gpu-memory-utilization 0.7`
- `--host 0.0.0.0`
- `--port 8001`

## 5. Baseline Summary

### Phase-1 baseline

- unit tests: `22/22 PASS`
- Phase-1 Runtime benchmark: `PASS`
- frozen Phase-1 closure: `24/24 PASS`
- real-mode L6 closure: `5/5 PASS`

### vLLM baseline

已验证服务层：

- `GET /health`: PASS
- `GET /v1/models`: PASS
- `POST /v1/chat/completions`: PASS
- `POST /v1/completions`: PASS

Phase-1 on vLLM benchmark：

- `L0-02`: PASS
- `L0-01`: FAIL, `finish_reason=length`
- `L1-02`: FAIL, `semantic_observation_event` / Artifact 未生成

当前 vLLM 路径的模型 artifact 是：

- `DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4`
- `compressed-tensors / Marlin WNA16`

### LMF baseline

当前保留为既有生产路径与文档基线：

- `LMFBackend` 仍然是当前 production backend
- `DeepSeek-R1-Distill-Qwen-14B`
- transformers / HuggingFace 4-bit loading
- documented smoke：成功生成 `ExecutionObservation`、`SemanticObservation`、`COMPLETE` Artifact
- 现有 LMF 启动脚本仍保留在 `D:\AI_Agent_FW\scripts\api\start_lmf_api.ps1`

## 6. 已知限制

- 当前会话未把 LMF 的同 case live baseline 重新跑一遍
- 当前 benchmark 只记录 prompt token counts，不记录 token ids
- 当前 vLLM 结果已经说明 transport/contract 可达，但 semantic output 仍不稳定
- 当前工作范围不包含 Reflection / Memory / LoRA / Truth Ledger 设计变更

## 7. 当前判断

Phase-2A 的关键问题不再是“能不能连上 vLLM”，而是：

```text
同一 Runtime contract
在 LMFBackend 与 VLLMBackend 之间切换后
semantic output 是否保持闭环一致
```
