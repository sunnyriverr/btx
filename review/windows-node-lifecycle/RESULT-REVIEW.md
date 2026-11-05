# Native Windows lifecycle result review

5 November 2026. Read-only child review by `/root/priority_gap_review` of run42005749177's retained ZIP, lifecycle.json and the four per-boot debug logs, without large extraction. Only this report was written; no product/test/Git/network/CI/VM/ledger action. Parent separately verifies the full source/configuration/checkpoint/command hashes and cache receipt.

**PASS for the bounded optional-helper monetary-node lifecycle; no evidence or claim blocker found.** This is a candidate acceptance observation, not a product fix or full #356 closure.

## Actual result

The record identifies exact source473a with clean full build-info, a six-step node relink taking12.28seconds, and new binary SHA25635b0aa504dfde65843a12374c731799d92ac7f10b1ab002a5b699b87356be485. It differs from the old362c version-only binary349c5d3c. No fixture/unit binary was built or invoked in this campaign.

Both primary boots omit modelnet and modelnetrequired flags. The logs show no existing btx.conf/btx_rw.conf, the same deliberately missing explicit modelhelper path, no substituted helper, and fresh helper-unavailable/monetary-node-continues diagnostics. Thus the default optional-helper path was actually selected; this was not a hidden Modelnet-OFF run. The restart uses the same datadir. Its excerpt begins with the new09:53:51boot and excludes the first09:53:45boot, confirming the corrected prelaunch offset supplied fresh diagnostics.

Each primary boot actually answers blockchain/network/blockcount RPC, reports regtest height0 and inactive networking/zero peers, then completes five health polls with the same genesis best hash. Startup timings recorded were0.547s and0.313s; these are single-case observations, not performance benchmarks. Both stop through real RPC, exit naturally0, remove their cookie and close the port.

The disabled control explicitly sets modelnet=0, answers the same RPC/health calls and naturally exits0 with the named disabled/monetary-continues log. The required control explicitly sets modelnetrequired=1, reaches the actual missing-helper diagnostic and named required-helper error, then naturally exits1 and completes shutdown. Its expected failure is not an arbitrary bad-argument/startup error.

## Cleanup and artifact boundary

The original record has no forced-cleanup events, no budget stops/failures, and empty stopped/final owned-process snapshots. Live snapshots contain only the relevant node PID. All four cases record cookie removal and closed RPC ports. No forced-cleanup log or .cookie member exists in the ZIP. A bounded scan of its text log/JSON members found no cookie-value or Basic/Bearer authorization-header pattern. Parent still owns full artifact/hash verification; this is not a formal secret-scanning guarantee.

## Honest scope

Healthy default logs also show `GUARD_EXECUTABLE_ABSENT (monetary node continues)`. Preserve that fact: neither guard admission nor a protected model workload was exercised. The helper was deliberately absent via an explicit override, not naturally discovered, started, crashed or recovered. Windows Unix-RPC/helper transport support is unqualified.

This is native Server2025/clang-cl candidate integration with the recorded unmerged prerequisites, wallets disabled, no peers/mining/spends and height0 throughout. Same-datadir genesis restart is not nonempty-chain recovery, catch-up or validation qualification. Full test_btx, stock accepted source, full-cl.exe/Windows11, GPU/live-network and release acceptance remain open. The evidence supports reporting a useful node lifecycle gap closed within this scope; it supports no new product repair or broader platform assertion.
