# Rejected snapshot import: save/restart qualification

**Before/after verified on macOS arm64.** Product commit 1dcc22b5278d38b8c1db51ef420bd6e68aebbb47, base `swapnet-v2` f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6. Addresses issue #562 item 3, originally identified by repch1c. The PR changes only `lab_api.cpp` and its maintained lifecycle test.

The import now runs existing validators against staged state before installing repository/content changes. Existing model/trajectory inputs are retained; runtime restrictions, identity material and one-use permits remain in the live Store. Disk-save failure handling and accepted-import integrity policy are unchanged.

| Executed check | Baseline | Candidate |
|---|---|---|
| Malformed piece rejected | BTX035_SCHEMA | BTX035_SCHEMA |
| Rejected repo visible immediately / persisted by unrelated save / present after native stop-start | Yes / Yes / Yes | No / No / No |
| Valid blob retained; subsequent valid model/piece import, restart and exact export | Pass | Pass |
| Same maintained regression: malformed piece and model/piece mismatch, later identity save/reload, valid model export | 7 intended failures | Pass |
| Current lifecycle suite | Not fully rerun on baseline | All 14 cases pass |

The baseline mismatched model also prevents export of the previously valid model. The regression checks both rejection codes, unchanged immediate disk image, no rejected repo in the later saved image, clean memory reload, and retained valid model/piece bytes.

## Exact executed profile

Apple M4, macOS26.5.1, nativearm64. Baseline daemon SHA-256 `7fb8eb5cef3b2688dda5b0eeda14068a443a851b3a4724df2daf823c1e82fa5b`; candidate `b7f4f6e7d9bd84bcef1340adea36473bf2a123a6c42747ea574b2455c43ed4b7`.

The daemon uses retained `36ab4300` build objects. Its actual #665 lab_api.cpp is byte-identical to current f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6; only that translation unit was replaced for the candidate. Current lab_exchange.cpp, git_snapshot.cpp and lab_disk.cpp match the retained source baseline. The maintained test binaries share the same final test object/support objects and differ in the modelnet library. This is **retained-object native integration, not a clean whole-current daemon rebuild**. Build commands and hashes are adjacent.

Only disposable wallet-disabled loopback regtest nodes were used; Modelnet was disabled and lab035 called the native dispatcher. No Linux/Windows, full node suite, production/mainnet, older-macOS compatibility, allocation-failure atomicity or large-store performance qualification. Static dependencies emit newer-macOS deployment warnings. Research/train/replay staging was source-reviewed, not independently exercised by these new rejection tests. Copying existing import-related maps adds unmeasured peak memory/latency. Separate #562 item4 integrity policy is unchanged.

## Executed commands

Native pair (same `test_atomicity.py`, distinct initially absent runtime paths; ports39561/39562 must be unused):

```sh
BTX_SNAPSHOT_BINARY=<baseline-or-candidate-btxd> BTX_SNAPSHOT_RUNTIME=<fresh-absolute-runtime> python3 test_atomicity.py
```

Baseline exits1 after completing restart and intended atomicity failures; candidate exits0. Both stop their child processes. `final-before/result.json` and `final-after/result.json` retain observations.

Maintained regression on baseline:

```sh
<baseline-lab-tests> --run_test=lab_lifecycle_tests/rejected_snapshot_import_is_not_saved_by_a_later_write --log_level=test_suite
```

Candidate current lifecycle suite:

```sh
<candidate-lab-tests> --run_test=lab_lifecycle_tests --log_level=test_suite
```

These cached compile/link commands are the executed path. A normal configured test_btx build can select the in-tree suite but that clean full build was not run here. Placeholder paths in published build receipts are sanitized provenance, not a portable build recipe. `manifest.json` records original and published file hashes. Runtime lab files/cookies/keys are omitted.
