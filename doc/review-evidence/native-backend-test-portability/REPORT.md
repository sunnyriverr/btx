# Windows unit portability — same generated target fails before, passes after

4 November 2026. Owner: BTX session1, thread01a1a0a2-417d-7400-a541-e3a986116398.

**Scoped PASS:** the actual root-generated `matmul_backend_capabilities_tests.cpp.obj` fails on stock `46caec76` and builds with the one-file repair. Native MSVC and clang-cl execute the exact repaired environment guard and its two new cases successfully. Full node linking and the complete `test_btx` build/run remain unqualified. Nothing was posted upstream; the product branch remains local.

## Why this work

Numair [requests full native Windows build and units on46caec76](https://github.com/btxchain/btx/issues/356#issuecomment-6620134468). Our [previous real root diagnostic](../windows-root-configure/REPORT.md) reached a concrete compile failure in the supported test target. This repair addresses that measured prerequisite, not a new network/consensus issue. Fresh public source, open PR, #356 discussion and named fork Actions checks found no adopted/competing fix or active matching native job. Private work cannot be ruled out. Both dispatches rechecked accepted head, all open PRs and ownership of the exact CI ref. See [initial check](preflight.json) and [final dispatch preflight](pre-dispatch.json).

## Repair and exact identities

- Base: `46caec762b0f130d497313d8ca9fa6894ac19ccd`, accepted `btx-035/swarm`.
- Local branch: `codex/fix-native-backend-test-env`; single product commit **`c3af59dfea2dd3ca9ed2e3efb7677f706b4196ad`**, directly on that base. One changed file: `src/test/matmul_backend_capabilities_tests.cpp`.
- Native run: [41761879608](https://github.com/sunnyriverr/btx/actions/runs/41761879608); fork-only orchestration commit `f87ef56b4741b8acb7e877dda8537fc2abf38512`. Separate exact accepted-source checkout; one approved source replacement after the original compile failure.
- Native candidate bytes SHA-256: `de04d3a5733eb36fa6490409aea77655acca874f3ff5c757dbccf336bbb55078`. Retained compiled unit object SHA-256: `b756ec56277c42932190b02e38ce947ca5af91677f164ef46b0505d1df77cb00`.

The test guard uses `_putenv_s` on Windows to update the CRT environment read by `std::getenv`; both original POSIX branches remain. This follows the already accepted guard in `matmul_metal_tests.cpp`. The reused source author, Numair Faraz, is credited in the product commit; repch1c's #356 portability report and JPP's earlier native audit are retained as diagnostic context, not represented as their execution of this new repair.

`<unistd.h>` remains included on POSIX. The existing zero-copy Metal case remains registered on Windows, where it asserts the accepted backend is unavailable and explains non-applicability. Its original page-size/aligned-allocation body is byte-identical on POSIX. The accepted build selects `metal/matmul_accel_stub.cpp` on Windows, whose probe reports unavailable. No Windows aligned-memory emulation, global compatibility header, CMake or production change was added. All35 original case names remain; two environment restoration cases were added. See [diff](patch.diff), [source manifest](source-manifest.json) and [Metal body/registration preservation](metal-body-preservation.json).

The [Microsoft CRT contract](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/putenv-s-wputenv-s?view=msvc-170) treats an empty value as removal. The existing helper callers here use null or a nonempty weight string; this repair does not claim Windows can preserve a distinct present-empty value. POSIX empty-state restoration is separately checked.

## Actual verification

Native Windows Server2025 AMD64, image20261030.294.1, Windows SDK10.0.26100.0, MSVC toolset14.51.36231/cl19.51 and clang-cl20.1.8. The real BTX object is compiled by clang-cl; cl.exe only compiles/runs the isolated environment component. CMake4.4.5/Ninja1.13.2, Release/C++20/static CRT profile.

The unchanged real root `windows-clangcl-static` preset is configured with tests ON and default Modelnet ON, wallet/SQLite/ZMQ ON, GUI OFF, unchanged manifest/baseline and documented `wallet;tests;zeromq` features. Cached native static OpenSSL3.5.4 and vcpkg port binaries are reused; exact dependency identities are checked. The ephemeral generated build is recreated, not a persistent VM. Final configure passes in94seconds, including port restoration/install.

| Check | Result |
| --- | --- |
| Original generated unit target | FAIL at line24: missing `<unistd.h>` |
| Corrected generated unit target, identical build command and compile database | PASS; object retained and independently rehashed |
| clang-cl /MT exact helper + exact two new in-tree cases | PASS with initially absent and preexisting nonempty variable |
| MSVC cl.exe /MT same component | PASS with both initial states |
| Deliberately omitted destructor restoration | Same assertions reject it; named restoration failures plus independent state-leak check, exit90 |
| macOS original helper + same new cases | PASS with initially absent, nonempty and empty variable |
| macOS final candidate helper + same cases | PASS for those states; helper/case bytes unchanged by later platform correction, so no duplicate run |

Both original and candidate are built with the **same generated target** `src/test/CMakeFiles/test_btx.dir/matmul_backend_capabilities_tests.cpp.obj`, same build tree and command, with unchanged compilation database. Baseline failure is required before installing candidate bytes. Neither Modelnet-OFF nor a reduced test list is used. Compiler warnings remain in raw records; warning-free builds are not claimed.

The two new cases exercise replacement, null removal, nested restoration, and returning to absence. Their runtime execution uses the source-extracted actual helper/case bodies with header-only Boost.Test and an independent caller-state guard; it does not substitute a reimplementation of the environment helper. The mutant must produce a failure in those named assertions, not merely exit nonzero. This is component execution, **not execution of the linked full test_btx suite**. No Metal/GPU computation was run by this campaign.

[Verification](verification.json) checks all26 command log hashes, all14,307 tracked source entries, baseline/candidate catalogs and the single approved delta, actual candidate object/executable hashes, cached dependency identities, root flags and exact extracted helper/cases. [Raw result](run-41761879608/result.json), [compile database](run-41761879608/compile_commands.json), [original compile](run-41761879608/baseline-unit-object.log), [corrected compile](run-41761879608/candidate-unit-object.log), [runtime/mutant logs](run-41761879608/mutant-component-expected-failure.log) and [Mac result](mac/result.json) are retained. Artifact ZIPs are digest-checked on download.

## Earlier incomplete results

- The first local component wrapper put Boost assertions in a global fixture's destructor after framework teardown. Actual cases passed, but the wrapper reported a setup error. Preserved in `mac/pilot-global-fixture/`. Corrected the independent wrapper to compare caller state and exit90 on leakage without using Boost after teardown. No product case was weakened.
- [Native41760698599](run-41760698599/result.json) reproduced the original include failure, but the environment-only candidate then failed on `sysconf(_SC_PAGE_SIZE)` and `posix_memalign` later in the same source. No component runtime ran. This was a real incomplete repair, not a pass. Earlier candidate `4a286b26` and inputs remain under `pilots/environment-only/`; [assessment](pilots/environment-only/assessment.json) records it.
- The initial claim that unistd was unused was incorrect: it supports that later allocation body. The corrected candidate retains the POSIX include/body and bounds the unsupported Windows path. A fresh independent [platform review](review/PLATFORM-CORRECTION.md) preceded the final native run. The same final harness is used; the material candidate change justified the rerun.

## Limits and next step

This closes the measured one-source compile prerequisite. It does not close #356: full native daemon/helper/library linkage, the complete unit target build/run, plain-MSVC project arithmetic, default-suite results, Windows Metal execution, Linux/MinGW execution and release qualification are not established. The Mac result is an environment-component check, not a full Mac object/GPU run. No production validation or backend-acceptance behavior changed. The static triplet/OpenSSL component do not qualify all final project dependency linkage.

Next: retain the verified one-commit repair for a focused #356-related handoff when publication is authorized, then advance the remaining full-native acceptance gate from actual failures rather than repeat this passed component campaign. Existing block100 submission-base and all stop records remain binding. Session2's read-only338 inventory is separate and uses no Windows/build resources. See completion receipt for source/resource release and final review.

## Learning

When a fatal missing header stops compilation, search the entire source for the APIs it supplies before declaring it unused. My first pass traced only environment calls and missed page-size/aligned allocation. The real generated-target gate caught that before publication. Preserve platform-specific test registration, keep valid supported-platform behavior intact, and inspect the final compile rather than equating a component check or green diagnostic workflow with project acceptance. No broader protocol rewrite or recurring campaign is needed; apply the existing whole-file/build-boundary review consistently.
