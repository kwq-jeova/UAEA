# UAEA Phase-2A vLLM Root Cause Analysis

Status: investigation baseline  
Date: 2026-08-12  
Scope: Phase-2A inference diagnosis only. Phase-1 Runtime semantics remain frozen.

## 1. Objective

This report explains why the vLLM path is much faster than the LMF path while
selected Phase-1 benchmark cases show pathological generation:

- repeated `!`
- `finish_reason=length`
- `L1-02` does not reach `observation_answer`
- no `semantic_observation_event`
- no Artifact

The goal is not to make vLLM pass the benchmark immediately. The goal is to
isolate the failure layer without changing the Phase-1 Cognitive Runtime.

## 2. Frozen Boundary

Phase-1 is frozen at:

```text
runtime/phase1-runtime
commit: de0ecb0e8837c848f842a996fa2dad1c93666f2f
```

Frozen Phase-1 responsibilities:

- Goal / Intent relation
- Workflow lifecycle
- Cursor execution model
- Capability execution
- Execution Observation
- Semantic Observation
- Artifact lifecycle
- Failure handling
- L0-L6 benchmark semantics

Phase-2A may extend backend adapters, trace collection, benchmark wrappers, and
diagnostic scripts. It must not add vLLM-specific logic to the Agent Runtime.

## 3. Current Architecture

```text
Phase-1 Cognitive Runtime
  -> ModelClient.chat frozen compatibility surface
  -> ModelBackend / InferenceRequest / InferenceResponse
  -> Backend Adapter
  -> Inference Platform
```

Current adapters:

- `LMFBackend`
- `VLLMBackend`
- `TransformersBackend`
- `MockBackend`

Trace is emitted by `TracingBackend` and `InferenceTraceRecord`, outside the
Phase-1 Runtime.

## 4. Environment And Artifacts

### LMF Baseline

```text
Backend: LMF API / LLaMA-Factory / HF transformers
Model artifact: DeepSeek-R1-Distill-Qwen-14B
Local path: D:\LM_Studio_Models\deepseek-ai\DeepSeek-R1-Distill-Qwen-14B
Quantization: HF 4-bit loading path, not AWQ
Tokenizer class: LlamaTokenizerFast
Chat template hash: 56a1447ad31926fdc21fb07e56e5642bd9c850c4f52d8c8af7bbe5f079a84f5f
```

### vLLM Baseline

```text
Backend: vLLM OpenAI-compatible API
Model artifact: DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4
WSL path: /opt/uaea-models/models/DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4
Served model: ds14b-awq
Quantization: compressed-tensors / Marlin WNA16 path
max_model_len: 16384
gpu_memory_utilization: 0.7
```

vLLM artifact config evidence:

- `model_type=qwen2`
- `max_position_embeddings=131072`
- `quant_method=compressed-tensors`
- tokenizer config does not embed `chat_template`
- `chat_template.jinja` exists and hashes to the same value as the LMF template

Important distinction:

```text
LMF HF 4-bit artifact != vLLM AWQ/compressed-tensors artifact
```

The current production migration changes serving engine, model artifact,
quantization format, generation profile, and template handling at the same time.

## 5. Benchmark And Trace Evidence

### LMF Phase-1 L0-L2 Baseline

Files:

- `D:\UAEA\data\benchmark_results\lmf_trace_L0.json`
- `D:\UAEA\data\benchmark_results\lmf_trace_L1.json`
- `D:\UAEA\data\benchmark_results\lmf_trace_L2.json`
- `D:\UAEA\data\inference_traces\lmf_phase1_l0_l2.jsonl`

Result:

| Level | Result |
| --- | --- |
| L0 | 2/2 PASS |
| L1 | 4/4 PASS |
| L2 | 2/2 PASS |

Trace summary:

- 15 inference records
- `finish_reason=stop` for all records
- `length_limited=0`
- `error=0`
- `input_token_ids` present
- `output_token_ids` present
- tokenizer path present
- `chat_template_hash` present
- `L1-02` generated `semantic_observation_event`
- `L1-02` generated Artifact

### vLLM Selected Phase-1 Cases

Files:

- `D:\UAEA\data\benchmark_results\vllm_trace_L0-01.json`
- `D:\UAEA\data\benchmark_results\vllm_trace_L0-02.json`
- `D:\UAEA\data\benchmark_results\vllm_trace_L1-02.json`
- `D:\UAEA\data\inference_traces\vllm\phase1\vllm_phase1_l0_l1_selected.jsonl`

Result:

| Case | Result | Main symptom |
| --- | --- | --- |
| L0-01 | FAIL | repeated `!`, `finish_reason=length`, 2 model calls |
| L0-02 | PASS | Runtime tool path passes, trace still shows repeated `!` |
| L1-02 | FAIL | no `observation_answer`, no semantic observation, no Artifact |

Trace summary:

- 6 inference records
- all `finish_reason=length`
- all `length_limited=true`
- output is pathological repeated `!`
- `input_token_ids=[]`
- `output_token_ids=[]`
- `chat_template_hash=""`
- requested planner `temperature=0.0` became effective `temperature=0.2`

## 6. API Smoke And Prompt Replay

### Diagnostic 1: Raw vLLM API Smoke

File:

```text
D:\UAEA\data\diagnostics\vllm_pathology_matrix.json
```

Scope:

- prompts: bootloader prompts, simple Phase-1-like prompts
- endpoints: `/v1/chat/completions`, `/v1/completions`
- temperatures: `0.0`, `0.2`, `0.7`
- max tokens: `32`, `128`, `512`

Result:

```text
total=72
ok=72
failed=0
finish_reason: length=62, stop=10
bang_pathology_count=0
```

Conclusion:

Raw vLLM transport/API is healthy. The vLLM API does not universally produce
repeated `!`.

### Diagnostic 2: Replay Real Phase-1 Trace Prompts Against vLLM

File:

```text
D:\UAEA\data\diagnostics\vllm_phase1_prompt_replay.json
```

Scope:

- source prompts from `vllm_phase1_l0_l1_selected.jsonl`
- bypass Phase-1 Runtime
- endpoints: chat and completion
- temperatures: `0.0`, original trace temperature, `0.2`
- max tokens: `32`, `128`, original max tokens

Result:

```text
total=108
ok=108
failed=0
finish_reason: length=91, stop=17
bang_pathology_count=54
```

Endpoint split:

| Endpoint | Calls | Finish | Bang pathology |
| --- | ---: | --- | ---: |
| chat | 54 | 54 length | 54 |
| completion | 54 | 37 length, 17 stop | 0 |

Conclusion:

The repeated `!` pathology is reproducible outside Phase-1 Runtime when real
Phase-1-style prompts are sent through vLLM chat completions. The same rendered
prompt through vLLM completions does not show high-ratio `!` pathology and can
produce structured planner-like output.

### Diagnostic 3: Chat Endpoint vs Rendered Prompt

File:

```text
D:\UAEA\data\diagnostics\vllm_chat_template_endpoint_matrix.json
```

Scope:

- selected trace records: `L0-01/chat_answer`, `L0-02/planner`, `L1-02/planner`
- compare vLLM chat messages against vLLM completions with:
  - canonical trace prompt: `<|system|>`, `<|user|>`
  - DeepSeek/Qwen chat-template-rendered prompt
  - DeepSeek/Qwen template without generation prompt
- temperature fixed at `0.0`
- `max_tokens=64`

Result:

```text
total=20
ok=20
failed=0
finish_reason=length for all
bang_pathology_count=15
```

Variant split:

