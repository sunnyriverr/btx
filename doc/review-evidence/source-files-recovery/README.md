# SOURCE_FILES recovery: native PASS, post-test wrapper FAIL

The Linux B1/B2 cases passed in [run 43709914054](https://github.com/sunnyriverr/btx/actions/runs/43709914054), harness `826d4384d53a6960befc38442be33ddfeff135ac`. The native framework exited **0**, and the strict result consumer passed. The overall CI job failed afterward in the optional evidence collector; `wrapper-exit.txt` is **1**. This is not a green workflow result.

## What passed

- **B1:** Ordinary `getmodel`, without either direct-seed flag, restored a retained-catalog model with missing local payload through real MinIO `SOURCE_FILES`. The fixture contains a valid SafeTensors file just over 8 MiB and a nested config. Model/artifact IDs and file SHA-384 values matched before and after restart. The accounted daily GET counter rose from **0 to 131**; the subsequent local read/export after restart added no origin reads.
- **B2:** A daily cap of **201**, from baseline 131, stopped recovery after a verified **4 MiB** prefix. The incomplete model could not be exported; the checkpoint and charged counters survived restart, and the same capped retry remained refused. Increasing the cap through normal configuration preserved previous charges. Recovery reused the prefix and completed with **67 additional accounted reads**, reaching 268. Exact IDs/hashes survived another restart without reimport. An unrelated healthy model remained usable during refusal.
- Six test helpers exited cleanly, the owned MinIO container was removed, and the framework stopped its node. No FakeS3 fallback, catalog flag edits, inference or monetary spending.

These are S3 budget counters, not independently captured HTTP trace or invoice counts. Stream progress `origin_get_ops` counts logical stream operations. The 67-read increment includes other-file overhead; it is not a claim of 67 weight-file range requests.

## Runtime identity and limits

Ubuntu 24.04 x86-64; retained helper SHA-256 `41c07b549f2c1b1abfa259345267757c52d7ba7e3bf501cb6b0e68a8d6a87bb6` from accepted `f40eb37a`, with older `8d6d8b1a` node/CLI RPC proxies. The helper, S3 store and file-stream sources matched `release-0.34.17` at `a4d86d12` before execution. The documentation correction is based on `61f13b88`; its affected wording and hydration function were unchanged. This is not a tested whole `61f13b88` daemon.

The immutable input artifacts are helper **14137827346** and proxy binaries **14095850633**. `expected-binaries.sha256` records member hashes. MinIO was `RELEASE.2025-04-22T22-12-26Z`, binary SHA-256 `53e2a2cb16c5366ea6fbbc479c19ddb4c6a0948273e752f740fb1fbf27bb817c`, on loopback only. The original base fixture retains its copyright header.

Not qualified: actual R2/WAN, provider AUTO policy, large-model scaling, other platforms, full current daemon/package, full suites or release readiness. Prior `PIECE_OBJECTS` and independent-backup results remain separate evidence.

## Wrapper failure and offline correction

`collector-failure.txt` contains the actual failure: `collect.py` imported `base_minio`, which imported `test_framework` outside the staged framework path. This happened **after** both tests and the consumer completed.

`collector-before.py` is the executed version. `collector-fixed.py` reads the two literal test credential labels using AST rather than importing the whole fixture. `collector-offline-fix.json` records the same synthetic collector failing before and passing after, with redaction and archived-byte checks. The fix was verified **offline only**. Native tests were not rerun, and the historical CI result remains failed.

Core result JSON, native log, exit files and runner traceback were retained. The extra scratch logs and preserved-fixture archive were **not uploaded** because the collector failed; they cannot be claimed recovered after the runner ended. Original fixture files were preserved by moves during the test; post-job retention of those optional files is not proved.

Original evidence artifact **14160410873** was downloaded and verified against SHA-256 `3c3fd0b80ee6fa663b19c0aec1f23b15f19dcecf726ecf6ac212ae5e058b78e5`. Published paths and unnecessary test credential labels in records are redacted. `SHA256.json` identifies these published files.

## Review entry points

Read `results.json`, `native-exit.txt`, `wrapper-exit.txt` and `native.log`. The original expected IDs/hashes are bound to both cases and restart results. The adapter, strict consumer and original runner scripts are included for review; they require the pinned framework, binaries and real MinIO setup, and must not be pointed at production. No rerun is needed to validate these saved results.

Credit to repch1c for the maintained real-MinIO fixture and quota work, and to Numair for integration and the existing admission/budget policy. This proposal corrects documentation, not product behavior.
