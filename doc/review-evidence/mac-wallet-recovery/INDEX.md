# Native Mac wallet recovery: scoped pass

Exact product source: `release-0.34.17@bd847e2b986722c1723b4cd60988d4f4908452d4`. One macOS 15.8.2 ARM64 regtest attempt, using hash-verified retained daemon/CLI binaries from build44018745153, without rebuilding. This is evidence about the adopted #486 recovery path, not a new product patch or a PR-wide release ACK.

## Result

Original encrypted/plain backup and refusal controls passed. Explicit refill/rescan recovered the exact receipt outpoints and3BTX total. The independently restored signer, with the original unloaded, made a confirmed0.25BTX P2MR payment with exact input/change/fee/balance assertions. Graceful restart retained the exact raw payment/block/confirmation/fee/balance/unspent state, relock/new-address behavior and backup bytes.

Exit0, normal `Tests successful`, all5required stages, no skip or bound. Fixture invocation plus monitoring/cleanup took22.559seconds; sampled owned data peaked21,842,182bytes. The owned process group was confirmed absent. Full job duration was124seconds.

## Executed entry and provenance

[Actual native run44025001701](https://github.com/sunnyriverr/btx/actions/runs/44025001701), dedicated control commit `7f74b81714449da708daa7237b0827b3d9547afa`, manual workflow `mac-current-build.yml`, `run_regtest=true`. Executed controller command: `python3 contrib/devtools/session3-mac-wallet-runtime/run.py`. [Immutable executed workflow](https://github.com/sunnyriverr/btx/blob/7f74b81714449da708daa7237b0827b3d9547afa/.github/workflows/mac-current-build.yml) and [fixture/controller](https://github.com/sunnyriverr/btx/tree/7f74b81714449da708daa7237b0827b3d9547afa/contrib/devtools/session3-mac-wallet-runtime).

The fixture preserves all original maintained recovery assertions and appends source-reviewed payment/restart checks; it is not an untouched default-suite invocation. Native daemon loader/RPC/startup was exercised with the exact recreated Python3.12.10 framework and hash-locked wheels. The ordinary framework supplied one clean-chain, loopback-only regtest node. Static CLI identity inspection is separate from daemon runtime.

- [Qualification receipt](qualification-receipt.json): tested identities, binary hashes, timings, records digest and limits.
- [Runtime result](records/runtime-result.json) and [functional log](records/functional.log): authoritative native outcome and every completed stage.
- [Constructor preflight](records/fixture-construction.log), [dependency setup](records/dependency-bootstrap.log) and [build verification](build-verification-receipt.json).
- [Evidence review](EVIDENCE-REVIEW.md), [original record digest catalog](records-verification.json), [all published file digests](SHA256.json) and [exact recipe copies](recipe).

All13 original record files are preserved byte-for-byte. The original Actions ZIP SHA256 is `2f534cc4ecd4494eb79ff8cfb0e1f5f59bc2aefb5bf926b44cc92278ae2878a7`. `records/result.json` is the checkpoint helper's state; its tests_run=false/complete=false are not native test results. `records/runtime-result.json` plus functional.log establish the native pass. Recipe copies retain the executed input checkpoint identities; future reruns require artifact availability and a separate host/resource check. Actions artifact expiry does not affect these permanent plain-file records.

## Limits and credit

One hosted ARM64 Mac, headless CPU/SQLite diagnostic profile, permitted serial prover, recreated external Python runtime. No CLI commands, GUI/Qt, GPU/Metal, ModelNet/SwapNet, shielded spending, crash/reorg, other-platform/default-consensus/full-suite or release-package qualification. No real wallet, keys or coins accessed; no new product source repair. Source review is internal review, not a second native-platform run.

Credit JPP for documenting the locked-PQ recovery limitation and requesting Mac coverage, and Numair for incorporating the recovery changes. This adds native Mac evidence to their existing work.
