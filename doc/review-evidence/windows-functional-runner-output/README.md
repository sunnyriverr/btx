# Redirected Windows functional-test output

Bas (bs1812) reported that CP1252 pipes still fail while the runner prints its own Unicode path. The focused check also found a passing child could result in exit 1 when the stock runner printed the pass symbol. [Original report](https://github.com/btxchain/btx/pull/714#issuecomment-7229637772)

**Tested on** Windows Server 2022 (20348), Python 3.11.9, release source `c2e71aafc48a41593277e335c8bc370e45599f01`. The real `test_runner.py` and `combine_logs.py` ran with naturally redirected CP1252 stdout and stderr, with Python UTF-8 mode off. The fixture provided a synthetic child, disposable cache setup and two timestamped logs.

| Control | Stock | Patched |
| --- | --- | --- |
| CP1252 failure | Exit 1 with an encoding traceback. Combined logs and result summary missing. | Exit 1 with original child diagnostics, both combined logs and summary. |
| CP1252 pass | Passing child, but runner exited 1 at summary printing. | Exit 0 with passing summary. |
| UTF-8 failure | | Exit 1 with original Unicode and complete diagnostics. |

- [Before artifact](https://github.com/sunnyriverr/btx/actions/runs/46108486210/artifacts/15248741210) and [executed baseline controller](https://github.com/sunnyriverr/btx/tree/4478687797142e93b86614245a3a0b9ef7b22f8d)
- [After artifact](https://github.com/sunnyriverr/btx/actions/runs/46108699330/artifacts/15249075373) and [executed candidate controller](https://github.com/sunnyriverr/btx/tree/b271df52acb5dbdf129f72aff65146c582a61963)
- [Verified result and SHA-256 values](VERIFIED.json). The nearby display logs are decoded to UTF-8 and their line endings are normalized. Artifacts retain the original bytes.

Fixtures only. The full functional suite and daemon-backed cases did not run. No BTX build was needed.
