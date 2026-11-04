# Native Windows Modelnet operation compatibility

**Three generated native targets fail before and compile after; scoped safety controls pass. Full Windows build acceptance remains open.**

Code: `d1d332f4da09baf73ba52a0c548d7468dc03dca9`, one independent three-file commit on accepted `ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629`. Credit: repch1c's Windows inventory and Jpp-matata's process-boundary/contribution guidance. Existing source authorship is retained.

## Behavior and prerequisites

Windows explicitly refuses the existing unsupported fork/exec runners and private Unix operations rather than using fake permission/execute constants. Private PEM writing refuses before file creation/truncation or the writer callback. POSIX behavior and explicit OpenSSL CLI override/fallback are retained. This does not implement a native Windows worker manager or private Unix endpoint backend.

The actual native test tree includes this fix **plus pending #404 at `1b404ed8` and #403 at `ef10c7be`**. The product commit does not include those fixes. Its reconstructed composition matches all 14,309 tracked source entries in the native evidence; tree `1095f4dc811dd9b01106fc4e9f2d11fae1594b71`. PR403's four child descriptor-cleanup sites remain after stdio setup and before exec. Replaying403 over the independent patch has an overlapping runner-declaration context; candidate-helper.cpp is the exact resolved tested file. candidate-helper-standalone.cpp and standalone-candidate.patch contain only our repair. This is not qualification of the independent branch or stock ECD as a complete node.

## Executed results

Native [run41805139945](https://github.com/sunnyriverr/btx/actions/runs/41805139945), CI0abc90adf0b0332a7ac3246dbee127b9d86155e2: Windows2025 AMD64, MSVC toolset14.51.36231, SDK10.0.26100.0. Actual project objects use clang-cl, C++20/static CRT and default Modelnet ON.

| Actual generated target | Baseline | Candidate |
| --- | --- | --- |
| generate.cpp.obj | X_OK compile failure | Compiles |
| pq1_runtime.cpp.obj | popen/pclose compile failure | Compiles |
| helper.cpp.obj | POSIX type/mode compile failures | Compiles |

The same commands and compiler database are used on both sides. Both MSVC and clang-cl pass six-mode, 36-check extracted-function controls; 24 successful native PE marker launches validate the positive executable control. Guard calls produce no subsequent marker, resident entry or private-file/endpoint mutation. Unset/empty/explicit environment cases are preserved. Those controls do not prove daemon-wide absence of filesystem side effects.

Mac baseline and candidate each pass 40 extracted-function controls, including legitimate workers, protocol/cleanup, POSIX executable/private-file/socket cases, and all four403 descriptor-close sites. Real fs/generate/UniValue types and subprocess code are used. Logging is substituted without acceptance assertions; fixture close-range macros are0 and optimized SHA is disabled. No full Mac node or new Linux run is claimed. Native/API component execution is not complete helper/node acceptance or default test-runner coverage.

The candidate-only Modelnet continuation fails after 1,327.91 seconds at bounty_eval.cpp's pid_t/usleep declarations. No node linking, default build or project unit execution follows; #356 remains open. No bounty runtime behavior was investigated. The job is red because of this later build barrier, not failed target pairs. No timeout/resource stop is reported.

## Reproduction entry points

`check_inputs.py` verifies package source/fixture identities without compiling. `source-manifest.json` identifies the exact403+404 baseline and candidate bytes. `runner.py`, `workflow.yml`, dependency-identity.json and fixtures/ preserve the native executed relative layout. The original workflow placed this directory at controls/contrib/devtools/windows-root-configure, checked out immutable404, applied the hash-checked403 baseline, then ran openssl/vcpkg/configure stages. It requires the documented verified native OpenSSL/vcpkg cache; it is not an empty-machine bootstrap. The native distinguishing commands are retained in native/result.json and native/selected-compile-commands.json.

To reconstruct the scoped native behavior fixture with real project headers:

```powershell
python fixtures/native.py SOURCE ROOT EVIDENCE
```

SOURCE is the isolated immutable BTX checkout, ROOT an owned scratch directory, EVIDENCE an existing output directory; native MSVC and clang-cl must already be configured. This invokes the exact retained fixture inputs; it does not substitute for the generated production target comparison. This published layout has input/AST checks; the Windows campaign itself was not repeated for publication.

For the Mac seam, provide an isolated404 checkout at source/ (or a local symlink to that checkout), then use the original relative commands:

```sh
python3 fixtures/generate.py
python3 fixtures/build.py --variant baseline --output fixtures/mac-baseline-build
python3 fixtures/run.py fixtures/mac-baseline-build/controls --output fixtures/mac-baseline
```

Repeat the named variant as candidate for comparison. Exact original build commands/results are under mac/; unnecessary personal paths are replaced and original record hashes retained. The changed run.py publication layout adds native-only positive-executable checks; the unchanged Mac branch was not repeated solely for that addition.

## Provenance and limits

Readable native command/control logs are under native/. verification.json and review/RESULTS.md record 21 checked command logs, six source catalogs and exact baseline restoration. Full catalogs, compile database and three object files remain in the original native artifact, whose digest/metadata are in native/artifacts.json; source-catalog and object checksums are retained here. They are not executable files in this evidence branch. Original artifact retention is 14 days; this branch retains source inputs and readable results. Branch/source assembly identities are in branch-receipt.json.

No full Windows node/unit/LAN, MinGW, GPU, live network or release qualification is claimed. Reuse the passing scoped evidence; repeat only for a relevant source/configuration change or substantive review request.
