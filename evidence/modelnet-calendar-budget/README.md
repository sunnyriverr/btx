# Cloud calendar budgets: rollback and saved usage

**Matched component proof:32intended assertion failures before,356/356assertions pass after.** Backward time no longer renews consumed daily/monthly cloud allowance. Code: [f3c2270c](https://github.com/sunnyriverr/btx/commit/f3c2270ccb9f23697a413c1a9e9dfd90936e0f0f).

## Executed qualification

[Run44047253189](https://github.com/sunnyriverr/btx/actions/runs/44047253189), test recipe commit550a7f569d80b358504f33593354c2ad14546f48. The job executed `python3 -B proposal/stage.py`, then the pinned Ubuntu22.04 container and `python3 -B proposal/qualify.py`. The exact workflow and scripts are under recipe/. The checkpoint is an ephemeral CI artifact; the commands describe the executed retained-cache recipe, not a portable full-build reproduction claim.

- Same consumer object linked before/after: all4daily/monthly GET/byte cases previously allow backward/return reads; candidate refuses them with0origin GETs. Initial and next-window reads still return exact6bytes.
- Two maintained regression bodies: baseline32intended failures across all4quota contexts; candidate344assertions pass. Covers exhausted and partly-used allowance, persistent origin, saved budget reopen, healthy remaining reads and refusal when consumed.
- Existing forward day-rollover/reopen case:12/12assertions pass on both versions. Candidate total3cases/356assertions pass. Logs and observations are under raw/.
- The baseline classifier requires the exact intended errors, all quota contexts and no fixture/fatal/forward failure. Offline negative controls are retained. Independent read-only review checked the paired results.

## Identity and practical limits

Linux x86_64, Ubuntu22.04/GCC11.4 with retained production libraries frombd847e2b plus the earlier detach overlay. Only the candidate `s3_store.cpp` object was rebuilt; the test and wrapper objects are identical across both links. The store source equals current `ea64a31e9b4f83375746ce2e65917bcb3c2026e9` before the two comparison changes. Binary/object/source SHA256s are in qualification.json and RESULT.json.

This is actual S3PieceStore with fixed-clock hooks, disk-backed FakeS3 and real budget-file destruction/reconstruction. It does not alter host time, run the full helper/node/test_btx, call realS3, test concurrency, or qualify Windows/macOS/release builds. Lifetime counters remain monotonic. A future-dated saved window remains authoritative until time advances beyond it; this repair does not establish trusted time.

The full modified test-source passed a local macOS syntax-only check using exact current cloud headers and retained remaining headers/config. A stale-header preflight first lacked an already-adopted multipart declaration; no product failure was inferred. Neither syntax check is a native Mac runtime result.

## Maintained tests and credit

The focused PR includes `cloud_12f_calendar_rollback_preserves_exhausted_allowance` and `cloud_12g_calendar_rollback_preserves_remaining_allowance` in src/test/modelnet_cloud_tests.cpp. Qualification compiles these exact bodies in the declared standalone Boost wrapper; it does not claim execution through the full test_btx target.

Existing BTX copyright and credential/temporary-directory fixtures are retained. Existing #516 atomic budget persistence is unchanged. No new co-authorship is inferred from source review. One focused patch, no schema migration or unrelated code changes.
