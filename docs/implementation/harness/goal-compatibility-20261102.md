# G0/G1 Goal compatibility acceptance — 2026-11-02

## Conclusion

Overall **PARTIAL**. Limited **Goal/Execution Contract PASS**, safety gate **PASS**;
**Model Behavior PARTIAL / Goal Behavior PARTIAL**. Goal Off / non-injecting Shadow can serve as
a low-interference research baseline. Optional projection/adoption remain explicit experiments.
This is not long-term Goal Formation/Evolution or Research Workflow PASS.

## Controlled real comparison

SharedExecutionBoundary explicitly enabled; frozen Codex rust-v0.163.0, Bolt/vLLM 0.32.0,
32K, seq1, Eager, fixed KV 1GiB, engine plan 36GiB. Four fresh sessions, one owned launch,
identical three user prompts/tool definitions: README read, candidate proposal without tools,
then ordinary checksum question without Goal creation/revision. No forced outputSchema/text.format.

| Mode | Completed turns | Actual tools / README result | Goal result |
|---|---:|---|---|
| Off | 3 | 3 calls: wrong-path read failed, list succeeded, corrected read succeeded | no Goal records |
| Shadow, no injection | 3 | wrong-path read failed; model acknowledged non-reading | rejected old source text as current-user quote; no candidate |
| Shadow, optional injection | 3 | one correct read succeeded | one pending candidate; no automatic adoption |
| Adopt, optional injection | 3 | one correct read succeeded before adoption | explicit test_driver adoption; active Goal delivered in later ordinary question |

Primary run: /home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/goal-compat-live-20261102T123059Z.
18 provider responses HTTP 200, 12 native completed turns.

Supplement: /home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/goal-compat-active-20261102T124823Z.
Two additional real turns close the post-adoption tool gap: source-checked model proposal,
explicit Host adoption, then actual read_section under active Goal
b57c6392-ca0d-4871-be20-32b177a48b60.
The active Goal was present in the request BEFORE the tool call. Execution, excerpt hash and
subsequent evidence delivery PASS; Goal remained active, authorization unchanged.
Three more HTTP 200 responses; two completed turns. Controls are test_driver actions under the
authorized experiment, not presented as human confirmation.

Supplement **Model Behavior PARTIAL**: answer omitted the requested quotation; source quotation
was incorrectly placed in goal_hypothesis.quote, and relation=form despite an active Goal.
Host correctly rejected non-user source text. Observation survived rejection, no duplicate
execution/adoption/revision. Do not promote rejected Goal metadata into an answer or user intent.

## Context / authority checks

- All four sessions: identical tool-schema hashes; native Tool Calling unchanged.
- Off/passive Shadow: zero Goal blocks in every audited request.
- Optional/Adopt: exactly one uaea.goal_state and one external_uaea.goal_hypotheses block per request,
  no accumulated duplicates. Optional instructions/schema cost about 2.7–2.8K serialized characters
  on the first request. Session paths/IDs, random generation and tool outcomes differ; this is not
  a statistical or causal non-inferiority experiment.
- All six primary Observations, including failures, reach later audited input.
  Three successful reads deliver the same 821-character excerpt, SHA256
  a6b85b87eb56f805d9955a263cf4b8716fff964d51f2b06adc84dd374a2ba335.
  Supplement matches. Evidence bytes are checked separately from final prose.
- Ordinary questions: zero extra candidates/revisions. Stable owner per session; authority lists
  unchanged; no Shadow adoption; no turn/tool success automatically completes Goal or Workflow.
- Sanitized audit is not literal wire bytes; some authorization-named diagnostic values are redacted.
  Authority conclusions additionally use Host state, execution receipts and source checks.
  Source identity/hash does not establish semantic correctness or execution permission.
- Off answer quoted only the first physical line; optional/adopt primary quotes joined a newline.
  No zero-tool false-read claim occurred in these tests, but full-sentence fidelity is not universally PASS.
- No natural Compaction. Host restoration/forged-summary containment/deduplication were tested offline,
  not established for a real long-history session.

Primary real-trace checks 18/18 PASS: compatibility-checks.json.
Post-adoption supplement checks 9/9 PASS: active-analysis.json.
These are fact/contract checks, not model quality scores.

## Minimal changes

- harness/goal_integration.py: independent projection=none|optional, journal/snapshot record setting.
  none collects valid observable final proposals, injecting no Goal block.
- scripts/h3_harness_interactive_repl.py: --goal-projection forwarding + run manifest field;
  default Goal Off unchanged; no forced response schema.
- tests/test_goal_integration.py: five additional tests: passive collection/no fabricated candidate,
  two-turn Harness shape compatibility, failed tool/unsupported claim under adopted Goal,
  bounded candidate projection and repeated restoration deduplication.
- This acceptance document is the only new documentation file in this task.

No new cognition rules, Goal algorithm, second model call, Core/frozen Runtime/model dependency
or safety changes. Passive Shadow cannot infer a candidate when no metadata is output.

## Regression / safety

34 Goal tests PASS; 44 isolated suites: **506 cases, 504 PASS, 2 SKIP, 0 FAIL**.
Skips: optional installed-vLLM CPU parser/generation diagnostics.
Actual commands/logs: regressions.json, regression-logs/, goal-tests.log;
reproduction runner: run-regressions.py.

Win32/PDH idle probe: 12 valid samples, 0.337–0.493s.
Both launches passed simulated GPU-stop and stale-heartbeat process-tree termination.
Main 515 / supplement 187 model samples; maximum sampling duration 0.424s, no real safety stop.
Combined resource extremes: Dedicated 29.05GiB, Shared 0.201GiB, Commit 66.43/114.48GiB,
Windows Available minimum 26.85GiB, WSL Available minimum 17.48GiB.
Stops unchanged: GPU48GiB, Windows Available6GiB, Commit headroom max(16GiB,20%limit),
WSL Available4GiB, Swap256MiB, monitor freshness3s.
These policies are not hard CUDA or host allocation limits.
Earlier 28.33s sensor delay did not recur; cause remains UNKNOWN.

930 protected existing files per launch; no changes outside UAEA.
Both owned process trees empty; ports8000/8003 cleanup verified separately.
Original Qwen environment, UMA patches and frozen Runtime retained.

## Readiness / remaining limits

A limited Goal Contract baseline is available for top-level Formation/Evolution research.
Optional projection/adoption must remain opt-in: the supplement shows answer/Goal metadata
confusion, and a tiny fixed-order sample cannot prove zero behavioral impact.
General candidate recognition, conflict-driven revision, long-term continuation, natural Compaction,
cold-session restoration and complete research quality remain unproven.
No model-specific patch is used to conceal these gaps.

Unified human entry remains scripts/start_h3_harness_interactive.sh, existing n1x/external/Bolt settings.
Goal Off remains default; append --goal-mode shadow --goal-projection none for passive observation.
Optional projection and explicit /goal controls remain experimental. No manual acceptance requested.

HEAD unchanged: 122040dde1bf75b9d9eabd3ed00236cf8a1375e0.
Frozen submodule unchanged: 1f311291df027baceca40779643e5107b9eb6fb3.
Existing P3.5/G0/G1 changes and historical unused artifacts preserved. No Commit/Push.
COMPAT.patch and before/ backups only roll back this task; reverse-check before applying.
