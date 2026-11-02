# Reproduce the final Linux comparison

See REPORT.md for exact scope and identities. Build both variants from cbf65894 with common-prerequisites.patch applied (worker-descriptor code from 0f94479c, original authorship retained). Build btx-modeld and retain it as baseline. Apply lan-candidate.patch, rebuild the same target, retain candidate. Do not apply the LAN patch again if already building from this review branch. These build prerequisites are shared test setup, not additions to the LAN product commit. This uses an isolated disposable Linux helper test environment, not an active node. Retain the same non-LAN prerequisites on both binaries; verify guest-build.json and source-identities.json. Use isolated checkouts/build directories; preserve any unrelated source and cache before changing inputs.

The final test expects Linux `ip -j addr`, Python 3, an IPv4 address on `eth0`, ordinary UDP multicast loopback, and two real helper binaries built against the same dependencies. It uses UDP 29448 and ephemeral TCP/Unix sockets. Confirm those resources are free and the selected interface matches before running. No network reconfiguration is needed.

Place the unchanged final test.py under /tmp/btx-lan-linux/test.py, and the matching binaries as baseline and candidate. In the guest:

```sh
python3 /tmp/btx-lan-linux/test.py /tmp/btx-lan-linux/baseline baseline
python3 /tmp/btx-lan-linux/test.py /tmp/btx-lan-linux/candidate candidate
```

Run kernel-probe.py in the same boot to independently confirm the receive-interface metadata. This script uses a separate UDP socket; it does not instrument the helper. The harness writes baseline-results.json and candidate-results.json under /tmp/btx-lan-linux. It expects and records the baseline property's failure; both script exit statuses are zero when the expected comparison reproduces. Inspect regression_pass for the before/after verdict.

The final harness bytes equal guest-test.py and have SHA256 e54f95f0aa20cd1e0bf40b27b49128139dd7fd89b12a723d4f15bf21f63a0d25 (use summary.json as the authoritative hash).

After collection, restore the source/binary backup, remove owned runtime directories, verify the UDP port is free, stop the owned VM, and record the cache warning from guest-cleanup.json. Current VM is already stopped and restored; do not rerun simply to reconfirm unchanged evidence.
