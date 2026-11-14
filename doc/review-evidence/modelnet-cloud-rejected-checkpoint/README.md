# Cloud recovery after integrity rejection

**Verdict:** the same corrected-origin test fails before this change and restores exact bytes after retry and helper restart. Valid partial/EOF resumes remain usable; whole-file SHA-384 and pieces-root checks still gate publication.

Code: aa947a7e85886104d420de4e13eee39880c81a80 on swapnet-v2/a5d1637f. Five files: cloud caller, file_stream.cpp/h, maintained functional and C++ regressions. Native helper was compiled at3a9effab; final04e15df1/aa947a7e changes only the maintained test's scenario identity. Existing [repch1c MinIO fixture/report](https://github.com/btxchain/btx/issues/613) and [667 recovery work](https://github.com/btxchain/btx/pull/667) are reused;667 is already incorporated at5667ecdb.

## Problem and repair

After a corrupt origin file is rejected, its quarantined bytes and EOF cursor can survive. Correcting the origin does not replace those rejected bytes; getmodel remains nonlocal/shortstream and export INCOMPLETE across restart. The fix records per-file rejection before cleanup, retries marked cleanup on the next attempt, and removes the marker last. No live pieces, catalog identity, pins or accounting are removed.

The saved cursor for a short final piece remains aligned, but resume accounts for the actual file length and reauthenticates all pieces. A typed hash/root failure flag keeps network, budget, quota and publication failures from discarding useful progress. There is no automatic second download in the rejecting call; the integrity error remains visible.

## Executed acceptance

| Row | Evidence |
|---|---|
| Same asserted corrected-origin test | [Before43642792699](https://github.com/sunnyriverr/btx/actions/runs/43642792699): native exit1, shortstream after restoring exact origin bytes and restarting. [After43643834503](https://github.com/sunnyriverr/btx/actions/runs/43643834503): native exit0, exact stored/exported bytes and restart. Main script SHA2569d99e9ff7b893ba6f7e6e6028b275e3eb987e4d11c2da4e69a2d9d5a7aefce1b. |
| Exact maintained functional test | [43644057714](https://github.com/sunnyriverr/btx/actions/runs/43644057714): identical final module fails before and passes after; includes ordinary partial resume and real-MinIO layout matrix. |
| Interrupted cleanup and marker-write failure |43643834503: marker+job/missing quarantine, marker+quarantine/missing job, and permission-denied marker creation. Exact recovery and restart pass; unrelated path preserved. Explicit local filesystem fault-state injection, not timed crash/power-loss testing. |
| Storage-pressure recovery |43643834503: pinned disposable filler prevents publication; removing it through normal RPC lets the valid EOF checkpoint finish with0origin GETs; exact export/restart pass. |
| Existing safety/healthy controls |43643834503: corrupted bytes and exhausted GET budget still refused; unrelated healthy model stays usable. |
| Compiled production components | [43644602712](https://github.com/sunnyriverr/btx/actions/runs/43644602712): current file_stream.cpp with retained dependency libraries, replacement-main driver checks SHA/root rejection and short-EOF quota recovery. Maintained C++ test file compiles; fulltest_btx not run. |

[Exact manifest](manifest.json), [before](before-result.json), [after](after-result.json), [maintained pair](maintained-after.json), [cleanup](cleanup-controls.json), [quota](quota-eof.json) and logs are in this directory. The positive recovery test does not edit catalog/cursor/quarantine state; separate fault controls explicitly construct cleanup-interruption states. The standalone pair's imported base fixture differs by a four-line readiness probe; the maintained before/after pair uses identical complete test bytes.

## Executed entry points and identity

Immutable fork recipes: [before at7f7091d8](https://github.com/sunnyriverr/btx/tree/7f7091d824e45441ae1304abc6c35ec7572aa027), [helper build at62ed83c6](https://github.com/sunnyriverr/btx/tree/62ed83c67a954b92229047f4ea678c17abb6e30e), [native after/controls atee0a5612](https://github.com/sunnyriverr/btx/tree/ee0a561220e4059c068812b7abbabcacd2f5a70c), [maintained pair ateb8d97e6](https://github.com/sunnyriverr/btx/tree/eb8d97e62a4432c6f4a922d638f3426058c38e36), and [compiled controls at7607e0ba](https://github.com/sunnyriverr/btx/tree/7607e0ba15239a7ae702f53a1adca4b650c83d56). They pin inputs and check native exits/results; a green before job means the expected failure was verified.

Native runtime Ubuntu24.04x86-64 with real pinned MinIO; helper build Ubuntu22/GCC11/OpenSSL3.5.9, verified cache,12planned incremental actions. Before helper SHA25683fb3f0b1be5cca1e7edfaa8571e0f5c0ee53391d1303a86828e480f2cc2d99b; after214de8dad821fc433bad8c31c558c7e1958efdcb83909aee9daafbc5324a6c1d. Older retained8d6node/CLI proxy RPCs; not a whole-current-daemon rebuild.

## Limits and corrected test tooling

No native Mac/Windows, WAN/R2, full-suite/release, model execution/spend, large/multi-file performance or power-loss qualification. Arbitrary malformed/missing local jobs and catalog-metadata deletion remain separate unqualified cases. No FakeS3 fallback in these native claims. The component checks use retained dependency libraries; native helper integration is separately executed above.

The helper compiled successfully before an auxiliary driver failed on filesystem path syntax. Later driver fixes derived the actual object path and retained the original main's translation support; product bytes stayed unchanged. First native qualification passed the main/control rows but the new maintained scenario reused a previous model identity and stopped at upload setup. It was given distinct deterministic data and rerun before/after. [Corrections](fixture-corrections.md), failed job identities in the manifest, and the initial maintained failure log remain visible. Do not describe those aggregate workflows as green.

Original immutable cache and exact helper binary remain retained. Candidate object-cache upload was skipped after the auxiliary failure; future retention order was repaired offline without repeating the helper build. Broader ModelNet recovery qualification remains separate from this focused repair.
