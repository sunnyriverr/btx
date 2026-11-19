# Funded recovery-only refund on a97af7b3

One native macOS ARM64 diagnostic run with saved BTX a97af7b3 and Bitcoin Core 32.1 on isolated regtest. The funded taker restarted with `-swapnetmode=recovery` while the counterparty stayed offline. Both funded and terminal restarts reported the recovery lock and rejected switches to taker and maker.

The original BTX refund refused before maturity and at maturity minus one, entered the mempool at height 2226 and reached 20 confirmations. It spent the original outpoint, paid the original local wallet within the fee caps, and left one funding output and zero held budget. Terminal restart preserved the operation records and accounting. The controller exited 0 in 160.617 seconds, with clean process cleanup.

The shared control socket did not start because the fixture path was too long. The run used the diagnostic serial CPU profile with ModelNet, Metal and GUI off and test-only MatMul activation settings. It does not qualify the shared control plane, mainnet or a release.

[Original native BTC fixture and verification recipe](https://github.com/sunnyriverr/btx/blob/dff0050ab37e05d83a765bb2a0329bf98cc0fb09/doc/review-evidence/public-market-native-a97/README.md). Apply the included fixture diff to the retained original fixture and invoke its existing controller with `--execute refund` and matching saved inputs. The sanitized receipt preserves the binary identities and original-run receipt hash. The evidence branch contains only a report, selected result fields and the fixture delta.
