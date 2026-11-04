# Native Windows S_ISREG fallback — tested compilation and file-type repair

Code `a8b96b89917f9e15ca5f4d3d716c26627098d6a1` directly on accepted `46caec762b0f130d497313d8ca9fa6894ac19ccd`; one file, three added lines. No PR401 stack.

The native CRT compatibility header omitted S_ISREG, stopping the real Modelnet store.cpp consumer at735. A guarded fallback compares the complete file-type mask against _S_IFREG. Existing definitions are retained. The adapter remains Windows-only; store.cpp, lstat/reparse handling, hashing/size checks and storage safety guards are unchanged. Credit: repch1c's Windows defect inventory and JPP's native investigation.

| Executed check | Original | Candidate |
| --- | --- | --- |
| Same root-generated store.cpp.obj, native clang-cl | Unknown S_ISREG at735 | Produces object |
| Full adapter + file-type fixture, native cl/clang-cl | Missing predicate compile failure | 23/23 checks each |
| Predefined predicate, both native compilers | 2/2 each | 2/2 each |
| Mac same file-type fixture | 23+2 pass | 23+2 pass; identical preprocessed program/system predicate |
| Deliberately incorrect bit-test version | Not applicable | Compiles, fails intended socket/symlink cases |

The native checks use actual regular files, directories, missing paths and file/directory/dangling symlinks through the existing adapter and unchanged post-materialization type predicate. Character/FIFO/socket/mixed modes are synthetic classification inputs, not device creation. Permissions and single evaluation are checked. All owned fixture directories are removed. No privileges were enabled or granted.

Native Windows Server2025 x64 image20261030.294.1, clang-cl20.1.8, MSVC19.51.36260/toolset14.51.36231, SDK10.0.26100.0, C++20/static CRT. Actual windows-clangcl-static root configuration: tests/default Modelnet/wallet/SQLite/ZMQ ON, GUI OFF. Same build directory, actual compiler command and compile database before/after. [Executed native job](https://github.com/sunnyriverr/btx/actions/runs/41777361014), CI14791a1688ce649eef8f25470fede00cafd4d403. All31 native command logs,14307 source entries across four catalogs, seven fixture executables and the generated object were hash-verified. Full catalogs, database and binaries are in that job's artifact; native/artifacts.json records its download digest. Store object SHA256: c5d3b4ff3c7460e62af152bb495478d83294065cc6b074c941a5e641b3f1f3e3.

## Reproduce

### Native Windows generated consumer

Use an isolated stock46 checkout and its documented native clang-cl dependencies. The executed native/runner.py configure stage records every exact preset/dependency argument and performs this pair; native/workflow.yml records compiler initialization and exact source checkout. It reused verified OpenSSL3.5.4/static CRT and pinned vcpkg dependency caches; it is not a clean dependency rebuild. Native controller inputs are together in native/ with their original relative filenames. To use the retained workflow, copy native/ to its controls/contrib/devtools/windows-root-configure location.

After the recorded root configuration, the distinguishing command is:

```powershell
cmake --build D:\btx-native-035\project-build --target src/modelnet/CMakeFiles/bitcoin_modelnet.dir/store.cpp.obj --verbose -- -j 1
```

Original must fail specifically on missing S_ISREG at store.cpp735. Install only candidate.h as src/compat/mingw/posix_extra.h (hash in source-manifest.json); run the identical command and require a new object. Do not disable Modelnet, alter store.cpp or inject a compiler definition. The actual controller also compiles/runs file-type-check.cpp with both native compilers, validates a preexisting predicate and rejects the wrong-bit mutant.

### Mac file-type/POSIX control

The exact executed script and all its relative inputs are at this evidence root:

```sh
python3 posix-check.py
```

It builds both actual header variants, runs23 normal and2 preexisting-definition checks for each, compares full preprocessed programs and the system S_ISREG definition, and requires cleanup. It uses only a disposable directory under posix/ and refuses an existing runtime fixture directory. It needs Apple command-line clang, C++20 and the existing ability to create symlinks. Original Mac stdout logs and a derived summary preserve result values/hashes; unnecessary personal command paths are omitted. The original local verification record's SHA256 is retained in posix/results.json. This is the same executed script/input layout, not a fresh platform campaign for publication.

## Limits

This is a generated production-object compile plus file-type component qualification. It does not execute complete ModelStore::MaterializeFile, hash/materialization races or recovery, full daemon/helper linkage, test_btx build/run, node/network/wallet/model transfer, native Linux/MinGW, or release qualification. #356 remains open for the full native Windows build and unit run. macOS controls do not establish every POSIX platform.

Original records retain their test-time local/unpublished status. Publication state is tracked separately; tested code and native logs are unchanged. Fixture-preparation and verifier metadata corrections were resolved before handoff, with no additional native job or weakened product assertion.
