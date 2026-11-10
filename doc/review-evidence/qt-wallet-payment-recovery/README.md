# Explicit Qt payment recovery: Linux qualification

**PASS for the scoped native workflow.** Product commit [a2ee89e7e2a90357e2f50600577bd5120a701101](https://github.com/sunnyriverr/btx/commit/a2ee89e7e2a90357e2f50600577bd5120a701101) on release-0.34.16 `dac9aee53520bd49ed320ec7a49b9072fc7d88d9`. This is an explicit user recovery action, separate from #475's funding prompts and #486's restore warning. Credit JPP (Jpp-matata) for reporting the missing recovery path; original scanner authors and headers are preserved.

## Reproduce and inspect

The maintained test and native prerequisites are in `test/functional/feature_qt_wallet_recovery.py`, its test-only `qt_recovery_delay.c` helper, and `doc/qt-wallet-recovery.md` at the product commit. The test is registered in the extended functional list and needs explicit Qt/X11/AT-SPI inputs. An unconfigured invocation skips with exit 77; this is not product coverage.

The actual executed native entry point is [run 42821337738](https://github.com/sunnyriverr/btx/actions/runs/42821337738), fixture `a8a4ea10fed2bb6a069a54dd220d8b9e4328e002`, using [build 42821051260](https://github.com/sunnyriverr/btx/actions/runs/42821051260), fixture `3e1934fb7427953481e8c8afcb23d728d230a8ce`. Those immutable fixture branches record the bounded retained-cache build and executed wrapper. The documented standalone command is a reconstruction recipe, not a separate additional run. The native wrapper copied and checked the exact maintained test before execution.

## Observations

- A disposable encrypted stale backup sees one of two real regtest receipts; the original encrypted wallet and plain-backup controls see both. Recovery retry finds both exact outpoints totaling 3 test BTX, at the unchanged tip, and relocks.
- Cancelling the unlock prompt releases the reservation without unlocking. During a real scan, a competing scan is refused; Cancel yields the actual scanner abort, releases the reservation and relocks. The missing receipt remains absent until retry.
- An initially unlocked wallet retains its policy; the ordinary RPC rescan still works. A new block plus a newer timed RPC unlock during recovery both survive successful completion.
- Cancellation uses a bounded test-only fread delay gated on this wallet's actual scanner start. No product delay or scanner-result substitution is present. The skip control exits 77, and the configured native test exits 0. See [native log](native-test.log), [results](native-result.json) and [hash inputs](qualification-input.json).

Ubuntu 22.04 x86_64, GCC 11.4.0, Qt 6.2.4, OpenSSL 3.5.9, virtual X11; economic/cpu-diagnostic regtest. Baseline daemon and CLI bytes are unchanged. The product patch SHA-256 is `c786d666dd70021b48dd7e3f7941c2779db8d3ba38668564c864ab8e6ded06e4` and candidate Qt SHA-256 `1f5316436856bdc05c57e4593a7936ea59a3c3ab1d86560493026cfe91b0dc28`. Product source/test bytes are mapped in [package-check.json](package-check.json).

## Comparison and limits

[Baseline run 42814749023](https://github.com/sunnyriverr/btx/actions/runs/42814749023) supplies the earlier verified observation that the stale backup lacks a receipt and the native recovery action is absent. Its original fixture is preserved and differs from the final corrected candidate automation. **This is not an identical-harness baseline assertion failure.**

No native Windows/macOS, full wallet suite, pruned history, reorganisation, very long history, concurrent wallet unload, timeout-expiry race, live-wallet reproduction of #475, or release qualification is claimed. Key derivation and a current block read are cooperative cancellation boundaries; the finite refill range cannot find arbitrary later addresses. Ordinary unlock does not automatically rescan. No production wallet was used.

The review decision is whether to accept this explicit Qt recovery path; platform and wider lifecycle qualification remain separate. Raw evidence and exact retained fixture/build identities are provided without rerunning tests for publication.
