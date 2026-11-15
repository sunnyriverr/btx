# Shared relay reservation budget — Linux before/after evidence

**Verdict:** the full normal helper forwards40MiB against one32MiB reservation before the fix and stops at32MiB after it. An exactly exhausted reservation reopens before; the fix rejects it. Ordinary64KiB forwarding passes both. Expiry cleanup fails before and passes after in a linked production-library fixture.

Original report: [repch1c, issue560 item5](https://github.com/btxchain/btx/issues/560). This is an opt-in `-modelrelay` accounting repair. No monetary/validation policy changes.

## Identity and reproducible entry point

- Proposed product commit: `561aa06dd55ea0782066036e241491c9c1d65c6c`, based on `release-0.34.17` at `1e2f8b5f12295002334d3390c12cac0bb4ae2aff`.
- Actual execution base: `61f13b8870ed98c7b10db2e32c04fb647023f4ef`, plus [fix.patch](fix.patch), SHA256 `f16387ec63cfd789e6c21cc9144a89e4a69e13df04906e503a808fb87360419b`.
- All four current-base input files are byte-identical to that tested base: [source-equivalence.json](source-equivalence.json). The newer entire release was not rebuilt.
- Executed entry point: [fork CI run43716952389](https://github.com/sunnyriverr/btx/actions/runs/43716952389), recipe commit [46afd598](https://github.com/sunnyriverr/btx/tree/46afd5980bbb11ea948f641d4332d786a1b29f23). The exact recipe is archived in [recipe/](recipe/).
- Ubuntu22.04 x86-64, GCC11.4, CMake3.31.6, OpenSSL3.5.9. Normal `btx-modeld` targets incrementally rebuilt using a hash/mode/timestamp-verified checkpoint; no stubbed accounting/TLS in the native run.

The executed workflow restores the named pinned cache, verifies current source, configures and inspects the actual Ninja plan, builds baseline/candidate helpers and the linked expiry fixture, then runs `native_test.py` in a Docker network-none namespace. The archive records specific retained-cache prerequisites and expiry; it is not a promised clean-from-zero build after those artifacts expire. Build, execution, and missing/error/cleanup result gates propagate failure.

## Observations

| Case | Baseline | Candidate |
|---|---|---|
| Two admitted connections,20MiB each, one32MiB reservation |41,943,040bytes delivered; budget assertion fails |33,554,432bytes total; passes |
| Exactly fill32MiB, then offer1024 more |HTTP200,1024 extra bytes delivered |HTTP403, no extra target stream/bytes |
| Ordinary64KiB |passes |passes |
| Independent sink hash, byte counter and connection cleanup |hash/counter match target; active0; clean helper exit0 |same |
| Short-TTL expiry cleanup, linked real production library |active count1 remains; raw exit1 at the intended assertion |active0 and expired row removed; exit0 |
| Pending short-write reconciliation at expiry (candidate-only) |not an old API case |commit7 actual bytes, release unused claim, active0, row removed |

Raw results: [native-result.json](native-result.json), [build-result.json](build-result.json), [baseline-expiry.log](baseline-expiry.log), [candidate-expiry.log](candidate-expiry.log), [native helper logs](native-logs/). [VERIFIED-RESULT.json](VERIFIED-RESULT.json) records downloaded artifact/binary hashes. The raw baseline budget/expiry failures are expected proof, not product passes hidden by the successful qualification job.

Baseline helper SHA256: `04b068ab4aebd2be1893268d384fe6561cfc06ee72c84f8701ee5e3dc5fe9458`.
Candidate helper SHA256: `c98edadee33ec69aaa82523c3520d3c45cb59a0c385f4e0a6983885d62d2e888`.
Binary artifact14163077249 is available from the run until29November2026 13:10UTC. All four retained helper/fixture members were downloaded and hashed against actual execution records. Logs are retained in this branch independently of artifact expiry.

## Scope and limits

- Real strict outer PQ1 handshake, peer certificate, HTTP reservation/connect, address guards, helper splice, status RPC and TCP target byte observation execute. TEST-NET203.0.113.1 is assigned only to isolated loopback; no external relay/network traffic or funds.
- The inner target is an opaque TCP sink, not nested PQ1 model serving or a complete model download.
- Expiry is a short-TTL executable linked against actual production libraries, not a one-hour native-server timer test. The candidate-only pending-byte case supplies a short-write count at the table boundary.
- Three maintained regressions are added to `modelnet_conn_tests`; the full `test_btx` executable/suite was not built or run here. The normal in-tree cases are `relay_shared_byte_budget`, `relay_byte_claim_cleanup`, and `relay_claim_expires_without_fresh_allowance`.
- No native Windows, current-patch native macOS, clean-from-zero build, load/throughput or release qualification.
- First attempt43716018430 linked the helper but the test-only expiry entry point omitted BTX's translation global. It was corrected, and its verified checkpoint reused. The successful run's baseline helper completion took6.95seconds rather than repeating the earlier44-file compile. This was a fixture error, not a product result.

The repair claims shared allowance before each read, bounds reads in both directions, commits actual successful writes and returns unused claims. Expired active records survive only for in-flight reconciliation/closeout; new admission/claims remain refused. Default opt-in, target/identity guards and splice deadlines remain.
