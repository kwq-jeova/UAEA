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

## H2.5 Isolated Source-owned Harness Runtime

H2.5 repeated the dynamic-tool probe with a source-built Codex runtime rather
than the Desktop-installed binary. The upstream source was kept outside the
UAEA repository:

```text
source:
  D:\UAEA-deps\codex\rust-v0.154.0
tag:
  rust-v0.154.0
tag object:
  36eab01061df3cde5f95ec20a526777b430091ba
commit:
  6b9826e3aa83b1a5947db50f4332cb9c65f1b340
```

The source was built with the pinned upstream Rust toolchain (`1.95.0`) in
WSL. The staged artifact is:

```text
D:\UAEA-runtime\codex\source-rust-v0.154.0-wsl-x86_64\codex
```

It is an x86-64 Linux ELF with SHA-256:

```text
14cbd07db472b3a79aca95dfb4490a385c85be2116b3ca8631bc938b4e48e0fe
```

The source build succeeded in `10m 52s`. The upstream source tree was
restored to clean after Cargo generated workspace package-version updates in
`codex-rs/Cargo.lock`; those build side effects are not part of the upstream
source revision.

### Runtime Provenance

The H2.5 probe was:

```text
/mnt/d/UAEA-runtime/codex/source-rust-v0.154.0-wsl-x86_64/codex app-server --stdio
```

It was started as a local WSL child process by:

```text
D:\UAEA\scripts\h25_source_owned_app_server_probe.py
```

The probe used only:

```text
CODEX_HOME:
  /mnt/d/UAEA-runtime/codex-home-h25
workspace:
  /mnt/d/UAEA-runtime/codex-workspace-h25
app-server platform:
  Ubuntu 24.04 / x86_64 / linux
Codex version:
  codex-cli 0.154.0
```

The app-server returned `remoteControl/status/changed` with
`status = "disabled"`. The command did not use `--code-mode-host`, did not
use the Desktop binary, and did not use the user's normal Codex home. No
remote Harness service was observed.

This closes the runtime-location question as:

```text
Harness runtime: LOCAL, WSL process
Windows-native source artifact: NOT BUILT
Remote Harness service dependency: NONE OBSERVED
```

The distinction matters: this is a local Linux runtime under WSL, not a
Windows-native `codex.exe`.

### Model Plane

For the H2.5 run, the explicit model path was:

```text
source-built WSL codex
  -> local WSL app-server
  -> HTTP Responses request
  -> http://127.0.0.1:8002/v1
  -> diagnostic vLLM 0.26.0 in WSL2
  -> qwen25-14b-awq
  -> Qwen2.5-14B-Instruct-AWQ
  -> local RTX 5090 D v2
```

The `8002` server used the same model, quantization, `dtype=half`,
`max_model_len=8192`, `gpu_memory_utilization=0.7`, and single-GPU boundary
as the frozen profile. It additionally used only the previously approved
diagnostic flags:

```text
--enable-auto-tool-choice
--tool-call-parser hermes
```

The vLLM server log recorded successful local `POST /v1/responses` requests
for the H2.5 turn. The frozen `8001` server and its startup script were not
changed and were not used by this diagnostic run.

### Tool Plane

The tool path remained separate from model transport:

```text
local source-built app-server
  -> item/tool/call over local stdio
  -> H2.5 Python probe
  -> D:\UAEA harness adapter
  -> UAEA ToolRegistry
  -> mock.external_operation
  -> ToolResult
  -> ExecutionObservation
  -> bounded app-server contentItems
  -> local app-server continuation
  -> agent message
  -> turn/completed
```

The successful trace preserved the same `thread_id`, `turn_id`, `call_id`,
capability, and observation identity fields as H2. The dynamic tool call
received `{"text":"hello"}` and returned a bounded local
`mock://external/h25` reference. No remote tool service was involved.

### Context Provenance Closure

The H2.5 run confirms the existing separation:

```text
Qwen model config max_position_embeddings: 32768
Qwen tokenizer model_max_length: 131072
vLLM max_model_len: 8192
Codex config model_context_window: 8192
Codex reported modelContextWindow: 7782
```

The exact `8192` in the Harness profile comes from the isolated
`CODEX_HOME/config.toml` field:

```text
model_context_window = 8192
```

The diagnostic vLLM process independently enforced `max_model_len = 8192`.
The app-server reported `7782`, which is consistent with
`floor(8192 * 0.95)`. The binary exposes the effective-window metadata field,
but the internal percentage is not separately exposed as a UAEA configuration
value. Therefore:

```text
8192 source: CLOSED
7782 effective-window formula: runtime-consistent, internal constant not independently configurable
```

The source-owned probe also confirmed that bundled system skill descriptions
are still injected into the local app-server prompt even when host skill
discovery is disabled. This caused roughly `7224` input tokens before the
first tool call and triggered compaction before the final message. It is a
local Harness context-budget issue, not evidence that the Qwen model has only
an 8192-token native context.

### H2.5 Closure

```text
Source-owned local Harness runtime: PASS (WSL-local form)
UAEA local Capability Boundary: PASS
Local vLLM Model Plane: PASS on diagnostic 8002
Frozen 8001 profile modified: NO
8192 provenance: CLOSED
Windows-native source build: NOT PROVIDED
```

H2.5 does not authorize H3, context expansion, performance measurement,
additional capability migration, or changes to the frozen `8001` profile.

## H3 Harness Runtime Characterization

H3-A measured context-budget behavior without changing the frozen `8001`
profile, the Codex source commit, the model artifact, quantization, dtype,
GPU-memory policy, or UAEA Runtime contract. Each profile used an isolated
`CODEX_HOME`, a fresh diagnostic `8002` vLLM process, the source-owned WSL
Codex binary, the existing `HarnessDynamicToolAdapter`, and the same five
fixed workloads:

```text
ordinary no-tool response
mock.external_operation once
document.read_section once
mock.external_operation five-call loop
controlled failure once
```

The results are stored outside the repository:

```text
D:\UAEA-runtime\h3-results\
```

Each profile directory contains `result.json`, raw app-server events in
`app-server-events.jsonl`, app-server stderr, and the complete vLLM log.

### H3-A Profile Results

| Profile | vLLM startup | Codex effective window | KV cache tokens | Peak GPU used | App-server result |
| ---: | ---: | ---: | ---: | ---: | --- |
| 8192 | 64.017 s | 7782 | 32928 | 17632 MiB | PASS |
| 16384 | 86.040 s | 15564 | 28256 | 16768 MiB | PASS |
| 32768 | failed before health | not available | not available | 13264 MiB during load | `FAIL @ gpu_memory_utilization=0.7` |

The effective Codex windows remain consistent with the observed 95% runtime
factor:

```text
floor(8192 * 0.95) = 7782
floor(16384 * 0.95) = 15564
```

The 32K vLLM log gives the exact failure boundary:

```text
required KV cache: 6.0 GiB
available KV cache: 5.18 GiB
estimated maximum model length: 28256
```

The sweep therefore stopped at the required boundary. No attempt was made to
raise GPU utilization to `0.8` or `0.9`.

### Harness Workload Observations

The 8K run had initial input occupancy of approximately `0.961-0.966` of the
reported `7782` effective tokens. It completed all turns, but not every
workload completed its requested tool-call contract:

```text
ordinary_no_tool: 0 tool calls, no compaction
mock_single: 0 tool calls, turn completed but workload contract not met
document_read_section: 12 tool calls, compaction occurred
mock_five_calls: 5 tool calls, compaction occurred
controlled_failure: 5 tool calls, compaction occurred
```