| Variant | Calls | Bang pathology |
| --- | ---: | ---: |
| chat messages with `enable_thinking=false` | 3 | 3 |
| chat messages without kwargs | 3 | 3 |
| completions with canonical prompt | 3 | 0 |
| completions with DeepSeek template prompt | 3 | 3 |
| completions with DeepSeek template without generation prompt | 3 | 3 |

Conclusion:

The pathology is not limited to the vLLM chat endpoint. It is reproduced by
`/v1/completions` when the prompt is rendered with the DeepSeek/Qwen chat
template. The canonical trace prompt sent to `/v1/completions` does not produce
high-ratio `!`.

This narrows the immediate trigger to the rendered prompt format and special
tokens used by the DeepSeek/Qwen chat template, combined with the current vLLM
AWQ/compressed-tensors serving path.

### Diagnostic 4: Special Token Attractor

File:

```text
D:\UAEA\data\diagnostics\vllm_special_token_attractor.json
```

Scope:

- source: `L1-02/planner`
- endpoint: `/v1/completions`
- prompts:
  - canonical trace prompt
  - DeepSeek/Qwen chat-template prompt
  - DeepSeek/Qwen template without generation prompt
  - DeepSeek/Qwen template without `<think>` marker
- temperatures: `0.0`, `0.2`
- max tokens: `1`, `8`, `32`
- stop variants: none, EOS literal, `stop=["!"]`

Result:

```text
total=72
ok=72
failed=0
canonical: 18/18 no bang pathology, 0 starts_with_bang
deepseek_template: 12/18 bang pathology, 12 starts_with_bang
deepseek_template_no_generation_prompt: 12/18 bang pathology, 12 starts_with_bang
deepseek_template_without_think_marker: 12/18 bang pathology, 12 starts_with_bang
```

Key observations:

- canonical prompt with `max_tokens=1` starts with normal text such as ` Sum`.
- DeepSeek-template prompt with `max_tokens=1` starts with `!`.
- DeepSeek-template prompt with `max_tokens=8` produces `!!!!!!!!`.
- `stop=["!"]` causes immediate `finish_reason=stop` with empty output for
  DeepSeek-template variants, confirming `!` is the first generated token.
- Removing the generation prompt or `<think>` marker does not remove the issue.

Conclusion:

The pathological output is a first-token attractor triggered by the DeepSeek/Qwen
chat-template-rendered prompt on the current vLLM AWQ/compressed-tensors path.
It is not primarily caused by long generation, retry behavior, or Phase-1
Runtime observation/artifact logic.

### Diagnostic 5: First Token Logprobs And Token Tail

File:

```text
D:\UAEA\data\diagnostics\vllm_first_token_logprobs.json
```

Scope:

- source: `L1-02/planner`
- endpoint: `/v1/completions`
- `max_tokens=1`
- `logprobs=10`
- compare canonical prompt, canonical prompt plus BOS, and canonical prompt plus
  DeepSeek assistant suffix

Result:

```text
canonical first token: " Sum"
canonical_plus_bos first token: " Then"
canonical_plus_deepseek_assistant_suffix first token: "Okay"
```

The full DeepSeek special-token prompt returned HTTP 400 when `logprobs` was
requested, so this diagnostic cannot report logprobs for that exact prompt.
However, it proves that adding only BOS or the DeepSeek assistant suffix
`<｜Assistant｜><think>\n` to the canonical prompt does not trigger `!`.

Token ids of key special strings:

```text
! -> [0]
<｜User｜> -> [151644]
<｜Assistant｜> -> [151645]
<think>\n -> [151648, 198]
```

Conclusion:

The `!` attractor is not caused by the assistant generation suffix alone.
The trigger requires more of the DeepSeek chat-template structure, especially
the use of special chat role tokens around the Phase-1 prompt body.

### Diagnostic 6: Template Surgery

File:

```text
D:\UAEA\data\diagnostics\vllm_template_surgery.json
```

Scope:

- source: `L1-02/planner`
- endpoint: `/v1/completions`
- `temperature=0.0`
- `max_tokens=1` and `16`
- surgically vary prompt rendering:
  - canonical prompt
  - canonical prompt plus DeepSeek assistant suffix
  - full DeepSeek chat template
  - DeepSeek template with user/assistant newlines
  - DeepSeek template with user/assistant markers replaced by canonical markers
  - manual DeepSeek prompt with and without BOS
  - canonical prompt with BOS

Result:

```text
total=26
ok=26
failed=0
```

No `!` first token:

- canonical
- canonical plus BOS
- canonical plus DeepSeek assistant suffix

`!` first token:

- full DeepSeek template
- DeepSeek template with added newlines
- DeepSeek template with BOS removed
- manual DeepSeek prompt with `<｜User｜>...<｜Assistant｜><think>\n`
- manual DeepSeek prompt with newlines

Conclusion:

The necessary trigger is not BOS and not the assistant suffix alone. The trigger
is the DeepSeek role-token prompt structure applied to the Phase-1 long system
and user payload. Once that structure is used, newline changes do not remove the
first-token `!` attractor.

## 7. Generation Profile Finding

### Diagnostic 7: Minimal Trigger

File:

```text
D:\UAEA\data\diagnostics\vllm_minimal_trigger.json
```

Result:

```text
total=32
ok=32
failed=0
```

Key finding:

- `simple_plain`: no first-token `!`
- `simple_deepseek_roles`: no first-token `!`
- `long_system_plain`: first-token `!`
- `system_first_1_lines_deepseek_roles`: first-token `!`

The first line alone is enough to trigger the issue when paired with the simple
README extraction user task:

```text
You are the semantic action planner for a local runtime.
```

Conclusion:

The DeepSeek/Qwen role-token template is a trigger surface, but it is not the
only trigger. A plain prompt with an uppercase `You are ...` system-style prefix
can reproduce the same first-token `!` behavior on the current vLLM path.

### Diagnostic 8: Trigger Phrase

File:

```text
D:\UAEA\data\diagnostics\vllm_trigger_phrase.json
```

Result:

```text
total=32
ok=32
failed=0
```

Bang cases include:

- `planner_exact/plain`
- `planner_no_semantic/plain`
- `planner_no_planner/plain`
- `planner_no_runtime/plain`
- `assistant_short/plain`
- the same uppercase system prompts under DeepSeek role-token rendering

Non-bang cases include:

- `planner_lowercase`
- `json_only`
- canonical `<|system|>` / `<|user|>` wrappers

Conclusion:

The immediate trigger is more specific than "DeepSeek template". The trigger
correlates with particular input token prefixes, especially uppercase `You are`
at specific sequence positions. Lowercase `you are`, a leading space before
`You`, and canonical wrapper tokens avoid the attractor.

### Diagnostic 9: Bang Root Layer

File:

```text
D:\UAEA\data\diagnostics\vllm_bang_root_layer.json
```

Result:

```text
total=55
ok=50
failed=5
bang_token_id=0
```

The five failed calls are `logprobs=10` requests for bang-triggering prompts.
vLLM returned:

```text
HTTP 400: Out of range float values are not JSON compliant: nan
```

This is itself useful: non-bang prompts return normal logprobs, while bang
prompts fail logprob serialization with `nan`.

Key findings:

- `upper_plain`: starts with `!`
- `upper_plain_bos`: starts with `!`
- `upper_deepseek`: starts with `!`
- `lower_plain`: normal
- `json_plain`: normal
- `upper_canonical`: normal
- `lower_deepseek`: normal
- `json_deepseek`: normal
- `stop=["!"]` stops immediately with empty output for bang-triggering prompts
- `logit_bias={0:-100}` does not suppress `!` for bang-triggering prompts

Conclusion:

