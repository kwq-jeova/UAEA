# UAEA Harness Feasibility Research

Date: 2026-09-12

This document records the first Harness research pass after the
`uaea-pre-harness-phase1-phase2-freeze-20260912` baseline. It is a feasibility
record, not a Runtime migration plan.

No UAEA Runtime, Web, Memory, backend, model, or inference parameter was
changed for this pass.

## Executive Decision

The first candidate integration surface is the Codex app-server protocol, not
the Codex TUI and not a direct replacement of the UAEA `ModelClient`.

The current evidence supports this bounded statement:

```text
Codex app-server can be investigated as an evented execution host.
The local vLLM service can potentially speak the Responses wire protocol.
Actual Qwen2.5 tool-call compatibility is not yet proven.
```

The app-server must not become the owner of UAEA Goal Hypothesis, Problem
Space, Epistemic State, or SQLite-backed cognitive history.

## Terminology

### Codex CLI / TUI

The installed CLI is a user-facing terminal client. It is useful for manual
operation, but it is not the preferred UAEA integration boundary.

### Codex SDK

The official SDK starts, continues, and resumes local Codex threads. It controls
the local Codex app-server rather than exposing a generic low-level model
client. It is therefore a possible host-side convenience layer, but it does
not by itself preserve UAEA Cognition ownership.

### Codex app-server

The app-server is the most explicit programmatic surface currently available.
It exposes a bidirectional JSON-RPC protocol over stdio by default, with
experimental WebSocket and Unix-socket transports. Its primitives are:

```text
initialize
  -> thread/start or thread/resume
  -> turn/start
  -> item and turn events
  -> turn/completed
```

This event model is suitable for a thin observation adapter.

### Responses API

This is the model-provider wire protocol used by Codex custom providers. It is
not the same thing as the app-server protocol.

### MCP

MCP is a tool/context connection protocol. Codex can connect to stdio and
streamable HTTP MCP servers. MCP is a possible way to expose UAEA
capabilities, but it adds another protocol and can hide the existing
`ActionRequest -> Capability -> ExecutionObservation` identity if introduced
too early.

## Verified Local State

### Codex host

The local installation reports:

```text
codex-cli 0.154.0-alpha.6.2
```

The CLI exposes:

```text
codex app-server
codex mcp
codex exec
```

The current user configuration uses a custom provider with
`wire_api = "responses"`. That provider is not the UAEA local-vLLM provider and
must not be reused implicitly for a local probe.

### UAEA inference boundary

The frozen UAEA path remains:

```text
Qwen2.5-14B-Instruct-AWQ
  -> vLLM 0.26.0
  -> http://127.0.0.1:8001/v1
  -> qwen25-14b-awq
  -> RTX 5090 D v2, single GPU, 24 GB VRAM class
```

The current vLLM startup script remains unchanged:

```text
--dtype half
--max-model-len 8192
--gpu-memory-utilization 0.7
```

During this research pass the service was not running on port 8001, so no live
model result is claimed.

### Local vLLM Responses support

The installed vLLM 0.26.0 package contains:

```text
vllm.entrypoints.openai.responses.api_router
vllm.entrypoints.openai.responses.protocol
vllm.entrypoints.openai.responses.serving
```

The route implementation registers:

```text
POST /v1/responses
GET  /v1/responses/{response_id}
POST /v1/responses/{response_id}/cancel
```

Responses serving is initialized for the normal `generate` task. The
Responses API response store is disabled by default in the installed package;
that is compatible with the current no-storage-first probe plan and does not
change UAEA SQLite behavior.

This proves package-level route availability only. It does not prove that the
current model, chat template, tool parser, or Codex event loop will work
end-to-end.

### Qwen2.5 tool-call evidence

The local tokenizer template contains a tool-call format based on:

```text
<tool_call>
{"name": "...", "arguments": {...}}
</tool_call>
```

and tool results represented with `<tool_response>` blocks.

