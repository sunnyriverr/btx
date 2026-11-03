# PR396: native erasure storage evidence

[Result and limits](REPORT.md) · [Native Windows run41740815956](https://github.com/sunnyriverr/btx/actions/runs/41740815956) · [Original header/CMake evidence](../native-windows-header/README.md).

Product storage commit: b6e3062e05887afdf1ad3fa5c2c2d8ea7ba773d4; parent is the original396header/CMake fix3c542cd6800755a891cd3ffafd839fd682e7ec40, based on acceptedab1b5cbe42d5b3ceb4faafff213292efed2bba18. Final source/test bytes match the executed CI payload772bb25a7d0d7c73a988c10d94e339903848ee3d.

## Reproduce the executed component test

Use Python3.10+ and C++20 compilers. On native Windows, open an x64 Visual Studio Developer command prompt and put clang-cl on PATH. MSVC, WindowsSDK/CRT and clang-cl are required. On macOS, clang++ from the installed developer tools is used.

```text
python runner.py ABSOLUTE_PATH_TO_A_NEW_OUTPUT_DIRECTORY
```

The directory must not already exist. The exact executed runner embeds the29immutable repository source/header inputs and test, so it needs no chain, model, wallet or dependency download. It writes isolated source/build/fixture directories and records commands, outcomes and log hashes in result.json. The supplied command is the same runner entry point executed by CI, with a caller-chosen output path. It was not separately rerun from this documentation branch.

On Windows, original source is expected to fail compilation; the header-only intermediate builds but fails binary-byte equality; the combined candidate builds and passes18runtime checks per compiler. On Mac, original and candidate pass18each. A zero runner exit means those expected outcomes match; it does not mean every variant passed. The test links11real production/dependency translationunits, no stubs.

The in-tree standalone regression is test/util/erasure_store_file_tests.cpp; it is executed by this runner and is not registered in default CTest/test_btx. `/MT` here is component static-CRT evidence, not the complete root preset. Full Windows node/helper/Modelnet/test_btx, dependency setup, Linux and native MinGW runtime remain unqualified. Native executable files/hashes were not retained. Raw source hashes, commands, execution logs and exact CI identity are retained.

Original Windows finding: repch1c in356. JPP's complementary coverage informed the scope. Existing Windows rename refusal and POSIX replacement behavior are preserved.
