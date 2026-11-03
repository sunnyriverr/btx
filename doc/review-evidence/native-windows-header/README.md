# Native Windows compatibility-header prerequisite

**PASS, scoped: identical final tests fail on ab1b5cbe and pass with the combined native header/compiler-option fix under both native cl and clang-cl. MinGW preservation passes.**

Fix: [3c542cd6800755a891cd3ffafd839fd682e7ec40](https://github.com/sunnyriverr/btx/commit/3c542cd6800755a891cd3ffafd839fd682e7ec40), based on ab1b5cbe42d5b3ceb4faafff213292efed2bba18. Three product files, one commit: native header declarations, the Windows Modelnet forced-include compiler option and a standalone in-tree regression. Original native build report: [repch1c, #356](https://github.com/btxchain/btx/issues/356). [JPP's Windows coverage](https://github.com/Jpp-matata/btx/actions/runs/41709716434) informed the prerequisite scope and avoided repeating his broad MinGW campaign.

## Exact result

[Run41734861012](https://github.com/sunnyriverr/btx/actions/runs/41734861012) executed CI tree9b8cd6145cde5e02332ccd12e38994e194cb745b. Its three product files are byte-identical to the clean fix commit; the CI-only files are the runner, provenance manifest and workflow. No tests were repeated solely for history packaging.

| Gate | ab1b5cbe | Combined fix |
| --- | --- | --- |
| Complete-header fixture, native cl, both include orders | Missing unistd.h | Compile/link/runtime pass |
| Same fixture, native clang-cl, both orders | Missing unistd.h | Compile/link/runtime pass |
| Unchanged production types.cpp through exact Windows CMake compatibility block, cl | Unknown -include; extra header source fails missing unistd.h | Object build passes with /FI |
| Same production block and TU, clang-cl | Unknown -include; multiple inputs with /Fo | Object build passes with /FI |
| MinGW fixture and actual-block component | Pass | Pass; preprocessed tokens per order and production types object bytes identical |

Native: Windows Server2025 x64 hosted runner, cl19.51.36260/toolset14.51.36231, clang-cl20.1.8, Windows SDK/UCRT10.0.26100.0. Four candidate native fixture executions check signed pointer-sized byte counts, both compatibility-header orders, CRT environment overwrite/preserve/remove, ordinary file reads/writes with position preserved, flush/cleanup and the existing unsupported-fork return.

The runner extracts the complete, exact production WIN32 compatibility block from each source version, uses CMake compiler detection and builds unchanged modelnet/types.cpp with its seven-file exact source closure. Logs and generated compile_commands.json are included. The object target declares the production link libraries but does not link them. CMake's [MSVC predicate](https://cmake.org/cmake/help/v3.22/variable/MSVC.html) covers compilers using the cl command-line interface, including clang-cl.

MinGW: GCC13-posix cross-compilation on Ubuntu24.04; no MinGW executable was run by this gate. Its preservation checks cover both compile paths and exact fixture token/object equality, not a full MinGW node build.

## Reproduce the packaged component gate

Use a fresh, narrow checkout to avoid unrelated assets and preserve exact source bytes. No node, wallet, chain data or model downloads are required. From Git:

```text
git clone --filter=blob:none --no-checkout --single-branch --branch codex/evidence-native-posix-header https://github.com/sunnyriverr/btx.git btx-native-header
cd btx-native-header
git config core.autocrlf false
git sparse-checkout set --no-cone /src/compat/mingw/posix_extra.h /src/modelnet/CMakeLists.txt /test/util/windows_posix_header_tests.cpp /doc/review-evidence/native-windows-header/
git checkout codex/evidence-native-posix-header
```

In an x64 Visual Studio Developer PowerShell, put LLVM clang-cl, CMake, Ninja and Python3.10+ on PATH. Both cl and clang-cl must be available. Use a new output directory:

```powershell
python doc/review-evidence/native-windows-header/check_header.py --repo (Resolve-Path .).Path --out (Join-Path $env:TEMP 'btx-native-header-check')
```

On Linux with CMake, Ninja and x86_64-w64-mingw32-g++ (GCC13-posix in the recorded run):

```sh
python3 doc/review-evidence/native-windows-header/check_header.py --repo "$PWD" --out /tmp/btx-native-header-check
```

The packaged runner and closure manifest are byte-identical to the executed runner; their adjacent directory moved from the CI helper path to this evidence directory. Root test source stays test/util/windows_posix_header_tests.cpp. The runner verifies Git source/header/CMake hashes before execution. Expected baseline failures count as controls, not overall CI failures; unexpected outcomes make the runner fail. This recipe has not separately been rerun from the documentation branch.

## Limits and remaining #356 gate

This is a component OBJECT build with /MD and standalone runtime controls. It does **not** qualify root configuration/build, static CRT, complete Modelnet library/linking, helper spawning, a full native node, test_btx/unpruned suites, consensus behaviour or a release. The standalone regression is not wired into the default test_btx/CTest list. There are no late-SDK, wide-path, large-offset or general POSIX semantic claims from this fixture.

Full #356 acceptance still needs compatible OpenSSL>=3.5 provisioning, direct native production Unix-header and unit-test portability prerequisites, then the actual native root build and unit run. This fix does not close that issue. Plain-cl arithmetic/compiler limitations are separate.

Earlier run41733782660 stopped before native compilation at a checkout-byte provenance guard; pinning core.autocrlf=false fixed that setup with product/harness unchanged. Run41734216763 passed the repaired header/runtime controls but exposed the existing forced-include option defect, motivating the coupled CMake correction. Neither failed combined run is counted as qualification. Final41734861012 reran both platforms after that material change and passed.

provenance.json maps exact source, runner, fixture and files. windows-result.json and mingw-result.json carry every command/outcome; logs/ includes compiler versions, before/after diagnostics, generated commands and runtime results. artifact-collection.json records the original compressed-artifact and binary hashes; the primary review surface is branch source and text evidence.