The 16K run had initial input occupancy of approximately `0.489-0.492` of
the reported `15564` effective tokens and did not compact:

```text
ordinary_no_tool: 0 tool calls
mock_single: 0 tool calls, workload contract not met
document_read_section: 1 tool call
mock_five_calls: 3 tool calls, workload contract not met
controlled_failure: 1 tool call
```

These results distinguish protocol completion from task success. A
`turn/completed` event proves that the Harness turn ended; it does not prove
that the model emitted the expected capability calls. The extra 8K calls and
the vLLM Hermes parser errors are retained in the raw logs as observed
compatibility behavior, not hidden by prompt or keyword changes.

### H3-A Measurement Boundary

The runner is:

```text
scripts/h3_context_characterization.py
```

It starts and stops only the diagnostic `8002` process and records:

- configured vLLM and Codex context;
- effective `modelContextWindow`;
- initial input tokens and occupancy;
- compaction events and token usage before compaction;
- dynamic tool calls and normalized UAEA traces;
- vLLM KV-cache allocation and rejection logs;
- GPU memory samples;
- vLLM/Codex RSS samples;
- app-server and workload latency;
- raw app-server and vLLM logs.

The runner uses the existing capability adapter and does not introduce a new
Harness abstraction. All three profiles were cleaned up after execution:
there were no residual vLLM or app-server processes, and the GPU returned to
zero used memory.

### H3-A Decision

```text
8K: technically runnable, but context-saturated for the current Harness prompt
16K: runnable under the unchanged single-GPU boundary and materially healthier
32K: not runnable at gpu_memory_utilization=0.7 on this 24 GB GPU
```

This is a characterization result only. It does not authorize H3-B, context
optimization, skill-prompt reduction, GPU-policy changes, or migration of
additional capabilities.

## H3-A2 - 32K GPU/KV Boundary

H3-A2 varied only `gpu_memory_utilization` for a diagnostic `8002` process.
The model, AWQ quantization, `dtype=half`, `max_model_len=32768`, Codex
`model_context_window=32768`, source-owned Codex binary, tool parser,
Harness adapter, ToolRegistry, isolated `CODEX_HOME`, and Harness prompt were
unchanged. The frozen `8001` profile was not used or modified.

### Profiles

| Profile | Startup | KV cache | Estimated/runtime boundary | Peak GPU used | Workload result |
| ---: | --- | ---: | --- | ---: | --- |
| 0.70 | FAIL | 5.18 GiB available | 6.0 GiB required; estimated max length 28256 | 13264 MiB during load | no workload |
| 0.75 | PASS | 7.22 GiB; 39440 tokens | maximum concurrency 1.20x for 32768 | 18884 MiB | runtime PASS; one tool-selection miss |
| 0.80 | NOT TESTED | not applicable | stopped after first viable profile | not applicable | not applicable |
| 0.85 | NOT TESTED | not applicable | stopped after first viable profile | not applicable | not applicable |

The first viable tested memory budget is therefore:

```text
minimum viable tested gpu_memory_utilization = 0.75
```

This is a tested lower bound, not a claim that `0.75` is the mathematical
minimum threshold.

The `0.75` profile took `70.041 s` to become healthy. vLLM reported
`7.22 GiB` available KV cache, `39440` KV-cache tokens, and no OOM or request
rejection. Peak sampled GPU memory was `18884 MiB` and final GPU memory
returned to zero after shutdown.

### 32K Workloads at 0.75

Codex reported:

```text
configured model_context_window = 32768
effective modelContextWindow = 31129
initial input tokens = 7764-7806
initial occupancy = 0.249-0.251
compaction = none
```

The fixed workload results were:

```text
ordinary_no_tool:
  PASS, 0 tool calls, turn completed

mock_single:
  workload contract miss, 0 tool calls, turn completed

document_read_section:
  PASS, 1 tool call, continuation completed

mock_five_calls:
  PASS, 5 tool calls, continuation completed
```

The `mock_single` miss is not accompanied by OOM, engine failure, request
rejection, or context compaction. The same profile successfully executed the
same mock capability in the five-call loop and successfully completed the
document capability path. It is therefore recorded as a model
single-call-selection nondeterminism, not converted into a false runtime
PASS and not treated as evidence of a 32K GPU/KV failure.

The vLLM log contains an `EngineDeadError` during final teardown after the
runner sent SIGTERM to stop the diagnostic process group. No such error
occurred during health checks or workload execution, and the process exited
with return code `0`; it is recorded as shutdown behavior rather than a
runtime workload crash.

### H3-A2 Decision

```text
32K startup: PASS at 0.75
32K runtime resource stability: PASS for the executed workload set
32K deterministic single mock-call contract: NOT CONFIRMED
32K support classification: SUPPORTED with a model tool-selection caveat
H3-A2 overall: PARTIAL
```

The narrow resource conclusion is:

> 32K is not blocked by a fundamental model or hardware impossibility under
> the tested configuration. It requires a larger vLLM memory budget than
> `0.70`; `0.75` is the first tested profile that both starts and serves the
> selected workload set.

This does not authorize changing the frozen `8001` profile, selecting 32K as
the final UAEA Harness context, increasing utilization further, or starting
H3-B. The known 16K profile remains the stable baseline for the next
architecture review.

## Harness Capability Ownership Audit

This section freezes the post-H3-A2 architecture ownership assessment. It is
an audit and migration recommendation only. It does not migrate capabilities,
delete Phase-1/Phase-2 code, fork Codex, change the frozen `8001` profile,
start H3-B, or change model, quantization, context, or GPU policy.

### Audit Evidence

The pinned Harness candidate remains:

```text
Codex CLI: 0.154.0
binary: /mnt/d/UAEA-runtime/codex/source-rust-v0.154.0-wsl-x86_64/codex
schema: /mnt/d/UAEA-runtime/codex-schema-v0.154.0-20260915
```

The source-owned binary exposes local CLI and app-server surfaces for:

- local app-server over stdio, Unix socket, or websocket;
- thread and turn lifecycle;
- `exec`, shell, command execution, resize, write, terminate, and output
  streams;
- sandbox modes and permission profiles;
- approval routing for command execution, file changes, patch application,
  sandbox escapes, MCP approval prompts, and permissions;
- app-server schema generation;
- dynamic tools;
- MCP stdio and streamable HTTP server configuration;
- skills, plugins, hooks, apps, and workspace dependencies;
- thread persistence, queueing, fork/resume/archive, compaction, token usage,
  goal metadata, memory mode flags, and timeline/item APIs;
- native web-search item/event shapes and browser/web feature flags.

The generated protocol schema contains concrete app-server request/notification
shapes for `DynamicToolCallParams`, `DynamicToolCallResponse`,
`ThreadStartParams`, `TurnStartParams`, `ContextCompactedNotification`,
`CommandExec*`, `FsReadFile*`, `FsWriteFile*`, `Mcp*`, `Skills*`, `Hooks*`,
`ThreadGoal*`, `ThreadMemoryMode*`, and `WebSearch*` items. H2/H2.5/H3-A/H3-A2
proved that this source-owned Harness can run locally against the local vLLM
model plane and can bridge UAEA dynamic tools into `ToolRegistry`.

### Ownership Matrix

