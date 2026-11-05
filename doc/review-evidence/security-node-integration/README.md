# Exact-e9 Linux node/guard integration

**PASS: accepted `e9c1e364` builds the real services and passes the unchanged maintained one-node security-guard lifecycle test.** This is scoped native Linux integration evidence, not a full security or release qualification.

## Inputs and actual result

- Product `e9c1e364262543a3a7543885e55fd6c2849bf1c0`, tree `3005bcb922e8f1c636a0f67ed5d8426308d95807`, branch `btx-035/model-security-v2`. No product/test patch or prerequisite forced include.
- [Native run41998533532](https://github.com/sunnyriverr/btx/actions/runs/41998533532), fork fixture `7d2f661f68d1c0110f05df793144084997626cba`. One native qualification; no publication rerun. Fresh root Release build of `btxd`, `btx-modeld`, `btx-guardd`, `btx-cli`:1898.3s, exit0. The framework requires the actual CLI even when --usecli is false.
- Ubuntu24.04 x86_64, GCC13.3.0, actual CMake3.31.6 at `/usr/local/bin/cmake`, Python3.12.3, glibc2.39. The apt package inventory also names CMake3.28.3; the selected executable and CMakeCache identify3.31.6 for this build.
- Modelnet/daemon/CLI/utilities/SQLite/ZMQ ON; GUI/wallet/C++ unit/bench/fuzz builds OFF. Functional config generation is independent of BUILD_TESTS. [Actual configure command and outcomes](native/state.json), [cache](native/CMakeCache.txt), [build log](native/root-build.log), [compile commands](native/compile_commands.json), [build graph](native/build.ninja).
- Private OpenSSL3.5.9, source SHA-256 `603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a`. Matching headers/static SSL/static crypto and BTX_OPENSSL prefix; version, algorithms and library hashes retained. Four ldd logs resolve dependencies, with no missing/dynamic system libssl/libcrypto. The product is not wholly static.

Credit: the maintained product/test retain their original authorship and [license](COPYING). The execution driver reuses JPP's Ubuntu/private-OpenSSL bootstrap pattern from [workflow1853cfd2](https://github.com/Jpp-matata/btx/blob/1853cfd2621d88ba10a6300819741544406f0fea/.github/workflows/btx-035-ci.yml); its older3.5.4 recipe is setup inspiration, not a claim JPP tested this security tree. Driver/result collection is Sunny River's work.

## Maintained test: one actual invocation

`feature_model_security_v2.py` is unchanged, SHA-256 `8cdf2bb75743e27ccf46e489ea25d4edfc6924a7afe4bd46dac688160ccc01bf`. It runs once, exit0, `Tests successful`, no skip/timeout/resource stop; process duration2.0s. [Test log](native/maintained-test.log), [framework log](native/functional-logs/test_framework.log), [node log](native/functional-logs/node0/regtest/debug.log), [result](native/result.json).

| Checked property | Result |
| --- | --- |
| Default node-owned guard responds through modelsecurity RPC | Pass |
| No policy, zero automatic spend, valid journal and truthful unqualified model/GPU/multi-host flags | Pass |
| Ordinary unknown-operation refusal | Pass |
| Pause and usable ordinary getblockcount | Pass |
| Clean restart changes guard_boot and retains pause/journal/height | Pass |
| Two normal node shutdowns, no leftover owned processes, private test directory removed | Pass |

The test uses one clean regtest node, no wallet/mining/policy installation/model execution. Existing framework corepolicy/softwareexpiry/regtest-seal overrides remain; peer/autoconnect/discovery and the helper listener are disabled by the framework. The source assertions establish the RPC properties; response payloads/boot IDs were not separately dumped.

The process observer sees real node-owned guards on both boots and modeld after restart. Its200ms sampling does not capture first-boot modeld; no claim of two observed helper starts. [PID/executable/start-time observations](native/observed-owned-processes.json). Cleanup finds no owned processes and sends no fallback TERM/KILL. `--nocleanup` preserves the directory for log collection only; the driver subsequently removes it.

The first helper's `RPC not ready (stopped)` message follows `Shutdown: stopping owned btx-modeld helper` (42.828 then42.872). Exact source `supervisor.cpp:307–318` returns stopped when shutdown interrupts WaitReady. This is not an independent startup timeout. **Model-helper RPC readiness and serving workloads are not qualified.** This case waits for the guard-backed security RPC, not helper readiness.

## Executed entry point and reproduction

The exact executed [workflow](recipe/workflow.yml) and [driver](recipe/run.py) are retained unchanged, outside `.github/workflows` in this evidence branch. The live fixture commit above installs them at `contrib/devtools/security-node-integration/` and checks out the immutable product separately. Its stages are source/runner admission, documented Linux dependencies, digest-verified private OpenSSL, root configure/build, the maintained functional test and always-run owned cleanup. It requires a fresh disposable Ubuntu24 runner, no production node/wallet or preexisting task path,10GiB initial free disk,2GiB stop floor,2 build jobs and phase/job time limits. Actual compiler/configuration/input commands are in state.json; Python AST/actionlint and internal source review preceded execution, without implying external reproduction.

The executed maintained-test command is recorded in state.json. In abbreviated form:

```text
BTX_OPENSSL=<matched-prefix>/bin/openssl python3 <build>/test/functional/feature_model_security_v2.py --configfile=<build>/test/config.ini --tmpdir=<fresh-owned-path> --portseed=27519 --nocleanup
```

A reproduced result requires the real four binaries, matching crypto, actual non-skipped test completion, unchanged source and owned cleanup. The relocated evidence copy is a record of the executed fixture, not a second executed launcher. No old component test, fake service or feature-disabled node substitutes for this path. No build cache or executable payload is included; hashes identify the actual binaries.

## Source identity and durable raw records

All four native before/after-build/after-test/final audits verify14,314 tracked blobs, file types and executable modes. They are byte-identical SHA-256 `91026e0151a8f5afa5a48830976d278bfcf9e12f589cb9bf8c7a244e244497e5`; the collector also matches every native entry to its independent immutable local e9 Git tree. [Canonical source catalog](native/source-catalog.json) is stored once. [Manifest](MANIFEST.json) maps all four original filenames to those identical bytes, and includes every published file's hash.

Original runner artifact13404065680 has archive SHA-256 `5a20e267075e34663d08d9e6a0ac77b7bcaf1501cbb23e21a5124d5efb3ff84b`,33,750,151 expanded bytes, expiry12Nov2026. Its33 raw files are preserved here, with only the four identical source catalogs deduplicated. This durable branch removes dependence on the temporary artifact for these records. Product binaries/cache were never retained in that artifact; their bytes cannot be recovered from hashes. [Collection receipt](identity/collection.json), [run](identity/run.json), [artifact metadata](identity/artifacts.json). Publication downloaded the same digest-pinned archive into bounded memory and did not rerun the qualification.

## Limits and decision

This fills the previously missing accepted-e9 native root-build/default-owned-guard/status/pause/restart observation. It does not qualify all six accepted repairs, policy/root install, full-store recovery, evaluation, model-helper service readiness or model workloads, GPU, physical multi-host protection, guard crash/absence, monetary validation, full unit suite, Windows/macOS or a release. No product change is proposed by this result.
