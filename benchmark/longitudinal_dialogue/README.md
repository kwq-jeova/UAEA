# Fixed multi-turn cognition research harness

Research-only driver reuses InteractiveAppServer, ProviderHistoryBridge, SharedExecutionHost, GoalIntegration and existing trace writers.
No second Agent Loop, automatic Goal Adoption/Memory Admission, maintained experience layer, public Web or production configuration changes.

## Prepare and run

Use a fresh output directory outside the repository. Never reuse existing output.

    python3 -B scripts/research/longitudinal_prepare.py --output /absolute/new-study
    python3 -B benchmark/longitudinal_dialogue/test_contracts.py

Start the existing protected Bolt 32K launcher separately only when ports/resources are free. Read its owned record path and readiness.
The driver never launches a model or disables safety. Its --guard must reference that owned protected service, not an unrelated user service.

    python3 -u -B scripts/research/longitudinal_dialogue.py --output /absolute/new-study --guard /home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/<owned-record>
    python3 -B scripts/research/longitudinal_audit.py --output /absolute/new-study

Afterwards normally stop only that owned model service with existing guard_ctl.py. Startup, shutdown and thresholds stay with the existing supervisor.
The 180s per Turn and existing 1800s guarded experiment deadline are bounded automated test limits, not manual service or Workflow lifetimes.
A timeout/unconfirmed native Turn stops the test; it is not task completion and must not be followed by another scripted input.
Native request_user_input is not given invented user answers. This suite did not trigger native input waits; conditional replies and their wait termination are not validated. Existing finite experiment supervision remains required.
No automatic response retries or script branches.

## Initial suite

Three synthetic pre-authored scenarios:
1. Ordinary chat → explicit community archive direction → budget/method constraints (3 turns).
2. Reviewable research evidence goal → correction of online-page path plus no server (2 turns).
3. Actual isolated document read → scope correction → missing source failure and previous-source recovery (3 turns).

Each runs in fresh sessions: Relevant History (Goal off) and existing Goal Shadow optional projection.
Repeat the path pair in reversed arm order: 8 sessions/20 turns.
Raw scripts and source bytes are identical. Candidate mode adds existing optional final-envelope instructions and up to 3 candidates.
This tests the existing Shadow mechanism, not a pure representation causal experiment. Plain responses/no candidates are recorded, not automatic cognition FAIL.
Actual sampling fields are recorded; no fixed-seed or identical-answer claim.

Only document.read_section is exposed, under protocol tool name read_section.
Working directory equals its isolated sandbox. Hidden code exists only in a fixture file; missing.md is never created.
Safety is not weakened to make reads succeed. No live Google/Fetch claim.
Evaluator-known source bytes are not model input before actual reading.

## Evidence and evaluation

Each session saves raw app-server events, normalized trajectory, HTTP audit, projection/semantic snapshots, Goal events,
Shared decisions/Observations, Tokens, version/run manifests and stderr. turns.json links user texts to native Turn IDs.
HTTP audit is a redacted/bounded structured snapshot with hashes/manifests, not literal raw wire bytes.
Check snapshot_coverage; delivery does not prove understanding.
Token usage total is cumulative per thread: use its last counter, never sum all updates.
Native compaction items and notifications are recorded separately to avoid double counting.

Offline evaluation checks trace availability, Turn lifecycle, projection exposure, authority-state invariants and one literal source criterion.
It does not judge natural Goal truth or all prose. Answer text, actual Observation and formal state remain separate fields.
Matching code without successful corresponding read does not pass grounding.
A literal value is not full Workflow completion, support for every statement or decision value.
Qualitative review must be separate, not model self-evaluation.

No natural compaction is forced; zero remains zero and compressed-history recovery is untested.
Two/three turns and one repeat establish small repeatable tests, not long-term cognition or statistical superiority.
Further candidate mechanisms must share history/permissions and explicit authority boundaries.
Do not add a Goal Engine merely to fill empty candidate results.
