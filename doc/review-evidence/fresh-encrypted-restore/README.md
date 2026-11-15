# Fresh encrypted bundle restore: verified evidence

Published code commit: `ea76a312132e40936a0e8430e76ff324b5fd5398` contains the exact tested three-file overlay; commit metadata changed after execution, source bytes did not.

Base: `release-0.34.17` at `1e2f8b5f12295002334d3390c12cac0bb4ae2aff`, plus [the three-file patch](fresh-encrypted-restore.patch). The product fix is limited to `src/wallet/rpc/backup.cpp`; the other files add/register the recovery regression.

A fresh encrypted deferred restore derived a fallback seed before installing the bundle. On pruned history its search retained keys, causing the seed-protection guard to reject a fresh destination. The patch skips that pre-install derivation only for the successful fresh-creation caller. The material check and existing-wallet state-loading guard remain.

Credit JPP (Jpp-matata) for the #703 restore control, Numair for recovery guidance/adoption, and repch1c for #717/#741 and the maintained import-guard test. These existing implementations and helpers are reused.

## Actual checks

| Check | Result |
| --- | --- |
| Same recovery test, unpatched base | **FAIL, 72s** at fresh encrypted deferred restore, RPC -4 seed guard; [before run](https://github.com/sunnyriverr/btx/actions/runs/43769085141), [receipt](before.json) |
| Same recovery test, repaired base | **PASS, 111s**; [after run](https://github.com/sunnyriverr/btx/actions/runs/43770868266), [receipt](after.json) |
| Maintained `wallet_importbundle_shielded.py --descriptors` | **PASS, 47s** on repaired base |
| Incremental `btxd`/`btx-cli` build | **PASS, 19.23s**, 10 planned steps, 725 restored objects; [log](build.log), [build result](build-result.json) |

The normal runner reported two Passed test rows and Passed ALL. Recovery reached actual pruning (pruneheight135, tip461), honest incomplete state and full-scan refusal, restart, same-database full-history recovery of the exact note, a confirmed payment, restart persistence and later receiving. The maintained guard test covers legitimate import, same-seed/funded-wallet refusal and subsequent own-note spending. All amounts and keys were disposable regtest fixtures. Owned processes and wallet/chain/cache data were cleaned.

The new recovery test and runner registration are byte-identical to the before run. Source/test/binary identities are in [qualification-receipt.json](qualification-receipt.json); [SHA256SUMS](SHA256SUMS) hashes the attached files. The original full native record artifacts are linked from that receipt. The small records ZIP was downloaded and digest-verified; the repaired build checkpoint was retained but not independently restored.

## Test entry point

With a matching configured wallet/SQLite build, the normal runner selection is:

```sh
python3 test/functional/test_runner.py wallet_seed_pruned_recovery.py wallet_importbundle_shielded.py --configfile=/path/to/build/test/config.ini -j1
```

This is the selection executed by the [pinned hosted driver](https://github.com/sunnyriverr/btx/blob/36a8fe774cda3e5adc3b59accf3eebd28983d259/wallet-fix-run.py). The hosted driver additionally bounds time/private storage, hash-checks executables and collects structured results. The in-tree test runs without that outer driver or any required recording option.

## Limits and setup notes

Ubuntu24.04 x86_64, Release CPU wallet/SQLite profile ([configuration](profile.json)); two selected functional tests, not the entire suite or a cold build. No Windows/macOS runtime, production-wallet, corruption, dedicated issued-index-only, concurrent-issuance stress or abrupt-interruption qualification. Internal source review is not independent platform replication. No consensus/proof-profile rule was changed by the fix.

One superseded setup job was cancelled during checkpoint restoration before compilation/tests to correct accounting for deliberately excluded `.github` files. An unchanged unused-function compiler warning is present in both base and repaired build logs. Neither is counted as passing test evidence. Qualification receipts are immutable execution snapshots; their publication flags describe the state when recorded.
