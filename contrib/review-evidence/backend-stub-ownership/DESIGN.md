# Windows backend linkage: independent source/design review

Reviewer: delegated `backend_linkage_review`, parent BTX test 1 (2). Read-only source reviewed from `git -C work/btx-contributions show cbf65894:<path>` on 2026-11-03. No compiler, linker, VM, GPU, node or public action was run by this reviewer. Outputs are confined to this review directory. The coordinator owns product changes, experiments, records and publication.

## Recommendation

Remove the nine CUDA/Metal/HIP definitions from `src/matmul/accel_v4_stub.cpp`; retain its three Ascend definitions and their present linkage behavior. CMake already selects exactly one vendor translation unit for every removed entry point in both disabled and enabled configurations. This is the smallest coherent repair of ownership, and changes neither device code nor selection conditions. Update the file introduction and `accel_v4.h` ownership comments so future additions do not recreate the redundant fallback. Adjacent HIP/CMake commentary that describes the removed weak definitions is stale after this change and can be corrected without touching implementation.

Do not repair this with `/FORCE:MULTIPLE`, new weak attributes, broad platform exclusions, or new enable macros. The rule is one selected provider per entry point. Weak definitions happen to mask duplication on ordinary GNU/Clang builds, but they are not required for CUDA/Metal/HIP with this build graph.

## Exact ownership at cbf65894

All names below are in `matmul_v4::<vendor>`. `single`, `batch`, `BMX4` mean `ComputeDigestAccel`, `ComputeDigestsBatchedAccel`, `ComputeDigestsBMX4CAccel`, with exactly the signatures in `src/matmul/accel_v4.h:235-274`.

| Vendor | Disabled provider | Enabled provider | Selection |
| --- | --- | --- | --- |
| CUDA single/batch | `cuda/matmul_v4_accel_stub.cpp:18,24` | `cuda/matmul_v4_accel.cu:551,683` | `BTX_ENABLE_CUDA_EXPERIMENTAL`, CMake lines 1374-1511 |
| CUDA BMX4 | `cuda/matmul_v4_bmx4_accel_stub.cpp:19` | `cuda/matmul_v4_bmx4_accel.cu:1281` | Same branch |
| Metal single/batch | `metal/matmul_v4_accel_stub.cpp:16,24` | `metal/matmul_v4_accel.mm:1551,1588` | `APPLE AND BTX_ENABLE_METAL`, CMake lines 1119-1373 |
| Metal BMX4 | `metal/matmul_v4_bmx4_accel_stub.cpp:21` | `metal/matmul_v4_bmx4_accel.mm:1290` | Same branch |
| HIP single/batch | `hip/matmul_v4_accel_stub.cpp:24,30` | `hip/matmul_v4_accel.hip:298,414` | `BTX_ENABLE_HIP`, CMake lines 1522-1679 |
| HIP BMX4 | Generic-namespace adapter in `hip/matmul_v4_bmx4_accel_stub.cpp:41` | Forwarding adapter in `hip/matmul_v4_bmx4_accel.hip:618` | Same branch |
| Ascend all three | `matmul/accel_v4_stub.cpp:109-127` | Same generic stubs remain | Always included at CMake line 1107 |

CUDA and Metal real sources are added directly to static `btx_matmul_backend`. Enabled HIP real sources belong to separate static `btx_hip_device` (CMake 1530); `btx_matmul_backend` privately links that archive (1573), and it participates in `BTX_BASE_ARCHIVES` when enabled (1865-1867). HIP's isolation protects host C++ sources from `hip::device` compile flags. Nothing in the repair should alter it.

The generic file defines all three CUDA entries at 43-63 if CUDA's macro is absent, all three Metal entries at 65-85 if Metal's macro is absent, all three HIP entries at 87-107 if HIP's macro is absent, and all three Ascend entries unconditionally at 109-127. At lines 37-41 `BTX_ACCEL_V4_WEAK` is empty for `_MSC_VER` **or** `__MINGW32__`, and `[[gnu::weak]]` otherwise. The vendor stub definitions are ordinary strong definitions with selection performed by CMake, not preprocessor guards. Therefore the nine duplicate definitions are present in a disabled Windows backend graph; whether every one is diagnosed at a particular link depends on archive extraction.

