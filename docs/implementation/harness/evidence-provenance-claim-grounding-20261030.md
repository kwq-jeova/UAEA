# Evidence provenance and claim grounding — 2026-10-30

## Decision and boundaries

Black-box design holds if observable source identity, executed capability receipts,
and model assertions remain separate. Full natural-language claim verification is
not available: a URL, HTTP 200, fetch receipt, or exact quotation cannot prove
semantic relevance, entailment, correct financial period, comprehension, or
workflow completion. No classifier, second model, provider-specific semantic rule,
planner, or new authority mechanism was introduced.

Formal entry now records completed model outputs and explicit URL associations and
sends a bounded numerical provenance summary at the next turn. Explicit typed
execution-assertion and exact-quotation checks are offline prototype APIs only.
The current model protocol does not negotiate these fields; the client does not
extract reading assertions or quotations from arbitrary prose. No claim is
blocked or semantically certified by this prototype.

The older shared semantic/execution contract remains opt-in and is not enabled
by this work. Native User Input answers are still not automatic permission grants.

## Search defect and repair

phase2/web_adapter.py previously rejected every link without a scheme and host.
The real SerpAPI organic results included /goto?url=… references: 8 entries became
1, 1, and 0 parsed results. The earlier raw_search_result_count actually counted
normalized parsed entries, concealing this loss.

Relative root references are now resolved against the fixed origin
https://www.google.com/. No origin is taken from model arguments or backend
metadata. Original links and per-index parse/rejection reasons are retained in
SQLite metadata and capability evidence. Protocol-relative references, ambiguous
bare paths, credentials, invalid ports, control/space/backslash characters, and
non-HTTP schemes are rejected. Duplicate identities are diagnosed. No request is
issued by parsing; existing fetch/URL/capability/sandbox checks remain in place.

An opaque /goto token remains opaque: the restored URL identifies a Google
wrapper, not a verified publisher or final article. No destination URL, provider,
publication date, or article identity is invented. Redirect destination/content
identity is a remaining limitation, not a claimed security or semantic validation.

Counts now separately track:
- search_transport.backend_raw: organic entries before parsing, including rejected/duplicate entries.
- parsed: valid unique normalized identities before result constraints.
- candidate_projected: candidates after constraints and requested max_results.
- model_visible: candidate identities present in the tool-response projection.
- visibility_basis: capability projection or final tool-response projection.
The final count measures serialized delivery, not model attention or comprehension.
Verbose rejection diagnostics remain in host records, outside the bounded model
projection. A parse/filter failure is no longer described as an empty provider response.
Legacy raw_search_result_count now means actual backend raw count for this backend;
parsed_search_result_count preserves the previously conflated parsed count.

## Existing evidence and minimum new links

Existing ActionRequest/ExecutionObservation/Workflow Step, canonical events, and
Source Coverage already separate proposals, tool outcomes, and discovered/fetched
URLs. Search snippets are not fetched pages; Turn completion is not fulfillment.

New harness/evidence_provenance.py consumes host-recorded Step outcomes:
- search_discovery identifies an observed search hit; it never implies page reading.
- page_response identifies an available fetch response, with content hash where supplied.
- capability_result supports the same identity/observation boundary for other capabilities.
- an intact source_excerpt includes event identity, snapshot hash, text, and text SHA256.
  If projection truncates/rewrites text or identity, excerpt_supplied is not established.
  The excerpt is a bounded projection, never proof the full document was provided.
- Model outputs are interpretation-only RuntimeObjectRecords with full text hash,
  event/raw references and grounding_at_output. They are never ingested as sources.
  Streaming deltas/empty starts are excluded; duplicate complete representations
  in one turn share a text-hash identity.
- Explicit HTTP URL syntax is associated with observed identities; no natural-language
  claim detector is used. Plain-text assertions remain unassessed.
- Evidence links are evaluated at output time; later fetches do not retroactively
  validate earlier generated claims. Historical model references grant no authority.

ground_claim independently reports:
1. execution_grounded: a typed operation/URL or source-id assertion matches an actual
   capability observation, or remains not established/not asserted.
2. source_linked: observed source identities vs unresolved references.
3. content_supported: always not_assessed_requires_semantic_judgment.
An exact quote match proves only substring presence in the intact supplied excerpt.
A nonmatch proves nothing about text outside that excerpt. Model assertions cannot
create a successful Step, authorize execution, or complete the Workflow.

The formal REPL includes a numerical evidence_provenance context entry with counts
and explicit model_output_is_source_evidence=false. No historical model prose is
promoted into that application-level entry. Existing assistant proposals remain
untrusted context. This is additional observable feedback, not enforcement of
natural-language truth or a guarantee of further model action.

## Offline verification