| Capability | Harness support | Current UAEA support | Proposed ownership | Migration priority | Reason |
| --- | --- | --- | --- | --- | --- |
| File | Native `FsReadFile`, `FsWriteFile`, fuzzy file search, thread file-change items, patch approval | Phase-1 `ToolRegistry` has `document.read_file`, `document.read_section`, `document.write_file`, `fs.list`, `fs.mkdir` | `HARNESS_NATIVE` for generic file IO; `UAEA_KEEP` only for cognitive/evidence-specific file interpretation | High, after one A/B file experiment | Generic file IO is mature Harness infrastructure. UAEA file tools remain valuable as frozen baseline and as a controlled comparison, not as permanent duplicate plumbing. |
| Shell | Native `exec`, `command/exec`, terminal streams, resize/write/terminate, background terminals | No equivalent mature Phase-1 shell runtime | `HARNESS_NATIVE` | High | Shell execution is generic agent infrastructure and already integrated with Harness sandbox, approvals, streams, and thread items. |
| Apply patch | CLI `apply`, app-server patch/file-change approval schemas, feature flags for patch events | No comparable UAEA-native patch lifecycle | `HARNESS_NATIVE` | Medium | Patch mechanics are generic coding-agent infrastructure. UAEA should consume resulting trajectory/events only if useful for cognition research. |
| Sandbox | CLI sandbox command, sandbox modes, permission profiles, app-server sandbox policy, network disable flag for sandbox state | Minimal Phase-1 path sandbox limited to project/sandbox path rules | `HARNESS_NATIVE` for execution sandbox; `UAEA_KEEP` only for research fixtures and frozen regression | High | Harness owns a broader, tested execution policy surface. UAEA sandbox should not become a second permanent policy engine. |
| Approval | CLI approval policy, auto-review, approval schemas for command/file/patch/permissions/MCP/sandbox | Phase-1 has no comparable generalized approval lifecycle | `HARNESS_NATIVE` | High | Approval is part of execution safety and tool lifecycle. UAEA may later add cognitive policy inputs, but not replace approval plumbing. |
| Network policy | Sandbox network disable surface and approval references; browser/web feature flags exist | UAEA WebAdapter uses controlled HTTP fetch/search and source history | `HYBRID` | Medium | Execution/network control belongs to Harness, but UAEA still needs provenance, evidence quality, and memory-ingestion semantics. |
| Web | Native web-search item/action shapes and browser/web feature flags; exact local/offline provenance semantics still unverified | `WebSearchCapability`, `WebFetchCapability`, SQLite source history, `EvidenceReference`, bounded projection | `HYBRID` until audited | Medium | Web is not just generic browsing for UAEA. Ownership depends on whether Harness web can satisfy controlled networking, local operation, evidence provenance, bounded projection, and future memory ingestion. |
| MCP/Skills | Native MCP add/list/get/login/logout; stdio and streamable HTTP; app-server MCP status/resource/tool schemas; skills and plugin surfaces | UAEA has no mature MCP/skill platform; earlier ToolRegistry capability metadata is not a skill system | `HARNESS_NATIVE` for generic extension plumbing; `UAEA_KEEP` for UAEA-specific dynamic tools/MCP servers | Medium | Harness already owns extension plumbing. UAEA should expose cognition/memory/experience interfaces through that surface when needed. |
| Thread | Native thread start/resume/fork/archive/delete/list/queue/timeline/items/turns/realtime APIs | Phase-1 has workflow/ledger/trajectory baselines, not a mature thread store | `HARNESS_NATIVE` for runtime thread lifecycle; `UAEA_KEEP` for research trajectory/evaluation records | High | Thread lifecycle is generic runtime. UAEA should record/consume trajectories for research, not maintain a parallel user-facing thread runtime. |
| Context | Native token usage, context compaction, context fragments, startup context, thread items | Phase-1 planner context and bounded execution observations; context vs memory still under research | `HARNESS_NATIVE` for token-window management and generic compaction; `UAEA_KEEP` for memory selection and cognitive-state projection | High | Harness should own the prompt-window mechanics. UAEA should decide what memory/cognitive evidence is worth injecting, not rebuild generic compaction. |
| Memory | Harness exposes memory feature flags, memory citations, reset/mode APIs, but semantics are product/runtime memory rather than UAEA research memory | UAEA has Candidate, EvidenceReference, SQLite source/evidence history, fixture evaluator; not final Memory Store | `UAEA_KEEP` | High research priority, not migration priority | UAEA memory is about evidence, episodic/semantic consolidation, retrieval by goal, and training data. It must not collapse into Harness transcript/context memory. |
| Goal | Harness exposes thread goal metadata APIs and a stable `goals` feature | Phase-1 has active goal/workflow records; current research distinguishes Goal Hypothesis from execution todo | `UAEA_KEEP` for Goal Hypothesis; `HYBRID` only for projecting goal hints into Harness lifecycle | High research priority | Harness goals are execution/thread metadata. UAEA Goal Hypothesis is cognitive, revisable, tied to problem boundary and epistemic update. |
| Training | No LoRA/training ownership; Harness can produce execution traces and events | UAEA has trajectory, candidate/evidence concepts, and post-training research direction | `UAEA_KEEP` | Later | Training corpus, experience evaluation, LoRA, and continual adaptation are the core UAEA research loop and should not be delegated to Harness. |

### Target Architecture Recommendation

The recommended long-term direction is:

```text
UAEA Cognition
  -> Harness Runtime
  -> Local Model + Generic Tools

plus

UAEA-specific Extensions
```

Harness should become the primary owner for mature, commodity agent runtime
infrastructure:

- agent loop;
- thread/turn lifecycle;
- shell/process execution;
- generic file IO and patch mechanics;
- sandbox and approval plumbing;
- MCP, skills, plugins, hooks, and extension transport;
- context-window mechanics and generic compaction.

UAEA should remain the owner of the research-specific layer:

- Goal Hypothesis and problem boundary;
- meta-cognition / L0;
- Working/Episodic/Semantic memory semantics;
- evidence quality and provenance interpretation;
- memory retrieval and consolidation policy;
- cognitive routing and policy;
- experience evaluation;
- trajectory-to-training-corpus conversion;
- LoRA / continual adaptation.

### ToolRegistry Future Role

`ToolRegistry` should not be deleted or migrated now. Its near-term role is:

```text
frozen Phase-1/Phase-2 baseline
+ compatibility bridge for H2/H3 dynamicTools
+ controlled test surface for UAEA-specific extensions
```

Its likely long-term role is narrower:

```text
UAEA-specific Extension Boundary
```

That means future `ToolRegistry` candidates are not generic file/shell/sandbox
tools, but UAEA-specific affordances such as:

- `memory.retrieve`;
- `memory.commit_candidate`;
- `goal.inspect`;
- `goal.propose_update`;
- `hypothesis.evaluate`;
- `experience.record`;
- `training.feedback`;
- domain capabilities that produce UAEA-specific evidence or learning signals.

Generic file, shell, patch, sandbox, approval, and thread plumbing should
gradually move to Harness if A/B evidence confirms it satisfies local UAEA
constraints.

### Web Ownership Decision

Web remains `HYBRID`.

The existing UAEA `web.search` and `web.fetch` implementations should be
preserved as baseline because they already provide:

- controlled fetch/search through `WebAdapter`;
- SQLite source history;
- `EvidenceReference`;
- bounded projection;
- separation between web evidence, memory candidate, and truth.

