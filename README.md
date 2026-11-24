# ModelNet restart and checkout on the 18d0b7ff CPU archive

**PASS** on native Ubuntu 24.04 x86-64 using the exact published `btx-0.34.17-x86_64-linux-gnu.tar.gz` from `18d0b7ff5337c2768f5f5e06c674d8c8898bedad`. The archive SHA-256 was `5b1a62706466f1ab42ca36309b7c63653c8aeb8d57acb86a406240596e02b256`.

An ordinary stop interrupted automatic acquisition with a verified 4 MiB piece. The piece and the job checkpoint survived. The restarted node owned a fresh helper that completed the transfer without a manual fetch. Public `exportmodelpath` returned the expected model and artifact IDs and materialized 8,388,681 bytes with the source SHA-384. Both node exits and the sender exit were zero.

The helper entered whole-file staging. **Fallback was not independently verified.** This is one same-version, loopback regtest observation. No upgrade, deliberately damaged input, CUDA, WAN or mainnet test.

[Result](RESULT.json) · [Release manifest](btx-release-manifest.json) · [Executable digests](binaries.sha256) · [Artifact receipt](readback.json) · [Raw CI evidence](https://github.com/sunnyriverr/btx/actions/runs/45388757632/artifacts/14916599812) · [Exact controller](https://github.com/sunnyriverr/btx/tree/3c331f6bc84ab7d0c03b1a2a20aecf8a96061966)
