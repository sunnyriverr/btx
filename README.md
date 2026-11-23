# ModelNet automatic download across an installed-node restart

**PASS** on native Ubuntu 24.04 x86-64, using the official CPU prerelease `btx-0.34.17-x86_64-linux-gnu.tar.gz` from `932a0238c70705b28ea344a7929cee09ada314c8`. Its SHA-256 was `e93be7a55b6f786ec0147aa7b02c06fdaf8e7a04dd1d748a47b2ccd9662a4d9d`. The prerelease manifest maps the archive to that commit. The checksum list is unsigned.

- During an automatic loopback regtest download, one 4 MiB verified piece was on disk when the installed CLI requested a normal stop. An automatic job checkpoint and the piece survived.
- The same installed node started a new managed helper. Acquisition finished without a manual fetch, with matching model and artifact IDs and all 8,388,681 bytes matching the source SHA-384. The tracked piece retained its hash, inode and modification time. Both node instances and the sender exited cleanly.
- The initial setup job verified and installed the archive but did not start a runtime case because the test wrapper assumed a flat install tree. The passing controller uses the paths returned by the installer. One runtime case ran. No rebuild.

This extends [repch1c's archive installation and startup result](https://github.com/btxchain/btx/pull/714#issuecomment-7098719845). It covers a normal restart of the same CPU package on disposable loopback regtest. Upgrade, abrupt shutdown, CUDA, WAN, mainnet and GUI were outside the run. Packet retransmissions were not measured.

[Machine-readable result](result.json) · [Archive manifest](btx-release-manifest.json) · [Installed executable hashes](binaries.sha256) · [Raw CI artifact](https://github.com/sunnyriverr/btx/actions/runs/45168025278/artifacts/14816056079) · [Passing controller](https://github.com/sunnyriverr/btx/tree/fd5be9febae1751a1a34e68b649e9d49a0240e62) · [Setup-only run](https://github.com/sunnyriverr/btx/actions/runs/45167852273)