Harness has native web-search item/action shapes and web/browser feature flags,
but this audit has not yet proven that Harness-native Web satisfies UAEA's
requirements for local operation, controlled networking, provenance,
bounded evidence projection, and future memory ingestion.

The next Web decision should compare:

```text
Harness-native Web events
vs
UAEA WebCapability evidence records
vs
Hybrid adapter that maps Harness Web events into UAEA Source/Evidence history
```

No Web migration is authorized by this audit.

### App-server Extension Surface Assessment

The app-server surface is sufficient for current bridge and near-term
experiments:

- dynamic tools can call UAEA extension code and return bounded content items;
- thread/turn APIs expose execution lifecycle;
- token usage and compaction events can be observed;
- client-provided context fragments can be passed at turn start;
- MCP/skills/plugins/hooks provide additional extension candidates;
- thread goal and memory-mode APIs exist as metadata/control surfaces.

It is not yet proven sufficient for full UAEA cognition ownership because Goal
Hypothesis, memory retrieval, meta-cognitive policy, and experience
consolidation may need lifecycle participation at:

- turn start before context formation;
- memory retrieval and selection;
- tool-policy construction;
- observation ingestion;
- turn completion;
- trajectory/evidence consolidation.

The current recommendation is therefore:

```text
Use upstream Harness first.
Prefer dynamic tools, MCP, hooks, and app-server protocol integration.
Do not fork Codex Core unless a concrete lifecycle hook is missing and cannot
be represented externally.
```

### Possible Future Codex Core Pressure Points

Future Core work may be justified only if evidence shows that external
extension surfaces cannot support one of these:

- pre-context cognitive-state injection before model prompt assembly;
- deterministic memory retrieval hook with citation/provenance control;
- observation-to-experience event stream with stable IDs;
- tool-policy modulation from UAEA cognitive policy without duplicating the
  Harness tool loop;
- local web provenance controls if Harness-native Web cannot be externally
  adapted;
- stable access to compaction inputs/outputs when UAEA memory formation needs
  more than final compacted text.

None of these justify a fork now.

### Baseline / Fallback Classification

The following old Phase implementations should be preserved as baseline and
fallback, not expanded as permanent duplicate infrastructure:

- Phase-1 `ToolRegistry` generic file/fs capabilities;
- Phase-1 sandbox path rules;
- Phase-1 workflow/runtime orchestration;
- Phase-2 direct Web REPL;
- Phase-2 WebShell semantic routing;
- Phase-2 generic execution lifecycle experiments;
- H2/H2.5 dynamic-tool bridge scripts;
- H3-A/H3-A2 characterization scripts.

They remain valuable for reproducibility, regression, and A/B comparison.
They should not be deleted, and they should not be expanded unless a baseline
or comparison need is explicit.

### Next Migration Experiment

The next highest-value migration experiment is not H3-B and not a broad
capability migration. It should be a narrow A/B ownership probe:

```text
Harness-native file/shell lifecycle
vs
UAEA ToolRegistry file/fs lifecycle
```

Acceptance should focus on:

- local Harness runtime and local vLLM path preserved;
- no change to frozen `8001`;
- same user task run through both paths when possible;
- trace mapping from Harness thread items into UAEA trajectory records;
- confirmation that UAEA cognition/memory/goal state is not owned by Harness;
- clear rollback to the frozen Phase baseline.

Only after this A/B probe should generic file/shell/sandbox migration be
considered.

## Harness-native Capability A/B

This section records the first narrow ownership experiment after the Harness
Capability Ownership Audit. The scope is intentionally limited to File. It
does not migrate Web, Shell, Sandbox, Goal, Memory, LoRA, or Codex Core, and it
does not change the frozen `8001` profile.

The probe script is:

```text
scripts/h3_file_ab_probe.py
```

It writes artifacts outside the repository:

```text
D:\UAEA-runtime\h3-results\file-ab-20260915-202417
```

The probe does not start vLLM and does not consume GPU. It starts the
source-built local Codex app-server and compares:

```text
Path A - Harness native app-server file API
  fs/readFile README.md
  fs/readDirectory project root

Path B - UAEA baseline
  ToolRegistry document.read_section README.md section_index=1
  ToolRegistry fs.list project root
```

### File A/B Result

```text
Harness-native File: PARTIAL
UAEA File baseline: PASS
Recommended ownership: HARNESS primary candidate for generic File
```

The `Harness-native File` result is `PARTIAL`, not full `PASS`, for a precise
reason: the app-server native File API passed directly, but this probe did not
prove a full model-mediated loop where the model autonomously chooses a
Harness-native file tool during a turn. H3-A/H3-A2 already proved the
model-mediated UAEA dynamicTools file path; the next A/B can close the
model-mediated native side if needed.

### Path A - Harness Native

Observed result:

```text
fs/readFile README.md: PASS
fs/readDirectory project root: PASS
read_file elapsed: 0.0652 s
read_directory elapsed: 0.0378 s
README decoded size: 7163 chars
directory entry count: 20
```

Observed semantics:

- `fs/readFile` accepts an absolute path and returns base64 file contents.
- `fs/readDirectory` accepts an absolute directory path and returns direct child
  entries with `fileName`, `isDirectory`, and `isFile`.
- The file API is local to the app-server process and does not require vLLM.
- The response is mechanically clean and compact, but it does not by itself
  produce UAEA `ToolResult`, `ExecutionObservation`, `EvidenceReference`, or
  cognitive provenance.
- Workspace restriction and authorization are app-server responsibilities; this
  probe used the repository root as cwd and did not attempt boundary escape or
  write operations.

### Path B - UAEA Baseline

Observed result:

```text
document.read_section README.md section_index=1: PASS
fs.list project root: PASS
read_section elapsed: 0.0635 s
fs.list elapsed: 0.0426 s
directory entry count: 20
```

Observed semantics:

- `document.read_section` returned a section-level extraction with heading,
  line range, content hash, source hash, section catalog, and content excerpt.
- `fs.list` returned sorted directory entries.
- Both results were normalized into `ExecutionObservation`.
- The UAEA baseline provides richer runtime/cognitive metadata for this exact
  read-section operation, but that richness is also why it is not merely a
  generic file runtime.

### File A/B Comparison

| Dimension | Harness-native File | UAEA File baseline | Ownership implication |
| --- | --- | --- | --- |
| Functional result | PASS for file read and directory list | PASS for section read and directory list | Both can read/list. |
| Workspace restriction | App-server/cwd/runtime roots surface exists; boundary escape not tested here | Phase-1 `Sandbox` path rules restrict reads/lists to sandbox and readonly docs | Harness is the better long-term owner, but write/boundary tests belong in Shell+Sandbox A/B. |
| Filesystem authority | Native app-server fs API with absolute paths | ToolRegistry-mediated capability names and sandbox resolver | Harness is more general; UAEA is narrower and research-specific. |
| Approval behavior | Not applicable for read-only direct probe | Not applicable for read/list baseline | Approval must be evaluated with write/shell/sandbox later. |
| Error semantics | JSON-RPC response/error shape | `ToolResult(ok, message, data)` plus observation status | UAEA observation semantics remain useful for cognition/evidence, but generic errors can map from Harness. |
| Tool lifecycle | Direct app-server request; no model turn required | Capability lifecycle through ToolRegistry and ledger | Generic file lifecycle should move to Harness; UAEA lifecycle can become an adapter/trajectory normalization layer. |
| Context/token overhead | Zero model-token overhead for direct fs API; model-mediated native path not measured | H3-A2 dynamicTools path adds tool schema and tool output tokens | Harness-native should be lower for direct runtime file access; model-mediated comparison remains open. |
| Latency | 0.0378-0.0652 s | 0.0426-0.0635 s | Similar for local reads; latency is not the deciding factor. |
| Event observability | JSON-RPC request/response and app-server events | Ledger events plus `ExecutionObservation` | Harness events are sufficient for runtime trajectory; UAEA still needs a normalization layer for cognition. |
| Audit/provenance | File path and response only in this direct probe | Resolved path, hashes, section catalog, line range, observation id | UAEA evidence/provenance semantics should remain UAEA-owned. |
| Runtime complexity | Reuses existing app-server File API | Maintains separate generic file implementation | Long-term duplicate generic File runtime is not justified if Harness boundary tests pass. |

