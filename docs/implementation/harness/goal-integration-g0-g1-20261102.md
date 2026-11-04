# Goal Integration G0 → limited G1 — 2026-11-02

Status: **PARTIAL**. Goal state/authority invariants pass in the scoped prototype.
Real candidates and explicit test-driver adoption were observed. Reliable Goal behavior,
semantic evolution and non-interference with tool generation have NOT passed.

Base Git HEAD: 122040dde1bf75b9d9eabd3ed00236cf8a1375e0.
Existing uncommitted P3.5 work is retained. No Commit/Push.

## Actual reuse and ownership

- Reuse Phase-1 GoalHypothesisRecord for inferred candidate content, RuntimeObjectRecord /
  RuntimeObjectStore for candidate, input and decision provenance, ActiveGoalRecord /
  active_goal_id for adopted task objectives, and ContextManager.set_active_goal_context.
- The same Semantic State / registered request record supplies input identity, full original
  text and SHA256. Goal objects do not replace Workflow ownership or execution facts.
- Codex retains the model/tool/turn loop and compaction. No Agent.handle, planner, new
  Goal Engine, second model, long-term Memory admission, or model environment change.
- This is a single-Workflow controlled adoption experiment. ActiveGoal.workflow_ids is
  not silently linked/reassigned. Cross-Workflow Goal continuity is not implemented.
- An adopted task objective is not verified world knowledge and grants no Capability rights.

## Modified boundaries

- harness/goal_integration.py: optional complete final envelope (answer + nullable
  goal_hypothesis), candidate retention, exact source quote/hash checks, reference diagnostics,
  explicit Host controls, separate decision records, Goal-only checkpoint/context recovery.
  No natural-language intent classifier, threshold-based promotion, tool dispatcher or loop.
- harness/event_normalizer.py: protocol role=user echoes are CONTEXT_MESSAGE, not evidence
  of a real user request. Trusted compaction lifecycle marks derived model claims.
- harness/semantic_state_adapter.py: Host prepare_turn stamps immutable input origin;
  H3 requires registered original input before binding native user echoes. Goal-related
  state cannot originate from a projection or compaction message.
- harness/evidence_provenance.py: records model_output vs compaction_derived origin;
  both remain unverified interpretation, never Source Evidence.
- scripts/h3_harness_interactive_repl.py: --goal-mode off|shadow|adopt, default off;
  collect only a bound completed user-turn final, project Host Goal identity/version
  independently of model summaries, handle controls only at the Host user entry.
- tests/test_goal_integration.py: 29 targeted contract tests.
- This document: scope, actual failures, reproduction and rollback.

The final implementation does NOT inject outputSchema/response_format into model requests.
It only offers the Goal final-envelope contract in bounded context and accepts a complete,
explicit envelope. Plain final text remains an answer and creates no Goal candidate.
No prose mining, code-fence extraction or JSON repair is used to fabricate a candidate.

## Goal state and authority contract

Candidate records preserve hypothesis, inferred confidence/status, relation proposal,
original input ID/hash/quote, model event ID, target/conflict/Observation references,
reference validity and base Goal-state hash. Unknown references are retained as unresolved;
they cannot be adopted. Quote match proves source identity, not interpretation correctness.

G0 never creates ActiveGoal, execution authority, completed Workflow or Memory.
G1 is an explicit Host control path, not a model tool:
- /goal status
- /goal adopt CANDIDATE_ID
- /goal revise CANDIDATE_ID
- /goal switch CANDIDATE_ID
- /goal suspend GOAL_ID
- /goal resume GOAL_ID
- /goal reject CANDIDATE_ID

Adoption/revision requires a retained original Host request, valid references, applicable
owner, current Goal-state basis and an explicit Host control input. Old proposals cannot
overwrite a changed Goal state. Candidate confidence has no promotion effect.
No automatic Goal completion is implemented; Turn completion, successful tools and model
claims do not complete Goal/Workflow. ActiveGoal status is independent of native turn state.

