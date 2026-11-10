# Model import retry and clean-restart observation on #503

**Bug observed at exact repch1c #503 `08fd0a6245598e8f9fedc6dac97629310335dd2d`: an import retry returns success/PINNED without a durable catalog entry. After clean restart, the model is absent and ordinary re-import is refused.** This branch adds evidence only; the product tree remains the tested author's tree.

## Measured journey

1. Healthy control: import two distinct tiny model fixtures; clean restart; both catalog entries, re-import and byte-exact exports pass.
2. Fresh helper with healthy model A: obstruct only `modeldir/catalog.json.tmp` with a nonempty directory. Import B returns `IMPORT_FAILED: catalog write failed`; the old catalog is byte-identical. B's exact stored payload already exists.
3. Remove the obstruction and repeat the same import request. It returns success and `PINNED`, but B is only in memory. Listing, two-second background grace and clean shutdown do not persist it.
4. Restart: A is unchanged and exportable; B is absent from the catalog/library. Re-import B returns `IMPORT_FAILED: destination artifact exists`; export by B's model ID returns `NOT_FOUND`. Both stored payloads remain byte-identical to their inputs.

This is false acknowledgment and orphaned catalog reachability, **not destruction of model bytes**. No fix was built.

## Exact execution and evidence

- Base: release `dac9aee53520bd49ed320ec7a49b9072fc7d88d9`; tested author tree `1fa445dd7b06901baf7888b97e6dbf79ac02ef0e`.
- Native Ubuntu22.04 x86_64, GCC11.4, retained OpenSSL3.5.9. Thirteen incremental helper build actions; original immutable checkpoint unchanged.
- Helper SHA-256 `2752a364a568d7032743c7020c2f9b621db97df32dbb5cffc81d6aecbda128dd`.
- [Executed CI entry point, complete build/native logs and artifacts](https://github.com/sunnyriverr/btx/actions/runs/42921100457).
- [Immutable executed workflow](https://github.com/sunnyriverr/btx/blob/12763af1bbf4b1877bfeb1e01e61f3805f33d63f/.github/workflows/model-import-recovery.yml) and [build recipe](https://github.com/sunnyriverr/btx/blob/12763af1bbf4b1877bfeb1e01e61f3805f33d63f/build_helper.py).
- [Exact executed fixture](native_fixture.py), SHA-256 `fcfb2d3c0b963fd11880b588552ac7eb76bc814a8e0a36e4a985d7c65e7dde71`.
- [Raw observations and RPC transcript](summary.json), [source/binary provenance](build-result.json), [claim receipt](completion-receipt.json), [artifact digests/file hashes](artifact-receipts.json), [internal result review](result-review.md).

The executed command was `python3 native_fixture.py --binary helper-binaries/candidate --expected-sha256 2752a364a568d7032743c7020c2f9b621db97df32dbb5cffc81d6aecbda128dd --output native-records`, from the isolated CI workspace after build verification. This evidence copy is byte-identical; it was not run again for publication.

Exit zero means the experiment completed. The healthy control passed, but `recovery_acceptance_pass` is **false**. Both helpers shut down normally and the owned runtime directories were removed; no forced signals were used.

## Limits and remaining decision

One candidate sequence with a separate healthy control. Inputs are accepted 35-byte SafeTensors storage fixtures from maintained hosting tests, not runnable-model/inference qualification. The fault is opening a blocked catalog temp output, not disk-wide ENOSPC, a late short write, power loss or a crash. No stock comparison, repaired before/after, node HTTP, peers, GPU, wallet, Mac/Windows, full-suite or release result is claimed.

A source-only review suggests `pinmodel B` before restart could force persistence; it was not tested. Conditional signed-package/peer recovery after restart was not qualified. No claim of irrecoverability is made.

Question for repch1c: should the import transaction/retry repair be handled in your work, or would you like us to prepare a focused follow-up preserving #503's file-write fix?
