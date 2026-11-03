# Windows SDK macro repair — tested candidate

**Ready for a focused handoff: `3ddffea282cd403da7e5d2350c8fd8990220eee5`, based on swarm `107efc934847f57ecb16a6b1d204a94eed5d8df2`.** Local product branch: `codex/fix-windows-sdk-macros`. No upstream submission.

## Repair and supported effect

The Windows SDK defines `FAR` and `NEAR` through empty lowercase `far` and `near` macros. BTX removes the lowercase names for legitimate identifiers, leaving SDK expansions broken. Preserve the uppercase aliases at their empty Win32 meaning before that cleanup. Apply the same six-line addition at both existing cleanup sites: `src/compat/compat.h` and `src/compat/mingw/posix_extra.h`. Every other cleanup directive and platform guard remains unchanged.

The third changed file is a standalone Windows regression, `test/util/windows_sdk_macro_tests.cpp`. It reads shell/IP-helper headers after BTX cleanup, asserts uppercase aliases and lowercase identifier behavior, and exercises FD_ZERO/SET/ISSET/CLR through a native executable. It initializes Winsock but opens no socket. The reverse SDK-first include order is also checked. This utility test is not registered in the default core unit-test runner.

Repchic reported the production blocker in issue356; JPP independently confirmed the earlier native failure. The [cause investigation](https://github.com/sunnyriverr/btx/actions/runs/41659525053) and [design review](review/DESIGN.md) explain why simply retaining lowercase macros is unsafe.

## Actual before/after result

[Native Windows run41662413529](https://github.com/sunnyriverr/btx/actions/runs/41662413529), exact qualification commit `776262d40c7140dcef0956996df42d134472285c`. Windows Server2025 x64, SDK10.0.26100.0, cl19.51.36260 / toolset14.51.36231, clang-cl20.1.8.

The same regression source and explicit configuration are used for original and candidate:

| Gate, with each compiler | Original | Candidate |
| --- | --- | --- |
| Late SDK-header regression | compile fails | links and runs successfully |
| SDK-first regression | compile fails | links and runs successfully |
| Exact shim-cleanup-prefix regression | compile fails | links and runs successfully |
| Complete `src/util/sock.cpp` | compile fails | compiles |
| Complete `src/common/args.cpp` | compile fails | compiles |
| Complete `src/common/netif.cpp` | compile fails | compiles |

Once per case; six native regression executables return0. All12 baseline compile failures match the observed macro problem: sock reports unresolved `far` at actual FD calls; args fails in SDK COM declarations; netif fails in `windot11.h` GUID declarations. Candidate compiles contain no errors. Clang warns that `/Zc:preprocessor` is unused; it was supplied but not active for clang. cl and same-compiler contrasts independently establish the result.

The complete production translation units and54 repository source/header inputs are extracted from pinned Git objects. Only the two intended headers differ. The original CMake configuration template is used with a recorded explicit Windows component profile: wallet/modelnet/GUI disabled, relevant Windows definitions and warning settings supplied. This is **not** the root CMake configure or complete documented preset build. There are no dependency stubs or package installations. The test manifest, generated-config hash, all commands and source identities are in `native/decoded/result.json`.

## Review and limits

[Fresh final review](review/FINAL.md) found no material blocker for this native x64 scope. It checks actual primary diagnostics and artifact identities, not just nonzero exits or the job badge. `summary.json`, `native/collection.json`, the original Actions log archive and decoded files preserve the evidence. Native Mac preprocessing of the ordinary non-Windows compatibility header is identical before/after; this is not Linux qualification.

The shim regression deliberately uses its exact SDK/cleanup prefix, stopping before unrelated POSIX wrappers. It does not qualify the complete forced-include shim, MinGW or modelnet. No complete node build/link, mainnet, wallet, validation, GPU or release behavior was tested. No claim is made about repairing the preexisting SDK-first FD_SETSIZE ordering. Standalone identifier checks are controls; a full net_processing build was not run. Source inspection found no existing uppercase FAR/NEAR identifier use in the surveyed exact107 C++ paths.

## Closeout

The tested product commit, patch and regression are retained unchanged. Shared source/index/dirty work are preserved; no runtime node or VM was started. All owned test/review/index resources are released after evidence packaging. Findings remain off upstream under the user's hold. Next useful action is publishing the focused repair with its exact native evidence, rather than repeating the completed campaign.

Learning: preserving SDK aliases and BTX identifiers together produces a smaller repair than renaming unrelated code. Cover both cleanup sites and real production translation units before calling a cross-header fix ready; keep a prefix-only shim check explicitly bounded.


## Reproduce the exact qualification entry point

In a disposable native x64 VS developer shell with Git, CMake, cl and clang-cl available, clear CL/_CL_/LINK and run:

```cmd
python check_repair.py --repo C:\btx --out C:\checks\sdk-new
```

The output directory must not exist and its parent must exist. The repository must contain the pinned BASE and CODE commits named in the script. This is the exact executed runner with closure.json; it extracts pinned source into owned output directories, configures the original header template for its explicit component profile, compiles and runs the standalone tests, and emits logs. Inspect result status and all command outcomes; classify expected baseline errors from the logs. No dependency installation or node start occurs.

SHA256SUMS.json identifies all supplied bytes. Native logs contain disposable hosted-runner paths, not workstation or wallet data. The raw Actions archive remains retained locally; decoded exact logs provide the primary review surface here.