The generated `!` is token id `0`, and it appears as the first generated token.
The inability of `logit_bias` to suppress token `0`, plus `nan` logprob failures
for the same prompts, points below prompt rendering and adapter behavior toward
the vLLM model execution / logits / sampling path for the current artifact.

### Diagnostic 10: Token ID Replay

File:

```text
D:\UAEA\data\diagnostics\vllm_token_id_replay.json
```

Result:

```text
total=46
ok=46
failed=0
```

Key findings:

- String prompt `You are a local assistant...` starts with `!`
- Token-id prompt for the same text also starts with `!`
- Replacing the first token id `2610` (`You`) with `1446` (` You`) removes `!`
- Replacing the first token id `2610` (`You`) with `9330` (`you`) removes `!`
- Prefixing EOS token id `151643` removes `!`
- Prefixing BOS token id `151646` does not remove `!`
- Prefixing newline removes `!`

Conclusion:

The behavior is tied to the actual input token id sequence, not only to string
rendering or local prompt reconstruction. This moves tokenizer/template mismatch
from primary suspect to trigger surface.

### Diagnostic 11: Prefix Transition

File:

```text
D:\UAEA\data\diagnostics\vllm_prefix_transition.json
```

Result:

```text
total=100
ok=100
failed=0
```

Stable bang prefixes:

- `You are`
- `You are `
- `You are a`
- `You are the`
- `<｜begin▁of▁sentence｜>You are`
- `<｜User｜>You are`

Stable non-bang prefixes:

- `You` alone
- ` You`
- `you`
- `You can`
- `You should`
- `You will`
- `You must`
- `You need`
- `You have`
- `System: You are`
- `<|system|>\nYou are`

Partial bang prefixes:

- `We are`
- `The model`

Conclusion:

The issue is now localized to a small set of token-prefix transitions, not to
Phase-1 prompt length or artifact extraction semantics. `You are -> [2610, 525]`
is the smallest consistently reproduced trigger.

### Diagnostic 12: vLLM Server Tokenize

File:

```text
D:\UAEA\data\diagnostics\vllm_server_tokenize.json
```

Result:

```text
total=12
/tokenize ok=6
/v1/tokenize 404=6
server_matches_local=6
```

For key prompts, server-side `/tokenize` matched local tokenizer ids exactly:

```text
You are -> [2610, 525]
 You are -> [1446, 525]
you are -> [9330, 525]
<｜User｜>You are -> [151644, 2610, 525]
```

Conclusion:

The tokenizer branch is mostly excluded for these minimal triggers. vLLM sees
the same token ids that the diagnostic layer reconstructs.

### Diagnostic 13: Minimal Backend Compare

File:

```text
D:\UAEA\data\diagnostics\minimal_backend_compare.json
D:\UAEA\data\diagnostics\minimal_backend_compare_vllm.json
```

Result:

```text
LMF split run:
  file=D:\UAEA\data\diagnostics\minimal_backend_compare.json
  LMF ok=3/3
  LMF bang=0/3
  vLLM offline

vLLM split run:
  file=D:\UAEA\data\diagnostics\minimal_backend_compare_vllm.json
  vLLM ok=3/3
  vLLM bang=1/3
  LMF offline
```

Because the current 24GB VRAM environment cannot keep LMF and vLLM loaded at
the same time, this diagnostic is a split-run comparison. In the latest
LMF-only run, LMF produced no bang pathology:

```text
system="You are a local assistant." -> normal text, starts_with_bang=false
system="you are a local assistant." -> normal text, starts_with_bang=false
system="Return one JSON object only. Do not explain." -> normal text, starts_with_bang=false
```

In the vLLM-only run against the same script and prompts, vLLM chat reproduced:

```text
system="You are a local assistant." -> "!!!!!!!!!!!!!!!!"
system="you are a local assistant." -> normal text
system="Return one JSON object only. Do not explain." -> normal text
```

Conclusion:

The same minimal trigger appears through the vLLM chat endpoint but not through
the LMF chat endpoint. Because these were split runs on different services and
different artifacts, this still proves production-path divergence rather than
backend-engine-only causality.

### Artifact Config Finding

The current AWQ/compressed-tensors artifact has inconsistent BOS metadata:

```text
config.json:
  bos_token_id = 151643
  eos_token_id = 151643

generation_config.json:
  bos_token_id = 151646
  eos_token_id = 151643

tokenizer:
  bos_token_id = 151646
  eos_token_id = 151643
```

This mismatch is not yet proven to cause the `!` attractor, because explicitly
prefixing the correct BOS token id `151646` does not remove it. It remains a
strong artifact-quality / implementation-compatibility risk that must be
isolated before declaring a vLLM engine bug.

### Experiment A Feasibility: HF + AWQ On Current Hardware

Scope:

```text
same AWQ/compressed-tensors artifact
  -> HF / Transformers direct inference
  -> vLLM inference
```

Current hardware and memory boundary:

```text
GPU: NVIDIA GeForce RTX 5090 D v2
VRAM: 24,455 MiB
WSL RAM observed during diagnostics: about 15 GiB total
WSL swap observed during diagnostics: 4 GiB
AWQ artifact size: about 9.4 GiB model.safetensors
vLLM steady-state DS14B AWQ serving: previously observed around 17 GiB+ VRAM
```

Diagnostic attempts:

```text
D:\UAEA\data\diagnostics\awq_hf_vs_vllm_vllm_only.json
D:\UAEA\data\diagnostics\awq_hf_vs_vllm_hf_cpu_attempt.json
D:\UAEA\data\diagnostics\awq_hf_vs_vllm_hf_cuda_attempt.json
```

vLLM-only result using the same AWQ artifact:

```text
minimal_upper  -> "!"       starts_with_bang=true
minimal_lower  -> " please" starts_with_bang=false
canonical      -> " Then"   starts_with_bang=false
deepseek_upper -> "!"       starts_with_bang=true
```

HF/Transformers direct-load feasibility:

- Transformers 5.14.1 has `compressed_tensors` quantizer support.
- `compressed_tensors` 0.17.0 is installed.
- Initial HF CPU/CUDA attempts were first blocked by missing `accelerate`.
- After dependency inspection, direct CPU loading entered compressed-tensors
  load/decompress but was killed by WSL OOM. Kernel log reported:

```text
Out of memory: Killed process ... task=python ... anon-rss about 15 GiB
Free swap = 0kB during the OOM event
```

- A CUDA direct-load attempt also entered compressed-tensors
  load/decompress, then WSL/GPU interop reported memory pressure and the
  process did not produce a completed diagnostic JSON. The observed path
  implies a large transient decompression / materialization peak, not merely
  the 9.4 GiB steady artifact size.

Conclusion:

```text
Experiment A is hardware-blocked on the current WSL2 memory profile.
```

This is not evidence that the AWQ artifact is incompatible with Transformers,
and it is not evidence that the artifact itself causes `!`. It means the direct
HF+AWQ comparison cannot be treated as a safe local experiment on this machine
without changing the memory envelope or using a more constrained loading path.

Current feasibility assessment:

| Path | Feasibility | Reason |
| --- | --- | --- |
| HF + AWQ CPU-only | NOT SAFE | WSL RAM about 15 GiB; compressed-tensors decompression hit OOM |
| HF + AWQ CUDA direct-load | NOT SAFE | 24GB VRAM may fit steady state, but transient load/decompress peak is uncontrolled |
| HF + AWQ while vLLM is running | NOT FEASIBLE | vLLM DS14B AWQ already occupies around 17GB+ VRAM |
| vLLM + AWQ single service | FEASIBLE | Already validated with `max_model_len=16384`, `gpu_memory_utilization=0.7` |
| CPU-only tokenization/config diagnostics | SAFE | Does not load model weights |

Therefore, direct Experiment A should remain paused unless one of these changes
is made explicitly:

