# Atlas recovery-export credential form

Verdict: same eight DOM checks yield 6 intended failures / 2 passes on ea64a31e, then 8 passes with repair. Four selected existing secret/JSON/prefill controls pass. Zero skips. Mac ARM64, Node 24.13.0. [Code](https://github.com/sunnyriverr/btx/commit/859223903cbf52e28b44abd53582d6ca08d9ea35).

Recovery export used a generic JSON textarea, leaving its passphrase unmasked after prepare and simulated native cancellation until the outer form closed. It now uses a confirmed password control and existing secret-field clearing before native review. A template request_object flag preserves the required [{passphrase:...}] wire shape. Native Rust approval and recursive credential redaction are unchanged. Ordinary positional and JSON forms retain their previous path.

Tests cover masked/confirmed inputs, no exact JSON credential editor, clearing before simulated cancel/unknown/success, object prefill, mismatch refusal, unchanged ordinary JSON routing and generated-schema agreement. Existing controls cover direct passphrases, secret-form inventory, ordinary exact JSON and numeric object prefill. These use Jpp-matata's existing minimal DOM fixture and Numair's operation templates. They are not native UI/approval execution: bridge responses are simulated, no wallet, node, real passphrase or export. No browser layout, OS native integration, Linux/Windows or release qualification. Preparation failure retains masked values until outer close, consistent with existing password forms.

## Exact identities

Tested base ea64a31e9b4f83375746ce2e65917bcb3c2026e9. Published on b921fc5e6a3a58d4ca661a270bf1dcfdd3ea5b08; intervening changes touch backend/ModelNet only, no gui/atlas files. This is a source-only rebase, not a new native build. qualification-receipt.json records original loaded file/test SHA256; logs are path-normalized. The final test was moved into maintained tests/ and identical bytes rerun on before/after. No product edits followed final review.

## Reconstruct

With two clean source trees at ea64a31e and the code commit above, copy candidate gui/atlas/tests/recovery-export.test.mjs into baseline tests/ and run in each gui/atlas directory:

```sh
node --test tests/recovery-export.test.mjs
```

Expect 6 failures / 2 passes before, 8 passes after. Existing selected controls on candidate:

```sh
node --test --test-name-pattern='passphrase|secret|prefill|exact JSON mode stays' tests/exact-json-mode.test.mjs tests/operation-prefill.test.mjs
```

Expect 4 passes. Original executions used these test paths in isolated local source copies. Exact payloads, raw outcomes and limits are in the adjacent manifest/logs. See candidate.patch for the five-file change. No native build needed for these component checks.
