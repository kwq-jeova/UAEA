# Optional Goal Hypothesis research channel

This is an isolated research entry, not a production Goal Engine or Memory admission path.

Use the existing longitudinal_prepare.py and immutable source bundle. Run the bundled longitudinal_dialogue.py with --goal-channel sideband and an already guarded service.
Relevant History remains Goal off. Only the goal_shadow arm registers the optional goal_hypothesis semantic tool.

## Shared objects and ownership

GoalResearch subclasses existing G0 GoalIntegration and retains Phase-1 GoalHypothesisRecord inside RuntimeObjectRecord / RuntimeObjectStore.
No Phase-1 source changes, ActiveGoal updates, Planner, second Agent Loop or second model are introduced.
Harness continues to choose and execute native tool calls. The research host accepts observable semantic proposals only.
The normal document adapter / SharedExecutionBoundary remains unchanged.

The research schema uses operation, candidate_id, hypothesis, quote, optional input_ids and evidence_ids.
Operations form/maintain/refine/revise/withdraw refer to CANDIDATE INTERPRETATIONS, not authoritative user Goal changes.
Each accepted call appends an immutable version with an explicit parent reference; old versions are not rewritten.
Multiple roots are allowed; no candidate is also allowed. A maintain event is a derived representation, not independent support.
Confidence is unassessed; no probability, entropy, weighting or semantic truth is inferred.

Quote and current native Turn must match the original registered user entry.
Historical basis references may name authentic cancelled inputs, but those references do not reactivate instructions.
Evidence references must identify actual ExecutionObservations; links do not establish content support.
The same quote can still support an incorrect model interpretation; that limitation is explicitly tested.

## Transport and factual boundary

goal_sideband.py translates the native protocol into GoalResearch.submit; it has no semantic domain or backend rules.
A thin ProposalSemanticView excludes this semantic-control call and its echoes from Capability/Source observations.
Canonical raw events remain available. A protocol tool receipt is not an external execution fact.
Only actual Capability calls produce the existing SharedExecutionBoundary Observation.

The native tool uses the same canonical type:function schema as existing tools.
Legacy optional final-envelope mode remains the default; sideband is opt-in and uses ordinary final text.
No per-turn proposal is forced. A two-per-turn/32-per-session bound is a maximum, not a quota.
The untrusted candidate projection is bounded to 4200 characters and exposes only recent heads / original input references.
Host-held candidates survive model Compaction by re-projection. The production channel has no general new-process / cross-run restore; see the explicitly isolated research recovery below.

## Verification

goal_hypothesis_audit.py checks native call identity, current original input, parent versions, declared source hashes,
and that semantic proposals are absent from domain ExecutionObservations.
It separates candidate generation, structural legality, semantic quality and decision value.
It never infers model-internal dependencies or declares cognitive quality from a valid schema.
Failed registration runs and completed baseline runs must remain separate when continuing an experiment.

## 2026-11-09 commit / publication consistency correction

The exact submitted native arguments are retained separately from the effective
hypothesis (maintain/withdraw inherit the parent text). Candidate receipts bind
the complete immutable record hash. Outbound heads carry that hash and the full
hypothesis, not a silent 300-character prefix; budget omission remains explicit.

The append-only RESEARCH_GOAL_VERSION event is the local research commit record.
The atomic snapshot is a materialized view. A snapshot or host-publication failure
does not turn an already committed version into RESEARCH_GOAL_REJECTED.
The same native Call ID with the same payload returns the original candidate
and retries snapshot/publication; changed payload is an identity conflict.
Publication attempts have their own RESEARCH_GOAL_PUBLICATION events.
Host publication success is not model receipt: only a later audited request with
matching ID, operation, parent, exact content and record hash establishes supply.

These are single-process research guarantees, not crash-atomic storage, process
restart replay, semantic truth, adoption or execution authorization.
The offline auditor was further tightened after the live bundle was frozen:
request time must follow the commit; missing timing does not prove delivery.
The post-hoc evaluator version is separately hashed; runtime source remains frozen.

## 2026-11-10 negotiated final-envelope research contrast

The existing Runner now also accepts --goal-channel envelope, only for the
opt-in goal_shadow arm. goal_envelope.py uses the same candidate payload and
GoalResearch validator, with the exact final object answer + goal_proposal.
Ordinary prose and malformed/extra-field JSON never become a proposal.

