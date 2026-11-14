# Expired Bitcoin backup: observation-only recovery

Tested repair: [7170b631010e722d96ee9fdcb7d81608552bcbbb](https://github.com/sunnyriverr/btx/commit/7170b631010e722d96ee9fdcb7d81608552bcbbb) on `swapnet-v2` base `70de5a454b4263c929b0162af6615c9dd756becd`. Credit repch1c for backup-recovery reports and Numair for the original/adopted recovery implementation. Related valid-window recovery: #666, already included in this base.

## Behavior

An imported committed Bitcoin backup can hit `UNSAFE_TIMEOUT` before lookup once its own deadline matures. The new path persists an observation-only latch before I/O, discovers the original output/spend and reports facts without enabling spending or changing financial accounting. Facts never become normal execution refs or prepared/broadcast/recovery flags. Direct cancellation, peer cancellation, refund, fee-bump and scheduler effects are fenced. Current lookup uncertainty preserves the last verified fact; the view distinguishes historical evidence from current status.

## Test results and exact scope

- Same initial23 cases: **21 failed / 2 passed before → 23 passed after**. Two added prepared-refund/latch-save-failure controls passed.
- Independent source review found loss of last verified status on a later read failure. Four added controls: **2 failed / 2 passed before that correction → 4 passed after**. Total29 new cases passed across bounded cohorts, not one claimed29-case run. Review includes the correction recheck, not an independent platform run.
- Existing **207 tests passed on the initial observation candidate**. That suite was not repeated after the last_verified correction; four focused regressions and the final native probe qualify that delta. Do not interpret207 as a full-suite run of the final Git tree.
- Native macOS ARM64/Core30.4 retained regtest: height182, own deadline180, actual original payment and confirmed refund. Coordinator progresses `spend_lookup_pending` → `original_refunded`; zero signing/broadcast/authority-accounting calls and unchanged financial table hashes. Direct cancel/peer-cancel/refund/fee-bump refuse `RECOVERY_READ_ONLY`; facts persist across SQLite reopen. A later **simulated read error** preserves last_verified. Native node was shut down cleanly afterwards.
- Relevant component controls preserve normal fresh funding, cancellation, existing prepared-refund recovery, ownership, retry, clock rollback latch and failed-save behavior.

## Maintained regression recipe

From the product checkout (requires the existing SwapNet pytest/crypto dependencies):

```sh
PYTHONPATH=contrib/swapnet:contrib/swapnet/tests python3 -m pytest -q contrib/swapnet/tests/test_observation_only.py
```

This is a portable reconstruction of the cohort commands. Original execution used a RAM-backed isolated source and owned temporary pytest directories. The first23/extra2 cohorts used the same maintained history helper under an external import name; final tests import `test_restored_history` directly, with no helper behavior change. The four final-delta cases ran with that import. Exact product/test hashes are in the manifest. Logs have local machine paths redacted; original logs remain in the working evidence.

Native proof reused an existing disposable authenticated backup and original/refund chain instead of creating another payment. Its fixture wallet files are not distributed; the result and read-only RPC counts are included. Reproducing native qualification requires an equivalent funded/refunded regtest backup, not just the pytest recipe.

## Limits

Newly marked committed Bitcoin restores only; old unmarked imported directories require reimport. This adds observation, **not automatic late settlement**, grant renewal, terminal accounting or late signing authority. No BTX/counterparty driver was used in the native probe; no full native two-chain settlement, Core32 native run, Linux/Windows native run, installed-package, mainnet, power-loss or deep-reorg qualification is claimed. Session/audit/observer-cache writes are intentional; financial state remains unchanged. Existing history scan bounds still apply.

The original23-case candidate was independently reviewed. The discovered last_verified issue was corrected and source-rechecked. Setup pilots (discarded fixture callback, insufficient RAM workspace and a correctly refused nonempty restore destination) were corrected without weakening product checks; none is counted as a product defect.
