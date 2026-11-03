# Qualification registry recovery — native Mac component result

**PASS, bounded repair on exact `cbf65894e6d61084527cd93e913a00c6794418dd`.** The final candidate passes all five focused native Mac component cases. Staged baseline evidence has two passing controls and three intended failing cases. The repair moves malformed registry bytes aside, preserves fail-closed behavior until a new registry instance, and reports actual rename failure truthfully. Native Windows and full daemon/test_btx integration remain unverified.

## Change

`patch.diff` changes two repository files only. Full candidate production TU SHA-256: `74f478799e7d9979e72e2ee6d372bbefaf5a3c54b79b8384bc9a2dd168a4263c`; native test TU: `29afdd9ae1f2e5b7a4df03bc8913cdce52c8f30bc0d401c6899c9f0b76beff27`. Patch SHA-256: `744bdb451d0721847082c8ea69d5543b12f0ecd8e0e996959422795c13d3af67`.

The production change closes the local read stream after obtaining bytes. It isolates existing parsing/strict getter work in a local lambda; `std::runtime_error` from malformed types or out-of-range integers follows the same corruption handling as the existing false-return branches. Existing accepted types, schema number, field defaults/casts and admission rules are unchanged. There is no catch-all, allocation-error recovery, parser/range redesign or new OS API. Filesystem quarantine is strictly outside the parser exception boundary, checks `ec`, and assigns `quarantine_path` only after success; failure returns a diagnostic beginning `registry quarantine failed: `. The first corrupted load always returns false, including after a successful move.

The existing `compute_profile_tests.cpp` gains three focused cases and stronger actual byte/source/new-instance assertions in its existing malformed-JSON case. No new test target/framework or CMake registration is introduced. repch1c's Windows item14 discovery is the source lead; the coordinator separately identified skipped non-object-row quarantine and strict-getter exception paths in the same Load function.

## Actual observations

| Focused case | Baseline | Candidate |
|---|---|---|
| Existing real toy CPU solve, verify/redeem, replay rejection and persisted redeemed state | PASS | PASS |
| Existing bounds/expiry/nonJSON corruption case, strengthened with exact quarantine bytes, absent source and empty new-instance/old UNKNOWN recovery | PASS | PASS |
| Schema1 entries[null] after actual redeemed/pending work, same-instance failclosed, byte isolation and old UNKNOWN/unredeemable after new instance | FAIL: source retained, no quarantine bytes, new instance still unhealthy | PASS |
| Actual nonempty quarantine-directory collision, both declared-corrupt payloads; preserve source/marker, truthful health/error, remove obstruction and recover | FAIL: false success diagnostic/path and skipped null-row isolation | PASS |
| Missing row fields (`entries:[{}]`) and oversized numeric schema, independently observed in one case | FAIL: both initial/new-instance Open throw, source retained, no quarantine | PASS |

Baseline was intentionally staged. Initial four tests ran on component adapter `4499cbc9…`, test TU `c4a46d63…`, binary `5f2ffe2b…`: two pass/two fail. Before applying any product change, the coordinator found getter exceptions; the one added case then ran alone on the final adapter/test TU, baseline binary `ab6a7f3e787c2ba1f412d698da652a084cfb4a976541904d7a378f2bccde7fac` (full actual identity in baseline-fields-run.json), and failed for both payloads. The initial four test bodies remained byte-identical when appending that case. The final candidate's exact adapter is `50c69f309b80a0490e2ce2f04309a68b7cdae15330f195f9685088b09e5c8e7e`; final binary `86510465e3828cc3c5770053f10a7245367212158c7c60ed2bb94033b7fd8ae3`. All five candidate invocations passed on the first attempt. The wrapper’s shell exit status indicates build/invocation completion only; recorded `all_passed=true` plus five individual zero test statuses establish the result. A separate read-only manifest aggregate assertion is documented and executed; it is artifact validation, not an additional native test. This is not a clean five-case before/after matrix and no unchanged baseline case was repeated for count.

