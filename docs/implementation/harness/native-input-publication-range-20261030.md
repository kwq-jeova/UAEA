# Native user input + publication range — 2026-10-30

Outcome: Native Input PASS; native publication filtering PASS; complete research
acceptance PARTIAL, with final evidence fidelity FAIL. No model retry was used to
replace the failed research outcome.

## Implementation boundaries

- scripts/h3_context_characterization.py enables
  features.default_mode_request_user_input in generated configuration for both
  profiles. Default collaboration mode is retained; Codex Core/binary is unchanged.
- scripts/h3_harness_interactive_repl.py receives item/tool/requestUserInput,
  renders questions, waits for actual stdin, sends the typed answers and resumes.
  Default answer timeout is 300 seconds, configurable with --user-input-timeout.
  Human wait time does not consume the model's turn timeout.
- harness/user_interaction.py validates questions and maps explicit numeric choices.
  Empty input never selects a recommended answer. Free-form replies are preserved.
  /cancel, Ctrl-C, EOF and timeout do not imply approval. Cancellation first sends
  turn/interrupt, then a cancellation error, rather than resuming with an empty
  answer. Secret input is intentionally unsupported in this plain-text REPL.
- phase2/terminal_input.py adds polled reads with deadlines/process-liveness checks.
  It does not spawn an abandoned background stdin reader on timeout.
- harness/semantic_state_adapter.py records normalized interaction facts and
  retains USER_REPLY inputs separately, with source IDs and original-answer hashes.
  A native question/answer is not counted as Capability execution.
  Answers do not automatically become UAEA execution authorization.
- phase2/web_adapter.py, web_capability.py and the interactive tool schema add
  inclusive published_from/published_to ISO date fields. Both bounds are required.
  Provider support is explicit: the current Google adapter encodes native tbs/cdr.
  Unsupported providers, fallback combinations and conflicting relative filters
  fail before HTTP; no filter is silently removed.
- WebSearchResult retains source_date_text exactly as reported by the search
  provider. evidence_boundary.py and codex_dynamic_tools.py project its source
  identity and accessed_at anchor. Relative labels are not parsed into verified
  page publication times or content periods.
- io_contract.py describes native interaction and the publication/content-period
  distinction. The shared execution-contract prototype remains opt-in; it is NOT
  wired into the production entry by this change.

The date filter is adapter transport, not a natural-language date classifier.
The model chooses the range from observable user input. Runtime validates ISO
dates, support and provenance of what was sent. The actual discussed fiscal/research
period remains a model interpretation and requires source evidence.

Native replies are retained as original input facts, not automatic permission
grants. An independently authenticated authorization bridge is still needed for
permission expansion; this task's test explicitly forbids provider fallback.

## Protocol and API references

Pinned local Codex rust-v0.163.0 source:
- core/src/tools/handlers/request_user_input.rs and request_user_input_spec.rs
- app-server/tests/suite/v2/request_user_input.rs
- app-server-protocol/src/protocol/common.rs

The existing Default-mode feature forwards a request with isBlocking=false.
The REPL nevertheless waits for an actual reply; it does not infer permission
from this transport flag, a default option, or elapsed time.

SerpApi documents native custom date ranges:
https://www.serpapi.com/blog/filtering-google-search-and-google-news-results/
https://serpapi.com/search-api

Format used: tbs=cdr:1,cd_min:MM/DD/YYYY,cd_max:MM/DD/YYYY.
The observation records the sent value and provider echo. Matching echo establishes
request transport only; provider enforcement is still best effort and does not
establish the document's substantive period.

## Offline verification

267 targeted tests PASS, including 12 new native-input tests and 7 new
publication-range tests. Coverage includes:
- blank replies, explicit choices, free-form replies, duplicate requests;
- wrong-thread identity, cancellation/EOF/timeout and inference timeout exclusion;
- separate retained reply provenance, no automatic authorization;
- native interaction excluded from Capability execution counts;
- date validation, unsupported combinations rejected before HTTP;
- exact native date parameter and echo; missing echo remains unconfirmed;
- raw source date labels retained without invented publication/content-period facts;
- existing Web/Harness/continuity and simulated N1X/5090D profile checks.