goal-events.jsonl records candidates, original controls and decisions. goal-state.json
is a derived checkpoint of Host records, NOT an independent authority ingress. Recovery
requires the original Host request/control/decision objects and matching identity/hash;
a forged/rehashed checkpoint or model summary is insufficient. Cold process/session
recovery of the entire Semantic State is NOT implemented. Future recovery must restore
original ledgers first; this prototype refuses to bootstrap authority from a snapshot alone.

## Deterministic / historical evidence

29 new tests cover:
source registration and forged user echo rejection; no-Action/null proposal; duplicate
model identity; inferred confidence; exact quotation; explicit adoption/revision/switch;
pause/resume and ordinary dialogue; conflicting/unknown references; actual frozen Registry
file read and Observation linkage; wrong compaction summary; scope/thread identity;
Host recovery and forged checkpoint denial; stale revision; original control persistence;
journal failure before mutation; no default provider output-format constraint.

Final regression: 44 isolated modules, **501 cases: 499 PASS, 2 optional SKIP, 0 FAIL**.
This retains the existing isolated-suite convention; one-process discovery has historical
fixture import pollution and is not substituted for this recorded run.

Reproduction:
```bash
cd /home/wqkan_wsl/uaea-n1x/UAEA
python3 -B -m unittest tests.test_goal_integration
```

Historical read-only normalization replay of interactive-32768-20261102-065220:
16 protocol user echoes become CONTEXT_MESSAGE; 10 native user-message events correspond
to 5 real registered inputs, with start/complete duplication retained for traceability.
Two actual compaction summaries are labeled compaction_derived, including the wrong
“已确认搜索业务增速…” claim. No new model/tool execution occurred in this replay.
This is source classification, not truth verification or a new Goal formation test.

## Real model experiments — keep failures

All used the verified Bolt/vLLM environment, 32K / one sequence / Eager / fixed1GiB KV /
36GiB engine plan and unchanged dual-side fail-closed protection. No simultaneous Qwen.

1. g01-live-20261102T082215Z:
   Strict final-schema request generated Goal JSON but confused input IDs, Evidence IDs
   and a nonexistent Goal target. Original prototype rejected it; zero adoption.
   The later candidate retention change keeps such a proposal as unresolved, not allowed.
2. g01-live2-20261102T083224Z:
   Dynamic ID enum constraints were tried, then withdrawn. Model wrote answer text followed
   by sustained whitespace and never completed the Goal JSON. This owned test was stopped
   via the existing controller; remaining=[]; no actual memory pressure was manufactured.
3. g01-live3-20261102T084100Z:
   One Shadow turn plus four G1 turns completed, 5 HTTP200 responses.
   Actual model output produced 1 Shadow + 4 G1 candidates. Scripted Host controls explicitly
   adopted, revised, suspended and resumed Goal 0bcddb8b-da0c-4c63-9b69-bea9318bb832.
   Actor is test_driver, NOT a real human confirmation or autonomous model adoption.
   Goal identity remained stable, pause survived ordinary dialogue, Host checkpoint recovery
   succeeded with the original records in memory, Workflow remained incomplete.

Important failures in run3:
- The revision candidate repeated the original Goal summary. A new adoption decision exists,
  but its Goal state hash did not change: semantic evolution was not demonstrated.
- The ordinary checksum question explicitly requested no new/revised Goal, yet the model
  supplied another revise candidate. Host did not adopt it.
- The final answer claimed README had been read. Actual Tool Call count was **zero**.
  No file Observation/Source Evidence was created, despite the claim.
- Native outputSchema became strict text.format=json_schema in all provider requests.
  Installed vLLM0.32 responses/protocol.py extract_structured_outputs / to_sampling_params
  apply that format to sampling. qwen3_coder uses its native tool protocol.
  Non-interference with tool generation therefore was NOT established; zero calls cannot
  simply be attributed to model capability. The hypothesis that a Harness “final schema”
  can safely constrain only a final semantic answer in this stack was withdrawn.

