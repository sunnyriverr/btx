# Live failover with a 72 MiB storage cap

The paired Ubuntu 22.04 loopback PQ1 test applied the published #517 and #519 changes to the same retained release checkpoint. The receiver started with an empty catalog and saved two verified 4 MiB pieces from B. The 71,303,243-byte model fit the 72 MiB cap, while counting those pieces twice would exceed it.

After B disconnected, both builds completed the original job from A with the expected SHA-384. The baseline replaced both saved pieces. The follow-up kept their inode, modification time and SHA-256. Both builds also allowed normal removal after cancellation and rejected the same model at a genuinely insufficient 64 MiB cap.

[Paired build and test](https://github.com/sunnyriverr/btx/actions/runs/42983418553) · [Controls on the same binaries](https://github.com/sunnyriverr/btx/actions/runs/42983941101) · [Source and binary identities](qualification.json) · [Composition check](composition.json)

The follow-up applies directly to #517. Its composition with #519 matches the tested source. The build reused verified objects from the release checkpoint with unrelated #473 changes, compiling the helper and catalog at -O0 for both variants. WAN, other platforms, concurrent cancellation and requeue, and clean project builds remain unverified.
