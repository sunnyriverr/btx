# Live Modelnet failover on Linux

**Fail before, pass after.** The fixture starts with A unavailable, downloads two verified 4 MiB pieces through B, restores A and disconnects B. The baseline worker retried B five times and made no connection to A in the 20-second window. With the fix, the same job contacted A in 0.78 seconds and completed in 3.03 seconds with the same receiver PID. The two saved files kept their inode, modification time and SHA-256, and the complete model matched the source SHA-384.

The B relay used a verified aggregate 1 MiB/s cap. On both binaries the permanent manifest-rejection control left A excluded after B disconnected. Cancellation preserved the saved pieces and all helpers shut down cleanly.

[Executed fork CI run](https://github.com/sunnyriverr/btx/actions/runs/42961438685) · [Build and input identities](provenance.json) · [Machine verdict](result.json)

The CI step ran the same native fixture on both helpers. To replay one case on Linux with a matching helper and strace installed, run:

    python3 -u native_fixture.py --binary /path/to/btx-modeld --expected-sha256 EXPECTED_SHA256 --output ./records

Use the appropriate helper SHA-256 from provenance.json. Expect STALLED on the baseline and RECOVERED on the candidate. Add --permanent-control to execute the rejection and cancellation case. This observational fixture reports both conclusive outcomes successfully, while the CI driver asserts the required result for each binary.

[Baseline observations](matched-baseline/observations.json) · [Candidate observations](candidate/observations.json) · [Baseline rejection control](matched-baseline-permanent/observations.json) · [Candidate rejection control](candidate-permanent/observations.json). Each case directory contains the connection trace and pacing samples.

This was native Ubuntu 22.04 x86_64 loopback PQ1 with three disposable helpers. Both builds shared the cached prerequisite tree with unrelated #473 changes. CI recompiled only the changed helper source and relinked it against verified compatible objects. The fixture is standalone. A clean project build, full-node integration, WAN and other platforms were not tested.
