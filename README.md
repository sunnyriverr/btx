# macOS wallet regressions for #475 and #476

Both maintained functional tests reached their intended failure in the baseline daemon and passed against the repaired daemon. The baseline was release-0.34.16 at `dac9aee5` with the respective wallet RPC source from Jpp-matata's #475 and #476. The final binary contains both independent repairs. The test and CLI hashes match before and after.

The runs used macOS arm64, Apple Clang, a SQLite wallet and fresh regtest data. Modelnet and Metal were disabled. The same daemon wrapper dropped the two Modelnet options absent from that build. Both tests ran with `--descriptors` against the build's `test/config.ini`.

| Test | Baseline | Final |
| --- | --- | --- |
| `wallet_locked_funding.py` | A locked wallet with 5 BTX returned -13 for a 10 BTX request. | The same shortfall returned -4. Fundable locked requests and sending after unlock passed. |
| `wallet_backupbundle_private_descriptors.py` | The blank wallet exported an empty descriptor list and returned a false passphrase flag. | Blank directory and archive exports passed. Populated-wallet signing and encrypted archive restore passed. |

[Baseline receipt](before-receipt.json) · [Final receipt](after-receipt.json) · [Source hashes](patch-identities.json)
