# Observed-preimage rollback — repair design review

**Verdict: the proposed narrow rollback is sound for the supported serialized coordinator caller. No design blocker found.** Review only; no product implementation, tests/imports, network or publication. Read the supplied diagnostic/source and the exact371013d6 native runtime worker source through local Git. This report does not qualify an implemented candidate.

## Correct repair boundary

Keep hashlock/preimage validation before any vault mutation. Only when the session-specific secret key was absent, insert the validated public-chain preimage, try save, and on Exception remove precisely that newly inserted entry and re-raise the original failure. Do not restore the entire dict from an old snapshot or touch prior entries. Let the exception prevent this tick's later secret_exposed/session transition and claim action, matching the existing failed-tick control.

This directly removes the faulty cache witness: after failed persistence, the next healthy tick sees the key absent and must attempt save again before proceeding. It preserves both preimage identity and retryability; it does not turn a filesystem error into success. Exception is appropriate here: errors during actual save still propagate after cleanup. No catch of process termination is needed to keep a soon-to-disappear in-memory cache clean. Avoid cleanup code that masks the original save exception.

Do not generalize rollback to ForeignKeyVault.create_key/new_secret or freshly generated private material. The independently tested startup BTC-key route resaves the earlier memory-only startup secret before the cached-secret branch; that control is materially different. This repair handles a validated public secret whose original chain evidence supplied the current insertion, not unconditionally regenerable private signing material.

## Concurrency and caller assumptions

The exact371013d6 src/swapnet/runtime.cpp:40–72 constructs one Engine inside Runtime::Work and executes Engine.Rpc, peer/message callbacks and Engine.Tick sequentially in that worker loop. The reviewed vault.save is synchronous: encryption, private file write, replace and fsync contain no product callback that intentionally mutates entries. Under that supported path, nobody can replace this same dict key between insertion and exception cleanup; removing the just-inserted key cannot remove another supported caller's later value. A new cross-vault transaction/lock framework is not required for this small repair.

Do not advertise the change as thread safety for arbitrary direct concurrent Python coordinator/vault mutation. Those public dict operations have no such existing synchronization contract. If implementation deliberately introduces an asynchronous vault writer later, ownership/rollback must be revisited; that is not a current gate. An identity-checked pop can be a defensive implementation detail, but must not obscure this single-writer reasoning or invite a broader concurrency rewrite.

## Failure after replacement

atomic_private_write can raise after os.replace when directory open/fsync fails (vault.py:31–35). At that point the new encrypted file may already contain the public secret even though this call did not establish its intended durability guarantee. Removing the newly inserted memory entry and re-raising is still safe: it does not delete the file, change old entries or erase session/financial records. A healthy same-process retry reobserves the same hash-bound preimage and saves it again. A restart may already load that secret from the replaced file; neither result should be mislabelled as rollback of disk publication.

The caller should not attempt to restore the old encrypted file after replacement or claim that every save error leaves old file bytes intact. The diagnostic only established that byte property for the pre-replace failure. This is why the scope should say “remove the unsuccessful new cache insertion” rather than “undo the disk write.”

## Focused qualification controls

Use the same observed-secret fixture and observable before/after contract. On stock source the desired healthy-retry durability assertion must fail; on candidate, the injected pre-replace failure must leave the new memory entry absent, old disk bytes/entries intact, session/operations unchanged, and the same healthy tick must durably save the identical observed secret. Reopen both vault and coordinator, verify exact identity and prior entries, and retain the no-extra-funding control. A manual save would conceal the caller defect.

Add one targeted post-replace directory-fsync failure only if implementing the described Exception rollback: establish that replacement actually occurred before the injected failure, that the file decrypts with the same new secret and old entries, that the new memory insertion was removed and the error propagated, and that healthy same-process retry/restart succeeds. Inject at the actual directory-fsync boundary rather than failing an arbitrary fsync call that may still precede replacement. This is a small disk-boundary control, not a native kill or power-loss matrix.

Retain a healthy observed-secret/restart control; an already-present secret/other entries control; invalid-preimage refusal before mutation; and the actual BTC new_key startup retry control demonstrating the untouched path. Source or test snapshots should prove cleanup removes only the newly added key, not private keys or unrelated secrets. No additional node build, full settlement rerun, real funds or platform gate is needed to establish these local persistence semantics.

## Claims and finish

After qualification, claim only that a failed observed-preimage save no longer leaves an in-memory cache entry that lets a later successful tick bypass persistence. Reobservation remains the observed recovery source. Preserve the diagnostic fact that the old implementation recovered once chain evidence was readable again; do not imply permanent funds loss, universal recovery with unavailable chain evidence, or power-loss durability. Finish with the narrow coordinator change, focused before/after/control results and exact source identity; no automatic publication or new campaign follows from this review.

## Final candidate source/test review

**Final source verdict: no blocking issue found in the supplied candidate.** Re-read the actual source/candidate coordinator diff and candidate/tests/test_vault_retry_durability.py. The parent reports matched stock3fail/4pass → candidate7pass with module paths/hashes; this reviewer did not execute or independently reproduce those results. Existing-control execution remains the parent's separate receipt.

The production diff implements exactly the reviewed boundary: inside the already-validated, previously absent session-secret branch, insert the observed entry; try the existing synchronous save; on Exception pop only this key and re-raise. Validation, existing-entry behavior, secret_exposed transition order, decision/claim/funding code, ForeignKeyVault and startup-generated private material are unchanged. The supported single-worker reasoning above applies without an additional lock or whole-vault snapshot restoration.

The maintained tests reach the actual failure/retry contract rather than merely checking the pop implementation. The observed-secret regression is parameterized over one and two pre-replace failures, records one replacement failure for each repeated tick, verifies unchanged session/operations and old disk bytes/entries, then calls the same tick with healthy storage. It checks the exact original preimage on disk and after coordinator restart **before another observation**, including successful vault.secret(hashlock) and another restart. The two-failure case would expose a still-cached unsaved entry because the next tick would skip the expected second failing save. The healthy-retry disk assertion likewise rejects the original one-failure behavior.

The POSIX directory-fsync control identifies an actual directory descriptor using fstat, fails after replacement, verifies the new secret is already readable on disk while the session has not advanced, then observes directory_calls==2 after the same healthy tick. That count discriminates a real second vault save from a no-op cache retry. The test correctly avoids claiming old ciphertext preservation after replacement or power-loss durability. It is explicitly skipped on Windows, matching the writer's platform-specific directory-fsync step.

The other four cases are useful legitimate controls: healthy observed-secret persistence/restart; actual Bitcoin UTXODriver.new_key startup resave of the identical original generated secret without funding; already-present observed secret leaves exact entries/ciphertext unchanged without rewriting; and invalid chain preimage raises PREIMAGE before vault/session mutation. Prior encrypted key/secret entries are checked through fresh decryption across the relevant paths. The tests retain deterministic chain/signing scope and direct coordinator-tick wording, and do not manufacture recovery through a manual vault.save.

No additional native/build/platform gate or broader failure matrix is requested. Subject to the parent's already scoped execution results and existing controls, the narrow candidate is ready for the authorized local repair closeout; publication remains separately held.
