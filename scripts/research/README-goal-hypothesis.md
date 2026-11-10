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
Host-held candidates survive model Compaction by re-projection. New-process / cross-run restoration is not implemented or claimed.

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
