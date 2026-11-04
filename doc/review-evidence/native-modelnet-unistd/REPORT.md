# Native Modelnet direct-header prerequisite — scoped PASS

**Both native compilers fail on the accepted baseline and compile the same two production files with the candidate. Ten direct-header runtime controls pass per compiler. Full #356 qualification remains outstanding.**

## Code and credit

Local branch `codex/fix-native-modelnet-unistd` at `487a69f035190526793c2b3dec6df9e0110b9fc3`, parent `2cdff4fc38571df6996d88018bf0ce4d0077b755`. Exactly three files change: a native-only forwarding header, three CMake lines inside the existing WIN32/MSVC branch, and the standalone direct-header regression/control source. Shared worktree, HEAD, real index and staged/dirty content remain unchanged; the isolated index was removed. See `branch-receipt.json`.

`src/compat/msvc/unistd.h` includes the accepted `compat/mingw/posix_extra.h`. The new BEFORE include path is PRIVATE to native `bitcoin_modelnet` compilation. No functions or emulation are added; the existing adapter is byte-identical. MinGW/Unix CMake call streams remain identical in local route evaluation. That is a source/CMake control, not a new native MinGW/Unix run. Core, test_btx and separate helper targets are not given the new include directory by this repair.

Original missing-header finding: repch1c in #356. Jpp-matata's build/testing coordination and complementary results informed the acceptance scope. Existing adapter authorship remains in the parent history; no unsupported co-authorship is added.

## Verified native results

[Windows run 41749124214](https://github.com/sunnyriverr/btx/actions/runs/41749124214), CI `a71c9c963eddbb09ba38858c9bdc4fed699d04fc`: Windows Server 2025 x64, SDK 10.0.26100.0, toolset 14.51.36231, cl 19.51.36260 and clang-cl 20.1.8. The clang-cl production builds retain ordinary deprecated CRT-name warnings; warning-free compilation is not claimed. Bounded Ninja/CMake Release component project, C++20, static CRT `-MT`, matching WIN32/NOMINMAX/SDK-floor definitions and the exact accepted/candidate Modelnet WIN32 CMake blocks. It does not configure the stock root.

| Same input/control | MSVC cl | clang-cl |
| --- | --- | --- |
| Baseline package_execute.cpp:18 | Missing unistd.h | Missing unistd.h |
| Baseline capability_control.cpp:21 | Missing unistd.h | Missing unistd.h |
| Candidate production objects | Both compile | Both compile |
| Candidate direct-header executable | 10 checks pass | 10 checks pass |

The standalone control reaches the exact new header and exercises CRT environment set/overwrite/no-overwrite/removal, binary pipe byte preservation and descriptor cleanup, and unchanged `fork` ENOSYS refusal. No process is spawned. There are no injected stubs or modified production sources: 46 actual repository source/header inputs plus the candidate adapter and same standalone control are hash-checked across four variants. The test is not registered as a `test_btx` case.

All three remote CI inputs match local bytes. The artifact ZIP SHA-256 equals the API digest `06a6367cb394059ad12a34c6392f15d58642a8393e745943cc9ffb4f6d1e6dff`. All 18 recorded command logs and 190 source-copy hashes are checked. Both native executable bytes match their recorded hashes. Production object hashes were recorded by the runner; object files were not uploaded. Compile commands confirm CRT/standard/forced include; Ninja dependencies resolve the exact native forwarding header. See `artifact-verification.json`, `result.json`, `closure.json`, compiler logs and compile-command records.

The cl version-only `/Bv` query exits 2 without an input; it is metadata, not a failing compile. The actual named configure/object/header/runtime controls determine the verdict. An initial local `cmake` lookup was absent from the shell PATH; using the existing absolute path completed the same route checks. No product repair was based on that setup failure.

## Scope and remaining work

This repairs one real native inclusion prerequisite. It does not qualify the complete Modelnet library, helper startup, full node link, root build, OpenSSL provisioning, `test_btx`, MinGW/Unix execution, GPU, validation or release behavior. Private include scope intentionally does not assert that other targets' direct POSIX includes are fixed. Known unit environment/Metal allocation and SDK OPAQUE barriers, OpenSSL 3.5+ dependency setup, and plain-cl arithmetic limitations remain.

The public ownership check found no matching fix or current full native result; private work is unknown. JPP's completed Windows MinGW runtime work was reused. Only this new repair's before/after and valid route controls ran; no earlier campaign was repeated. The CI branch is on Sunny's fork; the product branch is local. No upstream PR, issue or comment was created.

Independent source, recipe and final artifact reviews PASS in `../review/`. The branch and evidence are ready for a focused #356 handoff. No further test is needed for this scoped result absent a material change. Full native acceptance requires the remaining prerequisites and then a stock-root build/unit report on the accepted head.

## Learning

Distinguish adapting a forced header from resolving later direct system-header includes. Reusing the accepted adapter at a narrowly owned target boundary avoids duplicating emulation or masking unsupported process behavior. Representative real source compilation is more useful here than another unchanged full-build attempt.
