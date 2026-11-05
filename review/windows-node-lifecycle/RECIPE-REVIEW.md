# Native Windows lifecycle recipe review

5 November 2026. Bounded pre-dispatch review by `/root/priority_gap_review`. Read lifecycle.py, inputs.json, workflow.yml, CONTRACT.md, existing integration support and dispatch filename mapping. Only this report was written. No product source/Git/network/build/test/CI/VM/ledger action or delegation; no native result is claimed.

**No blocking issue remains after the prelaunch log-offset correction.** Parent owns dispatch and final evidence verification. Product default/refusal semantics are reviewed against the retained parent contract, not a new independent product-source audit.

## Material catch resolved

The initial start function measured debug.log size after Popen. A fast warm start could append its new helper-missing diagnostic before that sample, causing the run to discard the very evidence it must verify. Parent moved size capture before Popen; I reread the corrected line. Per-boot excerpts now use the proper boundary. Full final debug logs are also copied on failure. Because both optional boots share a datadir, their full-log copies can contain both boots; the offset-scoped files are the per-boot evidence.

## Source/cache/build

The recipe pins source473a/tree d860 and checkpoint4c2cf014/cache10047590725. It validates the recorded source/profile, full source catalog, unchanged configuration and only the documented two-field host transition. Ninja remains1.13.2. Bundle SHA and prerequisite fetch are checked before restore; dispatch supplies the actual filenames consumed by lifecycle.py.

Node plan and build both use the exact original full graph through explicit `-C` and `-f`, target btxd only. The nonempty plan is bounded at120steps and rejects command invalidation, root CMake regeneration and glob-bootstrap. Actual j4/k1 compile/link is bounded at900seconds with the existing resource floor. No full unit target is launched. Before/after binary hashes, clean exact-source build-info, import/version checks and unchanged canonical modelnet-library hash identify the new node. This is incremental candidate relinking, not a clean stock build.

Retention requires unchanged source/config/catalog and no owned survivor or forced-cleanup event. A new source/profile/run cache preserves normal Ninja progress without replacing the original3830-object input. Checkpoint or compile success cannot be promoted into runtime success.

## Real runtime and policy controls

Primary omits modelnet/modelnetrequired switches, using one deliberately non-existent explicit modelhelper path. Per the retained caller contract this selects existing optional-helper/no-substitute behavior. It does not qualify ordinary packaged discovery, helper admission/transport or a real helper crash. Required=1 must naturally refuse startup with the named helper error; disabled=0 must be an ordinarily healthy control. The missing path remains absent.

Readiness requires actual cookie-authenticated blockchain/network/blockcount RPC, regtest height0, inactive external networking and zero peers, followed by five live health samples. Both default boots require fresh missing-helper/monetary-continues diagnostics. The same owned datadir and genesis best hash are checked after restart. This is height0 initialization/restart, not nonempty-chain persistence, catch-up, validation, wallet, mining or sync qualification.

Loopback/cookie RPC, disabled P2P/listeners/discovery/autoupdate/LAN follow and wallet disablement keep the owned regtest isolated. Healthy cases stop through actual RPC and must exit naturally0, remove the cookie, close the port and leave no owned child. Required refusal must exit naturally1 with the expected error; arbitrary startup failure is not accepted.

## Cleanup and credentials

Datadirs are in a new run-specific root outside uploaded evidence and cached build directories. Process snapshots are cumulative. Forced child cleanup is recorded in dedicated events/logs, prevents PASS, and is also refused by retention. A later empty snapshot cannot hide that intervention.

Cookie bytes only form the in-memory HTTP header. Result records do not contain the cookie or authorization header; RPC failures expose method/error code. The workflow uploads evidence only, not datadirs. Process arguments contain owned paths/endpoints rather than an explicit RPC secret. Parent still verifies actual artifacts/logs; source review alone cannot certify their eventual contents.

## Acceptance boundary

A pass establishes exact-candidate Server2025/clang-cl node initialization, ordinary loopback RPC, optional-helper continuity, height0 restart/stop, disabled control and required refusal. Full test_btx, accepted stock, Windows11/full-cl.exe, packaged helper admission, Windows Unix-RPC support, GPU/live network and release acceptance remain unqualified. Unexpected valid-control failures must be classified before proposing a product fix. No posting authority follows from this review.
