# UAEA Phase-2A vLLM AB Difference Report

> 范围：比较同一 Runtime contract 下，LMFBackend 与 VLLMBackend 的语义闭环差异。

## 1. 比较对象

- A: LMFBackend
- B: VLLMBackend

### 当前可用证据

- LMF：文档基线、既有 smoke 结论、backend contract tests
- vLLM：当前实际 benchmark 结果
- 当前会话未重新跑出同 case 的 live LMF baseline，因此以下 AB 结论分为“已知差异”和“未采集项”
- 当前 LMF 与 vLLM 不仅是 serving engine 不同，模型 artifact 也不同，因此这份报告不能被当作纯 backend-only 对照

## 2. A/B 结论

### A. Prompt text

Runtime 发送给 Agent 的用户输入是同一层，不是差异源。

真正的 backend 差异在于：

- LMF 走 LLaMA-Factory 的 prompt/template 处理
- vLLM 额外注入 `chat_template_kwargs.enable_thinking=false`

结论：

- **Prompt 语义不是完全同构**
- **vLLM 的有效模板更保守**

### B. Input token ids

当前 benchmark 没有记录 token ids，只记录 token counts。

因此：

- 不能证明 token ids 一致
- 也不能证明 token ids 不一致

结论：

- **当前是 UNKNOWN**
- 后续需要增加 tokenizer/rendered prompt 级诊断

### C. Generation config

已知差异：

- LMF：temperature 直接透传
- vLLM：当前代码对 temperature 有下限约束，且附加 `enable_thinking=false`

结论：

- **generation config 已经不完全一致**
- 这足以解释部分输出分歧风险

### D. Stop condition

当前 vLLM 结果：

- `L0-01`: `finish_reason=length`
- `L1-02`: `finish_reason=length`
- `L0-02`: PASS

文档基线中的 LMF smoke：

- 能返回 `stop`
- 能继续走到 `Semantic Observation` 和 `COMPLETE` Artifact

结论：

- **stop 行为存在差异**
- 当前 vLLM 更容易在结构化输出路径上提前耗尽预算或不触发正确终止条件

### E. Output structure

LMF baseline：

- capability execution success
- Semantic Observation success
- `COMPLETE` Artifact success

vLLM 当前结果：

- `L0-02`：成功
- `L0-01`：仅返回 length-capped 输出
- `L1-02`：没有 `semantic_observation_event`
- `L1-02`：没有 Artifact

结论：

- **结构化输出链路尚未等价**
- **问题主要落在 semantic observation / artifact 生成阶段**

## 3. 差异优先级

从高到低：

1. prompt template / chat template 差异
2. generation config 差异
3. stop condition / length 截断
4. checkpoint 或 serving stack 行为差异
5. runtime contract 问题

当前 runtime contract 问题优先级最低，因为：

- backend contract tests 已通过
- `L0-02` 已证明 vLLM 能走通最小读场景

## 4. 当前根因判断

更合理的判断是：

```text
同一 checkpoint 在两个 backend 上
并不是“同一条推理路径”
```

差异来源更可能是：

- 模板渲染
- tokenizer 输入形态
- temperature 处理
- thinking mode
- stop/length 边界

而不是 Phase-1 runtime 自身把 semantic output 弄坏了。

## 5. 当前未采集项

下面这些项当前都建议继续补采：

- rendered prompt text
- token ids
- stop token / eos token 命中情况
- server-side generation parameters
- top-p / top-k / repetition penalty
- server response headers / raw choices metadata

## 6. 下一步建议

不改 Phase-1 runtime 的前提下，下一步应该做：

1. 把 LMF 与 vLLM 的同 case live baseline 补齐
2. 增加 backend 侧诊断日志，记录 rendered prompt 与 tokenizer 视图
3. 先对 `L0-01` 和 `L1-02` 做模板/参数排查
4. 如果仍然 length 截断，再看 stop/eos 和 serving stack 差异
5. 再单独设计模型 artifact 对照实验，避免把 AWQ / HF 4-bit 差异混进 backend 归因
