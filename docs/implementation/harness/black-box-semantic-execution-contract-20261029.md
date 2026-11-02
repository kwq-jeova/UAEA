# Black-box semantic/execution contract prototype — 2026-10-29

Status: opt-in application-layer prototype, offline verification only.
The production H3 launcher does not enable it. No Qwen inference, network search,
Codex process, or vLLM startup was performed for this change.

## Architectural judgment

The model proposes observable interpretations and actions. UAEA owns request
identity, accepted authority, execution decisions, observations and workflow facts.
The Harness transports messages; its tool names, session IDs, event shapes and
context implementation are not authority.

Provenance establishes origin, not natural-language entailment. An exact quote
does not prove that its surrounding sentence grants a permission.
A model's proposed scope cannot make a constraint persist across tasks.
No confidence threshold, keyword expansion or second model is introduced.

The current rule extractor remains transitional legacy behavior. Its conversion
of “指定 Google” into both provider selection and a fallback ban is NOT used as
authority by the new execution boundary. The legacy launcher is not migrated
before interpretation transport and application policy are validated.

## Changed boundaries

- harness/semantic_interpretation.py: candidates on existing RuntimeObjectRecord
  metadata. Host assigns request/model-event identity. Exact Unicode character
  spans are checked against the original text; meaning remains unconfirmed.
- harness/semantic_execution_contract.py: trusted EffectiveContract, parameter
  binding, conflict rejection, existing Registry execution, Step/Observation
  recording before projecting results to a Harness.
- harness/codex_dynamic_tools.py: optional execution_boundary injection, Codex
  decoding and delegation. Without injection, legacy schemas/behavior remain.
- harness/semantic_state_adapter.py and harness/request_continuity.py: preserve
  complete pre-turn input, surrounding whitespace and SHA256 on the existing
  workflow_request_input record. Interpretation/context summaries remain bounded.
  Native identity binding does not duplicate or replace the original input.

No frozen Runtime interface, Codex binary, UMA patch, model environment,
Goal Engine or Memory Ontology changes. No platform-specific logic.

## Interpretation transport

Pinned rust-v0.163.0 source exposes turn/start.outputSchema:
codex-rs/app-server-protocol/src/protocol/v2/turn.rs, output_schema field.
The turn processor forwards it as final_output_json_schema. It constrains the
final assistant message, NOT an interpretation before every action.

Two optional transport surfaces are provided:
1. _uaea_interpretation on a dynamic Action, stripped before the Capability call.
   It accompanies the same observable proposal; no separate model call is added.
2. FINAL_OUTPUT_SCHEMA / record_final_output: negotiated final JSON containing
   answer and interpretation. This supports candidates without an Action.
   The existing REPL does not yet negotiate or consume this final format.

A final-message interpretation cannot authorize earlier actions in that turn.
No tool call or interpretation is required to retain a request. Arbitrary prose
is not mined for hidden JSON or execution claims.

Tests prove supplied structured output traverses these parsers/adapter.
They do NOT prove deployed Qwen/vLLM/Codex reliably generates it, or that final-schema
negotiation works end to end. No obligatory semantic-tool continuation was added.

## Authority and minimal promotion conditions

Candidates remain status=candidate, authority_level=interpretation, with semantic
correctness not_established. There is NO automatic promotion API.

Authority enters through trusted application code as independently recorded
structured policy or authenticated structured user confirmation
(record_structured_authority). This ingress is not a model tool. Authenticating
a real human confirmation channel remains host-integration work. Tests use
explicit host fixtures, not live human authorization.

Before execution each authority reference must:
- resolve to an active execution_authority record, not a candidate;
- belong to the workflow and applicable input scope;
- have an independent source event and expected policy/confirmation kind;
- contain the exact structured binding or permission state being used.

Application policy must authorize the Capability. Unknown, revoked, out-of-scope
or unsupported authority fails closed. Quote matches, confidence and a reference
to raw user text do not satisfy this gate. Natural-language entailment is not verified.

