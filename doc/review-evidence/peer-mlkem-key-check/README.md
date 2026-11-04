# Peer ML-KEM key guard — scoped local evidence

Product `ce5f1769741468ce1702f377b6972f2c81f06447`, tree `edcd6d161824b3b052e441720e88f30c75fee495`, on accepted `ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629`. Original finding: repch1c. Numair requested [separate key-admission review](https://github.com/btxchain/btx/issues/338#issuecomment-6624390408).

The four-file change checks the peer key's canonical encoding before encapsulation/rekey. Recognized invalid PQ keys are refused under ordinary and PQ-only policies; genuine legacy policy is unchanged. The seed remains unrestricted. This follows [FIPS203 section7.2](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.203.pdf); it is not proof of key ownership, honest generation or full FIPS certification. Current published errata were inspected and do not alter this check.

## Rejection proof: local unit fault injection

**The same final unit fails before (exit1/two cases) and passes after (exit0), under default and PQ-only policies.** It uses only genuinely generated valid keys and unmodified production handshake bytes. The real predicate is called, then a test-only shim forces its Boolean decision false. An encapsulation shim counts calls and delegates real crypto unchanged. The actual baseline/candidate transport objects are not patched for the test.

| Injected false decision | Baseline | Correction |
| --- | --- | --- |
| Validation consulted | 0 | exactly1 |
| Receive failure | no | yes |
| Encapsulation | once | none |
| Hybrid/application state entered | yes | no |
| Application send after draining queued own handshake output | accepted | refused; payload intact |
| Fresh valid connection after removing injection | pass | pass |

The post-drain probe rules out buffer back-pressure. The candidate's37 pre-existing handshake bytes are allowed; no extra receive input is supplied. No v1 fallback or application delivery occurs in the rejected unit case. Baseline failures are deliberate assertion failures, not crashes or setup failures. A fixture error has a separate exit2.

[Unit fixture](guard-fault/unit.cpp), [executed launcher](guard-fault/run.py), [final results/commands/input hashes](guard-fault/results.json). The isolated archive has39 non-index members; only its wrapper object is replaced, and the other38 members are byte-identical. Original libraries, source and transport objects remain unchanged.

## Encoding and legitimate-operation controls

The real predicate passes local range/position/boundary checks, generated-key agreement and unrestricted-seed controls. The maintained ML-KEM tests compile. [Positive control fixture](runtime/positive_transport.cpp), [baseline](baseline-positive-results.json) and [candidate](positive-transport-results.json) establish exact bidirectional messages for default/PQ-only/mixed PQ and disabled/legacy-v2 pairings, with fresh connection instances. These earlier passing campaigns were reused for publication.

Fresh native macOS arm64/AppleClang17, root CMake Release with Modelnet/wallet/tests/benchON, GUI/ZMQOFF and runtime Metal compilation. Actual crypto/util/clientversion/secp256k1/UniValue targets and affected net/test objects built. [Source/library identities](source-build-identities.json) and [object commands](component-builds.json) identify the tested artifacts; nonempty build diagnostics and final predicate/unit logs are adjacent; positive stdout is retained in the aggregates. Empty successful logs and superseded pilots are omitted. Catalog hashes refer to retained local binaries/objects, not files offered for download.

Explicit component fixture: Params() supplies network magic and regtest type only, avoiding unrelated genesis/chain initialization. Transport state machine, AEAD, key generation and rekey code are real. Settings are restored. This is not a node or live-peer run.

## Reconstruct a disposable native Mac workspace

Clone the product branch into `source/`, copy this directory's `.py`/`.cpp` files preserving subdirectories beside it, and keep the evidence records separate from regenerated outputs. Normal project dependencies and Apple command-line C++ tools are required. Both named Git commits must be available. Commands reconstruct individually executed steps; a second clean bootstrap was not run for publication.

```sh
mkdir -p guard-fault/real
cmake -S source -B build -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DBUILD_GUI=OFF -DBUILD_BENCH=ON \
  -DWITH_ZMQ=OFF -DWITH_CCACHE=OFF -DBTX_MATMUL_METAL_PRECOMPILE_KERNELS=OFF
cmake --build build --target bitcoin_crypto bitcoin_util bitcoin_clientversion secp256k1 univalue -- -j2
python3 build_components.py
python3 link_positive.py
./runtime/positive-transport
python3 run_baseline_positive.py
python3 guard-fault/run.py
```

The baseline-positive step creates the original net object required by the unit. The final command explicitly verifies baseline failure and candidate success. It exercises valid recovery inside the new unit. It depends on the real generated compiler database and the scoped objects/link-command record created by the preceding steps. `runtime/key_check.cpp` is the executed separate predicate driver; compile it against the same generated includes and crypto/util/clientversion libraries with CoreFoundation/Security frameworks. `key-check-run-final.log` records its result.

## Limits and provenance

The rejection proof is **injected-decision control flow**, composed with separate encoding tests. No direct malformed-wire input, sockets, full node/test_btx, native Linux/Windows, full suite or release qualification. External unit/component harnesses are not registered in the default test runner. Full V1/PQ-only legacy-refusal runtime is unclaimed. A separate patch-application check on405 passes; no stacked proposal or combined runtime claim.

An initial send-gate probe was strengthened to drain queued own output; only the final fixture/results above are current. Initial broad link setup was narrowed to the disclosed Params fixture. Some preliminary setup diagnostics were overwritten; final executed commands and results are retained. No product failure is inferred from those setup attempts.

C++ fixtures and executed Python scripts are byte-identical to their local executed versions. Only unnecessary local paths in logs/records are redacted; public-copy-provenance.json maps identities. The source/build identity catalog selects immutable fields from the earlier qualification record; current unit claims come from its separate final aggregate. No secret wallet/operator data or prebuilt executable is published.
