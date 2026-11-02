# Evidence boundary and temporal fidelity — 2026-10-29

## Scope and architectural judgment

The fix changes evidence visibility/fact presentation, not model NLU or authority.
Lexical diagnostics no longer decide whether retrieved candidate links are visible.
Models assess research relevance; their assessments are never written as original
source facts or accepted user authorization.

No Codex Core, frozen Runtime, UMA, vLLM environment, Goal/Memory changes.
The shared execution-contract prototype remains opt-in and is NOT enabled by the
production H3 entry. Its offline tests are not real workflow acceptance.

## Root causes in the saved six-turn run

Origin: interactive-32768-20261029-010403.
The first real Google search succeeded, parsed 9 raw results and retained 3.
Lexical terms were google and the entire Chinese phrase 季度财报和电话会议分析.
Only google matched: uncertain. The old eligibility gate allowed citations only
for relevant, and the bounded adapter projected citable_results only. Thus real
candidates disappeared from the model-visible result and zero citation eligibility
was misreported by the model as an absence of material.

The following year-2026 query really executed but returned generic Google pages.
Removing the year later produced older results. That query change did NOT revoke
the retained original user input, but no structured time constraint had been
interpreted/confirmed. The compact historical projection could omit that earlier input.

The source page was accessed on 2026-10-29; its source-declared publication was
2025-10-10. The 900-character excerpt mentioned an Oakmark Q3 2025 investor letter.
The full saved article separately discussed Alphabet Q2 2025 earnings.
The model treated access time as the requested period and then guessed 2026 Q3.
Current date and Asia/Shanghai were already in its Harness input. No Compaction.

## Production evidence changes

- phase2/evidence_boundary.py: protocol-neutral candidate fact view; stable IDs
  tied to the observed search event, exact returned title/URL, citation scope,
  explicit semantic/constraint unknown states and separate counts.
  Also extracts only standard source-declared publication metadata (JSON-LD
  datePublished on page/article entities and article:published_time). No body-text,
  quarter, finance, language or provider date rules. Conflicting declarations stay
  unknown. published_at is a source claim, not externally verified truth.
- phase2/web_capability.py: remove lexical eligibility veto; report raw/retained/
  visible/discovery-citable/page-content-acquired counts. Failures and genuine
  empty searches stay separate from diagnostics. Original raw snapshots/DB stay intact.
- phase2/web_context.py: project separate accessed_at, source-declared published_at
  and unknown content_period alongside the bounded source excerpt.
- harness/codex_dynamic_tools.py and observation_boundary.py: preserve versioned
  candidate facts through result-size limits. Title/URL/source identities are not
  truncated. Visibility reductions report counts and projection limits, not absence.
  Older unversioned result compatibility remains; the new Capability always emits
  the versioned boundary. No semantic judgments use Codex event names.
- harness/workflow_continuity.py: discovered URLs include versioned available
  candidates, not just legacy lexically relevant hits. Discovery is not page acquisition.
- harness/request_continuity.py, semantic_state_adapter.py, io_contract.py and
  scripts/h3_harness_interactive_repl.py: supply a bounded untrusted view of retained
  original inputs on each turn, including source IDs/hashes and explicit omissions.
  No date extraction, authorization promotion or forced tool use is introduced.
- Opt-in semantic_execution_contract.py: decisions carry retained request IDs and
  request_satisfaction=not_established. This is a fact linkage, not time-policy enforcement.

Compatibility meaning of citable_results is now search-result-only citation:
the model may show a returned link/title/snippet as a discovered hit. This is NOT
permission to claim that the page was read, the source is substantively reliable,
the query is relevant, or the user's year requirement has been satisfied.
Candidate visibility does not turn source content into instructions/authority.

## Temporal continuity limitations

The original time request remains in the Runtime request records. Query rewrites
cannot mutate or supersede it. The new retained-input view reinforces this in Context.
Long histories/text remain bounded, with omissions/truncation explicitly reported.

There is still no confirmed structured temporal requirement wired into production
execution. The Runtime cannot infer natural-language entailment or reject a query
merely because a year string was removed. Results therefore keep
constraints_satisfied=not_established. This is PARTIAL temporal-constraint coverage,
not proof that the model will preserve the year across future turns.