- larger WSL RAM / swap budget
- a separate host with higher RAM/VRAM
- a verified low-memory Transformers compressed-tensors loading mode
- a smaller sibling AWQ/compressed-tensors model that shares the same vLLM
  kernel path and tokenizer family for mechanism testing

## 8. Generation Profile Finding

Code evidence:

```text
D:\UAEA\backend\vllm_backend.py
```

Current behavior:

- `default_temperature = 0.2`
- `default_chat_template_kwargs = {"enable_thinking": False}`
- payload temperature is normalized with `max(requested_temperature, 0.2)`

Therefore, Phase-1 planner requests with `temperature=0.0` are not actually
honored by `VLLMBackend`; they become `0.2`.

This is an adapter-level generation profile difference. It should be documented
before being changed. It is not enough by itself to explain the `!` pathology,
because prompt replay shows both `0.0` and `0.2` can reproduce the issue through
the chat endpoint.

## 9. Performance Finding

Observed selected trace throughput:

| Backend | Typical output speed | Notes |
| --- | ---: | --- |
| LMF | about 6-8 tokens/s | HF/LLaMA-Factory path, low GPU utilization observed |
| vLLM | about 97-102 tokens/s | vLLM serving path, AWQ/compressed-tensors artifact |

Most likely explanation:

- LMF uses the original HF/transformers serving path with 4-bit loading.
- vLLM uses an optimized serving engine and an artifact prepared for
  compressed-tensors / Marlin WNA16 execution.
- The vLLM artifact is smaller/faster at inference time, and the engine uses a
  more optimized scheduling/kernel stack than the current LMF path.

This explains speed, not semantic equivalence. Faster inference does not prove
that the same prompt/template/generation/artifact behavior is preserved.

## 10. Root Cause Isolation Matrix

| Experiment | Fixed variables | Compared variable | Current status |
| --- | --- | --- | --- |
| A. Backend equivalence | same artifact, tokenizer, prompt, generation config | HF/LMF vs vLLM engine | HARDWARE-BLOCKED locally for DS14B AWQ |
| B. Artifact equivalence | same backend, prompt, generation config | HF 4-bit vs AWQ/compressed-tensors | NOT PROVEN |
| C. Generation profile | same artifact, backend, prompt | temperature, max tokens, stop/eos, penalties | PARTIAL |
| D. Tokenizer/template | same artifact, backend, generation config | chat template, rendered prompt, token ids | PARTIAL |
| E. Production migration | real production paths | LMF original vs vLLM production | PARTIAL / FAIL for selected semantic cases |

The current selected vLLM benchmark is Experiment E, not Experiment A. It cannot
identify vLLM engine behavior in isolation.

## 11. Layer Assessment

| Layer | Assessment | Evidence |
| --- | --- | --- |
| Layer 1: Transport/API | mostly excluded | health/models/chat/completion work; raw API 72/72 OK |
| Layer 2: Backend adapter | confirmed difference | adapter forces effective temperature >= 0.2 and uses chat endpoint |
| Layer 3: Generation configuration | contributing difference, not primary trigger | temperature differs from planner request, but `!` appears at first token for both `0.0` and `0.2`; max-token length only amplifies repetition |
| Layer 4: Tokenizer / chat template | trigger surface, mostly excluded as root cause | `/tokenize` matches local ids; string and token-id replay behave the same; DeepSeek template is not the only trigger |
| Layer 5: Model artifact / quantization | strong suspect | pathology is observed on AWQ/compressed-tensors artifact; artifact has BOS metadata mismatch; LMF HF 4-bit path baseline does not show benchmark-level pathology |
| Layer 6: Inference engine / kernel / model implementation | strong suspect, not fully isolated | token-id replay, `logit_bias` non-effect, and `nan` logprobs point below adapter/template; need same-artifact and alternate-kernel isolation |
| Layer 7: Phase-1 Runtime | mostly excluded for pathology | prompt replay bypasses Runtime and reproduces chat endpoint pathology |

## 12. What Is Confirmed

- Phase-1 Runtime freeze boundary remains valid.
- LMF L0-L2 baseline is stable and trace-complete.
- vLLM transport and OpenAI-compatible API are operational.
- vLLM is much faster on the current artifact and serving stack.
- vLLM selected semantic failures are reproducible outside Runtime when real
  Phase-1-style prompts are replayed through chat completions.
- `VLLMBackend` currently changes effective temperature from `0.0` to `0.2`.
- vLLM `/completions` with canonical trace prompt does not produce high-ratio
  `!` pathology.
- vLLM `/completions` with DeepSeek/Qwen chat-template-rendered prompt does
  reproduce high-ratio `!` pathology.
- Plain prompts such as `You are a local assistant.` also reproduce first-token
  `!` on the current vLLM path.
- The minimal stable trigger includes token sequence `You are -> [2610, 525]`.
- Server-side `/tokenize` matches local tokenizer ids for the minimal triggers.
- String prompt and token-id prompt replay produce the same bang/non-bang split.
- Changing only the first token from `You` to ` You` or `you` removes the
  attractor.
- `logit_bias={0:-100}` did not suppress `!` for bang-triggering prompts.
- `logprobs=10` returns `nan` serialization errors for bang-triggering prompts
  while non-bang prompts return normal first-token logprobs.
- The `!` token is generated as the first token for DeepSeek-template prompts.
- `stop=["!"]` stops immediately with empty output for DeepSeek-template prompts,
  confirming the first-token attractor.
- The `!` token id is `0` in the local tokenizer.
- `<｜User｜>` is token id `151644`; `<｜Assistant｜>` is token id `151645`;
  `<think>\n` is token ids `[151648, 198]`.
- Adding only BOS or only `<｜Assistant｜><think>\n` to the canonical prompt does
  not trigger `!`.
- Using the DeepSeek role-token prompt structure with the Phase-1 prompt body
  does trigger `!`, even when newlines are inserted or BOS is removed.
- Current vLLM benchmark trace does not prove tokenizer/token-id equivalence,
  but the standalone `/tokenize` diagnostic proves equivalence for minimal
  trigger prompts.
- Current production comparison changes multiple variables at once.

## 13. Strong Hypotheses

1. The immediate trigger is a small set of input token-prefix transitions,
   especially `You are -> [2610, 525]`, causing a first-token token-0 (`!`)
   attractor on the current vLLM AWQ/compressed-tensors path.
2. Model artifact/quantization and vLLM implementation/kernel behavior are now
   the leading suspects. The current evidence points below adapter/template
   because string and token-id replay match, `/tokenize` matches local ids,
   `logit_bias` does not suppress token 0, and logprobs fail with `nan` on
   bang-triggering prompts.
3. Generation profile mismatch contributes to non-equivalence, but it is not
   the primary trigger for `!`: both `temperature=0.0` and `0.2` show the
   first-token attractor under triggering prompts.
4. `VLLMBackend` chat endpoint usage is a production-path exposure point because
   chat requests commonly put Phase-1 system prompts into token-prefix patterns
   that can expose the current vLLM path's first-token attractor.

## 14. Unknowns

- Whether the AWQ/compressed-tensors artifact produces the same pathology under
  a local transformers backend.
- Whether vLLM with the original HF artifact behaves like LMF.
- Whether the same AWQ artifact under a different vLLM kernel selection or model
  implementation path still produces `!`.
- Whether the artifact BOS mismatch affects vLLM initialization, special-token
  handling, or prefix-position behavior.
- Exact server-side token ids for vLLM chat requests.
- Effective stop/eos behavior inside the vLLM chat endpoint.
- Whether using `/v1/completions` with pre-rendered prompts is an acceptable
  backend adapter mode for Phase-2A.

