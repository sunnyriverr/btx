# Adopted funding fee recovery — matched Mac qualification

Qualified component repair at `86e3ed9f0852033395082bc35aac9d7012f863c1`, based on `release-0.34.17@371013d61dc124a363521df5b94e97f64d2464f2`.

A restored/adopted payment can deliberately have no new funding operation. Refund fee replacement currently dereferences `fund_op` and raises KeyError. Raw adoption can instead save a zero fee placeholder, which is not trustworthy historical fee evidence. The repair preserves the genuine locally prepared fee path and resolves adopted fees through bounded read-only local-node calls before replacement preparation. It binds the fee to the original asset/genesis/txid/output/script/amount, preserves combined authorization and signed branch caps, and refuses unavailable fees without changing the payment or saved refund.

## Executed evidence

macOS 26.5.1 ARM64, Python 3.12.14; actual production coordinator/drivers and SQLite journal; deterministic chain/node responses and signing.

| Inventory | Stock | Candidate |
| --- | --- | --- |
| Identical maintained 34-case test | 31 fail / 3 pass (2.48s) | 34 pass (3.87s) |
| Existing runtime recovery, restored history and observation-only controls | Not repeated | 65 pass (12.90s) |

The 31 failures are cases distinguishing one recovery boundary, not 31 separate bugs. Both runs used identical test bytes (`134e6eae6fa3017e711e0d6bd2ea66e33354940822fb99ee886a3ce753649f92`); before/after result receipts assert loaded module paths and SHA-256 hashes. `qualification.json` records production hashes and the local extracted-tree commit; that local commit is not a full upstream-tree revision. Publication verifies the PR source bytes against those tested hashes.

Controls cover absent funding record and adopted zero placeholder; measured zero; exact combined-cap boundary and excess; unknown/invalid/fractional/extreme decimal fees; original output/chain mismatch; typed timeout and healthy retry; canonical-block hints; principal, branch cap and maturity. Refusals preserve original payment/refund bytes, pointers, operations, budget, grants and transaction map, with zero refund preparation calls. Healthy retry works after real SQLite reopen and persists without new funding. Successful replacement keeps old operations and adds only its refund operation/transaction.

## Execution entry point and replay

The local executed entry point was `run_tests.py before`, `after`, and `controls` under Python 3.12.14 with pytest 8.4.2 and cryptography 46.0.4. The archived runner has personal paths redacted; it records provenance rather than serving as a portable installer.

Portable reconstruction recipe (not separately executed): use two checkouts, stock3710 and 86e3ed9f0852033395082bc35aac9d7012f863c1. Copy only `contrib/swapnet/tests/test_restored_refund_fee.py` from the candidate into stock, then run in each checkout:

```sh
PYTHONPATH=contrib/swapnet:contrib/swapnet/tests python3.12 -m pytest contrib/swapnet/tests/test_restored_refund_fee.py -q
```

Existing controls run on the candidate using the same environment and `test_runtime_recovery_v2.py`, `test_restored_history.py`, `test_observation_only.py` under that tests directory. Use an isolated writable test directory, no production wallet/node.

## Limits and review

No native Bitcoin/BTX fee RPC, funded settlement, real signing, Linux/Windows execution, full-suite or release qualification. The reused history fixture has a BTC-wrapper/BTX-leg adaptation; the new regression restores coherent actual asset identity after adoption before fee lookup. Both BTC and BTX fee-reader identities are exercised with deterministic RPC replies.

Independent agent source review caught decimal rounding and response-validation issues before delivery; these are corrected and covered. That is code review, not independent native execution. An initial baseline invocation accidentally loaded candidate imports and is excluded; the final matched runner checks exact source roots and hashes. Logs/receipts below contain only the final counted runs.

See [qualification](qualification.json), [before](before.log), [after](after.log), [existing controls](controls.log), [source review](FEE-REPAIR-REVIEW.md), [manifest](MANIFEST.json). Reuses the maintained SwapNet recovery fixtures and existing contributor work; no new consensus rule or funding authority.
