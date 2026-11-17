# Raw evidence review — run 44045340230

Verdict: no blocker found for the scoped automatic-search integration result. This is a source and archived-evidence audit; I did not execute the helper or rerun tests.

## Identities and build

- Accepted source: `ea64a31e9b4f83375746ce2e65917bcb3c2026e9`. Build receipt records exact tracked-byte verification, no retired tracked paths, 29,776 verified external checkpoint inputs and no differences. The bounded normal `btx-modeld` target compiled successfully in 32 actions / 497.084 seconds. The script does not inject a diagnostic adapter or product patch.
- Binary SHA256: `71f06f37edc1f680398ed2acf35711a38459e48e2bf7b5d84afce4e1ddf70258` in both build and runtime receipts.
- Test SHA256: `90ad5b3ddd2f931de1e7533f4ce6b13a427610ec0d44a7e4de3b4e43d65f8c32`, equal across local test bytes, input identities, build and runtime receipts.
- Helper/search source hashes match the previously reviewed implementation: `bf10a00b38d4f41fc3a69aefdff141a789ba4b4d3950e8dd01a51fba2e64ae17` / `175ab7d3cc8b110f50697e706bbc7050e157059435792fca17d367ba3bde1e8b`.

## Evidence independently checked

The native result is PASS in 38.790 seconds, UID/GID 65534, five helper starts, 22 recorded Unix RPC calls, five successful stages and zero remaining owned helpers. Startup logs identify normal PQ1 helpers with automatic spending zero; stop() requires exit code zero and treats kill-on-timeout as failure. Logs alone do not separately contain shutdown receipts, so clean-stop evidence is the successful checked harness path.

1. **No-contact control:** a fresh helper without the configured publisher is observed for 11 seconds without receiver RPC. It does not acquire the fixture IDs. This is a bounded negative control, not proof that all malformed/missing index files are healthy.
2. **Initial passive propagation:** the call ledger contains zero receiver RPC before all 17 signed records appear. Exact saved raw snapshots progress from 16 records at 16.848 seconds to 17 at 21.875 seconds. Every saved record field, including signature/public key/signer, matches the publisher export; all records share one signer. This exercises continuation beyond the 16-row gossip page, not just first-page delivery.
3. **Offline restart:** the source is stopped before receiver restart. The only two receiver calls in the entire test are then explicit LOCAL search and local raw export. All four remote query/response counters are zero; the raw export equals all 17 original signed records, and the successful harness verifies the saved index hash remains unchanged. The receiver index is already equal before either call. These calls therefore cannot explain the earlier passive positive result.
4. **Reconnect:** restarted publisher uses its existing state and endpoint, publishes record 18, and the receiver gains the exact 18-record map by passive observation. No additional receiver RPC occurs. Participation snapshots show the same 96-hex authenticated transport pin before/after restart, one authenticated peer, regtest, LAN discovery disabled, acquired_models=0 and automatic_spend_atoms="0".
5. **Health and cleanup:** the final path observes both processes alive and the exact receiver map for six seconds, then stops both cleanly. This is a short bounded health window.

For snapshots 2–5, I hashed the actual archived bytes and matched every hash to its observation receipt. Counts, ordered IDs and complete record fields match the recorded states: 16, 17, 17, 18. Snapshot 1 is correctly absent because the initial observation is no file/empty bytes, SHA256 `e3b0c442…b855`. observe_until saves the same raw bytes it hashes and parses; its separate success read is harmless here because the decisive complete maps are independently present in snapshots 3 and 5.

The 22 calls consist exactly of publisher 17 publishes + one export, receiver two offline LOCAL-only calls, then publisher one publish + one export. There is no receiver network search, import, retrieval, readiness RPC or rescue action. Source review of the LOCAL branch and automatic tick supports this causal separation; the publisher export reads metadata and does not push it into the receiver. The automatic configured-peer tick is the intended delivery mechanism.

## Claim boundaries

This is one successful normal Linux-helper integration on one host through explicit loopback peers, synthetic signed metadata and disposable regtest storage. It supports automatic metadata propagation, disk persistence across clean receiver restart, reconnect continuation, and a short healthy period. No product defect was demonstrated and no fail-before/pass-after claim is justified. It does not qualify physical LAN/WAN discovery, independent hosts, Windows/macOS runtime, real model-payload transfer or execution, payments, hostile inputs, abrupt power loss, long-duration health, full-suite or release readiness. The participation receipts themselves retain release_qualified=false.