### File Ownership Decision

The narrow result supports:

```text
Harness File -> primary candidate for generic File lifecycle
UAEA File -> frozen baseline/fallback and evidence/cognition adapter reference
```

This does not authorize deleting or rewriting the UAEA file tools. It only
confirms that the next file-related work should focus on mapping Harness file
events into UAEA trajectory/evidence records, not on expanding a second generic
file runtime.

## Harness Event Surface Audit

This audit combines generated app-server schema inspection with observed H3
raw app-server events. It does not implement Goal Hypothesis or Memory.

Schema evidence:

```text
D:\UAEA-runtime\codex-schema-v0.154.0-20260915
```

Runtime evidence:

```text
D:\UAEA-runtime\h3-results\context-16384-20260913-112122\app-server-events.jsonl
D:\UAEA-runtime\h3-results\context-8192-20260913-111740\app-server-events.jsonl
D:\UAEA-runtime\h3-results\context-32768-20260913-113828\app-server-events.jsonl
```

### Event Surface Table

| Event / lifecycle data | Available | Identity/order | Sufficient for future UAEA cognition |
| --- | --- | --- | --- |
| user message | YES | `item/completed` with `item.type=userMessage`, `item.id`, `threadId`, `turnId`, `completedAtMs`; event stream order and `emittedAtMs` available | YES for evidence; needs UAEA interpretation layer |
| agent message | YES | `item/completed` with `item.type=agentMessage`, `item.id`, `threadId`, `turnId`, `completedAtMs`; delta schema also exists | YES for evidence; final answer and intermediate deltas can be recorded |
| tool call | YES | dynamicTools emit `item/tool/call` with JSON-RPC request id, `threadId`, `turnId`, `callId`, `tool`, `namespace`, `arguments`; item completion uses `dynamicToolCall` with same call id | YES for dynamicTools; native tool item schemas also exist for command/MCP/Web |
| tool result | YES | `dynamicToolCall` item includes `id`, `status`, `contentItems`, `success`, `durationMs`, `threadId`, `turnId`; command/MCP/Web schemas expose their own item types | YES for runtime trajectory; UAEA must normalize into Evidence/Observation |
| observation | PARTIAL | Harness exposes tool result items, raw response usage, and item timeline; UAEA `ExecutionObservation` is not native Harness semantics | PARTIAL; sufficient source material exists, but UAEA observation adapter remains required |
| turn completion | YES | `turn/started` and `turn/completed` include `threadId`, turn `id`, `status`, `error`, `startedAt`, `completedAt`, `durationMs`, and item summary | YES |
| token usage | YES | `thread/tokenUsage/updated` and `rawResponse/completed` include `threadId`, `turnId`, input/output/total/cached/reasoning tokens and `modelContextWindow` | YES |
| compaction | YES | `item/completed` can include `contextCompaction`; generated schema also includes `ContextCompactedNotification` | PARTIAL; compaction occurrence is visible, but future memory formation may need deeper access to compacted inputs/outputs |
| error/cancel | YES | `turn/completed` can include failed status and error; schema includes interrupt/cancel/error notifications | YES for lifecycle; semantic error classification remains UAEA-owned |
| event ordering | YES | Stream order, `observed_at`, `emittedAtMs`, `completedAtMs`, `startedAt`, IDs, and thread/turn/item linkage are present | YES, with a UAEA event normalizer |
| thread id | YES | Present on turn, item, tool, token usage, compaction, error events | YES |
| turn id | YES | Present on turn, item, tool, raw response, token usage, compaction, error events | YES |
| item id | YES | Present on user/agent/tool/compaction/thread items; native schemas include item-linked notifications | YES |

### Lifecycle Sufficiency

Current assessment:

```text
Can UAEA observe enough Harness trajectory to derive Goal Hypothesis later?
PARTIAL

Goal inference implemented:
NO

Memory implemented:
NO
```

Why `PARTIAL`:

- The event stream is rich enough to reconstruct user messages, agent
  messages, dynamic tool calls, tool arguments, tool results, token usage,
  compaction occurrence, turn completion, failures, and event ordering.
- This is enough evidence to start an external UAEA trajectory normalizer.
- It is not yet enough to claim full Goal/Memory lifecycle ownership, because
  pre-context injection, deterministic memory retrieval, and post-turn
  consolidation hooks have not been validated as operational integration
  points.

### App-server Lifecycle Sufficiency

| Lifecycle point | Current status | Notes |
| --- | --- | --- |
| pre-context injection | `PARTIAL` | `turn/start` supports `additionalContext`, but pre-model prompt assembly hooks are not proven. |
| pre-model-call cognitive state injection | `PARTIAL` | Possible through `additionalContext` or dynamic tool/MCP patterns; not validated as a stable cognitive hook. |
| memory retrieval point | `UNKNOWN` | Harness has memory-mode/citation surfaces, but UAEA memory semantics are different and not integrated. |
| observation stream | `AVAILABLE` | Dynamic tool and item events provide enough data to normalize into UAEA observations. |
| post-turn consolidation | `PARTIAL` | `turn/completed` is visible; no dedicated UAEA consolidation hook is proven. |
| goal-state update | `PARTIAL` | Thread goal metadata exists, but UAEA Goal Hypothesis is not equivalent to Harness thread goal. |
| experience emission | `PARTIAL` | Event stream is sufficient input; stable UAEA experience schema is not implemented. |

### Event Surface Decision

The app-server event surface is strong enough for the next step to be external
trajectory normalization, not a Codex Core fork.

Current blockers:

- no proven model-mediated Harness-native File A/B loop yet;
- no validated pre-context UAEA memory retrieval hook;
- no UAEA adapter that maps Harness native File/Shell/Web items into
  `ExecutionObservation`/Evidence records;
- compaction output visibility may be insufficient for future memory
  consolidation, but this is not yet proven blocking.

### Recommended Next Step

Recommended next step:

```text
B. Deeper App Server lifecycle audit
```

Reason: File A/B already indicates Harness is the likely primary owner for
generic File, but the strategic UAEA question is now whether app-server events
and lifecycle controls are sufficient to support external Goal/Memory
cognition without a Codex Core fork. Shell+Sandbox A/B should wait until the
event normalizer/lifecycle hook requirements are clearer.

## Deeper App Server Lifecycle Audit

This audit closes the narrow lifecycle question raised above. It does not
perform Shell/Sandbox A/B, implement Goal Hypothesis, implement Memory, migrate
additional capabilities, enter H3-B, change the frozen `8001` profile, or fork
Codex Core.

Probe:

```text
scripts/h3_app_server_lifecycle_probe.py
```

Executed command:

