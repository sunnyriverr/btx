# Native Windows SDK fixture repair

**Four formerly failing generated fixture targets compile; all 55 selected cases / 575 assertions pass on native Windows Server 2025.**

Code proposal: `codex/fix-windows-sdk-launcher` at `3b453c7826e809c523855dd2f999a5da3f11e788`, one seven-file test-only commit on accepted swarm `666673a3153225ba264c7870e0e82e354df86765`. Prerequisites for the tested integration: [#411](https://github.com/btxchain/btx/pull/411) at `362c36b2` and [#415](https://github.com/btxchain/btx/pull/415) at `a75dc8f6`. Their code is excluded from this proposal. [Source map](publication-source-map.json) proves that adding these exact prerequisites gives executed source `4593f590eb711c6536a650a5ec7a29d4c50dbd37` / tree `76ee7f7faf8c4dac35affaa641219fd556bc0c22`. The publication commit was not executed separately; packaging did not change the tested combined tree or rerun tests.

Windows prerequisite audit credit: repch1c and Jpp-matata (#356). Existing license/source headers and original commit authorship/date are preserved. The shared launcher reuses the project's existing subprocess implementation; it is test-only.

## Actual execution

[Native run 42010437780](https://github.com/sunnyriverr/btx/actions/runs/42010437780), controls `3f8422d8`: Windows Server 2025 x64, clang-cl 20.1.8, MSVC 14.51.36231 libraries, SDK 10.0.26100.0, static OpenSSL 3.5.4; Modelnet/tests/wallet/ZMQ compiled ON, GUI OFF. An exact 3,830-object cache restore; 11 normal steps in 18.17 seconds. The new cache retains 3,835 objects; no source/library substitution or broad rebuild.

The actual bounded component entry point uses the original maintained main/fixture objects/library closure, adding one normally CMake-registered helper object. It appends edges to the immutable original Ninja graph, without filtering or rewriting the maintained full target:

```text
ninja -C D:\btx-native-035\project-build -f D:\btx-native-035\evidence\four.ninja --verbose -j 4 -k 1 bin/windows_fixture_boundaries.exe
D:\btx-native-035\project-build\bin\windows_fixture_boundaries.exe --run_test=<suite> --report_level=detailed --log_level=test_suite -- -testdatadir=D:/fb42010437780/node
```

The second command was executed once for each suite below. Full exact commands/hashes: [native/sdk.json](native/sdk.json). Frozen original graph plus explicit helper/component: [native/four.ninja](native/four.ninja); preparation/restore/retention logic: [fixture.py](fixture.py). It needs the recorded matching cache/profile to reproduce that incremental campaign; it is not a demonstrated clean full build.

| Suite | Executed cases | Assertions |
| --- | ---: | ---: |
| modelnet_cr12_sdk_tests | 11 | 127 |
| modelnet_cr12_desktop_tests | 10 | 77 |
| modelnet_cr12_ux_tests | 10 | 186 |
| modelnet_hcp_priv_port_ops_tests | 24 | 185 |

Python 3.12.10 and Node 22.23.4 actually ran; no optional TypeScript HONEST_NOT_RUN. Other suites are normally disabled by each --run_test filter; all 55 distinct selected cases executed across the four invocations. Original selectors and body-ID/catalog/scope/secret-refusal/no-HTTP/no-execute checks remain. The new nine-assertion control checks real exit code 7, stdout/stderr, large dual-pipe output and a script path with spaces/empty argument. Owned data removed; no forced cleanup or remaining owned test process.

Before: the same original four source blobs/generated commands failed at missing unistd in [run 41994623193](https://github.com/sunnyriverr/btx/actions/runs/41994623193). [Baseline receipt](baseline-reuse.json) and [original compiler log](baseline/candidate-unit-build.log) retain this evidence; no repeated baseline. After: actual native compile/build and four raw suite logs are under native/. [Verification](verification.json) checks logs, source/catalog/configuration, immutable graph prefix, binary/checkpoint and cleanup; [manifest](manifest.json) inventories every readable evidence file.

## Limits and next gate

This is the tested #411/#415 integration plus this repair, not stock accepted source. Full maintained test_btx build/run remains open on six other grouped fixtures and an earlier retrieval fixture. Source CMake registers the new helper; the retained frozen original full-target edge lacks it, so regenerate CMake normally before attempting a full maintained target. No full cl.exe, interactive Windows 11, production or release qualification is claimed.

Mac evidence is the final helper's actual Apple clang 17/arm64 exit/output controls only; eight reused project headers match candidate source. Complete maintained Mac/Linux SDK suites are unrun. Windows interpreter-alias failure fallback was reviewed, not separately forced. Generic process-library quotation, failed-launch handle behavior and cancellation are outside this qualification.

Next decision: review/adopt this focused fixture prerequisite, then resolve the distinct remaining native fixture contracts before full #356 qualification. Existing passing cases need no repetition for this history-only packaging.
