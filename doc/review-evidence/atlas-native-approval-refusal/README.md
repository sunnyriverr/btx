# Atlas native approval and wallet refusal

On macOS ARM64, the saved signed Atlas test app and matching node from `23ee567e` plus the frozen #858 candidate exercised one native `confirmswap` approval. The user approved the displayed regtest preview once. The node logged **one** `confirmswap`. Atlas displayed `RPC_-1 · WALLET_SELECTION`.

The node refused at its wallet selection check. No funds moved. Chain tip, UTXO stats, mempool, loaded wallets and the stored preview binding matched before and after. Swaps, mandates and reservations stayed at zero. The disposable node stopped with exit 0.

This was a zero-height local regtest node with no loaded wallets or peers, in observe mode. The preview's quote and signature were simulated. The wallet check refused the request before the observe-mode or expiry checks.

[Sanitized receipt, RPC count and checksums](receipt.json) · [Original #858 test recipe and build provenance](https://github.com/sunnyriverr/btx/blob/847ea0a9bccb973e477e4560259b068d9aa461be/evidence/atlas-market-review/README.md).

This follow-up reused the retained app, node and stopped-node seeding recipe with a fresh disposable node. It used the Atlas SwapNet `confirmswap` operation form with the seeded preview ID and a blank wallet. Before and after approval, the controller read the node's local state and checked the relevant SQLite row counts. The test used no rebuild or funded execution.
