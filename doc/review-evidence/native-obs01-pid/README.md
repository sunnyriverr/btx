# Obs01 native PID portability — tested fix

Code `1b404ed8e52eae249ac73036007ba5a382b0d3ba` on accepted `ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629`; one commit and one production file. Credit: repch1c's Windows defect inventory and Jpp-matata's Windows build investigation. Original source attribution is retained.

The native Modelnet archive cannot compile `obs01.cpp:120`: its selected unistd shim does not declare getpid. The fix selects `<process.h>`/`_getpid` on Windows and preserves `<unistd.h>`/`getpid` on POSIX. One local PID value feeds the existing temporary-directory prefix/path and TempTree owner. Cleanup and Obs01 qualification/gate logic are unchanged. The exact intended delta reconstructs the baseline when inverted.

| Executed check | Baseline | Candidate |
| --- | --- | --- |
| Same actual root-generated obs01.cpp.obj, clang-cl | Missing getpid, exit1 | Object produced, exit0 |
| Native MSVC extracted PID/path/lifetime fixture | Missing getpid compile failure |37checks pass |
| Native clang-cl same fixture | Missing getpid compile failure |37checks pass |
| macOS arm64 same POSIX seam |37checks pass |37checks pass |
| Deliberately constant PID | Not applicable | Rejected on Windows and Mac |

The fixture uses real util/fs.h and the exact TempTree/PID/path statements extracted from each source. It verifies the current PID against the Win32 and launcher identities, exact directory name, repeated same-process naming, real file/directory creation, normal/early-return/exception-unwind cleanup and unrelated sibling retention. TEMP/TMP/TMPDIR point at a fresh owned parent; no real user temp tree is removed. The baseline fixture does not include process.h for its oracle: that could hide the missing declaration. The constant-PID version compiles but fails7 assertions.

Native [run41790329187](https://github.com/sunnyriverr/btx/actions/runs/41790329187), controlsbd06c940138482ee8588dc7b81a5ba0289695573: Windows Server2025 x64, clang-cl20.1.8, toolset14.51.36231, SDK10.0.26100.0, Release/C++20/static CRT. Wallet/Modelnet/SQLite/ZMQ/tests ON, GUI OFF. Actual compiler commands and5,897-entry database are unchanged before/after. All23 command logs,14,309 source entries, candidate object and three native executable identities were verified. Only obs01.cpp differed, and the baseline was restored. Native/result.json records all command/output hashes; verification.json records checked outcomes. Full catalogs/database/binaries are retained in that job's artifact, with the ZIP digest recorded in native/artifacts.json; they are not executable sources in this branch.

## Reproduce

### Native generated consumer

Use an isolated acceptedecd checkout with its documented Windows clang-cl dependencies. Native/runner.py and native/workflow.yml are the exact executed setup/controller inputs, kept together with their relative input files. They reuse verified static OpenSSL3.5.4 and pinned vcpkg dependency packages; they are not a clean dependency rebuild or a bootstrap for an empty machine. The distinguishing command after recorded root configuration is:

```powershell
cmake --build D:\btx-native-035\project-build --target src/modelnet/CMakeFiles/bitcoin_modelnet.dir/obs01/obs01.cpp.obj --verbose -- -j 1
```

The baseline must fail specifically for missing getpid at obs01.cpp120. Install only candidate.cpp at src/modelnet/obs01/obs01.cpp (hashes in source-manifest.json), rerun the identical target and require a new object. Do not disable Modelnet or inject a compiler alias. The native controller also compiles the baseline and candidate fixtures with cl/clang-cl and runs the candidate/wrong-PID controls. To replay the retained workflow in its existing environment, place native/ under controls/contrib/devtools/windows-root-configure.

### macOS POSIX seam

The same executed relative input layout is at this evidence root:

```sh
python3 mac_checks.py
```

It compiles/runs both original/candidate PID/TempTree fixtures plus the wrong-PID control, checks launcher identity and owned-directory cleanup, and writes under mac/. It requires existing Apple command-line clang/C++20. The five source headers are exact immutable inputs matching the native accepted tree. Published Mac result metadata omit unnecessary personal absolute command paths; stdout, source and recorded binary hashes remain unchanged. This is packaging of the executed recipe, not another platform campaign.

## Limits and preparation notes

The complete production TU result is clang-cl compilation. MSVC runtime evidence is the extracted PID/path/lifetime fixture. Complete Obs01::Pass gates, Modelnet/node/helper link, project unit suite, Linux/MinGW runtime, GPU, network, wallet and LAN runtime were not exercised; #356 remains open for the actual full native build/unit run. A passing object does not provide a library closure. Resource evidence is object preflight plus command timeouts, not live object-stage memory sampling.

Two initial Mac fixture setup attempts omitted attributes.h and util/string.h. Resolving the five real-header closure fixed setup without fake headers/product changes; these are not product failures. The first raw pilot log was not retained; the second is retained locally. Earlier13bb integration results are separate and are not relabeled as this acceptedecd campaign. Internal agent review is not an independent external tested ACK.

Publication and adoption are tracked separately from original test records. The native campaign was not repeated. The packaged Mac entry point was checked once in a disposable copy; original test records and product bytes were preserved. The code branch is the proposed repair; this evidence branch supplies readable logs, exact inputs and limits rather than another production change.