283 targeted regression tests PASS; command and verbose output are in the audit.
New cases cover safe/unsafe relative identities, stage counts, parse vs empty
responses, search-only citations, unsupported reading claims, history reuse,
actual fetch plus unsupported semantic interpretation, exact/nonmatching/corrupt
excerpt checks, insufficient-evidence responses, temporal non-retroactivity,
streamed output deduplication, and generic capability evidence.

A simulated Harness X wrapper normalizes non-Codex receipts to the same Step
outcomes and produces equivalent source inventory and grounding results.
This is deterministic contract simulation, not a second real Harness/model test.
Codex event normalization remains in its existing adapter; core source/claim
functions do not import Codex events or inspect hidden model state.

Saved real response replay (no network or model calls), using formal 5000-char budget:

| Search | Backend raw | Previous parsed | New parsed | Candidate projection | Tool-response visible |
|---|---:|---:|---:|---:|---:|
| Q3, max_results=5 | 8 | 1 | 8 | 5 | 3 |
| Q3, max_results=10 | 8 | 1 | 8 | 8 | 3 |
| Q2, max_results=5 | 8 | 0 | 8 | 5 | 3 |

This proves transport of saved payloads, not renewed search availability, relevance,
publisher identity, or successful page acquisition. Candidate visibility is still
bounded by the existing projection budget; omitted sources are reported.

Old manual trajectory replay retains 12 complete assistant messages across 8
turns, 0 fetch observations, 0 supplied page excerpts, active Workflow and no
established completion. Two discovery records refer to the same URL in two search
observations; they are not independent publishers. Existing Source Coverage
continues to count unique URLs. Search-only URL associations can be source-linked
while their page/content assertions remain unverified.

Acceptance:
- Evidence Contract: PASS within the tested deterministic/offline boundary.
- Model Behavior: not re-tested; previous manual research behavior remains FAIL.
- Real Workflow: not re-tested; no supported research completion can be declared.

## Why factual counters did not produce research action

The original snapshots already projected fetched=0 and unattempted requests.
There was no compaction (maximum input 26639/31129). Therefore these observations
do not support a missing-history/compaction explanation. Transport loss is proven;
poor query diversification, failure to fetch, misreading validation rejection as
network denial, and repeated reliance on prior generated conclusions are observed
model behaviors. Instruction-following limitations and confusing/diluted context
are plausible contributors; no ablation establishes their relative causes.

Late turns still have erroneous new_task relation hints, although actual workflow
ownership stays unchanged. Missing allow_fallback still requires retry in the
formal legacy execution path. This task does not repair those independent issues.
No forced tool-per-turn rule, hardcoded research sequence, or NLP patch was added.

## Files changed this round

- phase2/web_adapter.py: safe reference normalization, source link identity, parse diagnostics.
- phase2/web_capability.py: raw/parsed/candidate counts, empty-state distinctions, typed excerpt provenance.
- phase2/evidence_boundary.py: actual raw counts and stage visibility.
- harness/codex_dynamic_tools.py: bounded delivery counts and unresolved destination marker.
- harness/evidence_provenance.py: shared source/claim prototype and model-output records.
- harness/workflow_continuity.py: retain source hash/excerpt and search transport in existing outcomes.
- harness/semantic_state_adapter.py: complete-output provenance hook and numerical summary.
- harness/io_contract.py: history/source/interpretation distinction and optional factual context.
- scripts/h3_harness_interactive_repl.py: wire factual provenance context into the shared entry.
- tests/test_search_transport.py and tests/test_evidence_provenance.py: new directed cases.
- tests/test_google_serpapi_backend.py and tests/test_web_adapter_shell.py:
  update raw-count and filtering-state expectations.

## Next human acceptance and current entry

With the existing external 32K+Hermes service running:

    bash /home/wqkan_wsl/uaea-n1x/UAEA/scripts/start_h3_harness_interactive.sh --profile n1x --turn-timeout 420 --user-input-timeout 300

Restart H3 to load these changes; vLLM requires no restart. Native questions accept
a number or free text; /cancel interrupts. Exit does not stop external vLLM.

Use one task: find a target-period report and conference call, request reading of
one actual candidate, then compare an earlier period. Inspect real search/fetch
receipts, exact observed URL (wrapper vs publisher), source hashes, supplied
excerpts, and final quotations. The model should disclose missing page evidence
or unverified hypotheses; absence of action must not appear as completed research.
Do not award Model Behavior or Real Workflow PASS from source-link/contract checks.

## Integrity and Git

145 protected files unchanged, including Runtime source, frozen harness/UMA/32K
artifacts and prior manual evidence. Runtime submodule clean. Main HEAD remains
e99df8dfac252b4ecd4fd0f502ce65573056d046; Runtime HEAD remains
1f311291df027baceca40779643e5107b9eb6fb3.
No dependency changes, live model calls, service restart, Commit or Push.
Existing uncommitted changes were preserved. x86_64 GPU execution was not tested;
the implementation has no platform branch and shared startup regression passed.
