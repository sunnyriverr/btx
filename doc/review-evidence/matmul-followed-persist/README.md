# Followed-chain body fixture on macOS ARM64

Functional case: feature_matmul_unrequested_followed_persist.py.

The original fixture exited 1 in 4.58 s. The patched fixture exited 0 in 6.62 s. Both ran locally on macOS 26.5.1 ARM64 with the same 26d5d2dd node, CLI and helper from checkpoint 14584973761. The case ran directly with the relocated checkpoint test configuration and fresh regtest directories.

An ordinary inbound archive peer was refused. The authorized peer's eight unsolicited historical bodies became available. A valid low-work competing block reached block acceptance and its body stayed unavailable. Reconnection caught up with zero refetches of the eight historical bodies.

The patch applies to 4134c67f with an identical original fixture. The runtime result is for 26d5d2dd. JPP reported the original Linux failure in [#891](https://github.com/btxchain/btx/pull/891). The Linux correction and full suites were not run.

[Original trace](baseline.txt) · [Patched trace](final-candidate.txt) · [Verified hashes and timings](receipt.json) · [Patch](fixture.patch)
