# Windows capability runtime compiler repair

**Cached project-generated compiler command fails before/passes after; scoped native CPU/refusal controls pass. Full Windows node linking and test_btx remain outstanding.**

Code `362c36b2fda0f73741c06c4bcb090153fea38a08`, one commit/one file/23 added lines on accepted `666673a3153225ba264c7870e0e82e354df86765`. Credit: repch1c and Jpp-matata for the native Windows audit and review guidance; upstream runtime authorship/copyright are preserved.

## Behavior

POSIX-only probes and resident-loader process APIs no longer prevent native Windows compilation. Windows accelerated paths return NOT_RUN; the common CPU fixture still loads, sleeps, refuses remap-only readiness and rebuilds readiness. No PID alias, replacement process launcher or fake device success is added. Typed-parameter authority, ABI, operator-env/path and missing-weights checks remain active. POSIX-selected code is identical except a blank line, including its nofollow/exclusive file creation and child-process checks. This changes no validation or MatMul acceptance rules.

## Executed evidence

| Check | Result |
| --- | --- |
| Exact cached project-generated clang-cl command | Before:7 errors for pid_t/popen/pclose/STDOUT_FILENO, exit1. After:object produced, exit0. |
| Windows clang-cl component | 37/37 pass, no build warnings. |
| Windows MSVC component | 37/37 pass, no build warnings. |
| Mac component | Same final controls:29/29 before and after, identical output, no build warnings. |

The compiler pair is [run41961409519](https://github.com/sunnyriverr/btx/actions/runs/41961409519), immutable controls [`0979920b`](https://github.com/sunnyriverr/btx/tree/0979920ba88245442bb163f0e618bef0bbf1034a/contrib/devtools/windows-root-configure). It validated10,094 cache files and5,897 compile entries, then directly executed the exact cached compile_commands entry in its original directory. Only capability_runtime.cpp changed; generated headers/build metadata stayed fixed; source and the originally absent target were restored; the project cache was not overwritten. This is a compiler-command pair, **not a successful Ninja target build, full link or clean full build**. Root Release/static-CRT profile had Modelnet, wallet, tests and ZMQ ON; GUI OFF. The remaining candidate warning is the preexisting unused /Zc:preprocessor driver option.

That workflow subsequently failed in the standalone harness linker because the harness omitted the real package_pjson.cpp dependency. `native/initial-harness-link-failure.log` preserves it. Linking that actual source resolved the harness issue; product code and control assertions did not change. **The passed compiler pair was not repeated.** The final components-only [run41962074104](https://github.com/sunnyriverr/btx/actions/runs/41962074104), immutable controls [`7eba54ae`](https://github.com/sunnyriverr/btx/tree/7eba54ae76ff48be59af40fa36cad61d04332cf7/contrib/devtools/windows-root-configure), passed with both compilers.

Native host: Windows Server2025/x64, clang-cl20.1.8, MSVC toolset14.51.36231, SDK10.0.26100.0. The compiler pair used the original20261030.294.1 hosted image; the component run used20261103.298.1 with matching compiler binary hashes. Cross-image full-node cache reuse is not qualified. Earlier precompile setup refusals involved a cache-profile mismatch, overstrict original-profile rejection and a version-header prerequisite; no product compilation occurred in those attempts.

Controls execute actual runtime, SHA-384 smoke/digest, JSON, types and package code. **Only lease randomness is a deterministic test fixture.** They cover CPU readiness and preserved weights, sleep/remap/wake state, unknown leases/missing weights, empty bytes, ABI/runtime/backend and typed-authority refusals, required operator environment, and accelerated refusal even with an existing operator executable. All29 common controls match Mac output. Mac project dependency closure:40 files match exact666; native11 product C++ modules match that base. These assertions follow maintained JIT-RUN cases, but the maintained test_btx suite was not invoked.

## Entry point

Read `source-manifest.json`, `fix.patch`, `native/compiler/compile-command.json`, `native/compiler/pair.json`, the before/after logs and `native/{clang-cl,cl}/`. `verification.json` records the aggregate qualification; binary hashes were captured before execution, and final hosted executables/objects were removed afterward. Original immutable CI inputs retain the cache-based compiler recipe; its full catalogs/archive are also retained locally. This branch contains readable logs and controls beyond CI artifact retention, not a fresh-machine dependency bootstrap.

From this evidence directory:

```sh
python3 check_inputs.py /absolute/path/to/exact/362c36b2/checkout
python3 component.py /absolute/path/to/exact/362c36b2/checkout /absolute/owned/output candidate
```

The first command checks packaged hashes and the exact product checkout. The second uses the preserved executed component interface with the published candidate.cpp, actual source dependencies and caller-owned output. On a configured native Windows developer prompt use `python component.py SOURCE OWNED_OUTPUT candidate clang-cl` or `cl`. On Mac the default compiler is clang++; baseline controls use the same interface with `baseline`. The published directory itself was not rerun on native hardware; executed inputs/commands and their hashes are retained. Modified candidate experiments must update the copied candidate input rather than assume this frozen evidence tests unrelated code. Personal Mac paths were redacted in published metadata, with original hashes retained.

## Limits and next decision

This establishes the compiler repair and scoped CPU/refusal controls. It does not establish full btxd linking, full native test_btx, Windows11, native Linux, live POSIX CUDA loading, real GPU admission, mainnet or release qualification. Issue356 remains open for the full native Windows build and unit run. Review/integrate this focused prerequisite, then continue that integrated gate on the accepted tree.