Containment after run3:
remove provider outputSchema injection; preserve original tool protocol, optional complete
final-envelope parsing and Host validation. Also persist original Goal control inputs
separately from decisions/checkpoints. These changes passed offline regression. After the user requested continuation, the
optional-envelope case below was attempted. run-manifest hashes and source deltas are retained.
Do not claim the final optional-envelope path is real-model/tool acceptance PASS.

Run3 resources:
Dedicated peak29.20GiB; Shared0.134GiB; Windows Available minimum27.36GiB;
Commit peak66.37GiB; WSL Available minimum17.35GiB.
Protection simulation and stale-monitor termination passed; all owned descendants cleaned.
8000/8003 no listener and no GPU compute process at final check.
930 selected protected files compared; no changes outside UAEA.

## Authorized continuation: optional-envelope attempt

g01-optional-20261102T120931Z reused the same verified Runtime and protection.
It was stopped during model startup, before Harness/session creation or service-ready
evidence. The unchanged controller observed sample_seconds=28.3293491 (>3s) and correctly
triggered SENSOR_DELAY / fail-closed. Windows measurement itself took0.0124s; the delay's
root cause is UNKNOWN and was not expanded into a Windows monitoring project.

At the recorded samples: GPU peak23.32GiB, Windows Available minimum30.62GiB,
Commit peak57.36/114.48GiB. These samples do not prove memory exhaustion or its absence
during the entire delayed interval; do not infer CUDA OOM from the stop.
Owned descendants remaining=[], ports8000/8003 empty, GPU compute list empty.
No auto reload or protection relaxation followed.

The final optional message path is therefore BLOCKED/UNTESTED in real model+tool
operation, not a new functional FAIL. Plain final answers are permitted and recorded
as NO_GOAL_PROPOSAL without rejection or fabricated candidates; that addition passed
the final deterministic regression.

## Verdict and next minimum

| Dimension | Verdict |
| --- | --- |
| Goal Contract | Scoped PASS: source, candidate/adoption separation, authorization, state recovery |
| G0 integration | PARTIAL: actual candidates observed; final unforced channel not live-tested |
| Limited G1 state controls | Scoped PASS in scripted experiment; not autonomous semantic adoption |
| Goal Behavior | PARTIAL/FAIL cases: spurious candidate, unchanged revision, false read claim |
| Goal Lifecycle / Evolution | PARTIAL: controlled state transitions proven; meaningful model-led revision not proven |
| General tool compatibility | NOT PASSED; optional-envelope retest blocked by SENSOR_DELAY before Harness |
| Long-term Goal interaction | Not ready to claim PASS |

Next first confirm the existing monitoring chain is healthy without changing thresholds,
then run one small optional-envelope + native real-tool compatibility case with the same
source/permission/Observation standards. Only after that gate should longer
Goal continuity be studied. Do not add Goal keywords, a second interpreter, formatter repair,
a planner, global Memory or Core changes to manufacture PASS.
Explicit scope/goal switching, confirmation semantics, genuine Evidence-driven hypothesis
revision and cold-session ownership recovery remain research questions.

## Entry / rollback

Default remains unchanged: --goal-mode off. No model service is started by Goal controls.
Normal external Bolt entry (only after its protected service is deliberately started):
```bash
bash /home/wqkan_wsl/uaea-n1x/UAEA/scripts/start_h3_harness_interactive.sh --profile n1x --vllm-mode external --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x --execution-contract shared --goal-mode off --turn-timeout 420
```

shadow/adopt are experimental opt-ins, not a recommendation to begin long-term testing.
Legacy/shared execution selection remains independent. 5090D code uses the same implementation;
no new x86 GPU verification was performed.

Local provenance:
 /home/wqkan_wsl/uaea-n1x/goal-integration/g01-20261102T081128Z/
 contains before/, before.diff, incremental G01.patch, source hashes, regressions.json,
 historical-source-replay.json, live-attempts.json, live-analysis.json and REPORT.md.
Rollback should compare/apply only G01.patch against these before/ files, preserving P3.5
and existing unused/context-projections.jsonl. Do not reset/clean the worktree.
