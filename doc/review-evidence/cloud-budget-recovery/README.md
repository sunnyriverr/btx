# Cloud budget save recovery

**Fail before / pass after:** a failed startup rewrite used to damage committed cloud accounting and permit another same-day read. The candidate preserves the old file, returns a save error and remains unready. Healthy reopening retains the exhausted allowance.

## Code and attribution

Product base: `release-0.34.16` at `dac9aee53520bd49ed320ec7a49b9072fc7d88d9`. The focused product commit changes only `s3_store.cpp`, its private declaration and the existing cloud-test source. Original BTX copyright notices and the existing calendar-budget/credential fixture are retained. The writer uses the repository's exclusive-create, file-commit and replacement helpers. Related [#473](https://github.com/btxchain/btx/pull/473) covers release campaigns and explicitly excludes this budget file.

The cached execution tree contains the earlier, unrelated #473 overlay, rather than being a pristine release build. `manifest.json` records that exact baseline, the hash-matched candidate tree and the separately reconstructed clean product-patch tree. The clean tree was not rebuilt as a whole.

## Executed qualification

Ubuntu 22.04 x86_64, GCC 11.4.0 and pinned OpenSSL 3.5.9. The production cloud component came from the verified retained cache; only the changed `s3_store.cpp` was recompiled for the candidate.

- [Baseline run 42927462266](https://github.com/sunnyriverr/btx/actions/runs/42927462266): observation classified `REPRODUCED`, exit 1. Both maintained regression bodies failed at the intended save/startup assertions. A later candidate compile error in this run did not invalidate those completed baseline observations.
- [Candidate run 42927926052](https://github.com/sunnyriverr/btx/actions/runs/42927926052): reuses the verified identical fixture objects and saved baseline, classifies `PASS`, exit 0. Both regression bodies pass, 64/64 assertions. The complete modified test source also passes a syntax check with real repository headers.
- [Executed qualification source](https://github.com/sunnyriverr/btx/tree/dcdac7f97b1b4a9b3bd46bec387eda7b21451917/contrib/devtools/cloud-budget-fix): `build_resume.py` verifies cache/source identity, links the component fixtures, runs the observations under `strace`, checks expected baseline/candidate exits and compiles the full test source. No full helper rebuild was performed.

The component fixture executes the exact added test bodies with a small owned-directory setup instead of `BasicTestingSetup`. Its actual command selects `--run_test=modelnet_cloud_tests`; that fixture registers only the two new cases. It is not the full `test_btx` binary.

## Observations and limits

| Check | Before | After |
| --- | --- | --- |
| Startup write fault | 122-byte committed file truncates to 61 bytes; Init reports success | Confirmed EFBIG on separate temporary file; original 122 bytes unchanged; Init reports failure/unready |
| Same-day healthy reopen | GET/byte counts reset to zero; valid extra read allowed | GET1/bytes6 retained; budget refusal |
| Healthy reopen, real FakeS3 payload, clean day rollover, in-memory mode | Valid controls pass | Valid controls pass |
| Save fails after a completed read | Success reported and old file damaged | Error reported, output cleared, read remains charged in memory, old file preserved |
| Temporary cleanup | No temporary writer | No owned temporary files remain after the observed failure/recovery |

`baseline/` and `candidate/` contain actual observations, syscall traces, classification and test logs. `fixture/` contains the exact consumer, test bodies and result checker. The checker rejects missing fault evidence, incorrect identity/window, skips and failed valid controls. Credential strings in this fixture are synthetic test data.

The new maintained cases are `modelnet_cloud_tests/cloud_12c_startup_write_failure_preserves_budget` and `modelnet_cloud_tests/cloud_12d_post_read_save_failure_retains_charge`. They can be selected individually in a normally configured `test_btx`; that normal-target execution has **not** been claimed here. Fault injection uses POSIX `RLIMIT_FSIZE` and is excluded on Windows.

This is Linux/FakeS3 component evidence: no live S3, full helper/node/package restart, full unit suite or native Windows/macOS qualification. The change preserves previously committed state across the observed I/O failure. It does not recover already-corrupted files, change malformed-load policy, guarantee multi-process accounting, exactly-once remote billing or power-loss directory durability. Rollover arithmetic and serialized fields are unchanged.
