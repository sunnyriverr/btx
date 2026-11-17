# Atlas SwapNet: native cancellation and refusal

Tested on macOS ARM64, 18 November 2026 (Australia/Brisbane). **Scoped PASS; no product change.**

Atlas app `23ee567ea8a2d9cad8ca3264f8793e8371b3eb93` connected to saved node `cd3078e76398b20b7f500acd1348a5b5455f3d5e`. Disposable regtest, height 0, no wallets loaded, no peers. The newer app is locally ad-hoc signed, not notarized. [App provenance](native/build-provenance.json), [node profile](native/node-profile.json).

## Real native controls

Request: `refundswap`, parameters `[{"swap_id":"0000000000000000000000000000000000000000000000000000000000000000"}]`, blank wallet context. This ID does not exist and cannot spend. The driver made no refund RPC call.

1. App visibly connected as LIVE LOCAL. User verified native method/regtest/wallet NONE/zero ID and cancelled. Page independently observed `CANCELLED · Cancelled in the native confirmation dialog`; **zero** refund dispatches.
2. Same unchanged request, newly prepared and approved after the same visual checks. Page independently observed `RPC_-1 · NOT_FOUND: Swap not found`; **one** refund dispatch. App audit: one operation, **SUBMITTED → REJECTED**.
3. Node remained responsive at height 0, no wallets/peers/swaps/events. Owned node stopped by RPC, exit 0; owned app stopped.

[Before](native/before-cancel.json), [after cancel](native/after-cancel.json), [after refusal and health](native/after-refusal.json), [node dispatch excerpt](native/rpc-dispatch.log), [native app audit](native/app-audit.jsonl). The dispatch excerpt retains all RPC method lines, including the getblockcount logging-positive control, and omits unrelated node startup/personal paths. No cookie or credentials included.

The native macOS file picker/approval alerts blocked automation; user completed those selections and native button choices. Resulting UI text and backend/audit evidence were independently inspected. No screenshots or automatic dialog-content capture claimed. Initial typed JSON acquired a smart quote and was rejected locally; literal paste corrected the fixture before either native control.

## Mixed-version limit

Only the legacy refund path is admitted. `Host.rpc`, `Coordinator.request_refund`, and `_owned` ASTs match between both revisions; the single-object RPC wrapper is retained. [Comparison](native/compatibility-review.json), [source hashes](native/compatibility-inputs.json). Whole files are not claimed identical.

New app reads `getswapmode`, `getswapreadiness`, `getsharedp2pinfo` and newer market workspace calls receive Method not found from the older node. **New market/default-taker functions are unqualified.** No live wallet-scope refusal, valid financial operation, funded swap, unknown-delivery fault, Windows/Linux UI or release qualification is claimed.

## Earlier component evidence reused, not rerun

- [Status checks](status-check/REPORT.md): 11 focused passes on `cd3078e7`; actual view/renderer with controlled bridge replies.
- [Action checks](action-check/REPORT.md): 12 unique passes on `cd3078e7`, six representative forms from the original 14-action source inventory, actual JS Bridge with controlled Tauri/node responses. Original fixture ordering failures and focused corrections retained. These are not current-head native passes.
- Recovery-export repair #821 adopted `26164d1d` with original authorship; Numair's full web-suite/template results are attributed to him, not counted as our runs.

The diagnostic test files are included in each component directory. To reconstruct component execution, check out exact `cd3078e7` separately, copy the selected diagnostic into `gui/atlas/tests`, then run `node --test --test-timeout=10000 tests/<diagnostic-name>` from `gui/atlas`. This is a reconstruction recipe, not a new execution of this packaged layout. Native controls were executed interactively through the built app, not by a headless substitute.

No product defect found. This report establishes the narrow native approval-to-RPC result boundary; it is not an ACK of every change in #714. Files are bound by [manifest.json](manifest.json). Raw local records/build caches remain retained. Existing fixture code and renderer originate in the BTX repository; this evidence reuses those contracts and Numair's implementation.