The model artifact does not declare a vLLM `tool_call_parser` in
`config.json`. The installed vLLM parser registry also has no parser explicitly
named for Qwen2.5. The current UAEA startup script does not enable
`--enable-auto-tool-choice` or select a `--tool-call-parser`.

Therefore:

```text
No native Qwen2.5 tool-call path is currently validated.
```

This is an open compatibility item, not a reason to change the serving
baseline.

## Protocol Comparison

| Surface | Primary role | UAEA relevance | Current decision |
| --- | --- | --- | --- |
| Codex CLI/TUI | Human-facing client | Manual validation only | Do not integrate first |
| Codex SDK | Programmatic local Codex control | Convenience wrapper over app-server | Defer until protocol works |
| Codex app-server | Thread/turn/event control | Best event adapter candidate | First integration probe |
| Responses API | Model-provider wire format | Needed between Codex and vLLM | Verify with unchanged vLLM |
| MCP | Tool/context protocol | Possible capability bridge | Defer until dynamic-tool path is evaluated |

## Candidate Boundary

The smallest boundary that preserves the current UAEA research ownership is:

```text
UAEA Cognition
  -> bounded action/execution request
  -> Harness adapter
  -> Codex app-server thread/turn
  -> local Responses provider
  -> existing vLLM
  -> Qwen2.5 AWQ
```

For a capability call, the return path is:

```text
Codex app-server dynamic tool request
  -> UAEA adapter
  -> existing Capability Registry / Execution path
  -> bounded tool output
  -> app-server tool-call response
  -> app-server item/turn events
  -> UAEA ExecutionObservation adapter
```

The UAEA adapter must retain:

- capability identity;
- request identity;
- execution status;
- evidence/provenance references;
- trace identity;
- failure identity.

The adapter must not copy the following into Codex thread goal state:

- Goal Hypothesis;
- Problem Boundary;
- epistemic confidence;
- Memory decisions;
- Candidate/Truth decisions.

## Dynamic Tools Versus MCP

### Dynamic tools

The app-server exposes an experimental `dynamicTools` field on
`thread/start`. When a dynamic tool is invoked, the app-server sends an
`item/tool/call` request to the client and emits lifecycle events around that
call.

This is structurally close to the existing UAEA capability boundary:

```text
Codex model-visible tool
  -> client-side dispatch
  -> UAEA capability execution
  -> bounded result
  -> Codex continuation
```

The main risks are:

- the API is experimental;
- the app-server may persist dynamic tools in thread metadata;
- tool names and namespaces must satisfy Responses naming constraints;
- the Qwen2.5 model must actually emit a compatible tool call;
- Codex may still perform broader task interpretation than UAEA intends.

### MCP

MCP is more established as a tool connection surface in Codex, but an MCP
adapter would introduce:

```text
UAEA capability
  -> MCP server
  -> Codex MCP client
  -> model-visible tool
```

This can be useful later, especially if the same capability should be consumed
by multiple Harness clients. It is not the first probe because it adds a
second adapter and makes it harder to isolate whether a failure belongs to:

```text
Responses transport
model tool-call format
Codex app-server
MCP
or UAEA capability dispatch
```

## Architectural Warning

Codex app-server is not only a commodity tool loop. It also owns its own:

- thread history;
- turn orchestration;
- model-facing instructions;
- approvals;
- sandbox policy;
- optional thread goal state;
- skills and MCP integration;
- subagent and execution mechanics.

Therefore this migration would be unsafe:

```text
UAEA Goal Hypothesis
  -> Codex thread goal
```

The two concepts are different. Codex `thread/goal/*` is execution/product
state. UAEA Goal Hypothesis remains Cognition state.

The initial probe must therefore use a narrow task and compare the resulting
events, rather than assuming that a successful Codex turn means UAEA cognition
has been preserved.

## Staged Feasibility Plan

### H0: Protocol-only validation

No UAEA code change and no model parameter change.

Validate that a temporary custom Codex provider configuration can point to:

```text
base_url = http://127.0.0.1:8001/v1
wire_api = responses
model = qwen25-14b-awq
```