This is NOT the legacy G0 final schema. It records the real final agentMessage
ID with source_kind=model_negotiated_final_proposal, not a native tool Call ID.
Host validation occurs after native Turn completion; feedback and current heads
can enter the next user Turn. There is no extra model loop, response_format,
automatic natural-language extraction, formal adoption or permission change.

The native-tool-only goal_hypothesis_audit.py must not label final-envelope
commits as missing native RPC calls. The frozen interface study has a separate
explicit source-event binding audit plus the existing projection/transport
checks. See docs/research/goal-state-inference-interface-20261110.md.

## 2026-11-10 isolated cooperation contrast

--goal-channel cooperation selects goal_cooperation.py only in goal_shadow
cases with a frozen mechanism A/B/C field. All conditions first establish
their seed using the existing native Goal tool. No Host seed fabrication.

A retains the existing channel. B accepts optional final assessments and
explicitly declines candidate submission after the seed. C allows optional
assessments and the same existing native Goal tool. A native call already
contains a structured proposal and explicit submission intent: C requires
no preliminary assessment call or additional model loop.

Final assessments are journal-only interpretations, never submit commands.
Their model text is projected as untrusted context; trusted feedback contains
only observed event/commit references. submit_intent=true does not execute.
Do not equate final assessment generation, payload matching or commit counts
with semantic correctness or decision value. No JSON is extracted from prose.


## 连续金融回放（2026-11-10）

finance30脚本/来源：benchmark/longitudinal_dialogue/finance30/README.md。
显式max_turns才可扩展至30，默认仍10；分轮资料释放不构成工具执行事实。
只执行冻结bundle，保留失败与NOT_RUN；本次遥测中断后的Goal组未执行，
不得作为无候选或接口失败统计。详见docs/research/finance30-goal-continuity-20261110.md。


## 2026-11-12 research annotation correction (v2)

Semantic review records expression source, intent subject, and the exact scope of
user endorsement separately. A model-produced interpretation may describe user
ends; a user utterance may merely mention an agent task. Speaker alone proves neither.

Review material purpose/scope distortion, means/step mixing requiring context,
and harmless background redundancy separately. Method words or source facts
do not invalidate a candidate by themselves. Real quote/reference validity is
not semantic support. Current user clarification updates the current
interpretation; historical psychological truth remains unknown.

A semantic classification can be reviewed without a candidate. Lifecycle
maintain/refine/revise/withdraw is assessable only with an actual saved current
candidate, its content and scope. Do not assign operations from isolated text.
These are research annotations, not new Runtime fields, a semantic classifier
or adoption rules. Structural audit PASS remains distinct from these judgments.

The 2026-11-12 attribution/lifecycle study's strict clean-seed gate is a recorded
study decision, not proof that all extra background makes a Goal invalid.
A new one-feedback correction study preserves old evidence and uses a fresh
real Sideband seed when full Host process restoration is unavailable.


## 2026-11-12 isolated historical Goal recovery

recover_goal_history.py validates real Journal/Native/input/Observation/HTTP
records and restores the recorded Goal closure in a new research copy. It
preserves Thread/Scope/record/Call identities; it never mints an old candidate
from model prose or repeats external tools. A copied Native rollout is resumed
as the SAME Thread. Only the copy's rollout pointer is relocated; SQLite
schema and original files remain unchanged.

This is not a production restore hook or general Runtime recovery. It only
supports completed one-turn/single-Workflow checkpoints with the required
records, no ActiveGoal or additional effective policy, and complete successful
RPC receipts. Missing/contradictory evidence is rejected. Opaque model-output
objects and old projection/planner caches are not invented or silently claimed.

Tests: benchmark/longitudinal_dialogue/test_goal_recovery.py.
Historical fixtures are external; UAEA_GOAL_HISTORY can override their path.
Missing fixtures explicitly skip, never count as behavioral PASS.
Report: docs/research/goal-history-recovery-correction-20261112.md.

Restoration is not natural formation, a new assisted seed, semantic truth or
adoption. Actual feedback correction must still be proved by model behavior,
real submissions/current heads and subsequent requests. The first restored
live sample had no update and inaccurate saved-content claims; it is retained
as a failed correction, not a restore failure.
