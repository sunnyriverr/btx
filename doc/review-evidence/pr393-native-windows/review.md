# PR393 native Windows pre-execution review

PASS for the scoped component acceptance experiment. Source review only; no tests, builds, downloads, network actions, product edits or publication by this reviewer.

## Inputs and setup

The workflow is restricted to the dedicated fork CI branch, uses contents:read, a standard windows-2025 runner and a10-minute job bound. It installs no packages and creates no artifact/cache storage. It fetches the workflow commit plus exact basecbf65894, coded1ee21e8 and evidenceeca826d8, uses sparse checkout for its runner directory, then reads other component inputs through immutable Git objects. The native runner verifies published driver/source hashes and refuses non-Windows/non-x64 execution.

The cmd step obtains an x64 VS developer environment with vswhere/VsDevCmd, prepends the preinstalled LLVM path, clears CL/_CL_/LINK overrides, and propagates the Python exit code. The PowerShell fetch and checkout calls check nonzero exits. Tool availability, SDK presence, partial-clone retrieval and exact runner-image behavior remain runtime setup gates, not facts established by source review. The always step prints diagnostics and does not itself override the native test step's failed conclusion.

## Experiment and oracle

Seven real backend-stub translation units and the existing published driver are compiled with the same clang-cl profile for both revisions. Each object must report native x64 COFF. The baseline must fail direct and whole-archive linking with exactly the nine CUDA/Metal/HIP duplicate definitions; the checks inspect each expected function/vendor name rather than treating any linker failure as the reproduction. Candidate direct, whole-archive and ordinary-archive links must succeed and execute the driver's12 dispatcher entry points and selected backend surfaces. No duplicate-tolerance flag appears.

The published DRIVER was source-read from evidenceeca826d8. Its default TEST_CUDA/TEST_METAL/TEST_HIP flags are0, so it verifies disabled-backend fallback selection, output behavior and Ascend fallback retention. The candidate's full diff is five files; runtime change is generic stub ownership with adjacent comment changes. This native test does not cover enabled GPU providers, the whole node or all CMake profiles. Ordinary-archive baseline is not run; do not claim it failed.

## Result boundary

No blocker to the first bounded native run. Keep setup failures separate from the expected duplicate-symbol baseline, and inspect the retained result/logs before claiming fail-before/pass-after. Success will establish native Windows clang-cl/CRT/COFF component behavior, not full executable or release qualification.

Fingerprints reviewed:

- Native runner SHA256: 10b995f78d4ac910a708367ca262b8dde339f4a557d39af6ac32e100e26e2019
- Workflow SHA256: a031d09e72fdced3246d3327254064f1d39e6bdac363207e3861d7d973fe0601


## Final native evidence review

**PASS.** Reviewed the retained run/job metadata, raw log archive identity, decoded result and compile/COFF/link/runtime logs. This reviewer performed artifact/source checks only and did not execute another test or make network/publication changes.

Run: https://github.com/sunnyriverr/btx/actions/runs/41646082764, workflow commit22373c44035249ad74fd5a39e718a9d3c1298aba, attempt1. The single job and every setup/test/diagnostic step completed successfully. Recorded host is Windows Server2025 build10.0.26100, native x64 target; clang-cl/LLD20.1.8, SDK10.0.26100.0 and MSVC tools14.51.36231. Tool binary digests are retained in decoded/result.json.

The45command results have exactly two nonzero exits: source-direct-link and source-whole-link. Both variants compile all seven real stub TUs plus the driver; all16object-header logs identify COFF-x86-64. Each baseline link log contains exactly the nine expected CUDA/Metal/HIP duplicate definitions. These are the demonstrated defect, not a setup/compile failure. Candidate direct, whole-archive and ordinary-archive links each exit0; all three executables exit0 and print the12dispatcher/output/vendor-surface PASS marker. Executable hashes are recorded. The same extracted driver and compiler profile are used on both sides.

The executed runner SHA25632f61177dd2891fb7468971f9c9039d046d3000f92418424e644d54ffcdf3652 differs from its committed LF blob SHA25610b995f78d4ac910a708367ca262b8dde339f4a557d39af6ac32e100e26e2019. Independently hashing the exact Git blob after LF-to-CRLF conversion reproduces the executed hash. This is accounted-for checkout normalization, not an unexplained script change. Production source blobs are read through git show, checked against their published hashes and written as bytes by the runner; CRLF checkout conversion does not change them.

Raw logs.zip SHA256bf5762f30999960ead5c036cf30c60c2f1c89c848d01e2bbb7052c78cb107b68 independently matches summary.json. Decoded files remove Actions timestamp prefixes and are derivative records; raw bytes remain available.

This closes the native Windows clang-cl/CRT/COFF **disabled-backend component** gate. It does not establish a full btxd build/link, whole CMake profile, enabled CUDA/Metal/HIP provider, GPU computation, all Windows compilers, runtime validation or release readiness. Baseline ordinary-archive linking was not run, so only baseline direct/whole links may be described as failing. The executable marker covers the driver's12dispatcher calls plus its selected disabled-backend surfaces, not twelve independent full-system tests. No further repetition is justified by the retained result alone.
