# Windows fixture path repair: native scoped PASS

The same three maintained cases abort on Windows path limits before the repair and pass afterward with **49 assertions**. Native lock, isolation, attribution, freshness and default-temp controls also pass. This does **not** complete the full Windows build/unit acceptance tracked in [#356](https://github.com/btxchain/btx/issues/356).

## Code and exact tested source

- Standalone one-file patch: [aeaa069d](https://github.com/sunnyriverr/btx/commit/aeaa069dafe60f2b11362182913165dda4f8e268), based on accepted `666673a3`. Only `src/test/util/setup_common.cpp` changes; all test bodies/assertions remain intact.
- Tested before: `4609dde66f1da8023927196a55b6332dbcbeff3e`, unit binary SHA-256 `c2d4e9fdd24c74699a9c559234cce371bfcf8e93bb22a7c9ac27050fd7837dfb`.
- Tested after: [f9d4b894](https://github.com/sunnyriverr/btx/tree/f9d4b89424a551a3e24da30893b6ed6fb410c9f9), unit binary SHA-256 `e863772fdb50b08d9ac11c07639423041de531fc98ceff32e5b34922efb272a7`. The standalone and integrated fixture file are byte-identical.
- This tested tree includes pending Windows prerequisites #411/#415/#417/#418/#420/#421 and the remaining fixture/WAN/AHP corrections. [All integrated commits and authors](tested-source.json) identify that scope; these prerequisites are not part of the one-file proposal. Original authorship and source headers are preserved.

Windows uses the first 128 SHA-256 bits of the complete test name as a bounded directory component, and prints the full name. Per-test locks, random default suffixes, fresh-data handling and teardown are unchanged. POSIX keeps the original path string by inspection. The component is bounded; arbitrarily long caller-supplied roots are not guaranteed to fit.

## Executed evidence

Windows Server 2025 x64, clang-cl 20.1.8, MSVC 14.51 libraries, SDK 10.0.26100; Modelnet/tests/wallet/ZMQ enabled. [Profile and producer receipts](producer-receipts.json).

| Case | Before | After |
| --- | --- | --- |
| `modelnet_authz_tests/encrypted_release_plaintext_not_served_while_not_downloadable` | Path-error abort | PASS, 19 assertions |
| `modelnet_file_stream_tests/whole_file_fallback_keeps_a_piece_and_does_not_wait_out_the_deadline` | Path-error abort | PASS, 12 assertions |
| `modelnet_hosting_tests/removemodel_checks_in_use_before_unpin_and_deletes_the_directory` | Path-error abort | PASS, 18 assertions |

[Before log](baseline-three.log) · [before XML](baseline-three.xml) · [after log](candidate-three.log) · [after XML](candidate-three.xml).

The three-case command is identical except for the report filename. [Exact commands, exits and timings](commands.json) retain the actual arguments. Baseline proof comes from [run 42212786159](https://github.com/sunnyriverr/btx/actions/runs/42212786159); its original raw evidence is reused by source/binary/inventory/selector identity rather than repeated in the successful follow-up. Candidate and controls ran in [42214724275](https://github.com/sunnyriverr/btx/actions/runs/42214724275).

- A real Windows byte-range lock makes the actual executable [refuse the same test directory](same-name-lock-refusal.log) with nonzero exit before deleting its sentinel.
- A [different test passes while that lock remains held](different-name-isolation.log), with an independent directory identifier and the first sentinel intact.
- After unlocking, the normal three-case run clears stale data and removes the three selected lock files. Full names and calculated directory identifiers match the actual output.
- The [default-temp invocation](default-temp-control.log), without `-testdatadir`, passes and leaves no files in its controlled temp root; empty intermediate directories are permitted. Final owned-root cleanup and mapped-drive removal pass.

The native registration inventory is byte-identical before/after; [one canonical copy](registered-inventory.log) is retained. A zero-exit collection job is not used as the test oracle: [verification.json](verification.json) records recomputation from the raw XML/logs and the expected negative lock control.

## Build, entry point and limits

The cached incremental unit build takes **14.62 seconds**, with 11 planned steps. All 5,885 original object paths remain: 5,882 byte-identical, three planned rebuilds (fixture, version and generated-canary metadata consumer). [Build plan](fixture-unit-plan.log) · [build log](fixture-unit-build.log). Configuration, rules and compile table remain byte-identical. No MatMul source or acceptance rule changed; untouched node binaries remain baseline `4609` binaries.

Actual producer entry point: the [pinned Windows workflow](https://github.com/sunnyriverr/btx/blob/bf286e19d49b7c1a284047992289ec93b361ab01/.github/workflows/windows-root-configure.yml), calling [these executed controls](controls/fixture_fix.py). Its inherited restore/parser/job controls are pinned in the receipts. This is a retained-cache producer, not a newly qualified portable cold-build recipe. The initial ordinary Ninja dry-run stopped at CMake's bootstrap before compilation; the successful build uses the established **byte-identical manifest copy** of the maintained graph, with exact one-C++-file and configuration guards. Normal bootstrap is not qualified here.

**Still needed:** integrate prerequisites and complete the full native Windows build/maintained unit run on the accepted tree. This is not a stock `666673a3` Windows qualification, full-suite pass, native `cl.exe`/MinGW result, POSIX runtime run or release sign-off. The other earlier failure observations were not retested on this fixture repair.

The earlier Windows path-length failure class was reported by repch1c in [#356](https://github.com/btxchain/btx/issues/356#issuecomment-6635802518). This scoped fixture repair and its native evidence do not imply an independent human ACK, adoption or merge. [File hash manifest](manifest.json).
