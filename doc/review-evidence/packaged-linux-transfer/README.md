# Packaged Linux transfer: native PASS, original wrapper FAILED

The unchanged maintained transfer case passed once on Ubuntu 24.04 x86_64 using the untouched published Linux archive. The original CI wrapper failed after the case, source checks and package equality assertion. Its result and logs are preserved unchanged. The wrapper was then repaired and verified **offline only**; the native test was not repeated.

## Exact inputs and executed path

- Published source: `2f3b574867c11ab79eba829123689b76e6137a38`.
- Archive: `btx-0.34.16-x86_64-linux-gnu.tar.gz`, asset `721231861`, 158893566 bytes, SHA256 `796b9edd064272b1f443cf3e08646565936183f9f1e15339cad60e84e1014b32`. The producer build was not independently reproduced.
- [Original native run 42430108849](https://github.com/sunnyriverr/btx/actions/runs/42430108849), fixture `1f199e694c3bc6e0f64bce180a2ccbd9571d47be`. That job remains **failed**.
- Maintained `test/functional/feature_swarm_lan_discover.py`, Git blob `4fb26d734d1b588b0734b135fb6c2a15d01e5b38`. [Exact unchanged case bytes](maintained-case.py).
- [Executed workflow](ci/workflow.yml), [executed driver](ci/run.py), [actual arguments and raw state](run-42430108849/result.json), [dispatch identity](dispatch-receipt.json). The workflow's step label retains an old startup/restart title; its command invokes the transfer driver shown here.

The driver installs documented runtime libraries, pins and downloads the archive, writes a functional-test config and runs the maintained case with `--onlynet=ipv4`, `--nocleanup` and a disposable runtime. It supplies the package paths through that config; no helper override, overlay, source build or package cache. The workflow is the actual executed recipe, including its disclosed bookkeeping defects, not a claim that the corrected driver was run.

## Observations

[Raw test output](run-42430108849/maintained-transfer.log) records the complete journey PASS, then `Tests successful`; framework exit 0, no LAN skip, about 20.64 seconds. Four same-host nodes exercise authenticated PQ1 peers, automatic model acquisition with catalog `bytes_verified=true` / `incomplete=false`, shared-family observations, zero-storage refusal, and a new acquisition after the original publisher stops. No model inference or workload code runs.

All 128 package file hashes matched in the executed before/after equality assertion. The driver saved the before manifest and equality flag, not a separate after manifest. Selected source hashes and clean tracked status were checked. Normal teardown left no owned processes or runtime directory and required no extra signals. See [offline evidence verification](run-42430108849/verification.json) and [original collection/hash receipt](run-42430108849/collection.json).

## Wrapper repair and offline validation

The executed driver checked singular `Test successful` rather than plural `Tests successful`, then accessed undefined `observed` after the source/package checks. A human-readable archive annotation also retained old source `0ac06fd2`; the actual checkout, source audit and fixture pin are `2f3b5748`. These errors remain visible in the original records.

The [corrected driver](wrapper-repair/run.py) and [shared classifier](wrapper-repair/result_handling.py) separate native-case verdict from wrapper/integrity/cleanup verdict. Skip returns 77 and never counts as a pass; failure wins over skip text; incomplete logs and mismatched source/package or unclean teardown prevent wrapper success. The native command/profile and existing safety assertions are unchanged.

[Sixteen local tests passed](wrapper-repair/validation.log), using the saved result/log and in-memory failure/skip/incomplete controls. The tests reproduce the old bookkeeping error, execute only the corrected driver's finalization/save/exit statements and inspect its wiring. They do not execute setup, download, cleanup processes or the native case. The original record still yields native PASS / wrapper FAIL; only an explicitly labelled in-memory control with the known wrapper exception removed yields wrapper PASS. Synthetic controls are not native failure/skip observations.

Reproduce those **offline tooling checks**, without starting BTX:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 doc/review-evidence/packaged-linux-transfer/wrapper-repair/validate.py
```

[Validation receipt](wrapper-repair/validation-receipt.json) and [manifest](manifest.json) bind the exact files. All 17 original evidence/recipe files rehash unchanged. The corrected wrapper has **not** been dispatched natively.

## Limits

One short same-host IPv4 regtest case. Catalog verification is the byte oracle: no independent assembled-file digest, receiver restart, physical multi-host/WAN, throughput, GPU, inference, full-suite or release qualification. This extends the earlier archive startup/restart evidence to the maintained acquisition journey; it does not establish a BTX transfer defect or qualify current source changes after `2f3b5748`.
