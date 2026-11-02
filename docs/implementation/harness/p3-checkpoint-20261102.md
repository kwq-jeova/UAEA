# P3 Git checkpoint — 2026-11-02

Status: scoped Contract PASS; Model Behavior PARTIAL/FAIL; Research Workflow NOT PASSED.
This is an engineering checkpoint, not a production research-quality release.
Known Search TLS and natural-compaction failures remain open.

## Scope and lineage

Parent baseline: e99df8dfac252b4ecd4fd0f502ce65573056d046 on main.
This checkpoint captures previously uncommitted, user-authorized current-request,
semantic interpretation, evidence provenance and native-input prerequisites
together with P0–P3.4 changes. These edits overlap within the same source files;
one atomic checkpoint preserves a runnable tree without inventing historical
intermediate commits.

- P0: redacted outbound HTTP audit, message order/state manifests, source hashes.
- P1: original request retention; candidate interpretation, authority, Model Claim,
  acquisition and supplied-excerpt facts remain distinct.
- P2: SharedExecutionHost/Boundary opt-in wiring reuses existing Registry, store and
  Canonical Trajectory; legacy remains the default and operational fallback.
- P3–P3.4: file receipt/source links, exact supplied-excerpt hashes, bounded Fetch
  evidence allocation (80 to existing 900 characters in recorded successful cases),
  Host recovery, native Turn ID correlation and time-metadata retention.
- Preceding authorized changes: native user input waits for real replies;
  explicit publication ranges, Google language serialization and search-reference
  normalization; weak lexical relevance is diagnostic rather than citation authority.
- Historical dated documents are retained as stage reports, not current release
  assertions. This checkpoint and the limitations below qualify their older results.

No Codex Core, frozen Phase-1 source, model environment, UMA patch, dependencies,
resource protection or profile defaults are changed by the checkpoint operation.
The only code edit during Git preparation was a test fixture:
test_web_environment now locates the Codex --version probe by command, rather than
mistaking a later Git manifest probe for it. Runtime/Harness behavior was not edited.

## Included / excluded

Included: shared Python/Shell implementation, related automated tests and dated
architecture/acceptance documents. Model-specific names/paths in historical N1X
documents are reference context, not shared defaults.

Excluded and retained locally: unused/context-projections.jsonl (test output),
ignored bytecode, model weights, virtual environments, credentials, raw runs,
HTTP snapshots, memory samples and local experiment/guard scripts. No .gitmodules,
submodule Gitlink or binary version record is changed.
A private Web environment stays outside the repository; never add it to Git.

## Validation and reproduction

Python 3.12.3, Linux aarch64. 42 isolated unittest modules:
452 cases = 450 PASS + 2 optional installed-vLLM CPU SKIP, 0 FAIL.
Python compile without bytecode: 47 changed/new .py files.
Shell: bash -n scripts/start_h3_harness_interactive.sh.
Git: diff --check. Static checks and credential/path review passed.
No new real model invocation, external search, dependency installation or GPU test
was performed for this Git checkpoint. Existing real-run evidence is summarized
below; offline PASS must not be promoted to Model Behavior or Workflow PASS.

From a clean checkout with the pinned Phase-1 submodule available:

```bash
git submodule update --init --recursive
python3 --version
for suite in \
  tests.test_harness_boundary_integrity \
  tests.test_harness_dynamic_tool_adapter \
  tests.test_harness_event_normalizer \
  tests.test_harness_generation_diagnostics \
  tests.test_harness_io_contract \
  tests.test_harness_observation_boundary \
  tests.test_harness_projection_capacity \
  tests.test_harness_provider_history \
  tests.test_harness_request_action_basis \
  tests.test_harness_request_continuity \
  tests.test_harness_runtime_connection \
  tests.test_harness_semantic_authority \
  tests.test_harness_semantic_execution_contract \
  tests.test_harness_semantic_promotion_audit \
  tests.test_harness_semantic_state_adapter \
  tests.test_harness_source_coverage \
  tests.test_harness_trajectory_reader \
  tests.test_harness_trajectory_writer \
  tests.test_harness_version_manifest \
  tests.test_harness_workflow_continuity \
  tests.test_contract_convergence \
  tests.test_evidence_provenance \
  tests.test_evidence_visibility_temporal \
  tests.test_search_transport \
  tests.test_native_user_input \
  tests.test_publication_range \
  tests.test_google_serpapi_backend \
  tests.test_p3_execution_closure \
  tests.test_context_projection_closure \
  tests.test_n1x_harness_startup \
  tests.test_h3_interactive_schema \
  tests.test_projection_delivery_recovery \
  tests.test_turn_completion_correlation \
  tests.test_fetch_evidence_budget \
  tests.test_web_adapter_shell \
  tests.test_web_environment \
  tests.test_terminal_input \
  tests.test_web_context \
  tests.test_web_network_observability \
  tests.test_phase2_web_architecture \
  tests.test_web_source_smoke_script \
  tests.test_web_intent
do
  python3 -B -m unittest "$suite" || exit 1
done
bash -n scripts/start_h3_harness_interactive.sh
git diff --check
```

