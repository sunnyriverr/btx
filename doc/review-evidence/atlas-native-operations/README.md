# Atlas afd65919 — native operation acceptance

Scoped PASS for Numair’s requested Mac export-preparation refusals and native PSBT warning comparison on `afd6591970e7f8d65871412b9d7cf03b48f30b97`.

Start with REPORT.md and summary.json. fixture.json contains only public synthetic unsigned data. progress.json transcribes the native refusal observations; user-evidence.json records screenshot observations and hashes. Full original screenshots include background conversation and are retained privately. The internal reviewer read them; this is not independent execution or release qualification.

Exact app/source/build identities: [preceding build evidence](https://github.com/sunnyriverr/btx/tree/477bb1b9b990d2954a2b47a0578b37d7910a8551/doc/review-evidence/atlas-afd65919-mac). The same app was reused without rebuilding or modifying its source. macOS26.5.1 arm64.

## Reproduction

1. Build that exact Atlas commit as documented in the linked build evidence. Connect through its native UI to an owned peerless regtest node with wallet RPC support and **no loaded wallet**. Our older fixture node hash is recorded in summary.json; it is RPC infrastructure only. Do not connect production wallets.
2. Tools → RPC console → exact method → Open command. For each of `exportwalletbundle`, `dumpmasterprivkey`, `z_exportviewingkey`, use default raw `[]`, blank wallet context, then Prepare for native review. Expect `KEY_EXPORT_DENIED`; correlate node RPC logging to verify these method calls are absent.
3. Open `walletprocesspsbt` from the same console. Paste fixture.json’s PSBT into the native form. Leave sign and bip32derivs checked and wallet context blank. Set sighashtype `ALL`; prepare and inspect the real native “Authorize exact operation” dialog. Expect the fixture hash and transaction skeleton, ALL, PSBT placeholder, no signature-reuse warning. **Cancel** and verify CANCELLED in the app.
4. Repeat the same synthetic PSBT with `NONE|ANYONECANPAY`. Expect matching hash/skeleton and the explicit warning quoted in user-evidence.json. Cancel and verify CANCELLED. Do not approve signing or broadcasting.
5. Verify no target method invocation for the cancelled cases; stop owned app/node and remove disposable cookies/data. Our initial uncaptured pilot did reach the empty node and returned no-wallet error; that one RPC is disclosed and excluded from cancellation evidence.

The control tool could not read macOS modal dialogs, so a human supplied screenshots and cancelled. The instructions above describe the exercised path, not an unattended script. Raw PSBT placeholder coverage is not a claim about recursive secret redaction. No named/wrapped parameter, HTLC/timelock, signing, Windows/Linux, full-suite or release qualification.

SHA256SUMS.json verifies sanitized public bytes. Original-local hashes in summary.json identify pre-sanitization records. No product code changes are included.
