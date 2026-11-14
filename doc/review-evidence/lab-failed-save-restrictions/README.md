# Lab failed-save restriction recovery

Native Mac before/after confirms issue #562 item 1, originally reported by repch1c. The product commit is 044344686ab9ad14be03fff13c5f3a8f1b9ac161, based on release-0.34.16 88c9b49cb16360fc8fbf3f84003b8b54c29e6db5. Only lab_api.cpp and its maintained lifecycle test change.

| Check | Baseline | Candidate |
|---|---|---|
| Native local lab035 RPC acceptance | 2 fail, 1 pass | 3 pass |
| Maintained lab_lifecycle_tests | 11 pass, 2 fail | 13 pass, 609 assertions |

A directory at the disposable lab.json.tmp triggers a real unrelated identity-save failure. The old lab.json remains byte-identical. Before the change a previously paused gate accepts a fresh preparation and a revoked identity signs again. After the change the same requests remain refused with BTX035_PAUSED and BTX035_IDENTITY_REVOKED. Explicit resume, fresh action permits and unrelated save retry work; stale/consumed permits remain unusable. Other lifecycle cases exercise corruption, idempotency, bounded reads and admission.

## Executed boundaries

Apple M4, macOS 26, native arm64; disposable wallet-disabled regtest, modelnet helper disabled. The real registered lab035 RPC calls the daemon's lab dispatcher. Permits were consumed, not actual model processes launched. No wallet or money operation was tested.

The matched daemon pair reuses the verified 36ab43008cac48aa5c8410e4b70d90a249196a33 cached build, replacing the baseline/candidate lab API object and relinking both with the same local SDK and dependencies. Relevant lab_api, lab_disk, research_rpc, action_authority and guard_machine sources byte-match release 88c9b49cb16360fc8fbf3f84003b8b54c29e6db5. The C++ suite uses the maintained test file from the selected release plus the two new cases, with real BasicTestingSetup and reused cached product libraries. This is not a clean whole-current-release build. Build receipts record exact object/link inputs and executable hashes.

Local static dependencies emit deployment-version warnings (built for macOS 26, linked with a macOS 15 minimum); no older-macOS compatibility claim follows. Linux, Windows, full unit/functional suites, publication-failure rollback, transitioned-key scenarios, power loss and changed restart-persistence policy were not tested.

## Commands and provenance

Executed native harness, once per matched binary, with separate disposable output directories:

    BTX_ROLLBACK_BINARY=<matched-btxd> python -m pytest -q test_native_rollback.py --basetemp=<owned-case-directory>

Executed maintained suite on both matched test binaries:

    TMPDIR=<owned-temp-directory> <matched-lab-tests> --run_test=lab_lifecycle_tests --report_level=detailed --log_level=test_suite

The branch contains the maintained test, so a normal configured test_btx build can select the same suite. That standard full build command was not executed here; our recorded custom cached link is the executed path. The standalone harness starts only an explicitly supplied btxd on loopback ports 39361/39362; use owned unused ports and an empty temporary directory.

Logs, binary hashes, source comparison and verified checkpoint header receipt are adjacent. Private lab state/events and secret material are omitted. Local machine paths in published logs/JSON were replaced with placeholders; manifest.json distinguishes original and published hashes. Do not treat placeholder build paths as a fresh portable build recipe.