```text
cd /mnt/d/UAEA
/opt/uaea/vllm_env/bin/python scripts/h3_app_server_lifecycle_probe.py --context 32768 --gpu-memory-utilization 0.75
```

Artifacts:

```text
D:\UAEA-runtime\h3-results\lifecycle-32768-20260915-203305\result.json
D:\UAEA-runtime\h3-results\lifecycle-32768-20260915-203305\app-server-events.jsonl
D:\UAEA-runtime\h3-results\lifecycle-32768-20260915-203305\app-server-stderr.log
D:\UAEA-runtime\h3-results\lifecycle-32768-20260915-203305\vllm.log
```

The probe started only the diagnostic `8002` local vLLM runtime with:

```text
max_model_len = 32768
gpu_memory_utilization = 0.75
Codex model_context_window = 32768
```

The frozen `8001` profile was not used or modified. The diagnostic vLLM process
started successfully, became healthy after `72.028s`, and was stopped by the
probe with `vllm_returncode = 0`.

### Lifecycle Control Results

| Lifecycle question | Status | App-server support classification | Evidence | Current limit |
| --- | --- | --- | --- | --- |
| Pre-context / pre-model injection | `AVAILABLE` | Directly supported by App Server through `turn/start.additionalContext` | The probe injected `uaea.lifecycle.goal_state` and `uaea.lifecycle.meta_policy` containing marker `UAEA_PRE_CONTEXT_MARKER_20260915`; the model replied exactly `UAEA_PRE_CONTEXT_MARKER_20260915`. | This proves stable pre-turn application context injection. It does not implement UAEA memory retrieval or a Goal engine. |
| Raw trajectory observability | `AVAILABLE` for the observed event surface; `PARTIAL` for future native-tool completeness | Directly supported by App Server events; normalization can be thin external orchestration | Event stream captured ordered `thread/started`, `turn/started`, `item/started`, `item/completed`, `item/agentMessage/delta`, `rawResponseItem/completed`, `rawResponse/completed`, `thread/tokenUsage/updated`, `turn/completed`, user messages, agent messages, command execution attempts, ids, and token usage. | Dynamic-tool observability is already proven by H2/H2.5/H3-A2. This lifecycle probe observed native command/file attempt events, but not successful native file completion because sandbox execution failed locally. |
| Pre-compaction access | `PARTIAL` | Available through thin live event-stream capture before compaction; deeper compaction payload details are not fully proven | No compaction occurred in this run (`compaction_items = []`). Earlier H3 event captures observed `contextCompaction` items. Raw events are streamed and can be consumed before turn completion when UAEA subscribes live. | Exact compaction input/output visibility remains unclosed. UAEA should consume raw Harness trajectory from the live stream before relying on compacted summaries. |
| Post-turn trigger | `AVAILABLE` | Directly supported by App Server `turn/completed`; future UAEA work can attach thin external orchestration | `turn/completed` includes stable thread/turn linkage and final turn state. Token usage is emitted through `thread/tokenUsage/updated`; raw response completion is separately observable. | The trigger exists, but Experience evaluation, Goal evidence update, Memory consolidation, and training trajectory emission are not implemented in this checkpoint. |

### Model-mediated Native File Result

Status:

```text
PARTIAL / NOT CONFIRMED AS SUCCESSFUL
```

The model attempted a native Harness command/file path:

```text
/bin/bash -lc 'cat README.md'
```

The app-server emitted `commandExecution` items with:

```text
id = call_8b430ac931877d6a
cwd = /mnt/d/UAEA
commandActions = read README.md
status = failed
exitCode = 101
```

Failure reason:

```text
bubblewrap is unavailable: no system bwrap was found on PATH and no bundled codex-resources/bwrap binary was found next to the Codex executable
```

Conclusion:

```text
User -> model autonomous native file attempt -> Harness native command/file item
```

is observable, but:

```text
User -> model autonomous native file capability -> successful native file result -> model continuation
```

is not yet confirmed on this local source-owned Harness runtime because the
native sandbox dependency is missing. This is a Harness native execution
environment issue, not a UAEA `ToolRegistry` issue. The checkpoint does not
start Shell/Sandbox A/B to fix it.

### Lifecycle Closure Decision

```text
Pre-context injection: AVAILABLE
Raw trajectory observability: AVAILABLE for core thread/turn/message/tool/token lifecycle; PARTIAL for future full native-tool coverage
Pre-compaction access: PARTIAL
Post-turn trigger: AVAILABLE
Model-mediated native File: PARTIAL
```

Current App Server sufficiency for UAEA Goal/Memory research:

```text
PARTIAL
```

Reason:

- App Server is sufficient to start external UAEA lifecycle integration for
  pre-turn cognitive context injection, raw event capture, and post-turn
  triggers.
- A thin external UAEA trajectory normalizer is the right next boundary.
- Full Goal/Memory research still needs UAEA-owned retrieval, cognitive-state
  selection, evidence normalization, and compaction-before-memory policy.
- Successful model-mediated native File remains blocked by local sandbox
  dependency, so generic File ownership should not be declared fully closed
  from this probe alone.

Concrete reason to fork Codex Core:

```text
NO
```

No architecture-level blocker currently proves that UAEA must fork Codex Core.
The observed gaps are either external orchestration work (`additionalContext`,
event normalization, post-turn consumers), environment setup work (native
sandbox dependency), or still-unproven compaction-detail questions.

Recommended next step:

```text
Build a thin external Harness event normalizer that consumes live app-server
events into UAEA trajectory/observation records.
```

Do not begin Goal/Memory implementation yet. Do not start H3-B until the
normalizer requirements and native sandbox dependency are separately reviewed.

## Harness Event Normalizer / UAEA Trajectory Contract

This checkpoint adds the first thin event-normalization boundary between Codex
App Server protocol events and future UAEA cognition consumers. It does not
implement Goal Hypothesis, Memory, Evidence scoring, Experience evaluation,
LoRA, Shell/Sandbox A/B, native File sandbox repair, Web ownership audit, H3-B,
or a Codex Core fork.

Implementation:

```text
harness/event_normalizer.py
tests/test_harness_event_normalizer.py
```

The normalizer converts raw App Server JSON-RPC messages into a stable
UAEA-neutral event shape:

```text
TrajectoryEvent
  sequence
  event_type
  identity:
    thread_id
    turn_id
    item_id
    event_id
  payload
  provenance
  raw_event_reference
  raw_event
```

The event is intentionally structural. It does not decide whether an event is
important, whether it supports a Goal, whether it should become Memory, or
whether evidence is true. Those remain future UAEA cognition responsibilities.

### Raw Event Retention

Each `TrajectoryEvent` retains:

```text
raw_event
raw_event_reference
provenance.source = codex_app_server
provenance.native_method
provenance.observed_at
provenance.emitted_at_ms
```

This keeps future schema migration possible. Later Goal, Memory, Evidence,
Experience, and Training components should consume normalized events first, but
can still trace back to the raw Harness event when a new parser or audit is
needed.

### Normalized Event Types

The current minimal event vocabulary is evidence-backed by H2/H2.5/H3 logs and
the lifecycle probe:

```text
USER_INPUT
AGENT_OUTPUT
TOOL_CALL
TOOL_RESULT
OBSERVATION
COMMAND_EXECUTION
TOKEN_USAGE
CONTEXT_COMPACTION
TURN_STARTED
TURN_COMPLETED
PRE_TURN_CONTEXT
ERROR
CANCELLED
RAW_EVENT
```

