# Trusted-mirror recovery on Mac ARM

Both full functional scripts ran on disposable regtest using the verified Mac ARM daemon and CLI built at release base 7d65025b. The input manifest pins the exact tested test-file bytes and binary hashes. No product code was changed or rebuilt. The local run used the workspace Python 3.12 runtime for the retained daemon's matching Python ABI. Local directory names were shortened in the saved logs.

| Case | Result |
| --- | --- |
| feature_matmul_trusted_mirror_bounded_park.py | Pass in 15.32 s. Bounded recovery reached the winning tip after the remaining bodies arrived. |
| feature_matmul_trusted_mirror_bounded_stall_open.py | Pass in 56.99 s. The mirror reached the winning tip after the stall window opened, without another submission. |

The older Mac and Linux failures stopped at a pre-body height wait. The current-base diagnostic found the winning tip indexed at 20 while the selected header stayed at 15. The patch changes only the pre-body readiness check in each case to require the exact indexed tip and its signed frontier. The active-tip and later recovery assertions remain in the tests.

Scope is the two local Mac ARM cases. No full-suite run, Linux rerun, mainnet test or release qualification. Thanks to JPP for the Linux comparison that helped locate the shared checkpoint. [Prior Mac report](https://github.com/btxchain/btx/pull/714#issuecomment-7070645929) · [Linux comparison](https://github.com/btxchain/btx/pull/891) · [Build evidence](https://github.com/sunnyriverr/btx/actions/runs/44975711173)
