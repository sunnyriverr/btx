# Pending CPU-confirmation worker test repair

**Scoped test-only repair.** Commit `8dad7098b22b01d759995b69f4a8278535b1a893` on `codex/test-worker-cpu-confirmation` changes only `src/test/matmul_verify_worker_tests.cpp`. Its bytes match the source executed in the paired native check. Production validation/consensus implementation is unchanged.

## Problem and correction

The prior diagnostic showed that the old AutoFallback fixture rejected its bad digest normally on portable CPU. It therefore never reached the retryable-pending outcome expected by the cleanup assertion. That was a test-route defect, not demonstrated blocked validation capacity.

The pending case now selects the existing StrictDevice confirmation-cache path. It fixes execution policy and the confirmation flag before computing their bound queue keys. The toy episode is explicitly checked not to require production-device admission. A real bounded portable CPU verification completes the good block's confirmation first. The bad block's actual CPU confirmation is then held on a latch. The unchanged worker must consume that pending result, report exactly `cpu_confirmation_pending`, run one retryable cleanup, release its captured test lease and scheduler ownership, and avoid creating a false header-verdict memo.

Under the same unchanged policy, following worker dispatch consumes the previously completed genuine good confirmation while the bad job is still pending. Its completion has a separate flag, so an earlier callback cannot satisfy progress. The test checks two scheduler acquisition/completion deltas, empty queue/reserved workspace, and absent bad memo. After releasing the CPU latch, real CPU recomputation rejects the bad digest. Scope cleanup drains the queue before restoring both policy flags and after joining worker callbacks.

A separate `cpu_confirmation_pending_does_not_replace_portable_rejection` control explicitly uses CpuDiagnostic. It checks that an unfinished queue entry does not replace normal portable invalid rejection, which produces a false completion and a present-false memo, with no retryable cleanup or retained lease. Explicit CPU policy makes this control independent of an eligible Metal/CUDA provider; AutoFallback would not guarantee that.

## Paired result

| Same maintained assertions | Old pending policy | Correct pending policy |
|---|---|---|
| Pending case | Fails the intended cleanup condition after20.135s | Passes |
| Portable rejection control | Passes | Passes |
| Process exit |201|0|

The final harnesses differ in exactly one pending-case policy selection, AutoFallback versus StrictDevice. Setup, data, assertions, control and unchanged worker implementation are otherwise identical. Raw candidate logs record actual worker outcome2 with `cpu_confirmation_pending`, subsequent valid dispatch, then the bad CPU confirmation finishing `invalid-consensus`. The final candidate completes both selected cases in0.207s; this removes a bad test timeout, not a measured improvement to network validation speed. `paired-result.json`, XML reports, console logs and `summary.json` are the evidence.

## Identity, scope and review

Base `cbf65894e6d61084527cd93e913a00c6794418dd`. Full maintained test-file SHA256 `a6753be55776e412a932db8ae76fca33bce39f6d33cec95ade00d14a144832cc`. Both complete test translation units compile, registering49cases; exactly the two named pending/control cases execute per variant. This is a native macOS arm64, CPU-only, wallet/Modelnet/Metal/CUDA-OFF partial relink with an identified base test-main object, fresh unmodified base worker object and21read-only archives. The link maps show one explicit worker object without an archive duplicate; archives, shared dirty source and original executables remain unchanged. `inputs.json`, `compiled-dependencies.json`, `build-result.json` and `source-manifest.json` preserve identities and commands.

This qualifies worker dispatch using pending and already-completed genuine CPU confirmations. It does not qualify fresh GPU execution while CPU work waits, actual network RC-admission lifecycle, native Windows/Linux, the complete worker/full unit suite, a full daemon build, mainnet or a release. The captured admission-like lease remains the existing fixture probe. The global policy/cache routes themselves are real production code; no bool-only verifier override or new production seam is used.

Internal source review caught a portability issue before execution: AutoFallback in the rejection control could select a real GPU. CpuDiagnostic corrected that. Final independent internal artifact review confirmed the paired result and scoped claims. No further run is needed without a relevant change or concrete review request.

## Resource pilot and cleanup

Both variants compiled and linked, but raw linker maps were18.2MB each, larger than budgeted. The final pre-run storage check stopped progression when measured space briefly fell to1,330,421,760bytes, below the1,342,177,280byte reserve. **No test ran during that shortfall.** Maps and14inactive completed test-fixture logs were archived losslessly with verified hashes; the paired runtime then stayed at or above1,388,609,536bytes. A later local-branch preflight also paused safely during a host-space fluctuation, then proceeded after a fresh passing reading. The receipts are `resource-pilot-build-result.json`, `link-map-archive.json` and `space-recovery.json`.

Owned temporary data was removed after log preservation; no wallet files were present. Reuse older archived logs/maps by reading or restoring their gzip copies. No active node, wallet, miner, VM or shared build cache was changed.

Reusable lessons: choose an explicit execution policy for a hardware-independent fixture, count following completion separately, and include diagnostic linker output in peak disk estimates. Compress bulky maps before starting a subsequent stage, rather than treating final executable size as peak usage.
