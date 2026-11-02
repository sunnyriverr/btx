# #381 submission-cap regression — sensitive control confirmed

**Cap2 passes; the cap99-only mutant fails solely at the final cap assertion. Both variants first complete all seven genuine native PASS/dispatched endpoints.** The primary local reproducer built and ran this one focused case once per variant on its first attempt (31.48s total); no retries or additional matrix were used.

The repository-native test correction is `test-only.patch`, matching local commit `3655ce1a9e6f9f41f9b4a37906701f045a2c46fd` on #381 parent6478f640. Exact executed test SHA256: `5333ef047469e7c628ff1c76b4b4aecc249b5575e01510b21a81e4f42a1f9bc1`. No new production API, observer or diagnostic overlay is introduced.

## Oracle and observation

The fixture seeds seven unique, locally eligible proposals, with no earlier evaluation rows or maintenance marker. Queue capacity8 exceeds jobs7; no other canary/remote/manual work is present. Each visited first-pass ID therefore successfully submits. A single SQL statement snapshots maintenance completion/error/cursor, strictly within1.5s of a clock started **before Service construction**. Maintain cannot begin a second pass before its2s minimum wait; unchanged markers alone would not establish that boundary.

| Variant | First completed-pass cursor | Snapshot after pre-constructor start | Final result |
| --- | --- | --- | --- |
|Cap2 | Exact sorted second challenge ID |6,894us | PASS; seven signed native endpoint pairs |
|Cap99 | Empty after visiting all seven and clearing the tail |12,556us | FAIL: first pass exceeded two submissions; seven signed native endpoint pairs already complete |

The cap verdict is captured before waiting for workers, and asserted only after all seven endpoints pass. Thus the mutant fails because of first-pass admission progress, not worker throughput, clock failures or cleanup. No maintenance error, observation-window miss, worker failure or timeout occurred. A future `FIXTURE_FIRST_PASS_OBSERVATION_MISSED` is a fixture-boundary failure and must not be called a cap defect or rerun until green.

## Inputs and limits

Both variants use exact #381 plus the identical unchanged #384 timing prerequisite, avoiding the already diagnosed completion-time confound. `linux/mutation.diff` verifies the only production-variant difference is `submitted==2` versus `submitted==99`; neither is a new product proposal. Native aarch64 Alpine/GCC14.2/musl, real static probe, explicit8MiB ELF stacks. Identified crypto/JSON archives from the prior fresh #384 packaged build were reused; this cap run is not a fresh dependency build. The README now documents those official dependency targets, explicitly not rerun here.

`semantic-audit.json`, `linux/work/results.json`, both raw summaries and `linux/provenance.json` retain cursor/timing values, fourteen signed endpoint pairs, source/archive/binary/harness identities and actual build inputs. The same harness object is linked into both variants. `reproducer/` contains the executed local entry point and source-only patches; its post-run README addition is documentation only.

This closes the specific nondiscriminating first-tick assertion weakness. It is a controlled cursor-based admission proof for this all-eligible fixture, not a generic submission counter, stress/full-daemon/default-stack/other-platform/release qualification. No unchanged starvation or timing matrix was repeated.

All owned processes, fixture directories and guest work files were removed; VM is stopped.646 cached sources and three cached library hashes remain unchanged; no packages were installed. Guest free space618405888bytes, host reserve above1.25GiB. See `cleanup.json` and `vm-final-state.json`. Coordinator owns the local test-only commit; executor performed no Git writes or publication.
