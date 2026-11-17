# Vault observed-secret save/retry — matched Mac evidence

Qualified component repair at `0c5cfd2e037af3474cd9ffb21ac2836a858dcb6b`, based on `release-0.34.17@371013d61dc124a363521df5b94e97f64d2464f2`.

The coordinator inserts an observed preimage into the live vault before saving. If save fails, the old ciphertext file is protected but the entry remains in memory. A healthy retry sees that entry, skips save and persists exposure state. Restart then lacks that secret. The fix removes only the newly inserted observed entry when save raises, and rethrows: retry must save before advancing. Generated startup keys/secrets and previously durable entries are not rolled back or rewritten.

## Executed qualification

macOS 26.5.1 ARM64, Python 3.12.14, pytest 8.4.2, cryptography 46.0.4.

| Inventory | Exact stock3710 | Candidate |
| --- | --- | --- |
| Identical maintained7-case regression | 3 fail / 4 pass, 2.37s | 7 pass / 0 skips, 3.09s |
| Existing execution, EVM-vault and terminal-observation controls | Not repeated | 45 pass / 0 skips, 7.40s |

Maintained test bytes in both roots: SHA-256 `b5ab66175c056b8dc079bd5b300a176653c61ab456f8dbe0cbb3b6b34838723d`. Loaded source roots and SHA-256 identities are asserted and recorded in the before/after/control receipts. `qualification.json` retains the local extracted-tree commit identity; that is not a full upstream-tree revision. The public PR code bytes are verified against the qualified source hashes.

The cases cover healthy persistence; one/two pre-replace failures; healthy same-coordinator retry saving the exact original preimage; real vault/SQLite reopening before any chain reobservation and a second restart; preserved old keys and an unrelated saved secret; actual Bitcoin new_key startup retry; an existing durable secret not rewritten; invalid preimage refusal; and POSIX directory-fsync failure after replacement, followed by a second real directory sync on healthy retry. All7 ran on Mac, zero skips. The directory-fsync case explicitly skips Windows, which does not execute that writer step.

Actual production vault encryption (AES-GCM/Scrypt), private temporary file writes, flush/fsync/replace, coordinator and SQLite are exercised. Faults are injected at the selected fixture vault's replacement or directory-sync step. Startup uses actual local Bitcoin key creation with a deterministic address reply. Pair chain observations, transaction construction and signing are simulated. No live wallets/nodes or funding.

## Execution entry point and portable replay

Executed local entry: `run_repair.py before`, `after`, `controls` under Python3.12.14. The archived runner has personal paths redacted; it is a provenance record, not an installer.

Portable reconstruction recipe, not separately executed: use stock3710 and 0c5cfd2e037af3474cd9ffb21ac2836a858dcb6b checkouts. Copy only `contrib/swapnet/tests/test_vault_retry_durability.py` from candidate into stock, then run inside each isolated checkout with the dependencies above:

```sh
PYTHONPATH=contrib/swapnet:contrib/swapnet/tests python3.12 -m pytest contrib/swapnet/tests/test_vault_retry_durability.py -q
```

Existing controls ran on candidate: `test_execution_v2.py`, `test_evm_vault.py`, `test_terminal_observation_persistence.py` under `contrib/swapnet/tests` using the same environment. Use a disposable private test directory, never a production wallet/node.

## Limits and review

This proves a local persistence contract, not permanent fund loss: with readable original chain evidence, the old code can reobserve and save the same secret after restart. No native Bitcoin/BTX settlement, Linux/Windows run, full suite, kernel crash/power-loss or release qualification. After a directory-sync error the new file can already exist; the fix neither restores the old disk file nor claims power-loss safety.

Independent agent source review found no blocker in the exact candidate and tests; this is not a second platform execution. No product format, crypto, spending authority, maturity, preimage verification, signature or fee policy change.

See [qualification](qualification.json), [before](before.log), [after](after.log), [existing controls](controls.log), [source review](REPAIR-REVIEW.md), and [published manifest](MANIFEST.json). The original diagnosis is separate historical evidence; the counts here use only the final matched contract tests.