content_period always stays unknown in source-fact projection; any model
interpretation must remain separately attributed to its source evidence.
Publication date alone is not a universal test of a document's discussed period.

## Targeted verification

10 new evidence/temporal tests cover lexical-veto removal, exact identity and count
preservation, projection limits, source metadata, conflicting/malformed publication
claims, no date inference from access/body text, and retained request continuity.

Related regression: 197 tests passed before the final compatibility edge-case change.
Final focused rerun: 44 tests passed, including the now-10 new tests, adapter,
observation boundary and identity/budget coverage. Counts overlap; do not add them.

Existing Web Capability tests were updated only where the old lexical veto was the
behavior under test. No full environment regression, new dependency, build or
live Harness workflow was run. Platform/profile parser coverage is simulated;
there was no x86_64 GPU run.

## Direct model isolation (not a Workflow)

Existing external Qwen2.5-14B-Instruct-AWQ service, port 8000, 32K + Hermes.
Four sequential Chat Completions requests, temperature=0, top_p=1, seed=42,
max_tokens=700. No second model, service restart or fresh web search/fetch.

A_before / A_after: same broad research question, exact old result vs new projection
from the saved original search. Old projection: model claimed material absence.
New projection: three URLs all matched observed identities; model judged them worth
reading, set needs_fetch=true and absence_of_material_proven=false.

B_before / B_after: explicitly retain the original year-2026 requirement and the
same original 900-character excerpt. Before: model rejected 2026 but reported an
unattributed Q3 2025 period; its purported verbatim quote altered the source.
After: model distinguished 2026 access from the source's 2025 publication, kept
content_period unknown, rejected a 2026 match and returned an exact excerpt quote.

Both B responses were Markdown-fenced JSON despite a plain-JSON request. Raw
responses remain unchanged. Fence removal was for human review ONLY; the deployed
structured interpretation contract was not exercised or silently relaxed.

A compares complete old/new projections, not a single-variable causal experiment.
B uses explicit requirements near the evidence in a short prompt; it is not the
original multi-turn H3 context. One deterministic sample per condition establishes
neither statistical stability nor general temporal reasoning correctness.

Model output is interpretation, not execution evidence. All search/fetch facts
come from the saved original run. These replay requests made zero tool calls.

## Verdicts

- Search Execution: original run PASS; no fresh search execution claimed.
- Evidence Visibility: Contract PASS; source/retention/citation scope separate.
- Semantic Relevance: narrow Model Behavior PASS; broader correctness unproven.
- Temporal Constraint: PARTIAL, source retained/projected; hard semantic enforcement not wired.
- Temporal Fidelity: sample date distinction improved; broad/multi-turn behavior unproven.
- Evidence Fidelity: PARTIAL overall; revised quote exact, old quote and strict JSON failed.
- Harness Independence: shared-fact/offline contract PASS; no real Harness X implementation.
- Real Workflow: NOT RUN, awaiting manual acceptance.

## Evidence and protection

Audit: /home/wqkan_wsl/uaea-n1x/audit/evidence-boundary-20261029T012144Z
See replay-fixtures.json, four request/response JSON pairs, model-review.json,
targeted-tests-final.txt, final-focused-tests.json and protected-verification.json.

57 protected original-run, frozen baseline/binary and UMA files match their
pre-change SHA256 values. Runtime submodule is clean; HEAD is unchanged at
e99df8dfac252b4ecd4fd0f502ce65573056d046. No Commit or Push.
The existing external vLLM process was neither restarted nor stopped.

## Minimum manual acceptance

Restart H3 to load the shared evidence/context changes. No vLLM restart is needed.

    bash /home/wqkan_wsl/uaea-n1x/UAEA/scripts/start_h3_harness_interactive.sh --profile n1x --turn-timeout 420

1. Search with an explicit year-2026 requirement; inspect real tool calls and counts.
2. Allow broader relevance while explicitly retaining the year requirement.
3. Read one returned candidate; compare access/publication/interpreted period and
   exact source quotations. Unknowns are acceptable; invented periods are not.

Judge execution, candidate visibility, semantic conclusions and Workflow completion
separately. This entry loads the evidence fix, not the opt-in execution contract.