## 15. Recommended Next Steps

### Phase-2A.1: Trace Completion

Keep this outside Phase-1 Runtime.

- Add vLLM tokenizer diagnostics for WSL model paths.
- Record `chat_template.jinja` hash when `tokenizer_config.json` lacks
  embedded `chat_template`.
- Record reconstructed token ids for vLLM where local tokenizer access is
  available.
- Label trace tokenization as `reconstructed_local`, not server-side truth.

### Phase-2A.2: Generation Profile Diagnostic

- Run a VLLMBackend diagnostic variant that preserves requested
  `temperature=0.0`.
- Do not change benchmark expectations.
- Compare only trace behavior: finish reason, repetition, output structure.

### Phase-2A.3: Endpoint Diagnostic

- Add a diagnostic-only vLLM completions adapter that sends pre-rendered prompts
  to `/v1/completions`.
- Compare chat endpoint vs completion endpoint using identical rendered prompt.
- Treat this as diagnosis, not a production decision yet.

### Phase-2A.4: Template / Token ID Isolation

- Run WSL-side tokenizer diagnostics directly against the vLLM artifact path.
- Compare token ids for:
  - canonical prompt
  - DeepSeek-template prompt
  - server-side vLLM chat request if an exposed tokenizer path or debug API is
    available
- Identify the exact token id for `!` and the final special-token suffix around
  the assistant generation boundary.

### Phase-2A.5: Artifact Isolation

- Experiment A: direct DS14B AWQ through HF/Transformers is paused on this
  machine. The current WSL RAM/VRAM envelope caused OOM during compressed-tensors
  load/decompress and should not be retried blindly.
- Experiment B: run HF 4-bit vs AWQ/compressed-tensors under one backend where
  possible.
- Diagnostic kernel branch: start a second vLLM server using the same AWQ
  artifact with an alternate linear backend or eager/model implementation option
  if vLLM exposes a supported setting. Compare only the minimal `You are` token
  trigger first.
- Diagnostic artifact-copy branch: create a non-destructive copied artifact with
  corrected `config.json` `bos_token_id=151646`, serve it on a separate port,
  and rerun `vllm_prefix_transition`. Do not edit the original artifact.
- Low-memory substitute for Experiment A: use a smaller Qwen2/DeepSeek-family
  compressed-tensors artifact, if available, to test whether the same
  `You are -> !` behavior appears across HF and vLLM without exceeding memory
  limits. Treat it as mechanism evidence, not DS14B proof.
- Minimal LMF compare is now captured in
  `D:\UAEA\data\diagnostics\minimal_backend_compare.json`. Because 24GB VRAM
  prevents simultaneous LMF+vLLM serving, keep future comparisons as explicit
  split runs with service state recorded.

### Phase-2A.6: Diagnostic Fix Candidates

Do not merge either candidate into the production path until artifact/template
isolation is complete.

Candidate 1:

```text
Diagnostic-only vLLM completions adapter
  -> send canonical Phase-1 prompt rendering to /v1/completions
```

Purpose:

- test whether Phase-1 semantic contract can close when vLLM avoids DeepSeek
  role-token chat rendering
- preserve Phase-1 Runtime semantics
- keep this out of production until validated

Candidate 2:

```text
Artifact/template compatibility audit
  -> use vLLM with original HF artifact if possible
  -> or use local transformers with AWQ/compressed-tensors artifact if possible
```

Purpose:

- determine whether the role-token `!` attractor belongs to artifact,
  quantization, vLLM engine, or a combination of them

## 16. Current Conclusion

The current evidence does not support the claim:

```text
vLLM engine alone caused Phase-1 semantic failure.
```

The evidence now supports this narrower conclusion:

```text
The full vLLM production path is not yet semantically equivalent to the LMF
baseline for selected Phase-1 cases. The repeated `!` failure is localized to
first-token generation for specific input token-prefix sequences, especially
`You are -> [2610, 525]`, on the current vLLM AWQ/compressed-tensors path.
DeepSeek/Qwen chat-template rendering exposes the issue, but it is not the sole
cause. Current evidence points below Phase-1 Runtime, backend adapter, and
tokenizer reconstruction toward model artifact / quantization / vLLM model
implementation or kernel interaction.
```

Confidence:

- High: transport/API is not the primary failure.
- High: Phase-1 Runtime is not the primary source of repeated `!` pathology.
- High: current production comparison is not a backend-only equivalence test.
- High: tokenizer mismatch is not the root cause for the minimal triggers.
- High: the current failure is reproducible at token-id sequence level.
- Medium-high: AWQ/compressed-tensors artifact and vLLM implementation/kernel
  interaction are the leading root-cause area.
- Medium: artifact BOS metadata mismatch is a compatibility risk, not yet proven
  as the direct cause.
- Low: Phase-1 artifact schema, semantic observation logic, or benchmark
  expectations cause this failure.

## 17. Root Cause Decision

Decision:

```text
C. Artifact + execution interaction remains the best current classification.
```

Why not A, artifact-only:

- The AWQ/compressed-tensors artifact has not been successfully run through an
  independent HF/Transformers generation path on this hardware.
- HF+AWQ failure observed so far is a hardware/memory feasibility failure, not
  a semantic generation result.

Why not B, vLLM execution/kernel-only:

- vLLM-only evidence is strong for the current production path, but same-artifact
  non-vLLM generation is still missing.
- The artifact includes a BOS metadata mismatch and compressed-tensors WNA16
  quantization, so artifact and execution cannot yet be separated.

Why not D, configuration/token-id-only:

- Server `/tokenize` matches local token ids.
- Explicit BOS prefixing did not remove the `!` attractor.
- The config mismatch remains a risk, but current evidence does not make it
  causal.

Why not E, no further isolation possible:

- Further isolation is possible, but not via blind HF+AWQ full-model loading on
  the current machine. The next useful experiments must avoid loading a second
  full DS14B copy or must alter the memory envelope explicitly.

Current confidence:

```text
C. Artifact + vLLM execution/kernel interaction: medium-high
A. Artifact-only root cause: low-medium
B. vLLM execution/kernel-only root cause: medium
D. Config/token-id-only root cause: low-medium
E. Cannot isolate further: low
```

Highest information-gain next experiment:

```text
Start vLLM with the same AWQ artifact but an alternate execution/kernel profile
that does not load a second model at the same time, then rerun only the
max_tokens=1 prefix test:

  minimal_upper: "You are a local assistant."
  minimal_lower: "you are a local assistant."
  canonical_upper
  deepseek_upper

Candidate toggles to evaluate one at a time:
  --enforce-eager
  --kernel-config '{"linear_backend":"torch"}'
  --kernel-config '{"linear_backend":"triton"}'

If an alternate vLLM kernel profile removes the first-token `!` while using the
same artifact, that would strongly implicate vLLM execution/kernel selection.
If all vLLM kernel profiles reproduce `!`, artifact/config compatibility
remains the leading branch.
```

## 18. 2026-08-14 GPU Kernel And Config Isolation Update

Scope:

```text
Same artifact: /opt/uaea-models/models/DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4
Same vLLM version: 0.26.0
Same minimal probes:
  minimal_upper: "You are a local assistant."
  minimal_lower: "you are a local assistant."
  canonical_upper
  deepseek_upper
Max new tokens: 1
Phase-1 Runtime: bypassed
```

The user-started service was not available by the time this run started. The
diagnostic wrapper therefore started exactly one vLLM instance per profile,
ran the max_tokens=1 probe, and stopped that instance. This keeps the test
inside the 24GB VRAM single-model envelope.

Startup path note:

