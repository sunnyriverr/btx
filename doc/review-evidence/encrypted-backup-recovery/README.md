# Encrypted backup restore guidance: tested Linux result

**Tested restore guidance on [8296d028](https://github.com/sunnyriverr/btx/commit/8296d028bfc942b38b1e8957ca0e8df7692d2277): the same regression fails on the absent warning before the change and passes afterward. Recovery remains explicit, not automatic.**

A supported stale encrypted backup can omit a confirmed payment to a genuinely later-issued address. Unlocking derives the address but does not revisit its historical payment. The common `RestoreWallet` warning explains finite keypool refill and explicit `rescanblockchain` recovery, preserving existing warnings. RPC and Qt callers share this warnings output; no unlock/scanner/derivation/encryption implementation changed.

JPP documented the underlying locked-PQ limitation in [#475](https://github.com/btxchain/btx/pull/475). This contribution adds the supported backup case and user-facing guidance; it does not include or supersede JPP's funding/fee-bump changes.

## Executed qualification

- Base `dac9aee53520bd49ed320ec7a49b9072fc7d88d9`, Ubuntu 22.04 x86_64, gcc 11.4.0, OpenSSL 3.5.9, retained exact-source build cache. The identical maintained test has SHA-256 `018fb524954a5351ecbd09a13b7de02b66f1169a3f9c9b9620959468954e3d04`.
- [Baseline run42738874911](https://github.com/sunnyriverr/btx/actions/runs/42738874911): all receipt/rejection/recovery controls complete, then the final warning-count assertion fails `not(0 == 1)`. See [baseline stdout](native/baseline-test.log).
- [Corrected candidate run42739600041](https://github.com/sunnyriverr/btx/actions/runs/42739600041): maintained test PASS, 39.01 seconds; candidate compilation 47.52 seconds. See [candidate stdout](native/candidate-test.log) and [final machine-readable result](native/final-result.json).
- Both native runs verify ordinary locked-wallet receipt, plain-backup recovery, failed restore, locked refill and wrong-passphrase rejection, exact two confirmed outpoints/total3 test coins after explicit refill/rescan at the same tip, and final relock. Candidate emits exactly one new recovery warning and retains the existing shielded warning.
- Daemon and Qt link; CLI binary unchanged. Full binary/source/patch hashes and retained-artifact identities are in [completion receipt](provenance/completion-receipt.json); [manifest](manifest.json) hashes this evidence. Both test matrices contain the new test, checked offline; this was direct test execution, not a full test-runner invocation.

The wallet fixture explicitly sets `-matmulvalidation=economic -matmulrcexecution=cpu-diagnostic`, keypool4, Modelnet off and auto-shielding off. It mines only disposable local regtest coins. This is wallet-guidance/recovery evidence, not default consensus or release qualification.

## Reproduction and provenance

The executed [initial workflow](executed-recipes/initial-workflow.yml), [qualification script](executed-recipes/qualify.py), [candidate resume workflow](executed-recipes/resume-workflow.yml), [resume script](executed-recipes/resume.py) and [checkpoint helper](executed-recipes/checkpoint.py) retain the actual cache/toolchain/configuration gates. These are original CI fixture files, not a newly executed reviewer package. Their original CI paths are recorded in those workflow files.

For a fresh source build with the appropriate wallet/SQLite features, the maintained invocation is `python3 test/functional/wallet_encrypted_backup_recovery.py --descriptors --configfile=<build>/test/config.ini`. That is the conventional fresh-build adaptation; our executed commands/configuration are in the native result and config logs, using source-matched binaries and an external checked config.

The first candidate attempt reused a stale baseline object because `copy2` preserved an older source timestamp. Its failure is retained in [invalid-candidate build](native/invalid-candidate-build.log), [invalid-candidate stdout](native/invalid-candidate-test.log) and [first result](native/first-run-result.json); it is not counted as a qualified candidate. The corrected runner requires newer source, a planned/rebuilt wallet object and a changed daemon hash before testing. It reused the already valid baseline proof without rerunning that test. Original inputs remained unchanged; runtime directories and owned processes were removed without forced cleanup.

The final code commit preserves exactly the tested source/test bytes. The existing runner's executable mode was restored from the pinned Git tree; the final patch was applied offline and its bytes/modes verified. That metadata correction did not change the direct test's executed content.

## Limits

No automatic historical discovery or unlimited derivation search is added. A successful explicit scan needs the relevant history and address range. Qt warning forwarding is source-reviewed and its binary links; actual Qt restore/dialog display was not exercised. No native legacy/watch-only predicate cases, Mac/Windows, pruned/cancel/concurrent/restart-after-gap, full wallet suite, default consensus, mainnet or release qualification is claimed. Existing shielded rescan/relock behavior is preserved, not newly qualified across those scenarios.

Only selected build/framework logs and provenance are included: no wallet databases, cookies, private descriptors or stores. Production wallets and the working node were untouched.
