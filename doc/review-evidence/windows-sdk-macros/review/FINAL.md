# Windows SDK repair — final artifact review

Material blockers: **none found within the reviewed native x64 component scope**. Verdict: **PASS, scope qualified**. The patch is a coherent, small repair of the observed SDK macro expansion failure while preserving lowercase `near` and `far` as BTX identifiers. This is an independent artifact/code review, not a second native execution.

Reviewed by delegated agent `sdk_repair_final_review` for BTX test 1 (2). Only this review output was written. No tests, builds, API requests, source mutations, runtime or publication were performed; the review reservation can be released. Shared records and publication remain with the parent/coordinator.

## Repair correctness

`fix.patch` changes exactly the two production cleanup sites, `src/compat/compat.h` and `src/compat/mingw/posix_extra.h`, plus a standalone regression source. Each site replaces the uppercase `FAR` and `NEAR` definitions with empty replacement lists before the existing lowercase cleanup. Thus SDK declarations and deferred SDK macros no longer expand through the removed lowercase tokens. The lowercase cleanup remains intact. The duplicated boundary is repaired consistently; no policy, validation, consensus, networking behavior or other production logic is changed in the supplied patch.

The standalone test rejects both lowercase macro names, requires both uppercase macros to stringify to an empty expansion, checks pointer-type equivalence, and uses lowercase names as local identifiers. It also exercises real SDK FD-set macros through startup, empty/set/present/clear/absent bookkeeping and returns a failing status on an unexpected result. No socket is opened. This distinguishes plausible incomplete repairs: retaining lowercase macros fails the namespace check; removing uppercase macros fails the expansion/type checks; repairing only `FAR` fails the `NEAR` check. Both normal late SDK inclusion and SDK-first inclusion use the same test bytes.

## Actual native results and diagnostic attribution

The collected result names baseline `107efc934847f57ecb16a6b1d204a94eed5d8df2`, candidate `3ddffea282cd403da7e5d2350c8fd8990220eee5`, Windows Server 2025 x64, SDK `10.0.26100.0`, MSVC toolset `14.51.36231` (`cl` reports `19.51.36260`), and clang-cl `20.1.8` targeting `x86_64-pc-windows-msvc`. Collection identifies run `41662413529`; preparation identifies CI commit `776262d40c7140dcef0956996df42d134472285c`.

All 33 recorded commands are accounted for: one component configuration, two compiler-version observations, 12 expected baseline compile failures, 12 successful candidate compiles, and six successful candidate executable runs. Version observations have `expected_ok: null`; they are not test controls. Every candidate executable exits zero. The three production sources are passed directly and completely to `/c` under both compilers, rather than replaced with reduced function excerpts.

| Case | Baseline primary evidence | Candidate evidence |
| --- | --- | --- |
| Standalone, late SDK | Both compilers first fail in SDK `combaseapi.h:385`; clang-cl shows `LPMALLOC FAR * ppMalloc` at the failing declaration. | Compiles, links against `Ws2_32.lib`, runs with exit 0 under both compilers. |
| Standalone, SDK first | Both empty-expansion assertions fail. clang-cl explicitly reports `sizeof("far") == 1` and `sizeof("near") == 1` as false; subsequent FD-macro diagnostics expand `FAR` to `far` in `minwindef.h:150`. | Same assertions, lowercase identifier control and FD bookkeeping pass under both compilers. |
| Exact shim cleanup prefix | Same uppercase assertions and FD-macro failure as SDK-first; the prefix is taken from each revision's real shim before `<csignal>`. | Compiles and runs with exit 0 under both compilers. |
| Complete `src/util/sock.cpp` | First failure at line 201, `FD_ZERO(&recv)`; clang-cl traces `winsock2.h:173` through `FAR` to the residual `far` token. | Object compilation succeeds under both compilers. |
| Complete `src/common/args.cpp` | First failure in SDK `combaseapi.h:385`, reached through `args.cpp:25` and `shlobj.h`; the displayed declaration contains `FAR`. | Object compilation succeeds under both compilers. |
| Complete `src/common/netif.cpp` | First failure at SDK `windot11.h:2538`, `DEFINE_NWF_GUID(GUID_NWF_OFFLOAD_CAPABILITY,0)`, reached through `netif.cpp:26`, `iphlpapi.h`, `netioapi.h` and `ntddndis.h`. | Object compilation succeeds under both compilers. |

The netif log does not print that GUID macro's full expansion: attribution to the repaired macro boundary is supported by the controlled two-header delta and successful same-profile candidate, not by a displayed expansion trace in that particular log. Do not describe its primary error as an FD or COM declaration error. Baseline cascades and error-limit termination are consequences, not additional candidate failures.

All candidate `cl` compile logs contain only the input filename. Every candidate clang-cl compile log contains only the warning that `/Zc:preprocessor` is unused; this same warning is present before the repair. It does not report a source or SDK diagnostic, and the successful compiles/runs supply the relevant valid controls. Candidate run logs and component-configuration log are empty, with exit zero recorded. No unexplained failing valid control remains in this matrix.

## Evidence identity

Recomputed SHA-256 values for all 34 decoded files match `native/collection.json`, including `result.json`. Local `check_repair.py`, `native-repair.yml` and `closure.json` hashes match the exact values in `native/preparation.json`; the runner hash also matches native `result.json`. The regression reconstructed from the new-file hunk hashes to `97515230124558be7b46b2b668b287daac8d9514edd9c8093ea3bdffe14bb3ba`, matching both product and native result.

Every recorded baseline source hash matches the closure manifest. The only before/after source-hash differences are the two compatibility headers, and their candidate hashes match `product.json`. All three production TU hashes and the original configuration-template hash remain equal across variants. The runner obtains revision-pinned Git blobs into separate output roots and uses one candidate regression file for both variants. It does not edit production TUs or inject a synthetic replacement compatibility header into those TU compiles.

These checks establish internal identity across the supplied patch, manifests, runner and decoded results. The live Actions envelope, raw-log archive hash, full Git objects and remote commit tree were outside this review's allowed inputs; run/CI-commit association relies on the supplied collection/preparation receipts rather than a fresh API verification.

## Boundaries and remaining blind spots

- Configuration uses CMake `configure_file` on the original pinned template with explicitly recorded Windows component variables. Modelnet, wallet and GUI are disabled in the declared profile. This is not a root project configure, production node link, full node build, installer or runtime acceptance result.
- The shim case tests the exact cleanup prefix ending before `<csignal>`, with only its closing preprocessor guards appended. The rest of `posix_extra.h`, its later interaction with other headers, MinGW, full modelnet and combined main-header/shim include orders are not qualified. The prefix regression deliberately does not include the late shell/IP headers from the main standalone test.
- Native evidence covers this x64 SDK/toolchain pair. The non-Windows receipt establishes equal main-header preprocessing hashes on macOS only; it does not establish non-Windows compilation or invariance of the complete shim.
- Expected baseline failures are recognized by nonzero status in the runner, rather than an automated diagnostic signature. Manual inspection above establishes that the observed failures are relevant to this repair; future runs should retain diagnostic review before treating that status as sufficient evidence.
- The standalone regression is an explicit compile/run utility, not evidence that an ordinary root build or test target automatically executes it.

No extra execution is needed to accept the narrow repair claim supported here. A later full shim/MinGW or node-build claim requires its own relevant evidence. Preserve the task's no-upstream-publication hold until the parent receives applicable authority.