Provider choice and fallback authorization are independent. The executor has no
Provider-name checks or language-specific rules. Offline fixtures configure a
system no-provider-switch policy, applicable to every provider, to bind a missing
allow_fallback=false. Provenance is system policy, never an invented user ban.
Without a binding, missing data stays a recoverable missing parameter.
Fallback=true without a grant remains authorization_unknown. Explicit conflicts
with fixed bindings are rejected.

Original proposal and effective parameters/per-field sources are separate.
Query/path/section are not invented or silently rewritten.

## Execution facts and Workflow

Existing ActionRequest, Registry.execute_capability, ExecutionObservation,
record_attempt and record_outcome are reused. Steps retain proposed arguments
and a separate execution_contract decision.

Canonical TrajectoryEvent records are emitted as EXECUTION_DECISION and OBSERVATION,
independent of Harness echo. The existing reader accepts them. Optional sinks can
persist these events. Production H3 journal merging is not yet wired; raw events
remain a separate transport diagnostic surface.

Fact distinctions:
- request with no Action: no execution, fulfillment not established;
- validation rejection: no Capability invocation;
- Capability result: independent of model-visible result projection;
- projection failure after success: recorded success remains;
- handler exception after invocation: execution_unknown, no automatic retry;
- turn completion: never establishes Workflow completion.

Receipts are cached by workflow + stable action identity. Reusing an identity
with different parameters is rejected. Same-identity replay after result/sink
failure returns saved facts without re-execution. This is process-local,
NOT crash-safe exactly-once I/O. Different action IDs are not deduplicated by
guessed semantic equivalence. No restart-recovery/retry engine is introduced.

## Offline acceptance scope

tests/test_harness_semantic_execution_contract.py covers forged candidate authority,
quoted/example text, provider/fallback separation, structured authority and revocation,
scoped grants, parameter sources, unknown permission, explicit conflicts, missing
parameters, cancellation, protocol equivalence, no-Action retention, result/sink
failures, receipt replay, unknown outcomes and original text beyond 500 characters.

File tests invoke the actual frozen Registry/Sandbox and check content hashes and
denied paths. Web tests invoke existing WebSearchCapability with an offline backend,
including successful source storage and credential-failure separation. No real
HTTP/model execution is claimed.

Harness X is only a differently shaped test input decoder, not an implementation.
Protocol equivalence checks cover success, unknown/granted permission, rejection
and real file reads, comparing decisions, parameters, observations and Step outcomes.

## Smallest next manual acceptance

First wire an explicitly selected experimental host configuration with recorded
application policy and the shared boundary; do not silently replace default policy.

Use the existing 32K + Hermes external service:
1. One ordinary no-tool question: retain full input; optionally receive a structured
   final candidate; create no execution evidence.
2. One Provider-selected search: inspect candidate, decision, parameter provenance,
   actual Tool Result and final answer.
3. Keep explicit-conflict enforcement in deterministic offline tests; do not require
   the model to generate a particular bad action.

Schema/inline generation failures are transport/model limitations, not grounds to
add provider regexes, a second model or a planner.

Current manual entry:
    bash /home/wqkan_wsl/uaea-n1x/UAEA/scripts/start_h3_harness_interactive.sh --profile n1x --turn-timeout 420

Restart H3 for the full-input retention change; an existing vLLM needs no restart.
This command still uses legacy execution and is NOT real-model acceptance of the
opt-in contract prototype.

## Recorded verification

Contract tests: 28 PASS. Related regression total: 139 PASS, 0 skipped.
All results are offline; 5090D profile checks are simulated, not x86 GPU acceptance.
git diff --check passed. Runtime submodule is clean at
1f311291df027baceca40779643e5107b9eb6fb3.
43 protected baseline/binary/UMA files match their pre-change SHA256 values.
HEAD remains e99df8dfac252b4ecd4fd0f502ce65573056d046; no Commit or Push.
Pre-existing uncommitted continuity changes were retained.

Evidence directory:
/home/wqkan_wsl/uaea-n1x/audit/black-box-contract-20261029T004542Z

See targeted-tests.txt, test-summary.json, protected-verification.json and
offline-evidence/ (fixture snapshots and canonical-format events).
