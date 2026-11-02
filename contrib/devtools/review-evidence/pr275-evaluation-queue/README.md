# Evaluation queue scheduling — review evidence

**Two targeted starvation cases fail on `fd3a905f` and pass with `6478f640`; the candidate passes all four focused cases. A separate baseline control failure remains unresolved.**

This is a follow-up to Jpp-matata’s [#275 item 6](https://github.com/btxchain/btx/pull/275#issuecomment-6433856983). The product commit is based on `btx-035/model-security-v2`; its only changes are `service.cpp` and `security_tests.cpp`.

The scheduler previously selected the two lowest challenge IDs before checking whether their plans were installed or admissible. Those entries could block later valid work indefinitely. The candidate persists a per-evaluator scan cursor, processes at most 32 returned IDs and submits at most two tasks per maintenance pass, then wraps to reconsider lower IDs and newly installed plans. Full admission remains unchanged. This bounds returned/processed candidates, not all underlying SQLite work.

## Executed evidence

One final run per variant in a native aarch64 Alpine Linux VM (musl 1.2.5, GCC 14.2.0, SQLite 3.49.2), using the actual threaded Service, production crypto/PQC implementation and static sandbox probe. Both executables use the same final harness and an explicit **8 MiB ELF stack**. No worker or admission mocks.

| Case | Baseline | Candidate |
| --- | --- | --- |
| 70 earlier missing plans; reopen, cursor continuation and wrap | Later valid run absent after 8 s | PASS |
| Four earlier plan-binding failures before run insertion | Later valid run absent after 8 s | PASS |
| Seven valid jobs, first-pass limit of two | Scheduling assertions pass; later missing signed report | PASS |
| Pause/local evaluation permission, then recovery | PASS | PASS |

Candidate: **4 PASS / 0 FAIL**, 24.73 s, 12 signed PASS/dispatched evaluation/receipt pairs. Baseline: **1 PASS / 3 FAIL**, 26.43 s, four retained signed PASS/dispatched pairs. Restart is an actual in-process Service close/reopen, not a whole-node crash test. Candidate checks include exact 32nd-to-64th cursor continuation, new lower IDs and a plan installed later.

The baseline’s extra valid-work failure was not resolved: the exact reportless row/error was not retained. One separate trace-only diagnostic caught `SEC_CLOCK_ROLLBACK` and failed earlier; that does not establish the original failure’s cause. The diagnostic patch is outside the product commit. Do not describe this as a clean all-controls baseline matrix.

## Reproduction and identities

- [Reproduction instructions](runtime/REPRODUCE.md): independent-worktree recipe supplied for reviewers, **not separately executed as written**. Recorded runs instead linked the baseline Service translation unit before the same freshly built component archive.
- [Result/provenance summary](runtime/summary.json), [exact binary/source identities](runtime/linux/final-identities.json), [ELF metadata](runtime/linux/linux-provenance.json), [compile/link inputs](runtime/linux/build/).
- [Candidate results and signed fixture envelopes](runtime/linux/candidate-results.json), [baseline results](runtime/linux/baseline-results.json), [separate diagnostic](runtime/linux/diagnostic-run.log).
- [Candidate patch](runtime/candidate.patch), [common tests patch](runtime/tests.patch), [diagnostic-only patch](runtime/diagnostic-only.patch).
- [Internal artifact audit](source-review/linux-receipt-audit.json): source/binary identities and receipt linkage/digests checked by a second agent. No independent human/platform rerun or independent cryptographic verification is claimed.

The existing 1 MiB automatic buffer in `artifacts::Stream` exceeds small default worker stacks. Measured musl default/configured thread stacks were 133,920 / 8,391,456 bytes. A native Mac pilot built but crashed with SIGBUS before any completed case; no Mac runtime PASS. An earlier Linux pilot failed because its report directory was 0755 instead of the required 0700. The final harness added signed-output retention without relaxing its assertions.

Not qualified: default-stack execution, Windows, full daemon, real-model workloads, queue-full stress or a release. A 32-ID scan every approximately 2 s can take approximately 1,024 s across 16k entries; this is not a 25-second freshness guarantee. All owned test processes/storage were cleaned and the VM stopped.

`publication-manifest.json` records original and published text hashes; only unnecessary local paths were redacted. Public test keys/signatures are synthetic fixture outputs; private keys and databases are excluded. No binaries are distributed here.