```text
Validated runtime script location observed on this machine:
  /opt/uaea/scripts/start_vllm_ds14b.sh

The diagnostic wrapper used:
  D:\UAEA\scripts\run_vllm_kernel_profile_diagnostic.sh
```

### Kernel Profile Results

| Profile | Startup | Actual WNA16 kernel | minimal_upper | deepseek_upper | Interpretation |
| --- | --- | --- | --- | --- | --- |
| baseline | PASS | MarlinLinearKernel | `!` | `!` | Reproduces production pathology |
| enforce_eager | PASS | MarlinLinearKernel | `!` | `!` | CUDA graph / compile path is not primary |
| linear_triton | PASS | TritonW4A16LinearKernel | `!` | `!` | Not Marlin-specific |
| linear_exllama | PASS | ExllamaLinearKernel | `!` | `!` | Not Triton/Marlin-specific |
| linear_torch | FAIL | none | n/a | n/a | No torch kernel exists for WNA16 mixed-precision layers |
| linear_emulation | FAIL | none | n/a | n/a | No emulation kernel exists for WNA16 mixed-precision layers |
| linear_machete | FAIL | none | n/a | n/a | Machete requires Hopper/SM90 according to vLLM error |
| linear_conch | FAIL | none | n/a | n/a | `conch-triton-kernels` not installed |
| linear_humming | FAIL | HummingLinearKernel selected, init failed | n/a | n/a | Humming NVRTC compile/repack failed before serving |
| linear_cutlass | FAIL | none | n/a | n/a | CUTLASS W4A8 path requires Hopper/SM90 according to vLLM error |

Result artifacts:

```text
D:\UAEA\data\diagnostics\vllm_kernel_profile_baseline_20260814T074236Z.json
D:\UAEA\data\diagnostics\vllm_kernel_profile_enforce_eager_20260814T074834Z.json
D:\UAEA\data\diagnostics\vllm_kernel_profile_linear_triton_20260814T075300Z.json
D:\UAEA\data\diagnostics\vllm_kernel_profile_linear_exllama_20260814T075741Z.json
D:\UAEA\data\diagnostics\vllm_kernel_profile_hf_override_bos151646_20260814T080310Z.json
D:\UAEA\data\diagnostics\vllm_kernel_profile_generation_config_vllm_20260814T080456Z.json
D:\UAEA\data\diagnostics\vllm_kernel_profile_disable_prefix_cache_20260814T080733Z.json
D:\UAEA\data\diagnostics\vllm_kernel_profile_disable_chunked_prefill_20260814T080858Z.json
```

vLLM logs:

```text
/opt/uaea-runtime/vllm/kernel-diagnostics/
```

### Config And Engine Feature Results

| Profile | Startup | Result | Interpretation |
| --- | --- | --- | --- |
| hf_override_bos151646 | PASS | `minimal_upper -> !`, `deepseek_upper -> !` | `config.json` BOS mismatch is not causal for this minimal trigger |
| generation_config_vllm | PASS | `minimal_upper -> !`, `deepseek_upper -> !` | model `generation_config.json` defaults are not causal |
| disable_prefix_cache | PASS | `minimal_upper -> !`, `deepseek_upper -> !` | prefix caching is not causal |
| disable_chunked_prefill | PASS | `minimal_upper -> !`, `deepseek_upper -> !` | chunked prefill is not causal |

The artifact metadata mismatch remains a compatibility risk:

```text
config.json:
  bos_token_id = 151643
  eos_token_id = 151643

generation_config.json / tokenizer:
  bos_token_id = 151646
  eos_token_id = 151643
```

However, diagnostic-only `--hf-overrides '{"bos_token_id":151646,"pad_token_id":151643}'`
did not change first-token behavior, so it is no longer a strong direct root
cause candidate for the observed `You are -> !` pathology.

### Revised Root Cause Decision

Decision:

```text
C. Artifact + vLLM execution/model-implementation interaction
```

Confidence:

```text
medium-high, increased from the previous report
```

What changed:

- The pathology is no longer attributable to a single Marlin kernel path.
- The same artifact under vLLM reproduces the first-token `!` across at least
  three distinct executable WNA16 kernels: Marlin, TritonW4A16, and Exllama.
- vLLM eager mode, neutral generation config, BOS override, disabled prefix
  caching, and disabled chunked prefill do not remove the trigger.

Current interpretation:

```text
The root area is below the UAEA backend adapter and above/beside raw transport:
vLLM's Qwen2/compressed-tensors WNA16 execution stack interacting with this
specific AWQ/compressed-tensors artifact.
```

This does not yet prove artifact-only root cause because HF/Transformers AWQ
generation remains hardware-blocked on the current machine. It also does not
prove vLLM-engine-only root cause because the original HF 4-bit artifact has
not been served through vLLM under the same memory-safe conditions.

### Updated Layer Classification

| Layer | Status | Evidence |
| --- | --- | --- |
| Layer 1: Transport/API | excluded | vLLM health/models/completions work; raw smoke is not universally pathological |
| Layer 2: Backend adapter | excluded for minimal trigger | pathology reproduces outside Phase-1 Runtime and outside VLLMBackend |
| Layer 3: Generation configuration | mostly excluded | temp 0/0.2, neutral vLLM generation config, max_tokens=1 all reproduce |
| Layer 4: Tokenizer/chat template | mostly excluded | `/tokenize` matches local ids; minimal raw prompt reproduces without chat template |
| Layer 5: Model artifact/quantization | strong suspect | AWQ/compressed-tensors artifact differs from LMF HF 4-bit artifact; same-artifact HF path blocked |
| Layer 6: vLLM execution/kernel/model implementation | strong suspect | pathology reproduces across multiple vLLM WNA16 kernels, not across LMF production path |
| Layer 7: Phase-1 Runtime | excluded | LMF L0-L2 PASS; minimal probe bypasses Runtime |

### Highest Information-Gain Next Experiment

Only one next experiment remains highest value under current constraints:

```text
Serve the original HF/LLaMA-Factory DeepSeek-R1-Distill-Qwen-14B artifact through
vLLM, if and only if it can fit as a single running model on the 24GB GPU using
a memory-safe quantization/loading mode.
```

Decision logic:

```text
HF artifact + vLLM normal:
  strengthens artifact/quantization root cause.

HF artifact + vLLM also produces `You are -> !`:
  strengthens vLLM Qwen2/model-implementation root cause.

HF artifact + vLLM cannot fit:
  keep classification at C and move this experiment to a larger-memory host.
```

Do not retry full HF+AWQ local Transformers loading on this machine without
changing the WSL RAM/VRAM budget. The previous failure was a hardware feasibility
failure, not semantic evidence.

## 19. 2026-08-14 Artifact Static And Logprobs Isolation Update

This update continues root-cause localization without loading a second full
model and without modifying Phase-1 Runtime.

### Original HF Artifact Feasibility

The original LMF/HF artifact is present at:

```text
/mnt/d/LM_Studio_Models/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B
```

Observed size:

```text
28GB total safetensors
model-00001-of-000004.safetensors: 8.7GB
model-00002-of-000004.safetensors: 8.7GB
model-00003-of-000004.safetensors: 8.7GB
model-00004-of-000004.safetensors: 3.5GB
```

Current memory envelope:

```text
WSL RAM: 15GB
Swap: 4GB
GPU VRAM: 24,455MiB
```

vLLM supports `bitsandbytes` as a quantization method in this installed version,
but the active vLLM environment does not currently have `bitsandbytes`
installed:

```text
bitsandbytes: ModuleNotFoundError
accelerate: 1.14.0
transformers: 5.14.1
safetensors: 0.8.0
```

Conclusion:

