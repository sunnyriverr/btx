# Default P2MR wallet receive and change coverage

Both functional tests ran on local Mac ARM regtest with the verified daemon and CLI built at release base 7d65025b. Input hashes matched before and after. The receipt records zero build-tool invocations. Logs shorten the local work directory path.

| Case | Result |
| --- | --- |
| Updated rpc_pq_wallet.py | Pass, 24.78 s. The fresh wallet had one active P2MR descriptor and 100 configured keys on each side. The default receive and change addresses belonged to their respective descriptors. |
| Unchanged wallet_btxwallet.py --descriptors | Pass, 5.28 s. Existing bundle and public descriptor checks passed. |

The patch changes one default-suite test. The inherited wallet_descriptor.py, including its legacy and SQLite checks, is byte-identical to the base. The inherited compatibility case was not run and its reported failure remains open. Linux, Windows, the full suite and mainnet are outside this run. [Retained binary build](https://github.com/sunnyriverr/btx/actions/runs/44975711173) · [Repch1c’s earlier diagnosis](https://github.com/btxchain/btx/pull/920)
