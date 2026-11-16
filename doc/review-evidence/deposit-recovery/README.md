# Watch-only deposit accounting recovery — scoped PASS

Product commit `68018960e528b95ae4e65ec737f0d820f1a6435c`, base `1e2f8b5f12295002334d3390c12cac0bb4ae2aff`. Test-only: new functional script plus one normal-runner registration. Credit JPP (Jpp-matata) for the A-STORES lifecycle plan and repch1c for deposit fixtures/reporting regressions.

Ubuntu24.04 x86_64 Release CPU/SQLite wallet, ModelNet/external signer disabled, retained binaries with no rebuild. [Run43789061021](https://github.com/sunnyriverr/btx/actions/runs/43789061021): `test_runner.py wallet_bcp1_recovery.py -j1`, configured using the retained build config. Selected descriptor case and ALL Passed9s;36.04s including cache/setup/cleanup. Exact status/amount/block identity/depth, complete duplicate-free ordinary/include_spent lists and spent_by survived wallet reload and clean restart. Live disconnect/reconfirmation passed before restart.

Source/binary/input/artifact identities and cleanup are in [verified-receipt.json](hosted/verified-receipt.json). Process group absent; private data removed; peak sampled40,198,637bytes. Raw wallet/RPC logs were not uploaded. [Assertion controls](assertion-results.json) exercise the actual assertion method offline: valid response passed,9altered responses rejected; no native coverage implied by these controls.

Three initial CI setup attempts are recorded: missing added-script build link, invalid -nomodelnet option in a build without ModelNet, then diagnostic confirmation. The final fixture checks build configuration before adding that option. No accounting assertion was weakened.

No product defect demonstrated. No fullsuite, crash/power-loss, restart-during-disconnect, mempool recovery, notification/ZMQ, signer or native Windows/macOS qualification. ModelNet-enabled setup branch source-reviewed only. This is a finite recovery slice, not complete BCP/1 certification.