`matmul/accel_v4.cpp:188-242` selects addresses of all four vendors' single/batch/BMX4 functions without preprocessor guards. Removing Ascend or conditionally suppressing it when `BTX_ENABLE_ASCEND` is true leaves a required dispatcher surface unresolved. Enabled Ascend+CANN adds only LT and RC implementations (`src/CMakeLists.txt:1680-1732`), not these generic entries.

## Build boundaries and entrypoints

A complete-tree exact-filename search found only `src/CMakeLists.txt:1107` as a build inclusion of `accel_v4_stub.cpp`; the other hits are explanatory comments/documents. There is no second build manifest or standalone direct compilation of this source in the revision. A tree inventory of CMake, Makefile, configure/build scripts, Visual Studio project, meson and bazel names plus relevant literal-source searches found no alternative product source graph. This is a repository-source conclusion, not a guarantee about external downstream build scripts.

The root `CMakeLists.txt:850` uses `add_subdirectory(src)`. Documented Unix/macOS builds invoke this graph. Windows entrypoints also converge on it:

- `CMakePresets.json` defines `windows-clangcl-static` as Ninja + clang-cl + x64-windows-static. It does not force accelerator options. The documented command in `doc/build-windows-msvc.md:87-88` builds btxd and btx-cli.
- The `vs2022` and `vs2022-static` presets use the Visual Studio generator and same source graph.
- `contrib/devtools/build-btx-windows.ps1:467-519` invokes root CMake using Visual Studio; CUDA is explicitly controlled by its switch. It does not maintain a separate source list.
- MinGW's documented path in `doc/build-windows.md:51-52` passes the depends toolchain to root CMake. `depends/Makefile` prepares dependencies, not another node source list.
- `scripts/build_btx.sh` configures the root and builds the configured graph. `contrib/guix/libexec/build.sh:531,556` also configures root CMake for its library/product builds. `contrib/matmul-v4/run-sm120-cuda-matrix.sh` builds the same backend target; its object path references do not redefine ownership.
- `ci/test/03_test_script.sh:141,155` configures and builds root CMake. The standalone `test/benchmark/build_bench.sh` compiles only `matmul_phase2_bench.cpp`, not this backend.
- Vendored PQC and other library Makefiles are not consumers of this generic source. No relevant source glob was found that would select it outside this explicit graph.

Actual conditions matter more than option names. Metal defaults ON on Apple and OFF elsewhere (`src/CMakeLists.txt:11,67`), but even a non-Apple `BTX_ENABLE_METAL=ON` cache value takes the stub branch because selection requires `APPLE`. The target compile definition is emitted only in the real Metal branch (1355). CUDA defaults from compiler detection (95-101); HIP defaults from compiler plus architecture detection (282-288). These are not universally OFF merely because a preset omits them. CUDA and HIP real-branch options also require their toolchain/architectures. Ascend's option can be ON with no CANN; the LT/RC graph remains fail-closed and its generic stubs still exist. Apple Metal plus CUDA is explicitly rejected (1114-1118).

Enabled defines are PUBLIC on `btx_matmul_backend` (Metal 1355, CUDA 1453, HIP 1571); `bitcoin_common` PUBLIC-links it (1733). Preserve these definitions: capability and test callers depend on them to include actual device behavior. Do not add a compile definition merely to hide a stub.

## Important gotchas

