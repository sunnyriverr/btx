# Native Windows capability socket repair

**The same stopped-daemon regression fails before and passes after; real native client traffic and daemon-owned socket-entry removal pass.**

Review/cherry-pick [the four-file code commit](https://github.com/sunnyriverr/btx/commit/80f7f2a30e7586a61eb9a1671e9abacb4028257e) on swarm `666673a3153225ba264c7870e0e82e354df86765`. [Exact tested integration](https://github.com/sunnyriverr/btx/tree/29d0fc8a973ff5ef92e51fa1da6ad5bab037b2d9) contains #411 at `362c36b2`, #415 at `a75dc8f6` and #417 at `3b453c78`. These prerequisites are excluded from the proposal; `test::ProcessId` is supplied by #415. Applying the clean four-file projection to exact prerequisite integration `4593f590eb711c6536a650a5ec7a29d4c50dbd37` gives tested tree `2e43e982cbb0c50fe2400bffac911d22e9b2d43b`. The clean branch alone was not built. [Source map](source-map.json).

The product change uses `SOCKET`/`INVALID_SOCKET` and existing `Sock` RAII for listener, accepted and client sockets; `RecvLine` retains native width. Release ordering and request/size/spend/privacy refusals are preserved. Actual [diagnostic stack](diagnosis/decoded-stack.json) and [compiled call site](diagnosis/trace-callsite-4.log) place the old shutdown failure at CRT `close` called on a Winsock socket. Names are verified map associations, not source-line PDB symbols.

## Execution and reusable evidence

Native Windows Server 2025 x64, clang-cl 20.1.8, MSVC 14.51.36231 libraries, SDK 10.0.26100.0, static OpenSSL 3.5.4. Modelnet/tests/wallet/ZMQ compiled ON, GUI OFF. Existing 3,837-object cache; original generated compile entries/configuration and full Ninja graph preserved. The scoped component links the maintained main, two JIT test objects and required fixtures/libraries. Full `test_btx` was not built or run.

| Case | Before | After | Executed source pair / CI |
| --- | --- | --- | --- |
| `modelnet_jit_tests/jit_api_priv_scale_journey_safety` | exit201 | exit0,97/97 assertions | e014b2f4 → dfffd303; [42030285275](https://github.com/sunnyriverr/btx/actions/runs/42030285275) |
| `modelnet_jit_tests/capability_socket_failure_paths` | exit201 | exit0,11/11 assertions | same pair/run |
| `modelnet_jit_journey_tests/jit_api_04_cli_verbs` | exit0xC0000409 | exit0,140/140 assertions | dce7a28f → e8f45463; [42031320252](https://github.com/sunnyriverr/btx/actions/runs/42031320252) |
| Stronger directory-entry observation in CLI case | after-only | exit0,141/141 assertions |29d0fc8a; [42032913033](https://github.com/sunnyriverr/btx/actions/runs/42032913033) |

Each matched pair differs only in the two product files. Initial CLI coverage in the first run failed because Windows `fs::exists` could not inspect a live AF_UNIX reparse point; that failed control is retained. Readiness was corrected on both sides to require an actual allowlisted client response, then only the CLI case was repeated. Product blobs and the first test file are identical across candidates, so the first two passing results are reused by identity.

The final extra assertion enumerates directory filenames before fixture fallback unlink; it establishes physical entry removal without following a reparse point. That additional run is after-only on unchanged product and is not relabelled as a matched pair. Neither all three cases on the final binary nor repeated baseline execution is claimed. The CLI exercises real Windows AF_UNIX IPC with an in-process daemon and maintained CLI entry point, using toy CPU model fixtures.

Actual commands and outcomes are in each [native sockets.json](native/42030285275/sockets.json), [CLI-pair record](native/42031320252/sockets.json) and [cleanup record](native/42032913033/sockets.json). The executed component command was:

```text
ninja -C D:\btx-native-035\project-build -f D:\btx-native-035\evidence\sockets.ninja --verbose -j 4 -k 1 bin/windows_fixture_boundaries.exe
D:\btx-native-035\project-build\bin\windows_fixture_boundaries.exe --run_test=<named case> --report_level=detailed --log_level=test_suite -- -testdatadir=<owned case directory>
```

Those commands ran with exact arguments recorded in the corresponding JSON; the after-only build retains its controller's historical `baseline-build` log label but executes no baseline test. [Executed controls](controls/) include each hashed driver/input/workflow and shared support. They require their matching retained cache/profile, not a demonstrated clean standalone build. Source bundles are integrity inputs; use the normal code/integration branches for review. [Verification](verification.json) and [manifest](manifest.json) give provenance. [Archive inventory](archive-inventory.json) records hashes for included logs and omitted bulky generated graphs/checkpoint/catalog records; ZIPs are not the review entry point.

## Cleanup and limits

The daemon joins/returns0 and the socket directory entry is absent before fallback unlink. No owned processes or socket entries remain; no forced process cleanup. An existing read-only `.st` model-fixture artifact remains after each broader positive case and is recorded before harness-assisted attribute clearing/removal. Socket/thread cleanup is natural; whole model-artifact self-cleanup and descriptor-leak counters are unqualified.

Full maintained Windows build/unit acceptance (#356), external helper spawning, Windows 11 interactive behavior, POSIX execution, GPU, production and release qualification remain outstanding. POSIX compatibility was source-reviewed through unchanged existing `Sock` behavior.

Credit: repch1c's Windows audit on #356 and Jpp-matata's review/testing guidance supplied project context. Existing source copyright and prerequisite commit authorship are retained; no independent tested ACK of this new repair is claimed. Packaging repeated no tests.