`OBSERVATION` is emitted for completed tool/command execution items as a
runtime result boundary. It is still not a user task and not a Memory decision.

### Identity And Ordering

The normalizer preserves native Harness identities when present:

```text
threadId -> thread_id
turnId / turn.id -> turn_id
item.id / itemId / callId -> item_id
JSON-RPC id / callId / itemId / item.id -> event_id
```

Because App Server events do not expose a universal monotonic sequence number,
the normalizer assigns an increasing UAEA `sequence` in receive order. This is
explicitly a UAEA-generated ordering identity, not a native Harness identity.

This is sufficient to reconstruct a turn trajectory such as:

```text
PRE_TURN_CONTEXT
TURN_STARTED
USER_INPUT
AGENT_OUTPUT
TOOL_CALL
TOOL_RESULT
OBSERVATION
COMMAND_EXECUTION
TOKEN_USAGE
TURN_COMPLETED
```

when those events are present in the raw stream.

### Pre-turn And Post-turn Boundary

The normalizer supports pre-turn lifecycle records by accepting the outer
orchestrator's own `turn/start` JSON-RPC request record:

```text
turn/start.additionalContext -> PRE_TURN_CONTEXT
```

This captures the already-proven pre-model injection boundary without
implementing retrieval or Goal state. The post-turn boundary maps:

```text
turn/completed -> TURN_COMPLETED
```

and emits `ERROR` or `CANCELLED` when the completed turn reports failed or
cancelled state.

### Compaction Handling

`contextCompaction` items normalize to:

```text
CONTEXT_COMPACTION
```

The current status remains:

```text
Compaction handling: PARTIAL
```

Occurrence can be represented, and raw events are retained. The exact
compaction input/output visibility is still not fully closed. UAEA future
Memory should therefore consume raw Harness trajectory before relying on
compacted summaries.

### Boundary Decision

```text
Goal implemented: NO
Memory implemented: NO
Evidence scoring implemented: NO
Experience evaluation implemented: NO
Codex Core fork required: NO
```

The event normalizer is now the recommended thin boundary for future cognition
work:

```text
Codex App Server events
  -> HarnessEventNormalizer
  -> TrajectoryEvent
  -> future UAEA Goal / Memory / Evidence / Experience / Training
```

The next work should build a live trajectory writer around this contract only
after the normalized schema is accepted.

## Live Trajectory Writer

This checkpoint adds a thin diagnostic writer on top of
`HarnessEventNormalizer`. It does not implement Goal inference, Memory
selection, Evidence scoring, Experience evaluation, SQLite persistence, vector
storage, long-term memory, native File sandbox repair, Shell/Sandbox A/B, Web
ownership audit, H3-B, or Codex Core changes.

Implementation:

```text
harness/trajectory_writer.py
tests/test_harness_trajectory_writer.py
```

The writer records:

```text
raw App Server event
  -> HarnessEventNormalizer
  -> TrajectoryEvent
  -> JSONL diagnostic trajectory
```

Each JSONL row is the serialized `TrajectoryEvent` and includes:

```text
sequence
event_type
identity.thread_id
identity.turn_id
identity.item_id
identity.event_id
payload
provenance
raw_event_reference
raw_event
```

The writer preserves UAEA receive order through the normalizer-generated
`sequence`. It supports:

```text
run-level trajectory:
  <run_id>.trajectory.jsonl

thread-split trajectory:
  <run_id>.<thread_id>.trajectory.jsonl
```

Unknown-thread events, such as early config warnings or initialization traffic,
are written to an `unknown-thread` diagnostic file when thread splitting is
enabled. This keeps the raw lifecycle observable without pretending those
events belong to a specific turn.

### Probe Integration

The lifecycle probe now writes normalized trajectories alongside the existing
raw app-server event log:

```text
scripts/h3_app_server_lifecycle_probe.py
```

The probe records outgoing `turn/start` requests into the trajectory writer so
that:

```text
turn/start.additionalContext -> PRE_TURN_CONTEXT
```

is captured before model execution. Incoming App Server stdout/stderr events
are also normalized as they are received. This preserves the proven lifecycle:

```text
UAEA cognitive state candidate
  -> pre-turn additionalContext
  -> Harness live event stream
  -> normalized TrajectoryEvent JSONL
  -> turn/completed
  -> future post-turn processing
```

The probe still uses only diagnostic `8002`. The frozen `8001` profile is not
used or modified.

### Real Probe Result

Executed:

```text
cd /mnt/d/UAEA
/opt/uaea/vllm_env/bin/python scripts/h3_app_server_lifecycle_probe.py --context 32768 --gpu-memory-utilization 0.75
```

Artifacts:

```text
D:\UAEA-runtime\h3-results\lifecycle-32768-20260916-200259\result.json
D:\UAEA-runtime\h3-results\lifecycle-32768-20260916-200259\app-server-events.jsonl
D:\UAEA-runtime\h3-results\lifecycle-32768-20260916-200259\normalized-trajectories\
```

Observed writer stats:

```text
event_count = 306
file_count = 2
PRE_TURN_CONTEXT = 2
TURN_COMPLETED = 2
TOKEN_USAGE = 4
COMMAND_EXECUTION = 3
OBSERVATION = 1
ERROR = 2
USER_INPUT = 7
AGENT_OUTPUT = 258
```

Trajectory files:

```text
lifecycle-32768-20260916-200259.01a0aa1a-8c1d-7770-a00b-91baa38496ac.trajectory.jsonl
lifecycle-32768-20260916-200259.unknown-thread.trajectory.jsonl
```

The run confirmed:

```text
user input -> Harness -> response / command attempt -> turn/completed -> JSONL trajectory
```

The native model-mediated File path remains blocked by the already-known local
`bubblewrap` / `codex-resources/bwrap` issue. The writer correctly records the
failed `COMMAND_EXECUTION`, `OBSERVATION`, and `ERROR` events; it does not try
to repair sandbox execution.

Compaction remains:

```text
PARTIAL
```

No compaction was forced in this checkpoint. The writer can record
`CONTEXT_COMPACTION` events when present, but compaction input/output
visibility remains a separate unresolved question.

### Writer Boundary Decision

```text
Live Trajectory Writer added: YES
Goal implemented: NO
Memory implemented: NO
Evidence scoring implemented: NO
Experience evaluation implemented: NO
Long-term persistence implemented: NO
```

The current trajectory boundary is now:

```text
Codex App Server live events
  -> HarnessEventNormalizer
  -> HarnessTrajectoryWriter
  -> JSONL diagnostic trajectory
```

This is sufficient for future cognition work to consume a stable UAEA event
contract instead of raw Codex JSON-RPC. It is not yet a Memory database or an
Experience evaluator.

## Trajectory Naming And Reader Contract

This checkpoint freezes the file naming and writer lifecycle contract, then adds
the minimal reader/validator. It still does not implement Goal inference,
Memory, Evidence scoring, Experience evaluation, SQLite, vector DB, LoRA,
Shell/Sandbox A/B, Web ownership audit, H3-B, native File sandbox repair, or
Codex Core changes.

### File Naming Contract

Canonical trajectory:

```text
<run_id>.trajectory.jsonl
```

This file is the canonical source for one Harness run. It stores the full,
ordered event stream that UAEA actually received and normalized during that
run.

Thread projection:

```text
<run_id>.<thread_id>.trajectory.jsonl
```

Thread-level files are derived diagnostic projections only. They are useful for
inspection and debugging, but they are not an equally authoritative data source.
Future readers and validators should treat the run-level trajectory as the
canonical source and derive thread/turn views from it.

