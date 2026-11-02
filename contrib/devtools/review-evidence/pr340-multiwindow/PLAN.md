# #340 multi-window recovery — active private experiment

User authorized next concrete uncovered recovery check. Current340head5deb327871efbca832e1a4e420f76dad74ff6b41 contains exactb3774256and5deb3278with Sunny authorship; JPP's6572480084reports relevant suites passing and confirms farther-arrival eviction is still a limit. No larger-range result found in fresh340/370threads. Those are reported results, not ours.

Closed own draft370as superseded after exact public commit/credit checks, per JPP request. closure-receipt.json verifies closed/unmerged, no extra comment.340remainsopen.

Decision: does the folded downloader actually advance and complete across four real download windows under the same strict-Metal toy profile, or does a reproducible progress failure require a focused follow-up? This is not a demand for a speculative quota scheduler or full mainnet throughput benchmark.

Pin head5deb3278; clean isolated source/build because the old cache has mixed historical objects. Generate an exact private regtest4196snapshot from the retained1124fixture, using hash-known previous validated fixture-maker binary; that binary is used for fixture creation only. Insert only exact private regtest4196snapshot metadata in the clean target build. No validation/fork rules changed.

Use existing pinned-consensus/no-available-quorum harness, prefix100→base4196=4096historical bodies; real BLOCK_DOWNLOAD_WINDOW remains1024. Serve only normal P2P requests from one source, no manual getblockfrompeer/requeue, no pacing to mask churn. Inject three fresh blocks at separated progress points across windows. Measure progress timeline, requests/hash, retained eviction/deferral logs, source connectivity, exact bytes/hashes and4096LOCAL_EXACT_REPLAY flags. Require snapshot completion, persistent flags after clean restart, fresh blocks and30shealth. Bound1200scatchup/45sno-progress, disk1.5GiB, logs600MiB; disclosed toy regtest rate/pending budgets, not default/mainnet qualification.

No automatic fix: if it stalls, first distinguish setup/pin/header fixture from production scheduling. If it completes, report measured bounded progress and remaining limits; don't manufacture an expected failing control or redesign for test count. No newPR or posting authorized by this execution; prepare one coherent result. Old wallet node remains retired, other work preserved.
