# Focused #381 cap test

Run this single entry point with exact #381 source (`6478f640`), the identified Alpine/aarch64 crypto and JSON archives listed in manifest.json, and a new private work directory:

`python3 reproduce.py --source SOURCE --crypto CRYPTO_ARCHIVE --json JSON_ARCHIVE --work NEW_WORK`

It applies the unchanged #384 timing prerequisite identically to both variants, then the test-only correction. The only variant difference is `submitted==2` versus `submitted==99`. The original standalone native probe is built; both executables use explicit8MiB ELF stacks. Dependencies are reused identified native archives, not a fresh whole dependency build.

Only the seven-valid-job case runs once per variant. Before any second maintenance pass can begin, a single SQL statement snapshots the first completion marker/error/cursor within1.5s of a timestamp taken before Service construction. All seven proposals are unique and locally eligible, no earlier evaluations exist, and queue8 exceeds jobs7: the cursor identifies successful first-pass admissions. Cap2 leaves the sorted second ID; cap99 exhausts seven and clears the tail cursor. The test then requires all seven genuine native PASS endpoints in BOTH variants before asserting the captured cap verdict.

Expected: cap2 PASS; cap99 FAIL only at the final budget assertion, with seven signed PASS/dispatched endpoint pairs in each. `FIXTURE_FIRST_PASS_OBSERVATION_MISSED` is an observation-boundary failure, not a product-cap finding; do not rerun until green. No production test API, diagnostic overlay, new clock test or starvation matrix is introduced. The product deliverable is test-only.patch; the mutation and timing prerequisite are test inputs, not new product changes. This remains a configured Linux component check, not full-daemon/default-stack/other-platform/release qualification.

Dependency provenance (recorded platform only): the supplied manifest pins the actual reused archive hashes from the previously executed fresh #384 packaged build. The following describes its official source targets; these commands were NOT executed again in this cap run:

```sh
cmake -S SOURCE/test/util/model_security -B dependency-build \
  -DCMAKE_BUILD_TYPE=Release -DBTX_SOURCE_ROOT=SOURCE \
  -DBTX_SECURITY_OVERLAY=SOURCE -DBTX_INTEGRATED_SOURCE=/nonexistent
cmake --build dependency-build --target btx_security_crypto btx_security_json --parallel 1
```

Use `dependency-build/libbtx_security_crypto.a` and `dependency-build/libbtx_security_json.a` only after matching manifest.json on native Alpine/aarch64, GCC14.2, musl1.2.5. The public #384 regression package also builds these targets under `WORK/build/upstream/`. Different compilers/platforms are unqualified and may produce different hashes; this recipe does not silently substitute them. This cap run is a focused source build with identified reused dependencies, not a turnkey fresh dependency build.