```text
Serving the original HF artifact through vLLM is not currently executable as a
safe one-command diagnostic. Full precision is over the 24GB VRAM budget, and
the only plausible low-VRAM path, vLLM bitsandbytes loading, is dependency
blocked. This is an environment feasibility block, not root-cause evidence.
```

### Static Token-0 Artifact Check

Diagnostic artifact:

```text
D:\UAEA\data\diagnostics\artifact_static_token0_lmhead_embedding.json
```

The AWQ/compressed-tensors artifact has:

```text
quantization_config.ignore = ["lm_head"]
lm_head.weight dtype = bfloat16
model.embed_tokens.weight dtype = bfloat16
```

Static comparison against the original HF artifact:

| Tensor | Token | HF vs AWQ |
| --- | --- | --- |
| `lm_head.weight` | token 0 / `!` | identical, cosine ~= 1.0, L2 diff 0 |
| `model.embed_tokens.weight` | token 0 / `!` | identical, cosine ~= 1.0, L2 diff 0 |

Important details:

```text
lm_head token 0 norm:
  HF:  0.981516
  AWQ: 0.981516
  rank_desc_1_based: 136401 / 152064

embedding token 0 norm:
  HF:  1.603274
  AWQ: 1.603274
  rank_desc_1_based: 238 / 152064
```

Interpretation:

```text
The `!` token's unquantized output-head row is not statically corrupted or
inflated in the AWQ artifact. The token-0 embedding row is high-norm, but it is
identical in the LMF/HF artifact and the AWQ artifact, so it cannot by itself
explain why LMF is normal while vLLM/AWQ is pathological.
```

This shifts suspicion away from token-0 static table corruption and toward the
hidden state produced by quantized transformer layers under vLLM's
compressed-tensors WNA16 execution path.

### Cross-Kernel Logprobs / NaN Diagnostic

Diagnostic script:

```text
D:\UAEA\scripts\diagnose_vllm_minimal_logprobs.py
```

Result artifacts:

```text
D:\UAEA\data\diagnostics\vllm_minimal_logprobs_logprobs_baseline_20260814T081728Z.json
D:\UAEA\data\diagnostics\vllm_minimal_logprobs_logprobs_triton_20260814T081855Z.json
D:\UAEA\data\diagnostics\vllm_minimal_logprobs_logprobs_exllama_20260814T082032Z.json
```

Observed behavior:

| Kernel profile | Trigger prompt plain output | Trigger prompt with `logprobs=10` | Control prompt logprobs |
| --- | --- | --- | --- |
| Marlin baseline | `!` | HTTP 400, `nan` serialization | normal |
| TritonW4A16 | `!` | HTTP 400, `nan` serialization | normal |
| Exllama | `!` | HTTP 400, `nan` serialization | normal |

The specific error for trigger prompts is:

```text
Out of range float values are not JSON compliant: nan
```

Controls such as `minimal_lower` and `canonical_upper` return valid logprobs
and stable top-token lists under the same server and kernel profiles.

Interpretation:

```text
The `!` first-token pathology is coupled with a prompt-specific numerical
anomaly in vLLM logprob generation. Because the anomaly reproduces across
Marlin, TritonW4A16, and Exllama, it is unlikely to be a single GEMM kernel
implementation bug. The evidence now points to the interaction between this
AWQ/compressed-tensors artifact, vLLM's Qwen2/compressed-tensors WNA16 model
execution path, and specific prefix hidden states.
```

### Revised Decision After Static And Logprob Evidence

Decision remains:

```text
C. Artifact + vLLM execution/model-implementation interaction
```

Confidence:

```text
high within the current hardware-limited evidence boundary
```

Layer ranking now:

| Rank | Layer | Confidence | Reason |
| --- | --- | --- | --- |
| 1 | Artifact + vLLM WNA16 execution interaction | high | Cross-kernel `!` and NaN reproduce only on vLLM/AWQ path |
| 2 | Artifact/quantization-only | medium | Same AWQ artifact has not run under independent HF generation |
| 3 | vLLM Qwen2/compressed-tensors implementation-only | medium | Original HF artifact has not run under vLLM |
| 4 | Static token-0 lm_head/embedding corruption | low | HF and AWQ rows are identical |
| 5 | Config/token-id mismatch | low | Tokenization matches; BOS override did not change behavior |
| 6 | Phase-1 Runtime / adapter / transport | very low | Minimal API probes bypass these layers |

Highest remaining information-gain experiment:

```text
Install or provide an isolated vLLM environment with bitsandbytes support, then
serve the original HF artifact through vLLM using a memory-safe 4-bit path.
```

This should be treated as an environment-gated experiment. Do not install new
packages into the stable vLLM environment without deciding whether that
environment is disposable or should be cloned first.

## 20. 2026-08-14 Bounded Isolation Decision Matrix

This section deliberately stops further low-value expansion. It answers the
current bounded question:

```text
Does the evidence point to the AWQ artifact, vLLM execution/model
implementation, or the current software/hardware combination?
```

### Physical Boundary

Current machine:

```text
GPU: NVIDIA GeForce RTX 5090 D v2
Compute capability: 12.0
VRAM: 24,455MiB
Driver: 581.80
WSL RAM: 15GB
Swap: 4GB
vLLM: 0.26.0
Torch: 2.11.0+cu130
Transformers: 5.14.1
compressed_tensors: 0.17.0
```

Installed inference-path availability:

| Runtime / package | Status |
| --- | --- |
| vLLM | available |
| Transformers | available |
| compressed_tensors | available |
| accelerate | available |
| bitsandbytes | missing |
| autoawq / awq | missing |
| SGLang | missing |
| TensorRT-LLM | missing |
| llama.cpp / llama-cpp-python | missing |

Artifact inventory:

| Artifact | Path | Size | Notes |
| --- | --- | ---: | --- |
| DS14B HF baseline | `/mnt/d/LM_Studio_Models/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | 28GB | original LMF/HF artifact, full checkpoint |
| DS14B AWQ | `/opt/uaea-models/models/DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4` | 9.4GB | compressed-tensors WNA16 production candidate |
| Qwen2.5 0.5B Instruct | `/opt/uaea-models/models/qwen2.5-0.5b-instruct` | 954MB | feasible alternative Qwen2-family vLLM control |

### Experiment Matrix

| Experiment | Artifact | Engine | Result | Interpretation |
| --- | --- | --- | --- | --- |
| LMF baseline | DS14B HF 4-bit loading path | LMF / HF | PASS, L0-L2 all pass, no `!`, no length-limited baseline traces | Phase-1 semantic baseline remains valid |
| Current production | DS14B AWQ compressed-tensors WNA16 | vLLM 0.26.0 | FAIL for selected cases; `minimal_upper -> !`; logprobs NaN for trigger prompts | Known failure path |
| AWQ alternative engine | DS14B AWQ compressed-tensors WNA16 | Transformers / AutoAWQ / SGLang / TensorRT-LLM | `blocked_by_hardware_or_environment` | HF+AWQ load previously hit WSL memory/OOM pressure; alternative runtimes are not installed |
| Alternative artifact | Qwen2.5 0.5B Instruct | same vLLM 0.26.0 / same GPU | PASS for minimal probe; `plain_bang=0`; `logprobs_ok=4`; no NaN | vLLM + RTX5090D is not globally broken for Qwen2-family prompts |

Alternative artifact diagnostic:

```text
D:\UAEA\data\diagnostics\vllm_minimal_logprobs_alt_qwen25_05b_vllm_20260814T082653Z.json
```

Important limitation:

```text
Qwen2.5 0.5B is not DS14B and is not an AWQ/compressed-tensors WNA16 artifact.
Therefore this experiment cannot prove that the DS14B AWQ artifact alone is
bad. It only shows that the same vLLM software/hardware stack can produce normal
first-token and logprob behavior for a Qwen2-family model using the same minimal
token sequence:

  "You are a local assistant." -> [2610, 525, 264, 2205, 17847, 13]