Cancellation and timeout are covered offline. The real model test exercised the
answered path. The final cancellation-order/scope checks were added after the
successful native answered-path run and verified by the final regression.
There was no second live-model attempt to seek a passing research conclusion.
No x86_64 GPU test or whole-environment regression is claimed.

## Real same-workflow acceptance

Audit root:
/home/wqkan_wsl/uaea-n1x/audit/native-input-temporal-20261030T014933Z

Run:
h3/interactive-32768-20261030-020240

The test used the unified shell entry, profile n1x, external port 8000, 32K Hermes,
frozen ARM64 rust-v0.163.0 binary and the existing Qwen model. Answers were supplied
by scripted stdin for repeatability; this was not a live human-operated session.
The prompts and exact reply are preserved in live-manifest.json.

One workflow, three user turns:

1. Research Google/Alphabet 2026 Q3; ask natively whether the user means
   publication date or financial period before searching.
   The real item/tool/requestUserInput arrived. Before answering, the driver held
   for one second and confirmed zero Capability calls and zero completed turns.
   It then supplied: financial period Alphabet 2026 Q3, publication window
   2026-10-01 through 2026-10-30, Google only, no fallback.
   The same turn resumed and acknowledged those meanings. It promised to search
   but made no search call until the next user turn.

2. Continue the same task, actually search/read evidence.
   One real web.search used published_from=2026-10-01 and
   published_to=2026-10-30, allow_fallback=false.
   Sent tbs was cdr:1,cd_min:10/01/2026,cd_max:10/30/2026 and the backend echoed
   that value exactly. Two normalized candidate identities were returned.
   One real web.fetch followed, but its URL was a Google search URL, not the
   returned MarketScreener candidate article. The projected body was only
   "Google Search" (13 characters). HTTP success did not establish article reading.

3. Summarize what was actually established.
   The model incorrectly claimed the article's full text had been obtained,
   cited the candidate article as if fetched, supplied an unsupported Chinese
   quotation, and stated access date 2026-10-29 despite the actual fetch timestamp
   2026-10-30T02:03:14Z. These remain failures, not repaired facts.

No Context Compaction occurred. The same workflow owner persisted.
All three turns completed, but Workflow remained active and
completion_established=false. Turn completion is not Workflow completion.

## Evidence and verdict

- native request: app-server-events.jsonl line 88
- date-filtered search call: line 308
- search result/filter echo: line 311
- actual fetch call/result: lines 313 / 315
- user-input-events.jsonl: awaiting_input -> answered with stdin source
- driver-events.jsonl: wait-before-answer assertions
- live-evidence-summary.json / acceptance-verdict.json: normalized facts and limits
- targeted-tests-final.txt / test-command-final.json: offline validation

Native transport: PASS.
Publication range argument/echo and source-label projection: PASS.
Real search execution: PASS.
Real page fetch transport: PASS; intended candidate article acquisition: FAIL.
Final factual/quotation fidelity: FAIL.
Overall multi-turn research acceptance: PARTIAL.

A possible next small boundary is linking selected candidate source_id to the
actual fetched URL/hash and final source claims. It must not be replaced by a
provider/domain-specific semantic rule or another model. That work was not
implemented automatically here.

## Preservation and manual entry

Protected checks cover 69 original-run, frozen baseline/binary and UMA files:
all SHA256 values unchanged. Runtime submodule remains clean at
1f311291df027baceca40779643e5107b9eb6fb3.
HEAD remains e99df8dfac252b4ecd4fd0f502ce65573056d046.
Pre-existing local changes were retained. No Commit or Push.

The external vLLM process (PID 4701 at acceptance) was neither restarted nor stopped.
Only the task-created REPL/app-server was closed.

    bash /home/wqkan_wsl/uaea-n1x/UAEA/scripts/start_h3_harness_interactive.sh --profile n1x --turn-timeout 420 --user-input-timeout 300

Restart H3 to load the changes; no vLLM restart is needed.
At a native question, enter a number or a free-form reply. /cancel interrupts
the current turn. No answer is selected automatically.
