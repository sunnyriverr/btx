# Normal linked helper result audit

Reviewed the retained normal-helper `build-result.json`, baseline/candidate `result.json`, `test.py`, normal target graph and matching source-hash receipt. Evidence audit only; I did not run or build the helper.

No blocking contradiction found. The normal linked helper run supports the narrow false-reorg-success repair through actual UnixRPC and process restarts.

| Evidence | Baseline | Candidate |
|---|---|---|
| Test status / exit | EXPECTED_CONTRACT_FAILURE / 7 | PASS / 0 |
| No-undo checks | Exactly four false | Exactly four true |
| Helper starts / retained helper logs | 4 / 4 | 4 / 4 |
| Recorded RPC calls | 31 | 31 |
| Unavailable-undo replies | Success, `reorg=true`, corrective events | Exactly four `UNDO_UNAVAILABLE` errors; null results |
| Funding snapshots at each no-undo attempt | Unchanged | Unchanged |
| Store bytes at each no-undo attempt | Changed by false-success event persistence | Unchanged |

The four cases are post-restart, repeated post-restart, fresh empty store, and exhausted history after a valid undo. Candidate errors contain the actionable recovery text, have no corrective event, preserve exact recorded store-file hashes and preserve the before/after funding snapshots. Baseline succeeds without correcting observations and changes the stored file for its events; these are the intended contract failures, not compiler/startup/control failures. Candidate's only RPC errors are the four expected refusals.

Both variants complete the relevant valid controls before writing their final result: same-process undo restores the original 100-atom watch-only observation; a known-correct saved manifest recovers the spent observation; recovery survives another actual process restart; re-observation restores confirmation metadata; export has one lot; successful keyed undo replay returns the identical original result and leaves store bytes unchanged. The fourth process uses a separate empty model directory. `stop()` waits for zero helper exit and removes the socket; a cleanup/startup/control exception would prevent the final recorded success status.

Source identity matches the scoped diagnostic repair: baseline bounty SHA256 is `626aeb0d2ff0fc3edd8ca24cfa6a9c372a4e45db526bc5acc54bf4c11c78c6b6`; candidate is `23ab54cd8c29efcdd8c8801ea014e792feb056af428d320644a90bc7424845d7`, both equal `fix-receipt.json`. Recorded tested binary hashes agree between build-result and each test result. Checkpoint bytes and 29,776 external inputs were verified with zero differences; current tracked bytes were verified after bounded synchronization. This is a compatible-cache incremental normal build, not a clean rebuild: 31 planned baseline actions, 8 candidate actions.

The target graph builds ordinary `bin/btx-modeld` from production `modeld.cpp` plus normal production libraries. The Mac diagnostic controller, its event-ID RNG adapter and dynamic-lookup linker flags are absent from this normal target. The Python harness sends actual Unix socket RPCs to those binaries; it does not replace store methods or randomness. The run therefore closes the prior direct-store/dynamic-link/process-restart evidence gap for this Linux profile.

Limits: one matched Linux x86_64/container pair on the exact recorded source/cache/toolchain. Operator-entered synthetic watch-only facts, no real chain reconciliation, wallet keys/signing/funding, mainnet, Windows, broad full-suite or release qualification. Saved manifests are conditional recovery inputs and do not prove authoritative chain truth. The patch preserves memory-only undo; it does not add durable undo or correct the separate existing valid-undo save-failure behavior. Publication remains held.
