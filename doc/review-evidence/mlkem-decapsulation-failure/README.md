# ML-KEM explicit decapsulation failure

Product `6fefe847007cc75708e3a964979e922213d2961a`, tree `c3a00d23ed7a7cff4e246e9b125b07fc0564613d`, based directly on accepted `ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629`. Original finding: repch1c. Requested failure contract: numair ([338](https://github.com/btxchain/btx/issues/338#issuecomment-6624390408)).

`Decaps` returns an optional secret. Invalid secret-key length fails before allocation or the primitive call. All five production consumers check failure before rekeying/derivation; wallet checks retain their false result. Existing secure cleanup and full-length wrong-key/ciphertext implicit rejection remain. Canonical peer-key admission is separate.

## Executed evidence

Native macOS arm64, AppleClang17, fresh root CMake Release; Modelnet/wallet/tests/bench ON, GUI/ZMQ OFF, runtime Metal compilation selected. Fresh crypto/util/clientversion targets built. Nine affected caller/test/benchmark translation units generated actual objects with their CMake commands. Three maintained test files contain the regressions; `test_btx` was not linked or executed.

| Same native component check | Baseline | Correction |
| --- | --- | --- |
| Valid agreement, wrong-key and altered-ciphertext implicit rejection | 3 pass | 3 pass |
| Invalid-length wrapper must return no secret | 3 contract failures | 3 pass |
| Note and both grant paths must reject invalid lengths | 9 contract failures | 9 pass |
| Valid note/grant recovery | 3 pass | 3 pass |

Each final configuration/case ran once. Original/current wrapper and note/grant source use actual generated compiler flags and common fresh unchanged supporting code, with real cryptographic primitives. The fixtures use generated disposable keys; the null localization hook is console glue. The baseline contract exits1 because invalid lengths still yield a secret; no crash or remote-impact claim.

[Wrapper aggregate](wrapper-results.json), [caller aggregate](caller-final-results.json), [actual object builds](caller-objects.json), [source/library identities](qualification.json). Raw logs are adjacent. Original binary hashes refer to locally retained executables, not downloads from this branch. Public-copy provenance maps redacted paths to original hashes. C++ fixtures and executed Python scripts are unchanged; only unnecessary local paths in records/logs were redacted.

## Reconstruct the local component workspace

Use a disposable native Mac workspace with normal project dependencies (CMake, Apple command-line C++ tools, Boost, OpenSSL, libevent, OpenMP and normal wallet dependencies). Clone the product branch into `source/` and copy all `.py` and `.cpp` files here beside it. Use an empty `build/` directory. Commands below reconstruct the individual executed steps; a second clean bootstrap campaign was not run for publication.

```sh
cmake -S source -B build -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DBUILD_GUI=OFF -DBUILD_BENCH=ON \
  -DWITH_ZMQ=OFF -DWITH_CCACHE=OFF -DBTX_MATMUL_METAL_PRECOMPILE_KERNELS=OFF
cmake --build build --target bitcoin_crypto bitcoin_util bitcoin_clientversion -- -j2
python3 build_callers.py
python3 bootstrap_caller_link.py
python3 run_wrapper_checks.py
python3 run_caller_checks.py
```

`bootstrap_caller_link.py` is a portable reconstruction helper: it compiles three unchanged supporting objects using the fresh database and recreates the caller link-command input. Its resulting command was compared with the executed command locally; it is not a separate runtime campaign. `run_wrapper_checks.py` and `run_caller_checks.py` are the executed entry points and explicitly check baseline failure/candidate success. They require both named commits to exist in the local source repository. Use the fixed product commit, not the evidence commit, for `source/`.

Initial setup errors are retained: the default Metal-precompile configure lacked the SDK tool; standalone links needed clientversion, console localization and unchanged uint256/polyvec support. Those were resolved. Earlier standalone-flags wrapper runs and a candidate-only caller probe remain in the private task history; the final aggregates above supersede them. An initial collector incorrectly expected SIGABRT; actual Release Assume behavior was classified from source and observations, and the final collector uses the explicit contract exit1. A historical metadata field accidentally held the collector hash under a harness label; final records distinguish them correctly.

## Limits

Actual wrapper and note/view-grant component execution, plus compilation of all changed consumers. No full `test_btx`/node, live peer handshake, wallet-validator runtime, native Linux/Windows, GPU or release qualification. Nonzero primitive-status handling is future defensive source coverage: today's primitive always returns zero. No production data or service was used. Independent platform verification is not claimed.
