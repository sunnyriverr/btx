# Full-store recovery: current component evidence

**Same maintained regression: accepted baseline 3 PASS / 2 FAIL with SEC_OBJECT_QUOTA; candidate 5 PASS.**

Product commit: `80cef2879ef8224a4cc945fdad6aeb8efb71bc52`, based on #275 `e9c1e364262543a3a7543885e55fd6c2849bf1c0`. [Product changes](https://github.com/sunnyriverr/btx/commit/80cef2879ef8224a4cc945fdad6aeb8efb71bc52). JPP identified the original quota findings; this carries forward sunnyriverr's previously tested finite-reserve proposal onto the current serialized import path.

## Observed result

| Case | Accepted base + identical test overlay | Candidate |
| --- | --- | --- |
| Receipt/evaluation authority and fresh commit | PASS | PASS |
| Policy expiry after callback entry | PASS | PASS |
| Actual policy rotation and stale binding | PASS | PASS |
| Authenticated policy replacement at ordinary cap | FAIL: SEC_OBJECT_QUOTA | PASS |
| Authenticated revocation at cap; ordinary evidence quota retained | FAIL: SEC_OBJECT_QUOTA | PASS |

Both recovery cases construct exactly 16,384 rows. The candidate admits each valid control and preserves its authoritative effects/journal. Both live evidence kinds refuse ordinary quota at the cap and, on the candidate, after revocation enters the reserve. Baseline stops at its failed recovery write, so post-recovery assertions execute candidate-only.

## What ran

Native macOS 26.5.1 arm64, Apple clang 17.0.0, CMake 4.4.3, Homebrew SQLite identified in provenance. Fresh component CMake target from selected exact source/dependencies, with no historical objects reused; affected objects rebuilt for candidate. One run per side. Regression SHA-256 `8b172e71f87d7f307836b235c087e3c69635ed901248a0a80a8eeeb708094c41` was identical.

Actual command arguments, binary/source/header/library identities and process exits are in [provenance.json](provenance.json); repository source inventory is [source-assembly.json](source-assembly.json), and the real generated compiler plan is [compile-commands.json](compile-commands.json). Raw outcome: [baseline](logs/baseline-run.log), [candidate](logs/candidate-ctest-detail.log). All output is retained under logs. User-specific local paths were normalized; [manifest.json](manifest.json) maps original and published hashes. It does not pretend normalized bytes are the original log hashes.

The maintained entry point is `test/util/model_security/full_store_recovery_tests.cpp`, registered as `security-full-store-recovery`. Normal reviewer reconstruction from the candidate checkout:

```sh
cmake -S test/util/model_security -B build/security-store -DCMAKE_BUILD_TYPE=Release
cmake --build build/security-store --target full-store-recovery-tests
ctest --test-dir build/security-store -R '^security-full-store-recovery$' --output-on-failure
```

This is a reconstruction recipe; the exact tested Mac invocation additionally pins compiler, O2/NDEBUG and Homebrew SQLite paths in provenance. A before/after check uses the identical new test/CMake overlay on e9, then candidate product code. The baseline must fail only the two recovery cases. A planning-only Make dry-run initially failed on absent not-yet-built recursive archives; target discovery plus generated compile commands replaced that probe before the actual build. Its [pilot output](logs/planning-pilot.log) is retained. No product/control failure was suppressed.

## Scope and limits

Real local signatures and production import entry points; unsigned inert rows seed only the count. Authority/current policy/roles/revocation/release denial, fresh commit expiry and database rollback controls pass. Entire accepted ImportCurrentEvidence and SQLite portability are preserved. References in the synthetic evidence are import-field fixtures, not completed worker/capsule workflows. The peer flag is a component option, not a transport exchange.

The reserve is 129 fixed shared rows, absolute 16,513: no record deletion, ordinary capacity reset, owner-exclusive priority or physical disk reservation. Older finite-tail, race, retained-negative-evidence and late-write results remain attributed to their original fd3 component run, not re-executed current evidence. Prepared-permit invalidation remains unchanged-source review in this run.

No native Linux/Windows, full node/service/guard lifecycle, worker execution/cancellation, mesh transfer, physical disk-full fault, full test suite or release qualification. [Final source/fixture review](source-review.md) is internal artifact review, not a second platform execution. Owned temporary databases were cleaned naturally; no production node or wallets were used.
