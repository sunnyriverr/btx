# Native Windows wallet export comparison for #467

Repch1c’s production change from `a6173eefc576a8692698e86037f1917278d23d9c`, applied to release `dac9aee53520bd49ed320ec7a49b9072fc7d88d9`, passed the real `exportwalletbundle` failure and recovery comparison. The release’s later wallet changes were retained. The sole edited source was `src/wallet/rpc/backup.cpp`, with applied Git blob `5183cc404c8e3f8fa7768f1971734d832c0e74cb`.

| Control | Release baseline | Release with #467 production hunk |
| --- | --- | --- |
| Normal export | Valid 573-byte bundle | Valid 573-byte bundle |
| Existing destination | RPC -8, bytes preserved | RPC -8, bytes preserved |
| Full volume | Reported success, left zero-byte file | RPC -4 write failure, no file left |
| Retry at the failed destination | Restored after manually removing partial file | Restored without manual cleanup |

The same harness and generated seed were used for both zero-funds regtest wallets on Windows Server 2025 x64. Free space was zero on the capped 64 MiB FAT virtual volume before each fault call. Each successful retry restored a second wallet and matched the first receive address. Both nodes stopped cleanly, wallet directories were removed, and the virtual volume was detached and deleted. Existing-file protection passed in both variants.

The exact retained Windows checkpoint was transferred from Session 1’s build and verified before reuse. Eight build actions produced the candidate node with the unchanged toolchain and dependencies. Two preparation attempts stopped before wallet execution while the runner’s Ninja plan and vcpkg prerequisites were resolved. The original cache was preserved.

One matched wallet RPC sequence per variant. Windows 11, NTFS fault behavior, other backup RPCs and the full wallet suite were outside the test.

[Executed native run](https://github.com/sunnyriverr/btx/actions/runs/42799926443) · [Exact runner workflow](https://github.com/sunnyriverr/btx/blob/94539f0c5d5671af1658b79730dec1cb98f74557/.github/workflows/pr467-wallet-matrix.yml) · [Wallet harness](https://github.com/sunnyriverr/btx/blob/94539f0c5d5671af1658b79730dec1cb98f74557/wallet_export.py) · [Machine results](wallet-results.json) · [Build record](build.json) · [Build plan](candidate-plan.txt) · [Build log](candidate-build.txt) · [Volume cleanup](volume.json) · [Provenance and binary hashes](provenance.json)
