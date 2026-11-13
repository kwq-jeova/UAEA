# Single-clock monitor candidate

No production installation before safety and50-minute real no-model validation.
Single outstanding challenge, bound to guard Run, sampler Run, increasing request
sequence and unpredictable nonce. The consumed identity is saved BEFORE any
WSL/proc/NVML read; unchanged requests never cause another read or cache return.
The collector exits on failure/late query. Late data cannot be superseded by a
later successful read. Counter and query validity remain mandatory.

T0 is Windows Stopwatch before nativeWindows capture. Challenge publication is
after T0. Linux reads and validates this exact challenge before collecting.
Windows validates exact nonce/run/sequence at T1, and requires (T1-T0)<=3sec.
Thus both Windows and Linux observations lie inside this causal interval.
The Linux2sec budget remains a separate required condition. Both UTC values are
audit metadata, not assumed synchronized. Old response files while ONE new
request is pending are NOT consumed and do not refresh the original deadline.

At-most-once: matching request tuple can be collected only once; reverse/conflicting
requests fail. Nonce embedsguardID/seq and random128bits, so reuse under a newer
sequence failsformat. Windows consumes each issued sequence once; replay/crossRun
responses fail. Production paths contain no fault injection.

Existing resourceReason function is byte-identical. Existing independent Windows
heartbeat watchdog and owned PID/group cleanup remain. No global time/driver/WSL
setting, runtime model parameter, permission, Goal/Memory or Agent loop changes.

Residual: OS/driver uninterruptible stalls cannot be made a hard memory cap by
application watchdogs.2s late-call rejection and3s deadline are soft protection
plus independent supervisor termination; not a CUDA allocation limit.
The separate existing N1X model-admission policy remains stricter and still has a
conservative UTC sanity check at startup; it is not bypassed or rewritten here.
If admission rejects, no model loading retry or artificial success is permitted.
