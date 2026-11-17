# Bounty undo/save retry — qualified normal-helper evidence

**Same actual-helper test fails before and passes after.** Code `9a4f575e13f90d5902466d4d74a2c7e7430a50c1`, stacked on #815 `13dcacc8632c552a22f23569c72c718e15aed6cb`, tested upstream base `bd847e2b986722c1723b4cd60988d4f4908452d4`. The repair-only commit changes one production file and adds the exact executed standalone regression. Credit repch1c for #468's atomic-save/error policy and #640/#796's saved facts and bounded undo; that policy is preserved for other bounty writes.


Publication update: upstream incorporated #815 during submission. Current PR817 code is `5cb66d5e5f513b7172a52ffca5cfb45089bdba14`, reparented onto `0f028a37c0e329a182be2582729ec974223970af` as one fix/test commit with **byte-identical qualified bounty.cpp and regression**. The newer base's bounty.cpp matches the tested815 baseline exactly; bounty.h, event_journal.cpp and model_watch.cpp are unchanged. Its helper.cpp delta only reports cloud-detach failure. Runtime evidence below remains the original bd847+815 pair, not a rerun of the newer integrated tree. Initial code9a4f575e is retained as the original publication mapping.

## Measured result

[Run44031548060](https://github.com/sunnyriverr/btx/actions/runs/44031548060), CI head a5c6e37b9a86a67bfb3b3fb0e7850298e359f00e. Ubuntu22.04/GCC11.4/x86_64 container on an Ubuntu24.04 hosted runner. Normal CMake btx-modeld target, real UnixRPC, UID/GID65534. One identical-script run per binary:7cases,14helper starts and144RPC calls each. Baseline completes all controls and exits7 (21of24 contract checks fail); candidate exits0 (24of24 pass).

With synthetic A100+B200, a real store-directory write refusal returns IO and leaves durable bytes unchanged. Before: live becomes100 and identical unkeyed/same-key retry consumes A too, saving0 across restart. After: failed request preserves live300 and undo history/epoch without publishing local or shared correction events; retry removes only B, retaining A100 across restart. Same-outpoint replacement restores earlier A100. Healthy remaining undo, keyed success replay, unrelated S50, verified re-observation/restart recovery and other-draft failed-save memory retention all pass. Shared-journal directory remains writable during the store fault, so premature publication is not masked. Raw calls also tie the successful candidate retry event IDs to journal provenance.

Start with `records/baseline/result.json`, `records/candidate/result.json` and `records/build-result.json`. The receipt records exact source/test/binary hashes and digest-verified record artifact14305488278. Candidate binary artifact14305413517 is retained remotely; it was not downloaded locally. Nine executed input files were remotely read back against their hashes. The baseline is the previously qualified normal #815 helper (`f62fb21f…`); only the repair helper (`79d69e94…`) was rebuilt. One31-action incremental normal-target build,509.47s; each native test4.58s. The owned checkpoint archive,29776external inputs and current tracked source bytes were verified before reuse. Source/evidence audits are included; they are not independent platform execution.

## Running the regression

The product branch contains the byte-identical script at `test/util/native_qualification/bounty_reorg_save_retry.py` (SHA2569f7313520600c366f8b99208f7364312b1043564e763323f554a1dd28322f9e1). It is not registered in the default functional runner. Run as an unprivileged user, with a usable runtime/OpenSSL provider and fresh disposable directories:

```
python3 test/util/native_qualification/bounty_reorg_save_retry.py PATH_TO_BTX_MODELD DISPOSABLE_RUNTIME_DIRECTORY OUTPUT_RECORDS_DIRECTORY
```

This exact invocation shape was executed from a staged copy of the script under /tmp. `workflow.yml`, `setup.sh`, `checkpoint.py` and `build.py` preserve the tested CI layout and dependency-checked build recipe; the recipe expects owned historical artifacts and fixed paths, so it is not a clean-build/one-command portability claim. The current full source comes from the product branch; baseline source is #815. Build normal btx-modeld by the repository instructions for a new environment. On Linux, directory permissions must genuinely deny the test user; root is explicitly refused. The script uses Unix sockets and POSIX identity/permission APIs; Windows needs a native equivalent fault fixture.

## Scope and tradeoffs

Synthetic watch-only observations, not wallet coins. No native Mac or Windows execution, funded/signing workflow, actual chain reconciliation, mainnet, full suite, disk-full/flush/power-loss qualification. One temporary complete index copy per explicit undo is O(facts+bounded undo) peak memory; ordinary observations are unchanged. The existing cross-store crash window after bounty commit and before journal delivery remains; no durable outbox or arbitrary post-commit exception exactly-once guarantee is added. Other bounty writes retain #468's intentional memory-on-failed-save policy. AI-assisted implementation/test preparation; execution and limits are recorded above.