1. HIP BMX4 has two namespaces. The real implementation and native availability probe are in `matmul_v4::bmx4::hip`; the generic dispatcher calls `matmul_v4::hip`. Both the real `.hip` and disabled stub supply the latter adapter. Counting only the nested namespace would incorrectly conclude the generic definition must remain.
2. Vendor stub files have additional required symbols. Metal files own v4/BMX4 `ProbeAcceleration`; HIP files own `HipBackendCompiled`, `Bmx4CHipBackendCompiled` and the nested BMX4 entry; CUDA BMX4 owns `ComputeDigestsOnlyBMX4CAccel`. Removing whole vendor stub files from CMake breaks those consumers. Removing only their overlapping functions would spread ownership across more files and require new conditions for enabled cases while retaining generic weak/strong complexity.
3. HIP disabled batch/BMX4 implementations clear output vectors; the redundant generic versions merely return false. Preserving the vendor definitions preserves their specified failure behavior. CUDA/Metal disabled calls return false without modifying outputs. A test that assumes all stubs have the same output side effects is wrong.
4. A static archive can conceal duplicate definitions when only one object is extracted. Ascend references pull the generic object; Metal/HIP probes and CUDA digest-only references can pull vendor objects independently. Direct-object links or forced extraction expose ownership more deterministically than a tiny archive-linked caller using only common signatures. Neither generic weak stubs nor permissive linker options should be mistaken for a selected device implementation.
5. Existing comments are partly historical, including the CMake BMX4 comment at 1165 and HIP adapter comments in its header/.hip. Source definitions and current branch selection are authoritative. `BTX_ENABLE_HIP_EXPERIMENTAL` in older documents is not the current selector.

## Discriminating validation without a Windows environment

Use one final harness against baseline and candidate, with exact input hashes and compiler commands. The narrow intended claim is source ownership and component linkage, not a complete Windows build.

- Compile the actual generic and six vendor stub translation units. A direct-object link references all twelve generic entries plus vendor-only probes/surfaces. In a Windows-strong conditional configuration the baseline must fail with duplicate definitions in the claimed namespaces, and the candidate must link. Keep ordinary native compilation as the legitimate weak-path control. Inspect symbol definitions as well as executable exit status.
- The native-host `_MSC_VER`/`__MINGW32__` simulation must be described precisely. Defining these globally can change standard/platform headers; if a lightweight header adapter is necessary, identify every replaced type/header and say that it tests the actual stub bodies/conditional linkage under a surrogate ABI. A native object is not a COFF object merely because `_MSC_VER` is defined. Compiler errors caused by the adapter are fixture failures, not the product duplicate.
- Verify candidate false returns across all twelve entrypoints and vendor availability probes; check the vendor-specific output behavior above. Ensure Ascend remains defined with and without `BTX_ENABLE_ASCEND`/`BTX_HAVE_CANN` defines.
- Include archive-linked coverage or symbol inspection that proves the candidate's vendor entries come from their selected objects. Baseline direct-object failure proves collision, while archive behavior explains the production mechanism; do not claim direct-object assembly is the entire node link.
- An enabled-provider control should replace each selected real vendor TU with a deliberately distinguishable fixture provider for all three entries, with the corresponding enable macro active, then call it and verify its distinct result/counters. Ensure generic object still supplies Ascend and no disabled vendor objects are included. This challenges accidental suppression and wrong selection for CUDA, Metal and HIP. Label it a provider-selection adapter, not GPU execution. If feasible also test a supported combination such as CUDA+HIP; do not demand Apple's intentionally forbidden Metal+CUDA pair.
- Assert the actual CMake ownership contract or capture source properties from the actual graph. A hand-written test source list alone cannot detect a CMake mistake. A source-level assertion is acceptable given the production patch leaves CMake unchanged; it is not equivalent to configuring real CUDA/HIP SDKs.
- A targeted bad control restoring one redundant strong definition should fail. A control removing Ascend or replacing an enabled fixture with a false-return stub should also be detected if those are material uncertainties; avoid a large ceremonial mutation matrix.

Native Windows clang-cl/MinGW toolchain build, Windows archive extraction, full node linkage, actual GPU compilation/runtime and device correctness remain unverified unless separately executed. No outcome here establishes network or consensus behavior. Final review should verify this distinction is maintained in the report and any later handoff.
