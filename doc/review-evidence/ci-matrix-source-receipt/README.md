# Local matrix source receipt

Base: `f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6`; code commits `efc107ca5d3c697674957303359295a8818f1b44` then `3a1889d8f0804c99827f4c42db82824f873272ad`.

The first commit repairs Bash 3.2 empty-array collection. The second saves source commit, observed working-tree manifest hash and dirty flags in run.json before dispatch, preserving existing TSV formats. The manifest can differ from committed HEAD under the explicit dirty-source override. This is source-selection metadata, not binary attestation.

Actual evidence: macOS arm64, Bash 3.2, Python 3.9.6; actual runner, disposable Git/worktrees, version-command doubles and marker-only dispatcher. With the same collection prerequisite applied on both sides, eight methods go from 5 pass/1 failure/2 missing-receipt errors to 8 pass. Original runner collection failure is retained separately in pilot-before.log. Paths in public logs are sanitized; logs otherwise unchanged.

Executed maintained recipe: `python3 -B candidate/test/util/local_mac_matrix_test.py` in an isolated candidate source snapshot. To run the maintained checks from the committed tree: `python3 -B test/util/local_mac_matrix_test.py` (reconstruction command; not separately executed from this publication commit).

No native BTX tests, compilers, seeds or hosted jobs. Single-job readiness fixtures do not establish parallel scheduling, failed-job handling, CI/all modes, other OS, binary/toolchain identity, concurrent-edit atomicity or crash durability. Final source review verified ordered/combined patches reproduce candidate bytes and original evidence hashes match; no test rerun for publication.

See candidate.log, prerequisite-corrected before.log, pilot-before.log, the ordered patches and manifest.json.