Use separate processes: some existing Phase-1/web tests intentionally replace
import modules in test setup, so one-process blanket discovery is not the recorded
reproduction command. The two skipped cases depend on an optional installed-vLLM
CPU diagnostics setup. Profile guards are exercised with simulated platforms;
this checkpoint does not claim a new 5090D GPU run.

## Recorded real acceptance and current limitations

The 2026-11-02 P3.4 controlled run had 2 successful Google searches, 2 successful
Fetches with actual 900-character delivery, independent HTTP 404/403 failures,
matching hashes/Host Observations, and a real native-compaction/controlled-context-
omission recovery. A later user session used the same P3.4 source hashes and
confirmed 4 successful 900-character Fetch deliveries. These are bounded evidence
transport results, not proof of relevance or complete page comprehension.

Still open:
1. Google/SerpAPI connections can fail at TLS open (URLError/SSLEOFError); lack of
   response is not zero search hits or global network prohibition.
2. Unknown provider-switch authorization must remain rejected. The model did not
   reliably follow legal retry/clarification paths and sometimes echoed internal
   terminal-attempt JSON with a wrong historical call ID.
3. The natural near-limit compaction triggered after the user's accidental clear
   input failed with at least 32769 input tokens against 32768. The Bridge appended
   14 Host recovery blocks to that compaction request. There is no final
   post-restoration token-budget gate; a controlled lower-load compaction PASS does
   not close this case. Do not disable Host facts/authorization to obtain a PASS.
4. Original constraints are retained, but model-derived semantic bindings and
   research fulfillment are incomplete. Relation hints are not confirmed Goals;
   Turn completed is not Workflow completed.
5. A 900-character prefix may still be navigation/boilerplate. Fetch success, a
   URL or quote match does not prove content support or sufficient research.
6. Equivalent publication instants expressed in different UTC offsets may be
   incorrectly marked as conflicting source declarations.
7. Model financial/date/unit reasoning remains unreliable in recorded cases;
   no complete Research Workflow PASS is claimed.

Local evidence identifiers (raw records intentionally not versioned):
- contract-convergence/p34-20261102T030423Z
- nemotron-bolt/records/p34-live-20261102T030829Z
- runs/h3-results/interactive-32768-20261102-033635
- contract-convergence/manual-review-20261102T035503Z
All are relative to the local N1X uaea-n1x working area.
They are optional local evidence, not build/test dependencies.

## Platform and manual entry

Keep one shared entry. 5090D uses --profile h3 (managed vLLM/8002);
N1X uses --profile n1x (external vLLM; specify the actual model/endpoint).
No silent cross-platform binary fallback. Shared must be explicitly enabled;
omitting it selects legacy.

For an already running, protected external Bolt service:

```bash
bash scripts/start_h3_harness_interactive.sh \
  --profile n1x --vllm-mode external \
  --base-url http://127.0.0.1:8003 --model nemotron-bolt-n1x \
  --context 32768 --execution-contract shared
```

This command does not start or manage the external model service. Keep the existing
N1X resource guard; this checkpoint is not permission to change safety thresholds.

## Rollback and update

After publishing, prefer a new git revert commit for the checkpoint; no force push.
To inspect the older baseline without discarding local work:

```bash
git worktree add --detach ../UAEA-pre-p3 e99df8dfac252b4ecd4fd0f502ce65573056d046
```

For behavior-only fallback, omit --execution-contract shared; this does not undo
all shared Context/Evidence changes or fix known research/compaction problems.
A full source rollback requires reverting the checkpoint, not just changing modes.

5090D should first ensure its worktree is clean, then fetch and pull --ff-only,
initialize the locked submodule, run the relevant offline checks and use --profile h3.
If locally divergent, stop for review instead of reset/clean/force. The checkpoint
does not install the N1X model environment or change the 5090D model service.