Use CLI `-c` overrides or an external temporary configuration. Do not modify
the user's normal Codex configuration.

#### H0 result

H0 passed at the configuration and app-server handshake level:

- `codex doctor --summary` loaded the temporary provider override;
- the provider was accepted with `wire_api = "responses"`;
- `requires_openai_auth = false` was accepted;
- `codex app-server --stdio` completed `initialize` and returned its normal
  initialization result;
- the probe did not start a thread or call the model;
- the user's normal `C:\Users\wqkan\.codex\config.toml` was not modified.

Endpoint reachability remains untested because vLLM was not running on
`127.0.0.1:8001` during this pass.

### H1: No-tool local Responses probe

With the existing vLLM server started exactly as already documented:

1. start `codex app-server` with the temporary local provider;
2. send `initialize`;
3. send `thread/start`;
4. send one ordinary `turn/start`;
5. record `turn/*`, `item/*`, finish status, and response text;
6. record model identity and latency;
7. confirm that no UAEA or Codex tool was invoked.

This isolates provider protocol and plain generation.

#### H1 result

H1 has two materially different results:

1. With the normal Codex user configuration, the first turn failed before
   generation because the Codex agent prompt exceeded the vLLM 8192-token
   context window. The vLLM error reported at least 8193 input tokens and zero
   remaining output tokens.
2. With an isolated temporary `CODEX_HOME` containing only the local provider,
   and with host skill discovery, plugins, MCP, shell/browser/exec tools, and
   project instructions disabled, the same no-tool turn completed:

```text
Codex app-server initialize: PASS
thread/start: PASS
turn/start: PASS
agent message: READY
turn/completed: PASS
```

The successful stripped-down run reported approximately:

```text
input tokens: 7861
output tokens: 2
total tokens: 7863
vLLM max context: 8192
```

This is a protocol compatibility result, not a usable default deployment
profile. It leaves only a small amount of context for a capability schema,
tool output, or multi-turn history.

The app-server also emitted:

```text
Model metadata for `qwen25-14b-awq` not found.
Defaulting to fallback metadata; this can degrade performance and cause issues.
```

That warning must be treated as an explicit adapter/configuration risk.

### H1-direct: Direct local Responses control

As a layer-isolation check, a direct no-tool request to the unchanged vLLM
Responses endpoint completed successfully:

```text
POST http://127.0.0.1:8001/v1/responses
model=qwen25-14b-awq
input_tokens=39
output_tokens=2
text=READY
status=completed
```

This separates the vLLM Responses implementation from the Codex prompt
overhead. The local Responses route is functional.

A direct request with one function tool also completed at HTTP level, but the
returned assistant message contained the Qwen XML-like text:

```text
<tool_call>
{"name": "echo", "arguments": {"text": "hello"}}
</tool_call>
```

It was returned as ordinary output text rather than a structured
`function_call` response item. The current UAEA vLLM startup script does not
enable automatic tool choice or select a tool-call parser. Therefore native
structured tool calling is not yet validated.

### H2: One deterministic dynamic capability

Expose one non-destructive capability, preferably an echo-style or
`document.read_section` fixture, through the app-server dynamic-tool request
path.

Do not connect Web, SQLite Memory, or Goal Hypothesis in this step.

Acceptance evidence:

```text
tool request received
  -> capability identity preserved
  -> UAEA execution result produced
  -> bounded tool output returned
  -> app-server continuation completes
  -> trace can normalize the event to ExecutionObservation
```

### H3: Existing capability comparison

Only after H2:

- compare `document.read_section`;
- compare `fs.list`;
- compare one failure path;
- compare an ordinary no-tool answer.

The old Phase-1 and Phase-2 baselines remain the A/B control group.

### H4: Web or MCP evaluation

Only after H2/H3 and only if a real requirement exists:

- evaluate `web.search` and `web.fetch`;
- decide whether dynamic tools or MCP is the smaller adapter;
- preserve existing bounded evidence projection;
- do not move WebShell semantic routing into Harness by accident.

