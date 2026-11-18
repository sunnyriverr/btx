# Atlas market native review — evidence

Verdict: two stale market-context regressions fail before/pass after; the final native trade-review path resolves the stored terms and Cancel submits nothing.

## Exact code and executed checks

Tested source: release-0.34.17 at23ee567ea8a2d9cad8ca3264f8793e8371b3eb93 plus the13-file candidate in candidate-manifest.json. Existing files preserve original Git modes. Product commit is linked from the PR; receipts retain actual input hashes rather than implying tests ran on a later commit. Publication-time release head a97af7b3 has14 changed files outside this patch; that head was not rerun.

| Boundary | Actual result |
|---|---|
| Actual market workspace + JS Bridge, controlled Tauri replies | Original4-case fixture2pass/2fail before→4pass after. Final union20 affected controls pass, zero selected skips. Review-driven stale-row correction and clean/late approval cleanup included; no financial execution. |
| Real Python Application/Host/SQLite |8 unique maintained methods pass: owner/principal/wallet scope, exact19field lookup, no implicit wallet binding/writes, malformed-record refusal, normal binding control, capability count56, and interrupted/reopened expired same-trade retry without a second trade. Chains/signing simulated. |
| Actual Rust formatter and production broker helper |5 formatter/parser +4 orchestration controls pass. Cancel, changed terms and preflight timeout have zero mutation dispatch; submitted mutation UNKNOWN/refusal/audit-error cases keep their original outcome and never retry. RPC/UI callbacks controlled. |
| Matched node + app | [Mac build44213267450](https://github.com/sunnyriverr/btx/actions/runs/44213267450):23edges/14C++compilations complete from verified retained cache. Final Atlas app builds/signature verifies. New compiled RPC registered owner/count56, missing preview refused, exact19 stored terms returned after restart. |
| Real native confirmation | Actual matched node and locally signed candidate app; one seeded simulated quote. User screenshot inspected and explicit user report confirmed exact assets/amounts/fees/wallet/IDs/deadlines and CANCELLED. Node log has0confirmswap dispatches; negotiations/reservations/mandates stay0. Both test node starts exit0; app quit, port closed. |

Node SHA b8aeceb1e87f66762617f3c87eba2bf7b9193895320ce3cdcaf1fa7c975b43dc. App SHA ac75eaadb91c861f5a8e0c45874c2d28b5941cc8b3344bffb7b76cda83012d08. Native build/runtime profile: macOS ARM64, walletON/SQLite with no loaded wallets, ModelNetOFF, MetalOFF, serial diagnostic CPU; no peers or mining.

## Maintained tests and reproduction limits

- `node --test gui/atlas/tests/swapnet-workflow.test.mjs` is the maintained focused frontend module. Raw receipts identify the selected case runs and reused passes;20 is a union, not20 newly repeated cases in each log.
- `PYTHONPATH=contrib/swapnet:contrib/swapnet/tests python3 -m unittest -v test_trade_preview_review` is the maintained backend module. The saved3.12 runtime reused an existing pure-Python pytest/pluggy dependency path; no install. Its exact invoked command is in the receipts. New capability control was run separately; earlier valid passes were reused.
- `cargo test -p atlas-core --test swapnet_review` is the maintained Rust test entry point. Local receipts describe the retained locked Cargo/native test linkage used; this command is guidance, not a claim of a fresh complete Cargo test run.
- The fork Mac build recipe and preserved checkpoint live in run44213267450. The native UI check used the exact saved app/node, a stopped-state seeded simulated quote, native cookie selection and human-assisted visual confirmation/cancellation. It is not an unattended or funded end-to-end recipe. Original native screenshot remains local because its background includes unrelated chat.

## Limits and credit

No actual confirmswap submission, native quote/signature qualification, funding/settlement, Linux/Windows, currenta97 runtime, default Metal/ModelNet, complete suite, coverage-percentage or release claim. Candidate-only native integration complements the focused component before/after; it is not a full native baseline comparison. Original previewswap/confirmswap functions are AST-identical; the added lookup does not extend expiry or grant funding authority.

Built on Numair's market implementation and existing repository market/storage fixtures. Implementation and internal review used Codex; that review is separate from independent human/platform acceptance. No additional public result or production qualification is implied by a CI success badge.

[Evidence manifest](manifest.json) maps retained original identities to the published path-redacted text. Logs and raw receipts are grouped under implementation/ and native-integration/.
