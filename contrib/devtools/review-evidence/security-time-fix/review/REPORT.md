# Final verdict

**Ready for scoped local review.** The narrow timing repair has matched native fail-before/pass-after evidence, with strict rollback and meaningful late expiry/permission controls. No additional test is required to review this exact local candidate. No product branch, posting, push, merge/release qualification or public handoff is authorized by this review.

Parent exact `fd3a905fed3bc4943ad24372da032af4d29304a3`; final five-file patch identity is in FINAL-SOURCE-AUDIT.json and execution/product-files.json. Reviewer owns only this review directory; model inherited, exact setting unverified. No reviewer build/test/VM/product/shared/public action occurred.

## Source safety and minimality

Database::CheckClock is unchanged; no clamp, disabled comparison or silently refreshed explicit API argument was introduced. Old explicit ImportRecord validation remains outside its transaction and keeps its supplied time. Explicit EvaluateChallenge entry/admission remains supplied-time based; its produced receipt/report completion now uses the fresh path, so the entire API behavior must not be called unchanged.

The named current-evidence helper accepts receipt/evaluation only, acquires its write transaction before loading the actual current policy, binds its ID to the original policy, reuses full record validation and the caller’s live authorization, then performs final fresh policy/record expiry checks before the original strict storage clock guard. Signed body timestamps are unchanged. A held active-policy replacement is refused by current-load+ID binding; that exact branch is unambiguous in source, so no additional epoch matrix is required for this scoped review.

Service evaluation admission now samples under its own short transaction, rechecks policy/challenge time immediately before inserting the durable attempt, and releases that transaction before native work. Optional transaction ownership is valid on both explicit/current paths. Extracted validation/storage helpers do not create nested transactions. Known callbacks and all three RunApprovedPlan callers were audited: no native worker or nested BEGIN occurs inside the evidence transaction. Canary/work can perform bounded admission/mesh scans under the new write lock, which can increase contention; that performance boundary is unqualified.

Fresh local permission withdrawal is an intentional tightening. Evaluation polling now includes it, and shared receipt persistence checks it for canary/work. Canary/work otherwise retain their original worker callbacks; no claim is made that every workload now immediately cancels on a local config edit. Other explicit-time broker/lifecycle/peer/mesh/work-result callers are unchanged; this is not a universal timing rewrite.

## Matched evidence and controls

Identical final compiled harness object shared across all three executables, one predetermined invocation per selected case,15 invocations total. Configured native aarch64 Alpine/musl/GCC14.2 with real static sandbox worker and common explicit8MiB ELF stack:

| Case | Baseline | Timing candidate |
|---|---|---|
| Ordered two valid jobs require both PASS reports | FAIL: A’s actual PASS receipt followed by clock refusal and reportless blocked row | PASS: both real PASS reports/receipts, preserved across in-process Service restart with only2 task selections |
| Explicit old-time contracts and live future-highwater rollback | PASS | PASS; no new target attempt admitted |
| Held challenge expiry | FAIL: report released | PASS: SEC_EVIDENCE_RELEASE_REVOKED |
| Held BrokerPause | PASS by stale-clock masking | PASS by SEC_EVIDENCE_RELEASE_REVOKED |
| Held signed worker revocation | PASS | PASS: SEC_SIGNER_REVOKED |
| Held local permission withdrawal | FAIL: report released | PASS: SEC_EVIDENCE_RELEASE_REVOKED |
| Held report-body expiry after validation/authorization | FAIL: expired report released | PASS: SEC_EXPIRED_OR_FUTURE |

Thus baseline3/7 and candidate7/7. The combined executable (scheduler381 plus this repair) separately passes the original7-valid-job case with seven real PASS reports and no worker errors. This is one affected-case integration result, not the full PR381 suite.

Candidate ordered A keeps signed report issue time `1793658400237`. Another worker advances the persisted bound to `1793658400258`; A then uses genuine fresh storage time `1793658400261`, accepted against that bound while fresh wall is also0261. Its earlier signed timestamp is not rewritten or clamped. Both reports bind their actual saved native probe receipts and expected output. On restart there are still only two task selections, preserving successful-attempt exclusion.

Negative controls are not accepted merely for a nonzero result: exact candidate worker errors occur before shutdown with runtime_available1, reportempty/blocked rows and the intended pause/local/role/expiry state. Final-body expiry is held inside the candidate transaction after validation/allowed, without competing DB writes; released wall `1793658402985` exceeds held record expiry `1793658402975`, and Fresh refuses before storage. Challenge/local/record expiry cases actually improve behavior that baseline failed; baseline pause’s clock error does not prove a proper late permission check. Synthetic future clock bounds use the unchanged API and never move the OS clock.

## Identity and artifact audit

Saved binaries SHA256: baseline `b28791d6c5a7f8568509262ef3ccd1993b15b61a8e09583a7d00a89cf3232ca2`; candidate `cb5cc7e6c10ee6fa2d0dbcb1223bd2a7dc6e6e292bd661643fca278bd32f9c20`; combined `600f32ad12464a39796fa677b9f66d1b34881794355f71bb3c9a7a3275b71c3c`; actual static probe `f4ec4bf05befc4ffe60475c475e46dbbba7b8355304412d6ecc76454b78f9110`. Harness source `9541f0d6114ed79123a56ce971afaee77ba8970a44938176be9641099f53325f`; single shared object `fba04f9e4fa3701cb179201dbcd44316037b564b7d2969dd45bf64bf3f303084`.

Reviewer independently hashed all five saved identity artifacts, recomputed receipt RecordIds, actual probe SHA384/runtime pins and output digest/length/exit0 checks, and verified every retained report/receipt challenge binding. Every retained execution receipt is real PASS/dispatched. Signatures are present and production import verification ran; reviewer did not independently execute ML-DSA verification or repeat a native test. ARTIFACT-AUDIT.json retains individual rows, reports, failure causes and timing fields.

Removing only diagnostic lines from the actual compiled baseline/candidate translation units independently reproduces the exact base/product files; the combined Service maps to381 plus this one dispatch change. Final product manifest and compiled header comment identities reconcile. One preserved GCC-Werror harness formatting build failure was corrected before runtime, with the same final object used everywhere. Crypto/PQC/JSON dependency archives were reused with recorded exact native source/config identities; this is a focused component rebuild, not a pristine full-daemon build.

## Remaining limits and handoff

The original historical unretained baseline event’s exact cause remains unproven. The fix targets the separately established mechanism. Default stacks, macOS/Windows, full daemon, sustained contention and complete canary/remote-work workflows remain unqualified. Known callback scans now under a write transaction warrant an explicit contention limit; no broader performance claim is made. A future public/merge handoff must retain the runnable regression artifacts and these scope limits, but no extra broad matrix is required before local review.

Final REPORT/summary/REPRODUCE/metadata/cleanup documentation agrees with audited artifacts; no material correction remains. Owned processes, fixtures and guest directory are removed, cached646source files/libraries unchanged, no new packages, and VMStopped verified. Reviewer reservation released. Coordinator owns the next local decision; no public write, product branch or #325 work occurred.