## Acceptance Criteria

Harness feasibility is not established by a successful health check. The
minimum evidence is:

```text
1. local provider request reaches unchanged vLLM;
2. no-tool response completes;
3. one capability call completes through the adapter;
4. returned events retain request/capability/execution identity;
5. no Goal Hypothesis or Memory state is owned by Harness;
6. no change is required to the frozen Phase-1 benchmark envelope;
7. GPU, KV/context, latency, and CPU/RAM overhead are recorded.
```

## Current Conclusion

The research should continue with H2 only as a separate tool-parser experiment.
It should not yet install a new SDK, modify the UAEA Runtime, or migrate Web.
Any vLLM parser/auto-tool-choice change must be isolated from the frozen
startup profile and recorded as a separate experiment.

The likely first implementation, if H1 succeeds, is a thin app-server adapter
that translates existing UAEA execution/capability results into app-server
dynamic-tool responses and translates app-server item events back into
`ExecutionObservation`.

The main unresolved question is not HTTP connectivity. It is whether the
current Qwen2.5 AWQ artifact produces tool calls that the installed vLLM
Responses implementation and Codex app-server can consume without changing the
frozen inference envelope.

## Sources

- [Codex SDK](https://developers.openai.com/codex/sdk/)
- [Codex app-server](https://developers.openai.com/codex/app-server/)
- [Codex advanced configuration](https://developers.openai.com/codex/config-advanced/)
- [Codex MCP](https://developers.openai.com/codex/mcp/)
- [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [vLLM OpenAI-compatible serving documentation](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)

## H2 Addendum: parser and continuation results

H2 used a separate vLLM process on port `8002` with the same model,
quantization, context length, GPU memory policy, and single-GPU hardware. The
only serving changes were:

```text
--enable-auto-tool-choice
--tool-call-parser hermes
```

The frozen `8001` startup script was not changed.

With one `echo` function tool and `tool_choice=required`, the `8002` Responses
endpoint returned a structured item:

```text
type=function_call
name=echo
arguments={"text": "hello"}
call_id=chatcmpl-tool-...
```

This differs from the frozen `8001` result, where the Qwen XML-like tool call
was returned as ordinary assistant text. The `hermes` parser therefore makes
the Responses-level function-call representation feasible for this diagnostic
case. It does not yet prove full Codex app-server compatibility.

The first `8002` response produced a function call successfully. Sending
`previous_response_id` for the tool result returned HTTP 404 because response
storage is disabled in the current vLLM process. The same continuation
succeeded when the adapter explicitly replayed the minimal sequence:

```text
user message
  -> function_call
  -> function_call_output
  -> next Responses request
```

The model then returned a normal assistant message acknowledging the tool
result. A future Harness adapter must therefore retain or reconstruct the
required turn items itself; it must not depend on server-side
`previous_response_id` persistence under the frozen serving profile.

The `8002` process was diagnostic-only and was stopped after the experiment.
No repository startup script or frozen `8001` profile was changed.

## Updated H2/Harness decision

The Responses layer is now proven for one deterministic function call when
the parser-enabled serving profile is used. The remaining probe is the
Codex app-server dynamic-tool request path. That probe must use an explicitly
isolated parser-enabled inference profile and must not modify the frozen
`8001` baseline.

Any future parser or auto-tool-choice change must be recorded as a separate
inference profile with context, VRAM, latency, and benchmark comparisons.
The likely first adapter remains thin: translate existing UAEA capability
execution results into app-server dynamic-tool responses, then translate
app-server item events back into `ExecutionObservation`. Short-lived
conversation replay state belongs in this adapter, not in vLLM response
storage.

The current unresolved question is whether Codex app-server can drive this
parser-enabled Responses profile while keeping the prompt within the frozen
8192-token context and preserving UAEA capability and observation identity.

## H2 Adapter Implementation Result

The first repository-local thin adapter is now implemented in:

```text
harness/codex_dynamic_tools.py
```

It maps an app-server `item/tool/call` payload into the existing UAEA
execution boundary:

```text
app-server dynamic tool call
  -> ActionRequest
  -> existing ToolRegistry.execute_capability()
  -> ToolResult
  -> ExecutionObservation
  -> bounded app-server tool response
```

The adapter keeps the following identities together without introducing a new
runtime:

```text
thread_id
turn_id
call_id
tool_name
capability
request_id
observation_id
```

The implementation was tested with both a deterministic
`mock.external_operation` capability and the existing
`document.read_section` capability. Unknown dynamic tools produce a controlled
failed `ExecutionObservation`.

## H2 Real app-server Probe

The corrected end-to-end probe used an isolated Codex home and a diagnostic
vLLM instance on port `8002`. The only serving differences from the frozen
`8001` profile were:

```text
--enable-auto-tool-choice
--tool-call-parser hermes
```

The successful event sequence was:

```text
initialize
  -> thread/start(dynamicTools=[mock_external_operation])
  -> turn/start
  -> raw function_call
  -> item/tool/call
  -> UAEA adapter dispatch
  -> UAEA_TRACE(ActionRequest + ExecutionObservation)
  -> item/completed(dynamicToolCall)
  -> function_call_output
  -> agentMessage
  -> turn/completed
```

The observed UAEA trace preserved:

```text
action_request.capability = mock.external_operation
action_request.request_id = app-server call_id
execution_observation.capability = mock.external_operation
harness.thread_id
harness.turn_id
harness.call_id
```

The model reported the returned fixture value in its final message. This is
the first repository-local evidence that an existing UAEA capability can be
executed through the Codex app-server dynamic-tool path and returned to the
model for continuation.

The probe also confirmed the known resource risks:

- the local Qwen model still uses fallback Codex model metadata;
- the app-server prompt consumed roughly 7.2k input tokens before the first
  tool call, with a reported model context window of about 7.8k;
- context compaction occurred before the final short answer;
- the diagnostic parser-enabled profile is not the frozen default profile.

The diagnostic `8002` process was stopped after the probe. The frozen
`8001` startup script, model, quantization, context length, KV policy, and GPU
policy were not changed.

## Regression Result After H2 Adapter

The repository test suite completed with:

```text
132 tests, OK
```

The unchanged Phase-1 scripted benchmark completed with:

```text
24/24 PASS
```

The adapter tests are intentionally limited to capability mapping, dispatch,
identity preservation, bounded response formatting, and controlled failure.
They do not claim that the Codex app-server should own UAEA cognition,
Goal Hypothesis, Problem Space, Memory, or Web semantic routing.

## Current H2 Decision

H2 is complete as a feasibility and boundary experiment. The result supports
continuing with a thin adapter approach, but does not justify a broad Harness
migration.

The next evidence needed is a small H3 comparison using:

```text
document.read_section
fs.list
one controlled failure
ordinary no-tool response
```

The comparison must keep the existing UAEA path as the control group and
measure context, latency, CPU/RAM, and GPU impact. Web, MCP, Goal Hypothesis,
SQLite cognitive history, and any Skill framework remain out of scope.

## H2 Runtime Provenance Closure

This section closes the provenance questions for the H2 dynamic-tool probe.
It describes the actual diagnostic run, which used port `8002`; it does not
change or replace the frozen `8001` serving profile.

### Harness Runtime

The H2 probe resolved `codex` to:

```text
C:\Users\wqkan\AppData\Local\OpenAI\Codex\bin\bffc5354119c8421\codex.exe
```

The executable reported:

```text
codex-cli 0.154.0-alpha.6.2
```

The file has a valid Authenticode signature for `OpenAI OpCo, LLC`. The probe
started it directly as a local child process:

```text
codex app-server --stdio
```

The H2 Python probe used `subprocess.Popen` with local stdin/stdout pipes. It
did not pass Codex `--remote` and did not pass `--code-mode-host`. No remote
Harness service was used for the app-server control plane or dynamic-tool
dispatch.

Therefore:

```text
Harness runtime location: LOCAL
Harness execution process: local codex.exe / local app-server subprocess
Remote Harness service dependency: NONE OBSERVED IN H2
```

This conclusion is about the Harness execution path. It does not claim that a
local Codex installation can never perform optional product telemetry or
updates; those are outside the H2 execution path and were not used as a
runtime dependency.

### Model Plane

The H2 probe set:

```text
CODEX_HOME =
  C:\Users\wqkan\AppData\Local\Temp\uaea-h1-codex-home-20260912

model_provider = uaea_local_vllm
model = qwen25-14b-awq
wire_api = responses
requires_openai_auth = false
configured base_url = http://127.0.0.1:8001/v1
```

For the parser-enabled diagnostic run, the app-server command applied this
CLI override:

```text
model_providers.uaea_local_vllm.base_url="http://127.0.0.1:8002/v1"
```

The effective H2 model path was therefore:

```text
local codex.exe
  -> local app-server
  -> local HTTP Responses request
  -> http://127.0.0.1:8002/v1
  -> diagnostic vLLM 0.26.0 in WSL2
  -> Qwen2.5-14B-Instruct-AWQ
  -> local RTX 5090 D v2
```

The H2 app-server output produced the expected Responses/tool events and token
usage from the configured local provider. The probe did not use the normal
remote provider in the user's Codex configuration, whose base URL is outside
the local path. The current repository and H2 artifacts do not retain a
packet capture or vLLM access-log line correlated to the exact H2 request, so
the endpoint conclusion is based on the effective CLI/configuration path plus
the successful local diagnostic serving process, not on a retained HTTP
packet-level capture.

### Tool Plane

The tool path was independent of the model transport:

```text
local app-server item/tool/call
  -> local H2 Python probe
  -> local D:\UAEA harness adapter
  -> local UAEA ToolRegistry
  -> local mock.external_operation
  -> local ToolResult
  -> local ExecutionObservation
  -> bounded app-server tool response
```

The H2 trace preserved:

```text
thread_id
turn_id
call_id
action_request.capability = mock.external_operation
action_request.request_id = call_id
execution_observation.capability = mock.external_operation
```

The mock fixture used a temporary local sandbox and returned a local
`mock://external/h2` reference. No remote tool service was involved.

The resulting plane-level status is:

```text
Harness runtime: LOCAL
Tool execution: UAEA local Capability Boundary
Model inference: local diagnostic vLLM on 127.0.0.1:8002
```

### Context Provenance

The three context values must remain separate:

| Layer | Observed/configured value | Evidence |
| --- | ---: | --- |
| Qwen2 model architecture | `32768` positional embeddings | local model `config.json`, `max_position_embeddings` |
| Qwen2 tokenizer metadata | `131072` model max length | local `tokenizer_config.json`, `model_max_length` |
| Frozen vLLM profile | `8192` | `scripts/start_vllm_qwen25_14b_awq.sh`, `MAX_MODEL_LEN` default |
| H2 Codex configured window | `8192` | isolated `CODEX_HOME/config.toml`, `model_context_window = 8192` |
| H2 Codex reported effective window | `7782` | app-server `thread/tokenUsage/updated` event |

The source of the H2 `8192` value is therefore closed: it was explicitly
configured in the isolated Codex H2 profile and independently matched the
vLLM serving cap. It did not originate from the Qwen2 model's native
`max_position_embeddings`.

The app-server reported `modelContextWindow = 7782`, not `8192`. The observed
number exactly matches:

```text
floor(8192 * 0.95) = 7782
```

The installed Codex binary contains the `effective_context_window_percent`
model-metadata field, and the runtime event exposes the resulting effective
window. This supports the interpretation that Codex applies an internal 95%
effective-budget factor to the configured 8192 window. The exact default
constant is not exposed in the temporary TOML or in a retained structured
diagnostic record, so the factor is recorded as a runtime-consistent
inference, not as a separately configurable UAEA parameter.

The practical distinction is:

```text
Qwen native capability: approximately 32K by model config
vLLM serving limit: 8192
Codex configured window: 8192
Codex effective usable window in H2: 7782
```

The H2 context failure was therefore caused by the combined serving and
Harness prompt budget. It was not evidence that the Qwen2 model natively has
only an 8192-token context.

### Localisation Decision

For the exact H2 diagnostic path:

```text
local Harness
  -> local UAEA Capability Boundary
  -> local vLLM inference
```

is satisfied. The diagnostic model endpoint was `8002`, because parser-enabled
tool calling was deliberately isolated from the frozen profile. The frozen
production-like path remains:

```text
local Harness
  -> local UAEA Capability Boundary
  -> local vLLM on 127.0.0.1:8001
```

but it was not running at the time of this provenance audit, and no claim is
made that the unmodified `8001` profile supports structured tool calls.

At audit completion, both `8001` and `8002` were stopped/listening on neither
port. The diagnostic `8002` process was cleaned up; the `8001` startup script
was not modified.

### Audit Evidence Commands

The closure was based on these read-only checks and the retained H2 probe
configuration/output:

```text
Get-Command codex -All
where.exe codex
codex --version
Get-AuthenticodeSignature <resolved codex.exe>
Get-Content <isolated CODEX_HOME>/config.toml
codex app-server --help
Get-NetTCPConnection -State Listen
```

For the WSL model/runtime:

```text
/opt/uaea/vllm_env/bin/vllm --version
grep context-related fields in:
  /opt/uaea-models/models/Qwen2.5-14B-Instruct-AWQ/config.json
  /opt/uaea-models/models/Qwen2.5-14B-Instruct-AWQ/tokenizer_config.json
```

The H2 probe itself records the effective app-server command, provider,
model, tool-call event, UAEA trace, token usage, and `turn/completed` result.

### Closure Status

```text
Harness executable/runtime local: PASS
Remote Harness service dependency in H2: NONE OBSERVED
UAEA local Tool Plane: PASS
H2 Model Plane local to diagnostic vLLM: PASS
8192 source: CLOSED
7782 effective-window formula: RUNTIME-CONSISTENT, exact internal constant not independently exposed
```

This closes H2 provenance only. H3 capability comparison, performance
measurement, context expansion, default-profile changes, and broader Harness
migration remain intentionally out of scope.

## H2 app-server dynamic-tool result

The app-server probe was run with the same isolated temporary Codex home and
the parser-enabled vLLM process on `8002`. A single
`mock_external_operation` dynamic tool was
registered through `thread/start`. The complete exchange succeeded:

```text
initialize
  -> thread/start(dynamicTools=[mock_external_operation])
  -> turn/start
  -> raw function_call(mock_external_operation, {"text":"hello"})
  -> item/tool/call
  -> UAEA probe response(success=true, contentItems=[inputText])
  -> item/completed(dynamicToolCall)
  -> raw function_call_output
  -> agentMessage("The mock_external_operation tool successfully processed the text \"hello\".")
  -> turn/completed
```

The app-server request preserved the important execution identity fields:

```text
threadId
turnId
callId
tool
arguments
success
contentItems
```

The observed token usage was approximately:

```text
first Responses request: input=7219, output=27, total=7246
continuation: input=7260, output=8, total=7268
app-server model context window: 7782
```

The model metadata warning remained:

```text
Model metadata for `qwen25-14b-awq` not found.
```

The probe also showed that the temporary Codex home still contributed system
skill descriptions despite host skill discovery being disabled. This is a
significant context-budget consideration for a practical profile.

This is the first end-to-end Harness feasibility result:

```text
Codex app-server dynamic tool
  -> local vLLM Responses
  -> Qwen2.5 AWQ
  -> client-side capability result
  -> app-server continuation
```

It is not yet a UAEA Runtime adapter implementation. It proves the protocol
path only. The next implementation step, if approved, should be a standalone
thin adapter experiment with one existing UAEA capability and explicit
event-to-`ExecutionObservation` normalization. It should remain isolated from
the frozen `8001` serving profile.
