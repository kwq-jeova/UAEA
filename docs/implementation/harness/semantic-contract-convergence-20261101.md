# Semantic/execution convergence — 2026-11-01

Status: scoped Contract PASS; real model behavior PARTIAL/FAIL. Legacy remains default.

The H3 entry supports --execution-contract shared (existing read-only Capability
surface) and --execution-contract legacy (rollback). No change to Phase-1 Agent Loop.
request_audit.py records a redacted HTTP-boundary snapshot and message manifest;
context-projections.jsonl records selected/omitted Context fields and identities.
Bridge auditing does not expose the server-tokenized prompt or establish understanding.

SharedExecutionHost owns explicit system policy and reuses the same semantic store
and ToolRegistry. SharedExecutionBoundary owns decisions, parameter sources and
observations; acquired source data is not automatically proof of model delivery.
Model interpretation remains a candidate. Unknown permissions are not granted.
Existing semantic validation is retained as a conservative compatibility gate.

The controlled paired run used real Qwen and Bolt, 4 turns/model, one load each.
Qwen searched/read but quoted incompletely; Bolt's search returned HTTP400 and later
generated a false file citation without a file call. These failures are preserved.
Turn completion and model claims never establish Workflow completion.

295 offline test cases: 293 passed, 2 skipped. No model/architecture-specific
cognition rules were added. No dependencies, Codex Core, frozen Runtime, UMA patch,
Qwen baseline, global settings or resource protections were changed. No Commit/Push.

Full report, source backups/diff and checksums:
 /home/wqkan_wsl/uaea-n1x/contract-convergence/20261101T015417Z/REPORT.md
Real protected model run:
 /home/wqkan_wsl/uaea-n1x/nemotron-bolt/records/contract-p3-20261101T020246Z/

This records implementation/testing, not a request to begin manual acceptance.
