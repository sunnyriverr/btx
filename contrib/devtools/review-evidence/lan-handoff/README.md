# LAN receive-scope candidate

Bug: a valid beacon arriving outside the joined LAN interface can trigger automatic helper dialing. This branch applies the exact tested indexed-interface correction plus the tested one-line Windows include-order correction.

- Base: `cbf65894e6d61084527cd93e913a00c6794418dd`. Three product files, preserving the exact tested candidate bytes. Helper body is unchanged; it was rebuilt for the private discovery type in the original Mac run.
- macOS: identical original harness observes the original off-scope automatic connection, while the corrected candidate rejects it and retains valid selected-interface multicast discovery through a real TCP/TLS ClientHello. Disabled, malformed and wrong-network controls reject; helpers remain responsive and exit cleanly.
- Fifteen focused policy cases pass; earlier guard-mutation evidence is retained. Combined Windows-only header correction produces the identical recorded Mac helper binary; no fresh repetition was needed for this branch preparation.
- Windows header-slice compilation on Mac with pinned genuine MinGW headers passes with the correction; this is not a native Windows/full translation-unit build or link. No native Linux/Windows runtime, physical multi-host LAN, completed peer authentication/model transfer, full suite or release qualification.

## Reproduce and inspect

`original/regression.py` and `combined/mac-regression.py` are the unchanged Mac harness; `original/policy_checks.cpp` covers focused policy cases. They require macOS sandbox-exec, an eligible interface, the matching helper binaries and recorded own-host networking assumptions. Inspect their arguments before running. Native Linux/Windows need platform-specific fixtures, not the Mac script unchanged. Full build/link inputs and identities are retained in the reports; no new binary was built here.

`combined/COMBINED-REPORT.txt` lists the precise remaining native checks. `combined/header_probe.py` requires the separately pinned MinGW header fixture described in that report; this branch does not include a Windows SDK. Historical report delivery/private wording does not describe current branch readiness. The three-file product correction is in the first commit; do not reapply the reference patch on top.

## Credit and provenance

Original LAN-boundary finding: repch1c in #338 item9. Candidate implementation, Mac testing and Windows include-order correction: Sunny River, with AI assistance. JPP supplied contributor/review guidance. Existing source copyright and base authorship are preserved; no native reviewer ACK or unearned co-authorship is implied.

Original corrected report: https://github.com/btxchain/btx/issues/338#issuecomment-6554059976
