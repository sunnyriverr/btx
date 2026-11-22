# Operator retry for finalized ETH withdrawal failures

Tested release base `d9a9480484cea303649f3eab1e82f8e3d7572c21` on Mac ARM64, Python 3.11.14 and Anvil 1.9.0 (`6056c584`). Both arms used the same pinned Solidity 0.8.24 contract. One deliberately low gas estimate triggered a real reverted transaction on disposable Anvil. The fixture seeded swap state and exercised production Python request dispatch, signer, journal and vault.

| Credited payout | Stock | Candidate |
| --- | --- | --- |
| Claim | [0.1 ETH stays credited](claim-stock.json) | [Exact payout once across reopen](claim-candidate.json) |
| Mature refund | [0.1 ETH stays credited](refund-stock.json) | [Exact payout once across reopen](refund-candidate.json) |

The traces retain the original fee allowance and gas charges. The patched path refused pending original attempts, fees above the remaining allowance, unauthorized callers and ambiguous credit. An interrupted retry reused the persisted operation. Native BTX daemon, CLI and Atlas execution are outside these tests.

## Reconstruct the matched run

Use the specified release commit once for stock and the PR head for the candidate. Install the selected source tree's SwapNet Python test dependencies in a local environment. Set `PYTHONPATH` to that tree's `contrib/swapnet` and `contrib/swapnet/tests` directories. From this evidence directory, run the following for each tree, replacing `stock` with `candidate` for the patched tree.

```sh
python3 -B qualify_retry.py stock /path/to/anvil SwapNetHTLC.json
python3 -B qualify_refund_retry.py stock /path/to/anvil SwapNetHTLC.json
```

The harness started Anvil on a disposable loopback endpoint and cleaned up its state. The source and evidence hashes are recorded in the [manifest](MANIFEST.json).