Failed baseline assertions were inspected, not inferred from exit codes: null-row checks found retained original/missing exact quarantine bytes and failed new-instance recovery; collision reported `registry quarantined` despite the directory obstruction; both getter payloads produced unexpected Open exceptions and repeated new-instance failure. Valid controls passed throughout. Candidate failures of these properties did not recur. No production assertion/test was relaxed in response to results.

## Execution and provenance

Native macOS26.5.1, arm64, AppleClang17, C++20/O2. The complete production qualification TU was freshly compiled per stage, without omitting production functions or test-injected symbol replacements on tested paths. The regression adapter uses exact native Boost case bodies and substitutes only bootstrap/BasicTestingSetup with a disposable-directory fixture. Actual CPU toy ExactReplay, Issue/RememberIssued/Verify/Status/Open/Health, strict UniValue getters, Save/RenameOver and filesystem rename execute. No redeemed rows or qualification authority state were fixture-injected; corruption bytes and collision directories are test inputs.

This is a partial component relink using read-only native prerequisites from the retained PR362 build `dabe7981c6cb12d7f98c9567d5035225bd6fd8a1`, not a clean exact-base whole-tree build. Every archive matches its retained original identity. The original library compilation has Metal/Accelerate support and its standard production backend stub objects may be linked; tests request CPU toy work only. Link maps identify real selected archive members and freshly compiled registry Open/Load as object2; the retained archive's old qualification object is not selected. The full TU's non-system header dependency closure is checked against immutable exact-base Git bytes, and compiled dependency hashes plus commands/maps/binary/log hashes are retained in `provenance.json`, `inputs.json`, `compiled-dependencies.json` and stage manifests.

The actually executed entry point is `run-component.py` (candidate run once, with final code/test bytes). `REPRODUCE.md` states local prerequisite identities, fixture boundary, staged baseline and the separate unexecuted normal test_btx integration recipe. No build or link warnings/errors were emitted. Pre-build preparation had a corrected relative-parent typo and premature invocation while source extraction was still running; neither wrote product/test changes or ran a test. The initial package/source hashes and those preparation limits are recorded; they are not product failures.

## Limits and cleanup

- New registry instance construction verifies persisted-file recovery; it does not execute a daemon restart, static RPC holder, helper process or node initialization. No full test_btx suite or clean whole-tree build ran.
- Mac success cannot qualify the stream-sharing repair on Windows. repch1c's native Windows failure and untraced cause remain externally reported; the primary MSVC source/OS contract supports the source diagnosis. Existing platform test should be reused for Windows confirmation.
- The PWC issuer allowlist is distinct from mining, device self-qualification, consensus and monetary state. No GPU, live node, wallet, VM, model execution, installation/download, spend or public write occurred.
- Wrong type/out-of-range getters now quarantine, but accepted numeric ranges/default behavior are unchanged. Unreadable/open/read I/O errors, filesystem exceptions outside the nonthrowing rename operation, concurrent writers/Windows no-op locking and destination overwrite/retention policy were not redesigned or broadly qualified.

Peak measured task logical bytes during execution:26,727,733 (~25.49MiB); lowest sampled free space:1,896,185,856 (~1.766GiB), above the1.25GiB floor. One compile/run process at a time, monitored every100ms; stage elapsed times are recorded, not a cost/speedup comparison. Owned fixtures/temp roots are gone; no secrets or owned live processes remain. All retained dependency hashes and shared dirty checkout HEAD/status match the initial record. Source/header projection, exact scripts, patch, binaries, objects, maps and logs are retained (~26MiB logical) for audit/reproduction; shared caches were read-only. See `cleanup.json`.

Executor work is complete pending final independent artifact review. Coordinator BTX test1 owns shared records, resource release, branch preparation and any authorized publication; none were delegated here.
