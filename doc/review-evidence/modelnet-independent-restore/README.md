# Independent ModelNet copy / CLI restore / restart: scoped PASS

Documentation base: main074dac167c26c1e091198f691ed5727817dba88a. Runtime: previously verified949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72 Mac command-line archive, source-compatible for these paths. No new build. Local macOS26.5.1 arm64/M4, wallet-disabled regtest, explicit external helper,8MiBquota, no listening transport/peers/LAN/NAT-PMP, SwapNetoff.

## Observed

Nine offline controls passed: file/hash/set/path/symlink handling, copy versus hardlink independence and required-row/failure/cleanup verdicts. Native run used the actual packaged btx-cli for five calls, all exit0: initial import/export, import from independent payload into a fresh helper modeldir, export, then export after same-store restart without a second import.

Two tiny files13bytes: model.safetensors10bytes (zero tensors) and assets/config.json3bytes. Export recorded both IDs and file SHA-384/size metadata. Ordinary file copies had distinct device/inode pairs from both original and managed checkout. Saved verification metadata stayed outside payload. Old original/modeldir were renamed under preserved-* paths, not deleted; fresh helper storeB had no old catalog/source path. Independent-copy import returned identical model/artifact IDs, and files were exact after restore and restart. Backup and originals remain exact. All six helper/node children exited0; PIDs absent/socket removed. Initial plain port-bind audit saw TIME_WAIT, not a listener; no listener remained and SO_REUSEADDRbind succeeded. No native rerun needed.

This is same-host logical-copy independence, not physical-drive-loss, timed-crash/power-loss, large-model, useful inference, cloud/peer, other-platform, full-suite or release qualification. Do not treat a tiny structural fixture as a useful-model result. Metadata such as aliases/private publisher keys/config/jobs/history was not restored or qualified.

## Inputs and reproducibility

Archive SHA25622ee49b866f7d1539387d7e30bc82b38174b0925e84a103f590d92485569de73. [Prior archive provenance](https://github.com/sunnyriverr/btx/blob/e7e1954fa9b7ebe24eff01586ad2adca8693248f/doc/review-evidence/integrated-mac-949/README.md). restore-manifest.json lists exact wrapper/native binary hashes. Replace `<BINARY_EVIDENCE_ROOT>` with the restored existing artifact tree; unchanged expected hashes are verified before services start. The public manifest also hashes the exact CLI Python source retained from the prior first-run profile, although this test calls packaged native btx-cli, not that script. Preserve that file for manifest verification.

Executed driver independent_restore.py and offline controls are included. Published paths in responses/logs/manifest are redacted; values and outcomes preserved. This path-adjusted reconstruction has not itself been rerun:

```
python3 offline_restore_controls.py
python3 independent_restore.py --run --manifest restore-manifest.json --scratch /tmp/btx-s2-export-UNIQUE --rpc-port 39631 --p2p-port 39632
```

Use a fresh owned scratch and free ports,1.35GiBinitialfree/1.25GiBreserve,48MiBscratchcap and900sworkflowdeadline. Do not point it at production data. Failed/skipped/missing required rows or bad cleanup cannot become PASS. Original raw local evidence retained separately; redacted files have SHA256.json checksums.

## Related evidence / credit

Numair's [retained-export contract](https://github.com/btxchain/btx/issues/613#issuecomment-6889166021) supplies the intended supported boundary. [Earlier Linux recovery evidence](https://github.com/sunnyriverr/btx/tree/24914510fefbb2864f7e2157170676fb2b2bce66/doc/review-evidence/modelnet-catalog-recovery) qualifies one-file surviving-checkout reimport/restart with retained707helper/olderRPCproxy, not an independent-copy/currentwhole-daemon result; credit to repch1c for the original fixture and quota work. Current source comparison confirmed ImportPath/MaterializeCheckout/MaterializeFile equal the prior f40trace. Existing recovery walkthrough and its attribution are preserved unchanged; the product patch only appends a section.