Filename segments are normalized by `HarnessTrajectoryWriter`:

- unsupported filename characters are replaced with `_`;
- empty segments fall back to a stable placeholder;
- long segments are truncated and receive a short hash suffix;
- colliding normalized thread ids receive a hash suffix;
- repeated original ids map to the same normalized segment inside one writer.

Tests cover illegal characters, long ids, repeated ids, and normalized
collisions such as `thread/A` and `thread:A`.

### Writer Lifecycle Contract

One writer corresponds to one Harness run, not one turn.

```text
writer open
  -> zero or more threads
  -> zero or more turns
  -> append normalized events
  -> flush at terminal boundary
  -> writer close
```

Terminal boundaries are:

```text
TURN_COMPLETED
ERROR
CANCELLED
```

The writer opens trajectory files in append mode and never rewrites existing
rows. If the process exits unexpectedly, rows already written and flushed remain
valid JSONL. Terminal events are flushed immediately; `close()` flushes all open
handles again.

### Sequence Semantics

```text
TrajectoryEvent.sequence
```

means only UAEA writer/normalizer receive order. It is not a Harness internal
causal sequence and should not be used as one.

Harness-native identity remains separate:

```text
thread_id
turn_id
item_id
event_id
```

### Reader / Validator

Implementation:

```text
harness/trajectory_reader.py
tests/test_harness_trajectory_reader.py
```

The minimal reader/validator provides:

```text
read_trajectory_jsonl(...)
validate_trajectory_records(...)
TrajectoryReadResult.project_by_thread()
TrajectoryReadResult.reconstruct_turns()
```

Validation currently checks:

- JSONL rows are readable;
- `sequence` is strictly increasing;
- event type and identity fields exist;
- raw event references remain present;
- raw events remain traceable;
- per-turn ordered timelines can be reconstructed;
- terminal events identify terminal state.

Malformed/truncated behavior:

```text
default:
  malformed JSONL line -> TrajectoryReadError

allow_truncated_final_line=True:
  malformed final line is ignored and recorded as a read issue
```

This behavior is intended for crash recovery diagnostics only. It does not
silently accept malformed middle lines.

### Diagnostic Script Hygiene

The following H3 scripts are retained as diagnostic/reproducibility tools and
are included in `py_compile` checks:

```text
scripts/h3_context_characterization.py
scripts/h3_file_ab_probe.py
scripts/h3_harness_interactive_repl.py
scripts/h3_app_server_lifecycle_probe.py
```

They remain outside Goal/Memory and ToolRegistry. Their role is to reproduce
Harness runtime characterization, File A/B, interactive Harness bridge testing,
and lifecycle/trajectory writer probes. They should not expand into permanent
UAEA cognition infrastructure.

### Reader Boundary Decision

```text
Trajectory naming contract: FROZEN FOR CURRENT H3 DIAGNOSTICS
Canonical source: <run_id>.trajectory.jsonl
Thread trajectory: derived projection
Reader / validator: PASS for JSONL diagnostics
Per-turn reconstruction: PASS for normalized run-level trajectory
Goal implemented: NO
Memory implemented: NO
Evidence scoring implemented: NO
Experience evaluation implemented: NO
```

## Real H3 Trajectory Artifact Smoke Validation

本次 smoke validation 只验证真实 H3 artifact 是否能被当前
`HarnessTrajectoryReader` / validator / per-turn reconstruction 读取和恢复。
它不实现 Goal、Memory、Evidence scoring、Experience evaluation、SQLite、
vector DB、LoRA，也不修复 native File 的 `bubblewrap` 环境问题。

验证对象：

```text
D:\UAEA-runtime\h3-results\lifecycle-32768-20260916-202534\normalized-trajectories\
```

Canonical run-level trajectory：

```text
D:\UAEA-runtime\h3-results\lifecycle-32768-20260916-202534\normalized-trajectories\lifecycle-32768-20260916-202534.trajectory.jsonl
```

该文件是本 run 的 source of truth。Thread-level 文件只作为 projection：

```text
lifecycle-32768-20260916-202534.01a0aa2f-2308-78d0-b5de-80057019dc47.trajectory.jsonl
lifecycle-32768-20260916-202534.unknown-thread.trajectory.jsonl
```

`unknown-thread` projection 保留 canonical stream 中确实无法归属到具体
thread 的 9 条事件。它不是第二权威源。

### Smoke Result

读取和验证结果：

```text
records = 409
validation_ok = true
read_issues = []
sequence_first_last = 1, 409
turn_count = 2
raw_traceable = true
```

事件计数：

```text
AGENT_OUTPUT = 353
COMMAND_EXECUTION = 6
ERROR = 2
OBSERVATION = 2
PRE_TURN_CONTEXT = 2
RAW_EVENT = 21
TOKEN_USAGE = 8
TOOL_CALL = 2
TOOL_RESULT = 2
TURN_COMPLETED = 2
TURN_STARTED = 2
USER_INPUT = 7
```

Per-turn reconstruction 恢复出两个 turn，并且 terminal state 均为
`TURN_COMPLETED`：

```text
thread_id = 01a0aa2f-2308-78d0-b5de-80057019dc47
turn_id = 01a0aa2f-256b-75c2-8e1f-b056d7a2efb6
terminal_state = TURN_COMPLETED

thread_id = 01a0aa2f-2308-78d0-b5de-80057019dc47
turn_id = 01a0aa2f-2e1e-7520-8e11-ad42e74f112e
terminal_state = TURN_COMPLETED
```

Thread projection 与 canonical stream 派生出的 projection 一致：

```text
unknown-thread:
  canonical_count = 9
  file_count = 9
  sequence_match = true

01a0aa2f-2308-78d0-b5de-80057019dc47:
  canonical_count = 400
  file_count = 400
  sequence_match = true
```

已知 native File / sandbox 失败被保留为 trajectory failure evidence：

```text
ERROR = 2
COMMAND_EXECUTION = 6
bubblewrap_related_records = 12
```

示例 failure 原始信息仍可通过 `raw_event` 和 `raw_event_reference` 追溯：

```text
bubblewrap is unavailable: no system bwrap was found on PATH and no bundled codex-resources/bwrap binary was found next to the Codex executable
```

### Contract Notes

旧 artifact：

```text
D:\UAEA-runtime\h3-results\lifecycle-32768-20260916-200259\normalized-trajectories\
```

生成于 run-level canonical naming contract 冻结前，因此只有 thread projection，
没有：

```text
<run_id>.trajectory.jsonl
```

中间 artifact：

```text
D:\UAEA-runtime\h3-results\lifecycle-32768-20260916-201859\normalized-trajectories\
```

暴露了 projection consistency gap：某些 `turn/start` response row 只有
`turn_id`，writer 当时尚无法在写入 projection 前回填 `thread_id`。当前 writer
通过 request-id / turn-id mapping 对后续真实 run 的 projection 做最小回填；
reader 也能在读取 canonical 时基于 `turn_id -> thread_id` 做只读投影回填。

当前 artifact：

```text
D:\UAEA-runtime\h3-results\lifecycle-32768-20260916-202534\normalized-trajectories\
```

在最新 reader/writer contract 下验证通过：

```text
Real artifact smoke validation: PASS
Canonical trajectory: PASS
Reader validation: PASS
Per-turn reconstruction: PASS
Thread projection consistency: PASS
Known failure preservation: PASS
```
