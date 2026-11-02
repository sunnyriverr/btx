# Separate security evaluation timing fix

**The focused candidate passes all7 acceptance/control cases; the same harness fails4 of7 on baseline.** The ordered two-job reproduction now produces two genuine signed PASS reports instead of losing the first report to `SEC_CLOCK_ROLLBACK`. An isolated combination with #381 also passes its original seven-valid-job acceptance, with seven native PASS/dispatched results and no worker errors.

Candidate is `candidate.patch` over exact `fd3a905fed3bc4943ad24372da032af4d29304a3`:5 product files,94added/30removed lines, including movement of existing checks and API comments. No product branch, shared checkout or publication was changed. Exact source hashes are in `product-files.json`.

## Repair and scope

Database::CheckClock is **unchanged**. Existing explicit-time ImportRecord behavior and EvaluateChallenge's explicit entry-time contract remain strict. New Service admission acquires its transaction before sampling/validating current authority, then resamples immediately before the running insert and rechecks policy/challenge time bounds.

A receipt/evaluation-only ImportCurrentEvidence entry serializes current-policy binding, the existing complete record validation and caller authorization. After expensive checks it samples a fresh commit time, performs cheap final policy/record expiry checks and uses the original strict clock guard. Signed event timestamps remain immutable. The original explicit import keeps its validation outside its transaction; its supplied-time semantics were not silently replaced.

Fresh local evaluation permission is intentionally rechecked at evidence release. Generated receipt/report completion therefore changes even when invoked through the explicit EvaluateChallenge API. RunApprovedPlan is shared by evaluation, canary and remote-work callers: their receipt completion now uses this fresh path, retains the original caller authorization and expected-policy binding, and checks current local permission. Canary/remote-work-specific workflows were source-reviewed, not separately executed. Other explicit-time clock callers were audited and left unchanged; this is not a universal clock API rewrite.

## Matched final sequence

Every selected invocation ran once, with the identical compiled harness object and diagnostic scheduling controls. There were no runtime retries or outcome injections.

| Acceptance/control | Baseline | Candidate |
| --- | --- | --- |
|Ordered two valid jobs, both signed PASS reports required | FAIL: first report lost to clock refusal | PASS; both native PASS, reports survive in-process Service restart and remain excluded from scheduling |
|Explicit clock/import/evaluation time contracts and live rollback bound | PASS | PASS |
|Challenge expires while report held | FAIL: released report | PASS: authority/expiry release refusal |
|Owner Broker::Pause while held | PASS, but denied by old stale-clock error | PASS: actual authorization refusal |
|Signed worker-key revocation while held | PASS | PASS: signer revoked |
|Local evaluation permission withdrawn while held | FAIL: released report | PASS: authorization refusal |
|Signed report expires after validation, before final persistence | FAIL: released expired report | PASS: final expiry refusal |

Candidate error causes are retained: `SEC_CLOCK_ROLLBACK` for rollback, `SEC_EVIDENCE_RELEASE_REVOKED` for challenge expiry/pause/local permission, `SEC_SIGNER_REVOKED` for revocation and `SEC_EXPIRED_OR_FUTURE` for final record expiry. Baseline pause's clock error is not evidence that its late permission check worked.

The rollback case tests older supplied timestamps against the real strict APIs and advances the persisted bound through CheckClock to test the live path's refusal of a subsequently lower wall sample. It does not alter the OS clock. The final record-expiry hold occurs inside the candidate transaction after validation/authorization, with no competing database writer; the baseline counterpart holds after validation before its old transaction. Other holds occur immediately before report import, outside transactions. All barriers have bounded cancellation. All retained execution receipts are native PASS/dispatched and match the actual static probe runtime/output. No barrier or process timeout occurred.

The separate combined executable uses #381's Service plus this timing repair and runs only the affected original seven-valid-job case once. Its PASS does not imply requalification of the entire PR or every platform.

## Evidence and cleanup

Native aarch64 Alpine/Linux6.12.81, GCC14.2.0, musl1.2.5, SQLite3.49.2; identical explicit8MiB ELF stack configuration. Unchanged security objects and the common harness are shared between variants. Two exact crypto/PQC/JSON archives were reused from the earlier clean native build; source/configuration identities are retained. All35 current compiled inputs match authored/target bytes;646 cached dependency files remained unchanged. The patch was applied to isolated exact-base files and all five hashes match the final manifest. Removing only diagnostic lines from the compiled baseline/candidate sources reproduces the exact baseline/product files; the compiled trust header matches the final commented header (`patch-and-compiled-source-checks.json`). This is a focused component build with reused dependencies, not a pristine full-daemon build.

`linux/final-sequence.json`, `acceptance-audit.json` and `linux/results/` retain all15 invocations, pre-stop/post-join rows, exceptions and signed envelopes. `linux/provenance.json`, tested identities, maps and compile/link commands identify exact inputs/binaries. A first build stopped at inherited adjacent-if test formatting under GCC-Werror; the corrected common harness was built before any runtime, and the failed build log is preserved. No product guard was changed to clear it.

All owned processes, fixture directories and guest work files are gone; VM is stopped. Cached source/library hashes are unchanged, no packages were installed, and618589184guest bytes remain free. Host reserve stayed above1.25GiB. See `cleanup.json` and `vm-final-state.json`.

Reviewer accepted source and raw results; final metadata is reconciled. Coordinator owns the next local review/commit decision. Default-stack/macOS/Windows/full-daemon/stress/release qualification is not established. The earlier historical reportless event remains retrospectively unproven; this repair addresses the newly reproduced and directly tested mechanism. No posting or push occurred.
