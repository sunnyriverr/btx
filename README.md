# FastStart metadata for the e2f4c6d0 Linux archives

The published manifest for source `e2f4c6d0` omits the platform mappings FastStart requires. The shipped Linux archives remain this cut even though the release branch moved to `c2e71aaf`. The corrected manifest adds mappings for CPU and CUDA 13 and records both archive hashes and sizes. The paired checksum file includes the new manifest digest and the two published archive digests. [Maintainer update](https://github.com/btxchain/btx/pull/714#issuecomment-7207733160)

The stock installer returned exit zero in one clean install from the exact published Linux CPU archive on macOS ARM64. Startup was disabled. The installed daemon and CLI wrappers and both underlying executables matched the archive bytes. CUDA was checked at platform selection. The earlier refusal controls apply to the identical installer and collector. [Verification receipt](verification.json)

For the release owner, replace [the manifest](btx-release-manifest.json) and [the checksum file](SHA256SUMS) together if the live archive digests still match this cut. The pair preserves the release's unsigned status.