```

### Confidence Assessment

Current root-cause confidence:

| Candidate | Confidence | Reason |
| --- | --- | --- |
| AWQ / compressed-tensors artifact or quantization path | medium-high | The failure is specific to DS14B AWQ production artifact and does not appear in LMF/HF baseline or Qwen2.5 vLLM control |
| vLLM execution/model implementation for DS14B AWQ WNA16 | high | `!` and logprobs NaN reproduce across Marlin, TritonW4A16, and Exllama under vLLM |
| Current machine/software stack globally | low-medium | Qwen2.5 0.5B vLLM control is normal, but SM120 + vLLM 0.26.0 + compressed-tensors WNA16 remains a compatibility risk |
| Tokenizer/template | low | Minimal raw prompt reproduces; token ids match; Qwen2.5 control uses same minimal token ids and is normal |
| Generation profile | low | max_tokens=1, neutral generation config, temperature variants, and logprobs diagnostics localize below sampling policy |
| Phase-1 Runtime | very low | Minimal API probes bypass Runtime; LMF L0-L2 baseline passes |

### Production Artifact Decision

Current evidence is sufficient to mark:

```text
ds14b-awq is not suitable as the current UAEA Phase-2A production artifact on
this RTX5090D / vLLM 0.26.0 / compressed-tensors WNA16 environment.
```

This is an environment-scoped production decision, not a universal claim that
the checkpoint is intrinsically invalid.

Reason:

- It fails the minimal `You are a local assistant.` trigger.
- It fails before Phase-1 Runtime semantics are involved.
- The failure is deterministic and appears at the first generated token.
- Trigger prompts produce vLLM logprob NaN serialization errors.
- Multiple vLLM WNA16 kernels reproduce the behavior.
- A feasible Qwen2-family vLLM control does not reproduce the behavior.

What remains unproven:

```text
Whether DS14B AWQ/compressed-tensors produces the same pathology under a
non-vLLM execution engine.

Whether DS14B HF baseline artifact produces the same pathology under vLLM with
a memory-safe 4-bit loader.
```

### Diagnostic Boundary Reached

On the current 24GB machine, the high-value local diagnostic boundary has been
reached.

Blocked branches:

| Branch | Status | Blocker |
| --- | --- | --- |
| DS14B AWQ + non-vLLM engine | blocked | HF/Transformers load exceeds WSL memory envelope; AutoAWQ/SGLang/TensorRT-LLM/llama.cpp are not installed |
| DS14B HF + vLLM 4-bit | blocked | `bitsandbytes` missing; full checkpoint exceeds VRAM budget |
| DS14B HF + vLLM full precision | not attempted | physically unsafe for 24GB VRAM |

Next single highest information-gain experiment:

```text
Use a cloned/disposable vLLM environment with bitsandbytes support, or a larger
memory machine, to run DS14B HF artifact through vLLM in a memory-safe 4-bit
mode.
```

Do not continue adding prompt variants or benchmark tweaks until one of the
blocked branches becomes executable.

## 21. 2026-08-15 Qwen2.5-14B-AWQ Control

The user added a new Qwen2.5-14B artifact and a matching vLLM AWQ artifact. This
section records a bounded simple test only. It does not change Phase-1 Runtime,
benchmark expectations, or the backend contract.

### Artifact

Path:

```text
/opt/uaea-models/models/Qwen2.5-14B-Instruct-AWQ
```

Static metadata:

```text
size: 9.4GB
model_type: qwen2
architectures: Qwen2ForCausalLM
max_position_embeddings: 32768
torch_dtype: float16
quantization_config:
  quant_method: awq
  version: gemm
  bits: 4
  group_size: 128
  zero_point: true
```

Tokenizer check:

```text
"You are a local assistant." -> [2610, 525, 264, 2205, 17847, 13]
"you are a local assistant." -> [9330, 525, 264, 2205, 17847, 13]
```

This matches the minimal token ids used in the DS14B pathology tests.

### vLLM Startup

Diagnostic startup:

```text
vllm serve /opt/uaea-models/models/Qwen2.5-14B-Instruct-AWQ
  --served-model-name qwen25-14b-awq
  --dtype half
  --max-model-len 8192
  --gpu-memory-utilization 0.7
  --host 0.0.0.0
  --port 8001
```

Observed vLLM execution metadata:

```text
vLLM: 0.26.0
quantization: auto_awq
kernel: MarlinLinearKernel for AutoAWQMarlinLinearMethod
GPU KV cache size: 28,256 tokens
Maximum concurrency for 8,192 tokens/request: 3.45x
```

This is not the same execution path as the DS14B failure artifact:

```text
DS14B failure path:
  compressed-tensors WNA16

Qwen2.5-14B-AWQ control path:
  auto_awq / AutoAWQMarlin
```

### Minimal Completions / Logprobs Test

Result artifact:

```text
D:\UAEA\data\diagnostics\vllm_minimal_logprobs_qwen25_14b_awq_simple_20260815T064048Z.json
```

Summary:

```text
total: 4
plain_bang: 0
logprobs_ok: 4
logprobs_failed: 0
```

Key results:

| Prompt | First generated text | Bang | Logprobs |
| --- | --- | --- | --- |
| `minimal_upper` | ` You` | no | ok |
| `minimal_lower` | ` you` | no | ok |
| `canonical_upper` | ` If` | no | ok |
| `deepseek_upper` | `To` | no | ok |

No `nan` serialization error was observed.

### Minimal Chat Test

Result artifact:

```text
D:\UAEA\data\diagnostics\vllm_chat_minimal_qwen25_14b_awq_simple_20260815T064048Z.json
```

Summary:

```text
total: 4
ok: 4
bang: 0
```

Chat cases tested:

| Case | Result |
| --- | --- |
| `chat_system_upper` | normal text, no `!`, finish_reason `stop` |
| `chat_system_lower` | normal text, no `!`, finish_reason `stop` |
| `chat_user_upper` | normal text, no `!`, finish_reason `length` due to max_tokens=32 |
| `chat_plain_bootloader` | normal text, no `!`, finish_reason `length` due to max_tokens=32 |

### Interpretation

This result strengthens the previous localization:

```text
The `You are -> !` pathology is not a generic vLLM 0.26.0 + RTX5090D + Qwen2
tokenizer failure.
```

It also shows that a 14B AWQ artifact can run on this hardware through vLLM
without reproducing the DS14B first-token `!` failure.

Current narrowed root area:

```text
DeepSeek-R1-Distill-Qwen-14B-AWQ-INT4
  + compressed-tensors WNA16
  + vLLM Qwen2/compressed-tensors execution path
```

The Qwen2.5-14B-AWQ result does not prove that every AWQ artifact is safe for
UAEA production semantics. It only supports that the DS14B failure is specific
to that artifact/path rather than a universal vLLM/Qwen2/14B/AWQ failure.

### Updated Production Guidance

The previous decision remains:

```text
Do not use ds14b-awq compressed-tensors WNA16 as the current UAEA production
artifact on this machine.
```

New candidate status:

```text
Qwen2.5-14B-Instruct-AWQ is eligible for the next bounded Phase-2A semantic
benchmark validation step, because it passes the minimal bang/logprobs smoke
test under vLLM.
```

This is not yet a Phase-1 semantic equivalence PASS. The next step, if desired,
is to run the existing selected Phase-1 vLLM benchmark/trace against
`qwen25-14b-awq` without changing Phase-1 expectations.
