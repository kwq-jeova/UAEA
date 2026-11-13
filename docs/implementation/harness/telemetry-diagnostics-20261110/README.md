# Diagnostic-only N1X change evidence

Applied to existing launch assets outside the source repository.
Before/after source and pins: research-records/finance30-monitor-20261110T082511Z.
The two patches add primary rejection context and collector publication records.
Resource limits, future-time refusal, 3s freshness and 2s sample budget remain.
fault-injection.ps1 extracts the actual production predicates for isolated tests;
it does not load a model or change protected thresholds.

The causal-freshness proposal is NOT applied. See the associated research report.
Do not reverse these patches over a later edited launcher without checking hashes.
