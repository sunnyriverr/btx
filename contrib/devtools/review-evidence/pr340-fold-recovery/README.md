# Requested PR340 integrated recovery check

PASS on3c1e9b4a, macOS26.5.1/M4/AppleClang17. Same immutable1024-body pinned-consensus strict-Metal harness; no product change. Four requested counters and complete limits are in REPORT.md/summary.json. This is scoped toy-regtest recovery, not a whole-PR Tested ACK, mainnet, full-suite or release qualification.

Requests4107, mean4.0107421875, max85; source staysconnected; retained-body evictions3067; capacity-deferral messages0. All1024local replayflags persist through restart, fresh1130 and30shealth. Churn remains; this run does not exercise the dispatch-storefull fallback. Prior counters are retained-log analysis only; differences in a single run are not a demonstrated retry improvement.

## Reproduction

The exact harness `pinned_snapshot.py` and exact test-only1124 snapshot metadata patch are included; harnessSHA838d2454c6e65fbc709c1e8469297ad5ea1c2492f90978121a001af17ad51678 is unchanged. Apply the metadata patch ONLY to an isolated3c1e9b4a test checkout, configure/build normal Metal-enabled btxd and btx-cli with the recorded options. Do not apply it to production.

The harness expects the original fixture layout beside its file: fixture-run/node0/regtest, plus fixture.json; and ../toolchain-2026-10-31/source/test/functional for its unchanged framework import. That source/framework tree is byte-identical between original70e35da0 and3c1e9b4a. The launcher records the actual tested head/config/binary paths. Paths in published launcher/setup logs are placeholders (/BTX_REVIEW_ROOT); adapt paths to a disposable local layout, not the assertions or snapshot commitments. The launcher was not a new functional-test implementation.

The exact disposable fixture is in the prior public evidence archive https://github.com/user-attachments/files/34228589/pinned-metal-snapshot-evidence.zip (SHA d82b378774f305137e5db002e74e518a60994f3e4e3619be5caa278b97babd0b). Its fixture-run/node0/regtest subtree contains the source databases/block files and exact snapshot. Restore that subtree before startup; snapshot hash alone does not prove the cached chain exists. Our first setup found those old cache files missing and failed at source0!=1124, before the scenario. Restoring22byte-identical files from that archive fixed the fixture; this excluded setup is disclosed, with no product/harness changes.

`target-net-events.log` preserves selected native log lines with original line numbers. Full raw source/target log hashes are recorded; absolute local paths only are redacted in public text. No token/cookie/wallet/private deployment files included. requests-per-hash.json supports exact max/mean recomputation; analyze.py records counting semantics. Cached executables, libraries and complete node directories are not committed.

AI-assisted testing/evidence by Sunny River. Existing upstream authorship retained; JPP incorporated the capacity fix and requested this integrated run. JPP's separate full test_btx Mac/unit evidence remains his result, not ours. No new tests were executed to publish this branch.
