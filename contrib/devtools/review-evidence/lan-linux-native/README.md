# Linux acceptance evidence for #338 item 9

Product commit af1ffda2 is unchanged. Original finding: repch1c. Existing receive-scope correction and native Mac/Linux verification: Sunny River; JPP contributor guidance and inherited source authorship retained. The common worker-descriptor prerequisite remains its separate 0f94479c correction, not part of the LAN patch.

Actual Alpine3.22.4 aarch64/musl CMake-built btx-modeld: identical final harness gives unwanted off-scope automatic TLS ClientHello 3/3 before and rejection3/3 after. Valid discovery after distinct-endpoint invalid packets succeeds3/3 both. Discovery-disabled controls and all14 clean exits pass. kernel-probe-final.json records actual same-boot IP_PKTINFO metadata from a separate socket.

REPORT.md has exact limits and pilot disclosure. REPRODUCE.md, common-prerequisites.patch and lan-candidate.patch describe source setup; test.py is the exact final runtime harness. The initial weaker endpoint-sharing pilot is disclosed in the report; these result files are only the final rerun. Evidence commit adds files only, no product changes. Incremental Release-O1 target build, not a clean full-project build. Own-host loopback/multicast in one VM; no physical multi-host LAN, glibc, native Windows, full authentication/model transfer or release qualification.

Public logs/metadata omit operator home paths/hostnames. No credentials, identities, wallets or model data are included. Summary capture-time posting hold is superseded only for this authorized handoff. Local source/binary restored, candidate cache objects require rebuild before reuse.
