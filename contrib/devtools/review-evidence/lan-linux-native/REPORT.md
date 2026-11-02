# Native Linux LAN receive-scope verification

Completed privately on 2 November 2026. **The identical final test reproduces the unwanted automatic connection in the original helper 3/3, and the existing correction rejects it 3/3. Valid discovery succeeds 3/3 on both variants.**

## Decision and coverage

This closes a Linux-specific acceptance gap for the existing LAN receive-scope correction, not a new defect or patch. Before execution, the GitHub API review found the swarm base unchanged at `cbf65894e6d61084527cd93e913a00c6794418dd`, no changed open-PR heads against the preceding review, and no equivalent native Linux result in the relevant #338 discussion. Related #348 port filters, #368 Winsock LAN-wire cleanup and #373 filesystem work cover different paths. See `coverage-check.json` for the checked heads and discussion identities. This is an acceptance-gap selection, not a new direct maintainer assignment.

Existing public code: `af1ffda2a5394061a98a3c50fc639b6dd8299875`, branch `codex/lan-discovery-receive-scope`. Existing handoff: https://github.com/btxchain/btx/issues/338#issuecomment-6554059976. This capture-time report accompanies the authorized evidence handoff.

## Actual workflow and result

The real CMake-built `btx-modeld` starts with LAN discovery enabled, peer following enabled, no configured model seed, zero storage quota, hosting/NAT-PMP off, and a fresh local RPC socket/model directory. A normal 48-byte beacon advertises a TCP listener owned by the test. Success means the helper automatically connects and sends a TLS ClientHello; it does not mean a completed authenticated session or model transfer.

| Final case | Original helper | Corrected helper |
| --- | --- | --- |
| Beacon sourced from the guest's own eth0 private IP but delivered through loopback | Unwanted automatic connection 3/3; acceptance property fails | No connection within 6 seconds, 3/3; property passes |
| Valid multicast after wrong-network and malformed packets | Automatic connection 3/3 | Automatic connection 3/3 |
| Discovery disabled, valid multicast beacon | No connection, 1/1 | No connection, 1/1 |
| RPC still responsive and helper exits cleanly | 7/7 | 7/7 |

Wrong-network and malformed beacons advertise a **different listener endpoint** from the later valid beacon. Each invalid beacon has a six-second no-connection guard; the valid beacon then produces the observed connection, and the invalid endpoint remains unused. This prevents attributing an earlier invalid-beacon dial to the valid packet. Each helper also has a two-second pre-beacon quiet control.

A separate same-boot `recvmsg` probe confirms actual Linux `IP_PKTINFO`: the negative packet arrives on `lo`, index 1, destination 127.0.0.1; the valid multicast arrives on `eth0`, index 2, destination 239.192.0.35. These are actual ordinary UDP packets, not injected ancillary flags or mocked interface indexes. Multicast TTL is zero with local loopback enabled. No route/interface/firewall settings were changed. The probe is independent of the helper socket; it is not per-packet instrumentation inside the helper.

## Build and provenance

Alpine 3.22.4, aarch64/musl; Linux 6.12.81; GCC 14.2. Existing local Lima VM, two CPUs. Compilation briefly used 1.5 GiB RAM; the final comparison ran at the original 1 GiB setting.

The original LAN files match `cbf65894`; the corrected three files match `af1ffda2` exactly, including its Windows-only compatibility header. Both variants share the preexisting worker-descriptor correction `0f94479c` in helper.cpp and the same cstdint include prerequisite in swarm_membership.h. Only the LAN/compatibility files differ between variants. This is **not** a claim of testing two pristine full repository commits.

Both binaries use the actual CMake `btx-modeld` target and retained Release `-O1` build cache. Baseline needed no new compilation; candidate rebuilt helper/native-discovery translation units and relinked. This is an incremental target build, not a clean full-project build. `source-identities.json` and `guest-build.json` record exact source/binary identities.

Final harness SHA256: `e54f95f0aa20cd1e0bf40b27b49128139dd7fd89b12a723d4f15bf21f63a0d25`.

Original binary SHA256: `c4d3991027719f24f4b01099014719ed42b888938bfd2fa625c8814047bd3943`.

Corrected binary SHA256: `cffa9dcf0bcceefd091ca0bde843f7d2e98c7a6d1217855f6fdc2ce2ced75573`.

## Controls, pilots and limits

The first pilot passed but used one endpoint for invalid and valid beacons with two-second guards. That could obscure which packet caused the eventual connection. The final harness separates those endpoints, increases invalid guards to six seconds, and reruns both unchanged binaries. Pilot evidence is retained under `pilots/` and is not counted in the final 3/3 results. A collection-script quoting error was corrected before guest execution; it changed no product code or result.

This is one Alpine VM with own-host multicast and a loopback receive-boundary case. It does not qualify a physical multi-host LAN, an external off-subnet sender, Linux/glibc, Windows, completed TLS authentication, model transfer, full suite, release or mainnet. Rejection is bounded by the stated six-second observation window, not a claim about all future behavior. Baseline harness exit zero records successful reproduction of an expected bad connection; the tested property itself fails before the correction.

## Cleanup and next step

All 14 final helper processes exited zero; temporary runtime directories were removed and UDP 29448 was free. Original three source files and baseline build/bin/btx-modeld were restored. **Cached helper/native-discovery objects and the static archive retain the candidate; rebuild affected targets before reusing this cache.** Common prerequisites remain as before. VM stopped, RAM restored to 1 GiB. Host free disk at closeout was about 2.14 GiB, above the 1.25 GiB reserve; unrelated dirty source hashes were preserved.

Sunny authorized adding this evidence once to the existing LAN handoff after local completion. No further unchanged Mac/Linux runs are justified. Native Windows build/runtime acceptance remains separate.
