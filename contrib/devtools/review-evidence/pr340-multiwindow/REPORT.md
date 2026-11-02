# #340 folded-head four-window recovery — private result

**PASS on5deb3278: a clean-built node completes4,096historical strict-Metal validations, follows fresh blocks, preserves completion across restart and passes30seconds of health checks.** This is one bounded toy-regtest acceptance run with regtest's unthrottled pending/rate budgets, not mainnet/default-policy throughput qualification. No new fix is justified by this run.

## Upstream disposition first

JPP folded exact b37742560c62ecffce5ea29ca233c23036c9bbd2 and5deb327871efbca832e1a4e420f76dad74ff6b41 into340, preserving Sunny River authorship. Public head340is5deb3278, equal to370's head. Verified public commits/parents/credit, then closed own draft370as superseded, per his explicit request. It was not merged;340remainsopen. No extra comment. closure-receipt.json records the result.

Fold request/result: https://github.com/btxchain/btx/pull/340#issuecomment-6572480084
Remaining larger-range limitation: https://github.com/btxchain/btx/pull/370#issuecomment-6562772634
Fresh340/370discussion check found no larger-range completion result. This is a scoped overlap check, not a claim about unpublished tests or every open PR.

## Exact experiment

New isolated source at5deb3278, clean CMake Release build ofbtxd/btx-cli, Metal ON, wallet ON, tests/GUI OFF. Existing shared object caches were not trusted/reused. Build took~854seconds and completed with compiler/linker warnings; not claimed warning-free. Then inserted only the exact private regtest4196snapshot metadata and rebuilt those targets. Source diff is8adds in kernel/chainparams.cpp; production downloader/validation code is unchanged. Commands/logs and binary hashes retained. No production node/wallet/miner was touched.

Fixture: extend retained1124chain to4196using the separately hash-known old strict-Metal fixture-maker binary. Snapshot hash, UTXO/state metadata and runtime verified. That binary makes data, not the test verdict. The scaled generator retains legacy1124/1024 log labels; fixture-validation.json explicitly corrects their interpretation using actual4196height,4197nchaintx and snapshot hash. No invalid snapshot bypass or arbitrary base-height acceptance.

Target starts at100; normal loadtxoutset loads the exact4196pin. Target has one pinned signer, consensus mode, no local signer, no available votes/quorum, strict-device Metal and CPU confirmation off. Source provides bodies through normal P2P requests, without manual fetch, pacing or modified window size. Real BLOCK_DOWNLOAD_WINDOW stays1024. Header bootstrap batches at2000to obey the existing wire limit; the old one-window helper would overfill that message when scaled.

Adapted existing harness for4096historical bodies, fresh-block injections spread over progress, and explicit restart-start timestamp. Same underlying acceptance checks; this is not an unchanged rerun or old-baseline comparison. Bounds:1200scatchup/45swithoutprogress,1500srunner,1.5GiBdisk,600MiBlogs. One actual run, not3repetitions.

**Important policy limit:** regtest RC activation sets pending/global/per-peer verify budgets toUINT32_MAX (kernel/chainparams.cpp2244–2250); no cap1override in this case. This does not qualify mainnet's one-pending-slot/rate-limited policy, production-size proofs, arbitrary ranges, multiple netgroups or long-running peer churn. The retained store's per-netgroup/global limits and real1024download window were not enlarged.

## Observations

|Boundary: background height|Seconds from source connection|
|---|---:|
|1124(one window)|38.52|
|2148(two)|73.75|
|3172(three)|171.11|
|4196(four)|260.61|

Complete hash/body/status verification and final runtime sample by263.08seconds. Largest gap between observed progress changes~2.79seconds. Timing is one local observation, not a benchmark comparison with the prior1024run.

- Every4096historical body matches source bytes/hash and has BLOCK_EXACT_REPLAY_VERIFIED, without the trusted-attestation flag. Runtime samples require strict-device/full Metal and zeroCPU GEMM/fallback/host-XOF paths.
- One source stayed connected; no alternate body peer/manual rescue. Three fresh tip blocks observed during background validation; all three followed. Foreground injection progress100/2148/4096, observed latencies~0.127/0.067/0.066seconds in this local run, not general latency guarantees.
- Clean restart preserves exact tip, completed snapshot and every local replay flag. Three more peer-generated blocks connect, then30seconds of health checks pass; final height4202. Authentication work equals claimed work at checked tips; pins/no-local-signer/no-quorum remain as configured.
-6,023native Requesting-block lines for4,096historical hashes: maximum2perhash, mean1.47046.1,911retention-eviction lines;0requested-background capacity-deferral lines. No historical request lines from before stopping for restart through the post-restart health window. Eviction counts cover the whole target log; request counts are restricted to101..4196. No network byte count inferred.

Churn remains real. These results show it did not stall this four-window case; they neither establish zero-overhead recovery nor justify a new scheduler patch. No actual failing product condition was found to fix. Do not extend the range merely to generate more tests.

## Integrity and next decision

summary.json, run/result.json, source diff/private pin, configure/build logs, fixture-validation.json, request counts/events and raw private observations support the result. Exact source SHA/binary/harness identities retained; no mixed shared libraries. Shared dirty source hashes verified unchanged. All owned node processes stopped and test ports bindable. Isolated fixtures/build preserved for reproduction; no automated monitor.

AI-assisted. This is native macOSM4 strict-Metal toy-regtest evidence, not Linux/Windows, default-policy, mainnet, full-suite, release or production GPU admission qualification. Publication has not been authorized for this new result; no upload/comment/PR. Next is one short340handoff with branch evidence and policy limits when authorized, acknowledging the verified fold and370closure. Do not create another PR, redo completed single-window controls or propose a throughput redesign from these metrics.
