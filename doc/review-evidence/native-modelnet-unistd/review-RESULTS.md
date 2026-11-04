# Native Modelnet direct-header repair — final artifact review

**Verdict: PASS for the scoped native component comparison. No additional test or run is needed for this handoff. Full #356 acceptance remains open.**

Reviewed [run 41749124214](https://github.com/sunnyriverr/btx/actions/runs/41749124214), CI `a71c9c963eddbb09ba38858c9bdc4fed699d04fc`, base `2cdff4fc38571df6996d88018bf0ce4d0077b755`. Source/recipe reviews are in DESIGN.md and RECIPE.md. This reviewer read artifacts only; no build, test, runtime, source/Git mutation or network action occurred. Only this reserved result file was written.

## Verified identities

- The downloaded ZIP SHA-256 is `06a6367cb394059ad12a34c6392f15d58642a8393e745943cc9ffb4f6d1e6dff`, equal to the API artifact digest. All 29 extracted files match the ZIP bytes.
- Four variants are present, with no execution errors. Their recorded file maps match the exact source/product manifest: 190 source/test/header hash entries in total. Baseline/candidate share the same test and production closure; only the native header and CMake route differ.
- All 18 named logs match their recorded hashes. Four CMake envelopes and four compile-command files match their hashes. The native compiler commands carry C++20, static CRT (`-MT`), forced accepted adapter, NOMINMAX and the SDK floor. MSVC accepts both slash and hyphen forms of these flags; a reviewer check initially expecting only slash forms was corrected without changing test artifacts.
- Remote-input verification names the reviewed runner `047e8567e051f3f05aa6343e1957515c6976c540fe89532834979642a13719f9`, workflow `89c2038e90b69b99ceb638210f5aaca1d6ae0a24c8b90fda23822974040d667e`, and exact payload.

## Actual paired results

Windows Server 2025 x64, SDK 10.0.26100.0, toolset 14.51.36231; cl 19.51.36260 and clang-cl 20.1.8.

| Case | cl | clang-cl |
| --- | --- | --- |
| Baseline package_execute.cpp | Missing unistd.h at line 18 | Same site/error class |
| Baseline capability_control.cpp | Missing unistd.h at line 21 | Same site/error class |
| Baseline standalone direct-header build | Fails on missing header | Same |
| Candidate real production objects | Both compile | Both compile |
| Candidate direct-header executable | Ten checks pass | Ten checks pass |

Individual baseline diagnostics were inspected, rather than inferred from aggregate failure. Candidate include dependencies show the exact `src/compat/msvc/unistd.h` route; object hash records include both production seeds. Those objects were hashed by the runner but not uploaded, so their bytes are not independently rehashed here.

Both actual executable artifacts are retained and their bytes verify against recorded hashes:

- cl: `96e9c2719282e47aeca8b4f7b5f7032d7e5f1429f4690dcc8066fef0cb6c36ca`
- clang-cl: `de28c6d9f8310b4ef96ff3324e7514eac5a081b2704fc81c1c973d0cd32ff1df`

Runtime logs report exactly `PASS 10 direct-header checks`: environment overwrite/refusal/removal, binary pipe bytes/descriptor cleanup and unsupported fork retaining ENOSYS. This proves the newly reachable accepted adapter route, not new process support.

The candidate clang-cl production log retains ordinary deprecated POSIX-name warnings (write/close/unlink). They are not failures in this component profile and were not silently removed. Do not call this a warning-free or stock-root build. cl `/Bv` returns 2 without an input; that is version-query evidence, not a failed named compile/runtime control.

## Scope and remaining work

The CMake condition/route records show unchanged MinGW and Unix calls, and a native PRIVATE include route. Those are source/CMake evaluations, not native MinGW/Linux/Mac compiler tests.

This qualifies two representative production objects and the direct-header executable in the bounded component envelope. It does not qualify root dependency resolution, complete Modelnet linkage, helper startup, all direct-header callers, the full node, Windows test_btx, or release behavior. OpenSSL provisioning, other unit portability barriers and plain-cl arithmetic remain separate. No product rules or adapter implementations changed.

Product branch packaging and any delivery remain the parent coordinator's responsibility; preserve credit to repch1c for the original #356 report and JPP for complementary coverage. No extra tests or public post are justified by this artifact review alone.
