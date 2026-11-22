# Mac ARM LAN discovery on 2c4da891

**PASS locally in 23.23 seconds.** The unmodified default `feature_swarm_lan_discover.py` ran on an ARM64 Mac with macOS 26.5.1 and Python 3.12.10. The four verified executables and original fixture came from stock revision `2c4da891f0089ebc0fb082e65d03a4efda4488a3` in [checkpoint 14703680085](https://github.com/sunnyriverr/btx/actions/runs/44892799366/artifacts/14703680085). Only the test configuration paths were relocated. The local multicast probe received 3/3 datagrams.

Each of the four nodes authenticated three peers. Verified model acquisition continued after the original publisher stopped. The test exited zero, cleaned its datadirs and left no test process group. All four binary hashes matched before and after. No build tools ran.

The [hosted Mac suite](https://github.com/btxchain/btx/pull/714#issuecomment-7070645929) timed out on that revision while waiting for authenticated peers. The local result establishes that the default case can pass with those binaries. The hosted timeout is still unexplained. The forced IPv4 case, multiple physical hosts and newer source revisions were outside this run.

See [the manifest](manifest.json), [multicast log](multicast.log) and [functional log](functional.log). Machine-specific paths in the test log were redacted.
