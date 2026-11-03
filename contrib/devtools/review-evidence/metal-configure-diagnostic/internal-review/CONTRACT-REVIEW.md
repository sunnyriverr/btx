# Metal configure diagnostic — independent source and contract review

Verdict: recommend a tiny default-language Metal compile **and** metallib link probe, fatal only inside the existing selected-precompilation branch. Keep the optional Metal 4 probe nonfatal and retain both runtime-compilation fallbacks. This is a source recommendation, not a tested implementation or native toolchain result.

Owner: BTX test 1 delegated reviewer `/root/metal_configure_review`. Only this `review/` directory was reserved. No product files, shared records, Git index/ref, build cache, VM, GPU, node or external service were changed. No compiler, CMake configure, test or toolchain command ran.

## Exact inputs and coverage

- Current target: `cbf65894e6d61084527cd93e913a00c6794418dd` (`btx-035/swarm`). `src/CMakeLists.txt` blob `2c0154c7a6ccb86b5a3550564a46e216313e0dfb`.
- PR #344 head: `7e26d77b82cc6ae1719e67ac5d6d4224426666cf`; `src/CMakeLists.txt` blob `d67a41f638444aed4436fb62d15949e4a94c2340`. Its last commit changes only `README.md` and `doc/build-osx.md`.
- Shared immutable Git objects were read from `toolchain-2026-10-31/source`; its mutable checkout was not used as the source identity or changed.
- Local fresh `pr344.json` and `comments.json` were read. repch1c's [comment 6542655967](https://github.com/btxchain/btx/pull/344#issuecomment-6542655967) reports macOS 26.6.2 / Apple M4 / CLT only: discovery of `metal` fails, configure accepts Metal ON, then a mandatory `metal -c` build command fails. That is another contributor's native report, not our reproduction. The coordinator owns fresh ownership/open-PR coverage investigation.
- The complete `if(APPLE AND BTX_ENABLE_METAL)` block through its stubs is byte-identical between the two revisions: 14,628 bytes, SHA-256 `880da3079644af0e89a94b64e6842815c78ce4b63999c983619b39903aa21f15`. The surrounding current libomp section **does** differ; do not run the older tree and call it current-swarm qualification.

## Reachability and preserved behavior

All line numbers below refer to the immutable current target.

1. `src/CMakeLists.txt:10–11,67` defaults Metal ON only for Apple. The implementation enters at line 1119 only for `APPLE AND BTX_ENABLE_METAL`; Objective-C++ and Apple-framework checks happen before the tool block. Metal OFF/non-Apple must not invoke the new probe. The separate dual-Metal/CUDA provider refusal at 1114–1117 is unrelated.
2. Lines 1192–1194 declare `BTX_MATMUL_METAL_PRECOMPILE_KERNELS` default ON, find `BTX_XCRUN_EXECUTABLE`, then select precompilation only when both are true. Finding the dispatcher says nothing about its `metal` or `metallib` utilities.
3. Lines 1211–1267 add six unconditional basic compile/link custom commands. They run `xcrun -sdk macosx metal -c ...` with the default language version, then `xcrun -sdk macosx metallib ...`. The backend depends on all six at 1333; these are not optional Metal 4 commands.
4. Lines 1275–1287 write a trivial kernel and try `metal -std=metal4.0`. Failure at 1330–1331 only prints a status; success adds three optional TensorOps libraries/definitions. Basic tool absence currently falls into the same harmless-looking status as unsupported Metal 4, while required basic commands remain scheduled.
5. Lines 1343–1348 explicitly preserve inline runtime compilation when `xcrun` is absent or precompilation is OFF. Making dispatcher absence fatal, moving a new fatal check above this branch, or requiring Xcode whenever Metal is ON would change supported behavior.
6. Runtime fallback is real source behavior: `src/metal/matmul_accel.mm:1407–1431` and `src/metal/matmul_v4_accel.mm:625–650` try libraries then inline source. The latter's optional TensorOps path at 694–736 can decline unsupported Metal 4 and retain the integer ALU path. This review does not demonstrate runtime availability or GPU correctness.

## Recommended minimal design

Inside `if(BTX_MATMUL_METAL_PRECOMPILE_KERNELS AND BTX_XCRUN_EXECUTABLE)`, before registering required commands, move/reuse the existing trivial kernel source creation. Run two sequential `execute_process` operations matching the required commands' SDK/flags:

1. `"${BTX_XCRUN_EXECUTABLE}" -sdk macosx metal -c <probe.metal> -o <basic-probe.air>` — **no** Metal 4 language flag.
2. On compile success, `"${BTX_XCRUN_EXECUTABLE}" -sdk macosx metallib <basic-probe.air> -o <basic-probe.metallib>`.

