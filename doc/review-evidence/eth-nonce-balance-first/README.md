# ETH nonce reservation ordering

Paired traces from macOS ARM64 with Python 3.11.14. The harness exercised BTX's production SwapNet coordinator, signing and durable SQLite journal against simulated chain replies and peer delivery. The stock source was pinned to release-0.34.17 at 7d65025b.

With insufficient gas, stock reserved nonce 0 before failing. After normal cancellation, reopen and top-up, a distinct payment returned NONCE_HELD before signing. The candidate created no reservation on insufficient gas. After the same cancellation, reopen and top-up, the distinct payment signed at nonce 0 and made one broadcast call to scripted RPC.

The same-open-swap retry passed on both versions. The signed and recorded pending operation remained byte-identical across reopen. Its original nonce was protected while the chain reply stayed at 0, and the next operation prepared at nonce 1 after the reply advanced. The candidate reserved nothing when the balance read failed. Both versions refused a fee-cap failure before reserving a nonce. The patch leaves existing reservation rows intact, including historical stranded rows.

[Stock trace](paired-stock.json) · [Candidate trace](paired-candidate.json) · [Executed harness](qualify.py) · [Pinned fixture and source blobs](source-pin.json)

For reproduction, make stock and candidate fixture trees from the pinned `contrib/swapnet/swapnet` package. Place the pinned `test_execution_v2.py` at the root of each fixture tree, and apply the PR patch to the candidate package. With the existing SwapNet test extras installed, run `PYTHONPATH=path/to/stock python3 -B qualify.py stock` and `PYTHONPATH=path/to/candidate python3 -B qualify.py candidate`. The traces contain identifiers and counters, with no signing keys or raw transactions.
