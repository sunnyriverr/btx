# FastStart manifest correction for 18d0b7ff

FastStart stops at platform selection because the published manifest omits `platform_assets`. The saved Ubuntu run matched the published archive and metadata hashes before hitting that error. [Baseline run](https://github.com/sunnyriverr/btx/actions/runs/45388491371)

The staged manifest uses the existing release collector's CPU and CUDA platform mappings and includes the archive metadata used by the installer. It preserves the source commit, tag commit and unsigned status. The paired SHA256SUMS contains the new manifest digest and both published archive digests.

The pinned FastStart installer ran on macOS against the exact Linux CPU archive with `--platform linux-x86_64 --no-start-daemon`. It returned exit zero and installed both the daemon and CLI. The CUDA platform selected the CUDA filename. Four refusal checks preserved the test installation with replacement requested. These covered a missing platform, a wrong manifest checksum, conflicting archive digests and an unsigned HTTP manifest without opt-in. [Recorded outcomes](verification.json)

For the release owner, verify that the live archive hashes still match, then replace the manifest and checksum file together. CPU execution and CUDA installation were outside this check.
