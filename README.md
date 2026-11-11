# Wallet restore retry after a failed copy

The same real `restorewallet` test failed on stock `dac9aee5` and passed on the
tested candidate tree `7dd16ae3` on Ubuntu 22.04.

| Check | Stock | Candidate |
| --- | --- | --- |
| 1,024-byte file-size cap on a 20,480-byte backup | Partial wallet left in both destination cases | Failed output removed; an existing directory and its sentinel are preserved |
| Same name after restoring the limit | RPC -36 (database exists) | Both retries succeed, with address ownership and label intact after unload/load |

Healthy restores, invalid-backup cleanup, existing wallet and symlink
preservation, and normal shutdown passed. The two runs used separate
disposable zero-funds wallets; hashes compare each run's own files.

The executed entry point is the **Matched failure and recovery qualification**
step in the [Linux run](https://github.com/sunnyriverr/btx/actions/runs/42940069075). For the same fixture outside CI, use a
Linux host, a wallet-enabled daemon and the tested checkout's functional-test
framework:

```sh
python3 qualification_fixture.py --binary /path/to/btxd \
  --functional-root /path/to/btx/test/functional --records /path/to/new-records \
  --expected-sha256 BINARY_SHA256 --expect baseline
```

Use `--expect candidate` and the candidate binary hash for the repaired daemon.
The classifier's baseline success means the original bug was reproduced.
See [provenance](provenance.json), [stock results](base-result.json),
[candidate results](candidate-result.json) and [build record](build-result.json).
The build reused the retained cache with the daemon target enabled.

The separate [Linux component results](component-result.json) use extracted
code, wallet-context stubs and explicit close-result/collision fault injection.
They supplement the native test; they do not qualify migration end to end.

Native Windows and macOS still need a build and failed-copy/retry check with
existing-file preservation and close-before-remove behavior. The existing
Windows descriptor-to-stream wrapping failure is outside this patch.
The Linux fault used a kernel file-size limit; physical disk exhaustion, a
full daemon restart, and the full wallet suite were not tested.
