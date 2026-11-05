# Native Windows worker resource accounting

**Five identical injected-refusal assertions fail on accepted `666673a3` and pass with `b2a68c64`; ordinary native workers and same-process recovery pass.** Windows Server 2025 x64/build 26100, MSVC 14.51.36231, standalone real backend/wrapper component. This is not a reproduced real resource-exhaustion or live-network failure.

Product `b2a68c64e64589522b6ba560744961d9f71d9149`, tree `116d9521a68d908f101593780284928cb680bb7e`, one commit/six files on `666673a3153225ba264c7870e0e82e354df86765`. [Code](https://github.com/sunnyriverr/btx/tree/b2a68c64e64589522b6ba560744961d9f71d9149); [maintainer request](https://github.com/btxchain/btx/issues/338#issuecomment-6636456097). Credit to repch1c/JPP for the Windows inventory and Numair for the native accounting direction; existing source authorship is retained.

## Behavior and evidence

The parent samples staged logical bytes through metadata-only file-ID handles and sums Job user+kernel CPU. It retains AppContainer/Job/handle/environment restrictions, OS user-time/memory/process limits, the existing input-plus-64 MiB live output allowance and final input/output verification. Bounded heap traversal avoids recursive 64 KiB stack buffers. One incomplete-pass retry retains the original clocks; inability to account refuses rather than counting partial/failed observations as zero. Only the invocation Job is stopped before explicit cleanup; no outputs are published on refusal.

| Case | Accepted source | Candidate |
| --- | --- | --- |
| Synthetic kernel-only CPU excess, tree total, Job-query failure, post-exit CPU excess, clock-query failure | Real ordinary worker succeeds; SAME rejection assertion fails | Expected refusal; real worker start/exit, no fresh outputs and staged-root cleanup observed |
| Fresh ordinary call after each refusal | No refusal to recover from | Same parent process succeeds with exact output, immutable inputs and cleanup |
| Uninstrumented ordinary worker | Passes | Passes: exclusive writing, rename/delete, exact 1 MiB output exceeding input-only cap; ordinary exit 7 preserved |
| Actual scanner boundary | New private helper absent | Real 8-byte file: cap 7 refuses/cap 8 passes; repeated same-instance sampling/interruption/recovery/removal pass |
| Actual policy helpers | New helpers absent | Envelope equality/overflow, user+kernel boundaries and invalid counters pass |

[Result](native/result.json), [commands](native/commands.json), [source/binary identities](native/identities.json), [artifact hashes](native/collection.json). Seventeen groups are one complete final campaign, not independent platform repetitions. Four binaries are hashed before/after. Expected baseline assertion failures are interpreted by the runner; aggregate native job passes.

## Executed reviewer entry point

[Native run 41968226148](https://github.com/sunnyriverr/btx/actions/runs/41968226148), immutable [CI commit](https://github.com/sunnyriverr/btx/tree/0ac8240aa154da353dc032a2aae9ff3f10bbf19d). In an x64 Visual Studio developer prompt with Python 3, from that checkout root:

```bat
set "CL="
set "_CL_="
python test/util/native_qualification/run_windows_accounting_tests.py --baseline-tree contrib/devtools/windows-resource-accounting/baseline --manifest contrib/devtools/windows-resource-accounting/inputs.json
```

This exact in-tree command was executed. The CI commit retains the accepted before source and manifest; [workflow](executed-workflow.yml) shows the executed setup. Root-derived C++20/Release/static-CRT flags link actual backend/wrappers/SHA384, without full Modelnet/node libraries, forced headers or a peer cache. No project dependency downloads are needed. From the product checkout alone, omitting the two optional arguments runs candidate checks without the baseline comparison. That shortened invocation is the documented interface, not an additional publication-time run.

## Fault injection and final-exit path

Negative cases use private `BTX_WINDOWS_ACCOUNTING_TEST` providers. Real APIs still execute; providers then replace selected accounting observations after the real finite worker starts. They do not enlarge its workload, shadow termination/cleanup APIs or add runtime/environment switches to production. The separate uninstrumented candidate omits the provider definition. Real CPU/disk quota violations were not reproduced.

The final trace records `completion_poll=1 process_signaled=1 job_query=1 active_processes=1`. Both the supervisor's actual completion poll and independently captured process handle prove the exit path. The Job count is diagnostic, not an exit oracle. Post-exit CPU refusal suppresses outputs and the same process then recovers normally.

Prior [run 41967700892](https://github.com/sunnyriverr/btx/actions/runs/41967700892) failed because its final-CPU provider never injected under an ActiveProcesses == 0 requirement; [failed trace](prior/final-cpu.log) and [aggregate](prior/result.json) are retained. The old log does not record that count or establish a Windows timing/handle cause. The corrected test requires the explicit completion poll plus signaled handle; it does not weaken the refusal assertion. Test-guarded observation plumbing changed, with non-test accounting behavior unchanged. Final comparison uses the same final fixture before/after.

## Limits

Windows 11 and full node/test_btx verification remain needed. This does not close #356 or qualify a release. Other compilers/filesystems, actual system sleep/wall-expiry, real model/full CLI-manifest, arbitrary directory churn/ancestor replacement/file-ID reuse and every filesystem error are unverified. There is no filesystem-name allowlist or unsafe pathname fallback; refusing unavailable accounting may limit unsupported profiles.

Sampling is logical size, not an atomic snapshot or physical disk quota. Requested 100 ms waits and bounded walks are not a hard deadline under synchronous-I/O/scheduling delays. Normal and injected-refusal cleanup passed; no new matching btx.native package directories remain and original fixture roots were removed. This is not registry-wide enumeration or recovery from actual termination/cleanup API failures. If exit cannot be confirmed, the source-reviewed STOP fallback deliberately defers deletion; it was not exercised as a successful cleanup case.

One existing backend C4267 conversion warning remains in baseline/candidate; no new warning appears. No native Mac/Linux rerun is claimed. Binary hashes are identities, not reproducible-build claims; no executables are packaged. Source manifest, identity.json, product.patch and MANIFEST.json bind this evidence. Native CI paths are retained to identify commands; no operator secrets/wallets are included.
