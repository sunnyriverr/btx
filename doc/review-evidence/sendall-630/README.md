# Sendall test and watch-only sizing

Tested base: `8d6d8b1aabf371b12f2b1f5797b950fed7962d4e`.

The code and test at this commit match the sources used in the narrowed
candidate. Logs cover the original funding failure, the watch-only sizing
failure with the updated descriptor, both fee comparisons and the full
patched functional test. The fee probes used disposable regtest funds and
`add_to_wallet=false`.

Native macOS arm64, SQLite descriptor wallets, ModelNet disabled.
`wallet_sendall.py` passed all 23 scenarios with zero skips and exit 0.
Linux, Windows and the separate `wallet_sendall_pq.py` were not run.
Local paths were removed from the logs. See manifest.json for hashes.

To reconstruct, build the baseline and patched daemon from the pinned
sources and use the attached Python runners with the directory layout
they specify. The logged runs used those runners and locally built binaries.
