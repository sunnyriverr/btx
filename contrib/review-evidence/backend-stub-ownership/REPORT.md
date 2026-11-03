# Windows backend stub ownership — tested candidate

**The component linker rejects the original duplicate definitions and accepts the candidate; all tested fallback and provider-selection controls pass. Native Windows verification is still required.**

Credit: repch1c reported the real clang-cl failure and `/FORCE:MULTIPLE` workaround in [issue #356, item 7](https://github.com/btxchain/btx/issues/356). We independently traced the source ownership and tested a bounded repair. This is not a new discovery of a Windows failure.

## Cause and repair

Base is `cbf65894e6d61084527cd93e913a00c6794418dd`. `src/CMakeLists.txt` always includes `matmul/accel_v4_stub.cpp`, which defines generic CUDA, Metal, HIP and Ascend fallbacks. It also chooses each vendor's real implementation or disabled-backend translation units. The generic file makes its functions ordinary strong symbols under `_MSC_VER` or `__MINGW32__`; the vendor stubs are strong too. Consequently nine CUDA/Metal/HIP definitions can collide. Native Unix weak linkage masks this duplication.

The candidate removes those nine redundant definitions. Their vendor implementations/stubs remain unchanged. Ascend's three generic fallbacks remain unconditional: enabling Ascend+CANN currently adds only LT/RC device implementations. Four adjacent files receive comment-only ownership corrections. CMake commands, backend selection conditions, algorithms and validation rules are unchanged. See `candidate.patch` and the independent `review/DESIGN.md` source map.

Fresh duplicate screen: 109 open PRs, earlier 107 heads unchanged; only our #391/#392 added. Cached matching-head file lists and targeted searches showed no competing repair. #245's cached API diff is capped; this was not a complete fresh full-diff audit. Unpublished work cannot be excluded. Details: `upstream-check.json` and `../priority-after391/checked-after392.json`.

## Actual local execution

Native macOS arm64, Apple Clang, exact identities in `identities.json`. From a Git checkout containing the code commit, run `python3 prepare_inputs.py /path/to/btx`, then `python3 run_checks.py` in this evidence directory. The input reconstruction command has been executed and verifies every exported file against the recorded input hashes. It compiles the actual generic translation unit, six actual vendor stub translation units and their exact project headers, including real `CBlockHeader` and `uint256` types. No BTX archives or mutable build caches are reused. There are no substituted project types.

To examine Windows-style strong linkage locally, a wrapper parses the project and C++ headers normally, then defines `_MSC_VER` or `__MINGW32__` before including the unchanged generic source. This selects that file's exact linkage branch while leaving the host headers/ABI native. **These are Mach-O objects and the macOS linker, not COFF objects or a Windows compiler/linker.** The generic objects' defined-symbol counts and strengths are checked: baseline 12 entries, candidate only the three Ascend entries in the all-disabled profile.

| Same harness / configuration | Original | Candidate |
| --- | --- | --- |
| Native weak linkage, all backends disabled | Links and runs | Links and runs |
| `_MSC_VER` linkage branch, direct objects and forced archive extraction | Both fail with nine duplicate symbols | Both link and run |
| `__MINGW32__` linkage branch, direct objects and forced archive extraction | Both fail with nine duplicate symbols | Both link and run |
| Ordinary static-archive link, native weak profile | Links and runs | Links and runs |
| Ordinary static-archive link, strong linkage profiles | Not used as the before oracle | Both candidate profiles link and run |
| One enabled marker provider at a time: CUDA, Metal, HIP; Ascend+CANN defines present | Each still fails on disabled vendors' duplicates | Each links and reaches all three selected marker functions; Ascend remains available as a false-return fallback |
| Deliberately substitute Metal disabled stubs for the expected enabled marker provider | — | Harness rejects the wrong provider at runtime |

The disabled checks call all twelve dispatcher-facing functions and relevant vendor-only surfaces (CUDA digest-only, Metal probes, HIP probes and its nested BMX4 entry). HIP batch/BMX4 vector clearing is asserted. For other false-return paths, the checks cover the seeded scalar digest byte, complete payload(s), and batch digest-vector size; they do not compare all digest bytes or batch digest contents. The enabled marker functions return an identifiable output byte so successful linkage alone cannot hide fallback selection. These are explicit **synthetic provider-selection controls**, not real GPU execution or a test of the dispatcher algorithm.

The source-graph check asserts the actual CMake enabled/disabled provider lists and HIP archive linkage; it also checks baseline/candidate CMake commands are identical after comments are removed. This is source inspection, not a complete CMake configure or GPU SDK build. The independent reviewer inspected alternate build entrypoints and found the product graph converges on CMake.

`results.json` records every command, exit status, log and post-command free disk; `summary.json` is written only after expected successes and deliberate failures are checked. `build-graph-check.json` records the source assertion. The initial successful component run preceded the final comment cleanup and added graph/CANN checks; the final complete recipe was executed again and is the evidence summarized here. One earlier candidate-preparation tool request aborted before dispatch with no stated reason or file changes; normal later preparation succeeded. No test failure is attributed to that tool event.

## Limits and next step

- No native Windows or Linux execution, actual GPU build/runtime, full BTX node link, full test suite or release qualification.
- A force-loaded component archive deliberately exposes ownership collisions; it is not a reproduction of the entire Windows node's archive-extraction order.
- Actual Windows clang-cl/MinGW compilation and ordinary executable linkage without `/FORCE:MULTIPLE` remain required. Existing unrelated #356 compilation blockers are not repaired here.
- No change to CPU fallback algorithms, GPU math, mining admission or consensus; those paths were not exercised by these component checks.
- All generated objects/executables are isolated under this task. No nodes, wallet, VM or production processes were started. Shared dirty source and caches are preserved. The tests themselves performed no external publication.

Independent final artifact review found the code and test boundary sound; its requested narrowing of the output-preservation claim is incorporated above. Local code commit: `d1ee21e828df480d6a3b9605a0d08a21fce8c6ef` on `codex/fix-backend-stub-ownership`. Next: native Windows verification and concrete reviewer feedback; the public handoff preserves repch1c's credit and these Windows limits. Do not repeat the same Mac checks merely while waiting for external review.
