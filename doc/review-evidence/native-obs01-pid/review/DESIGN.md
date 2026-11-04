# Obs01 native PID portability — bounded design review

**PASS for the proposed one-file portability repair and focused acceptance plan, with the fixture details below. This is source/design review, not a build or runtime result.**

Reviewed as `/root/obs01_portability_review`. Parent owns `src/modelnet/obs01/obs01.cpp` and this output subtree. No product file, Git ref/index, VM, build, public discussion, peer status or ledger was changed by this review.

## Cause and scope

The retained generated clang-cl command compiles the complete Obs01 translation unit with C++20, `/MT`, the native compatibility include directories and forced `posix_extra.h`. Run41784786903 has one compiler diagnostic at `obs01.cpp:120`: no global `getpid`. The repository-native `unistd.h` shim only includes the compatibility header; it supplies no PID declaration or mapping. Current acceptedecd has the identical Obs01 blob482fa81739b1cc94d1947e73fa0fad51cdf86356, and its native shim/forced-header text still lacks that declaration. The old run is not a native build of ecd.

The call supplies the decimal suffix of `btx-obs01-` for a temporary lab directory. It does not choose a signer, affect MatMul acceptance, change qualification flags, or determine consensus. `TempTree` already owns the recursive cleanup. Those mechanisms and the Prf/Qat/Rel gate order must remain unchanged.

Microsoft documents `_getpid` as returning the calling process ID as `int`, with no error return, and requiring `<process.h>`. This is appropriate for the native desktop CRT profile. See [Microsoft CRT `_getpid`](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/getpid?view=msvc-170). No shared shim, alias macro, new emulation or class-layout change is necessary.

## Recommended shape

Use the conditional native header, then a local `const auto process_id` selected at the sole call site:

```cpp
#ifdef _WIN32
#include <process.h>
#else
#include <unistd.h>
#endif
```

```cpp
#ifdef _WIN32
        const auto process_id = ::_getpid();
#else
        const auto process_id = ::getpid();
#endif
        const TempTree tree{fs::temp_directory_path() / ("btx-obs01-" + std::to_string(process_id))};
```

A duplicated conditional `TempTree` statement is also correct, but the local variable keeps one path construction and one lifetime owner. `auto` avoids an unnecessary POSIX PID-type assumption or cast. Both forms keep one PID query at the same control-flow point. Do not introduce `#define getpid`, suppress the native compilation failure globally, change the directory prefix, or modernize adjacent lab/gate code in this patch.

## Useful acceptance and controls

1. On exact acceptedecd, run the actual generated `obs01.cpp.obj` target with the unchanged command/database: baseline must fail specifically for missing global `getpid`; candidate must produce the object. Verify the sole source delta and unchanged generated flags/compile database. This is clang-cl translation-unit compilation; it is not node/library linkage or a full MSVC build.
2. Build the small native MSVC and clang-cl fixture from the exact selected include/PID/root statement and byte-identical `TempTree`. Prefer the actual header-only `util/fs.h` path wrapper over a substitute namespace. Its `using std::filesystem` operations and inline path wrapper allow this narrow fixture without a BTX archive; any unexpected link dependency must be classified rather than stubbed silently.
3. **Do not include `<process.h>` unconditionally in the baseline fixture to create an oracle:** that can supply deprecated `getpid` and mask the real missing-header path. The Windows oracle can be `GetCurrentProcessId` from `<windows.h>`, already part of the native compatibility environment. Compare the CRT PID with `static_cast<DWORD>(process_id)` against that independent Win32 value; avoid an unnecessary signed/unsigned assumption about PID range.
4. Prove the exact prefix+decimal PID suffix, repeated same-process naming, normal cleanup and early-exit/unwind cleanup. Put TEMP/TMP/TMPDIR under an explicitly owned fresh fixture parent before invoking the child. Verify the computed root belongs there, is absent before creation, and is removed afterward; retain an unrelated sibling sentinel. Do not operate under the user's real temp tree merely because the product expression uses `temp_directory_path()`.
5. Run the POSIX branch on Mac with real `unistd.h`/`getpid` and the same narrow path/cleanup controls. A launcher PID check can provide a separate process-identity oracle. Verify that the original `TempTree`, LabDir/PrepareLab, gate order, qualification checks and remaining source reconstruct byte-for-byte after removing the intended portability delta.

The actual full Obs01::Pass gates need not be linked or executed to establish this PID-declaration fix. The extracted runtime fixture proves only the PID-derived temporary-path/lifetime seam. Report that limit explicitly; it does not establish Prf/Qat/Rel gate behavior, modelnet archive linkage, node operation, full test_btx, Linux runtime, MinGW runtime or release qualification.

## Closure condition

The repair is ready for a scoped handoff only after the actual same-target before/after and legitimate native/Mac controls pass, input/source/binary/log identities are retained, the final diff is inspected and a fresh coverage check finds no adopted/competing correction. A source or accepted-head change during CI needs its own delta record. Keep the original13bb result distinct from the newecd campaign and preserve the posting hold.