Use files in `CMAKE_CURRENT_BINARY_DIR` with distinct basic-probe output names, quoted paths, and remove prior basic-probe outputs before trying. A successful stage must produce its expected output; otherwise an old artifact or a deficient test shim can mask failure. Run the probe each configure rather than cache a success across changes to selected developer tools. Keep both existing build-command invocations and the existing optional `-std=metal4.0` probe unchanged in meaning.

Give each operation a finite timeout (for example 30 seconds), record its actual result and diagnostic, and reject every result except the success string `"0"`, including launch failures/timeouts. On failure emit a bounded `FATAL_ERROR` naming **basic Metal compilation** or **metallib linking**, that precompilation is ON, the failed stage/result, and a short tool diagnostic (for example first 2 KiB, with truncation indicated). A generic nonzero error is insufficient. Do not silently switch the selected build to runtime compilation.

The hint should direct users to `doc/build-osx.md` for full Xcode/Metal-toolchain setup, and identify `-DBTX_MATMUL_METAL_PRECOMPILE_KERNELS=OFF` as the explicit runtime-compilation choice. Keep that choice's dependency on runtime compiler service clear; do not imply release packaging, launchd operation or GPU readiness is qualified. No install/download, Xcode selection, SDK policy change or environment mutation belongs in configure. Current target docs predate #344's new setup prose; a small associated docs note must be coherent with whichever docs revision is actually submitted.

### Why not only lookup or version output?

`xcrun -sdk macosx --find metal` plus `--find metallib` is the smallest lookup-only check and catches the reported absent utility. Checking only `metal` misses an independently missing `metallib`. Even checking both paths proves discovery, not that the selected utilities can compile and link with the same SDK used by the required build commands. The #344 docs also distinguish missing downloadable Metal-toolchain execution failures from ordinary path setup; this review has not independently established every Apple stub arrangement. A tiny compile/link probe directly checks the capability being required without guessing supported version flags or requiring Metal 4. It still does not prove every production kernel compiles, full target linkage, packaging or runtime service availability.

## Smallest discriminating observation/control contract

No checks below have been executed by this reviewer. Preserve exact source, probe bytes, command/configuration, selected tools/SDK and logs for each future result. Keep all unrelated prerequisites identical between baseline and candidate. Current AppleClang libomp and framework/language gates can fail before Metal: if they do, classify prerequisite failure rather than claiming this diagnostic works. Any explicit local-only serial-prover option must be identical and disclosed, never silently introduced into a release qualification.

| Case | Required observation | What it distinguishes |
| --- | --- | --- |
| Actual CLT-only environment, `xcrun` present, basic Metal unavailable, precompile ON | Establish actual utility failure. Baseline reaches the Metal block and accepts configuration; candidate stops **during configure** with the basic compile stage and actionable hint, before accepting a required-kernel build. Attribute existing third-party report separately if baseline cannot be reproduced. | A native missing-tool diagnostic, rather than unrelated dependency failure or an arbitrary nonzero configure. |
| Same unavailable basic tool, precompile OFF | Configure reaches the existing OFF fallback status; no new basic probe, optional Metal 4 probe or required metallib targets. | A misplaced unconditional fatal check. Runtime execution need not be attempted. |
| Dispatcher genuinely not found in the tool-selection contract, precompile ON | Existing no-xcrun fallback remains selected; no new probe/required metallib targets. | A new accidental requirement for `xcrun`. Use a narrowly isolated branch fixture if native Apple tools cannot be hidden without breaking unrelated compiler discovery, and label it component coverage. |
| Basic compile and link available, Metal 4 unsupported | Basic probe produces fresh AIR/library, configure succeeds, six basic dependencies remain present, optional Metal 4 failure retains its existing status and contributes no optional Metal 4 definitions/targets. | A guard that incorrectly requires Metal 4 or disables all precompilation after optional failure. Controlled dispatcher coverage is acceptable if labeled as such; it is not native Apple integration. |

Add one cheap adversarial **link-failure** variant to the last controlled case: basic `metal` compile succeeds but `metallib` fails; candidate must fail configure specifically at linking. It catches the realistic broken implementation that only tests compilation or lookup of `metal`, which could pass the CLT case and all four broad behavior rows. A recording dispatcher control must verify the actual invocation order/SDK/default language and create fresh expected outputs; a script returning success for every command is not a valid healthy control. No full native build, GPU workload or broad matrix is required merely to decide this configure guard.

## Handoff and limits

Source/contract gate is ready for the coordinator to choose a bounded implementation and actual observation after resource readiness. No product patch, native proof, package entry-point execution or publication is supplied here. The initial disk limit was subsequently cleared by the coordinator's reversible generated-cache archive; the executor now owns isolated baseline/candidate work. Reviewer retains only this output reservation for the exact proposed-diff and final-artifact checkpoints. No reviewer process or cache state was acquired that needs cleanup.
