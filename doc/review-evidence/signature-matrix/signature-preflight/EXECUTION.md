# Real GPG signature matrix — local PASS

## Actual results

Pinned BTX helpers: main074dac167c26c1e091198f691ed5727817dba88a, unchanged source. macOSarm64/systemPython3.9.6; task-local conda-forge GnuPG2.4.5 with libgcrypt1.11.1. Real RSA2048 OpenPGPv4 identities, two disposable principals and A’s signing subkey. Tiny asset.bin/manifest fixtures only. No mocked GPG success, no productionkeys/archives, no publishernetwork flow.

| Row | Actual outcome |
| --- | --- |
| G0 | Isolated signerA/B, public-key verifier and empty-key verifier ready;7rowfinalrun completed in7.09s |
| R1 | Real sign_release_bundle succeeds; actualGPG verifies and returns both signing-subkey and expectedprimaryfingerprints; bundle validation passes |
| R2 | Changed signedSHA256SUMS rejected by actualGPG with BADsignature |
| R3 | Changed asset retains validchecksum signature, but actualensure_bundle rejects the contenthash mismatch |
| R4 | RealBsignature accepted with expectedB, rejected with expectedA; signingCLIwrongpin restores originalunsignedmanifest/checksums byteexact and removes partialsignature |
| R5 | Emptyverifier withoutApubkey rejects with No publickey; no automaticretrieval configured |
| C2 | Same rolledbackfixture signs/verifies with expectedA on retry; bundle valid |

Setup G0 and six behaviour checks R1–R5/C2 passed (seven matrix rows). R6optional notrun. C1prior catchableinterruption controls remain simulated/injected evidence; no newSIGKILL/crash/restart qualification. No fullpipeline, officialsigner, signedofficialrelease, reproduciblebuild, nativeBTX/GPU/ModelNet/SwapNet, installer, seeds, hosted run or public post. This is component integration, not officialreleaseauthentication. No product patch needed.

## Setup failures retained separately

Initial package extraction needed zstd support/merge handling; extra libintl/ncurses runtime dependencies were identified before loading. GPG2.4.5/libgcrypt1.10.3 tools loaded but keygeneration faulted in the crypto library; both RSA and an exploratoryEd25519 attempt failed before BTXmatrix. Owned diagnostic summary retained, not a publicfinding or BTXdefect. Finalsuccessfulprofile uses libgcrypt1.11.1 and libgpg-error1.55, returns to plannedRSA2048; no acceptance assertion weakened. Do not describe this as Ed25519PASS or certifyoldtoolset.

Unrelocated condahelperpaths required explicit scratchagent startup/private libraryenvironment; launcherPIDs differed fromdaemonPIDs. Finaldriver verifies owneddaemoncommand before shutdown. A public-key import setup attempt failed before G0; fixed by providing an isolated verifieragent, then completefinalmatrix ranonce. Setup-attempt/agent-explicit-attempt/verifier-import-attempt records are distinct from finalmatrix-results.json. An intermediate cleanup driver error was corrected; final cleanup independently verified.

## Keys, agents and disk cleanup

Only disposable fixtureidentities used. All4privatehomes and fixture copies removed; no ownedagent remains on a separate processcheck. Publicfingerprints/status outputs remain in evidence; no privatekey/passphrase export archived. Agents were terminated only after matching task-owned commands; no ambientgpgconfkill or peeragentoperation.

User-authorized old-log cleanup losslesslycompressed171inactive historical log/GitHub snapshots outside livebookings/openfiles. EverydecompressedSHA256 matched before original removal; cleanup-receipt.json preserves originalpaths/hashes and gziprestore locations. Logicalspace saved about169.6MiB; actualfree movement differs with filesystem/backgroundwork. No binaries/keymaterial/currentledger/activepeerpaths deleted. Task-owned optionalheaders/docs/statictoolfiles also removed. Diskgate required1.25GiB+8MiB before run. No claim of continuouspeakmeasurement.

## Evidence and closeout

matrix-results.json andmatrix-raw.json contain final outcomes/actualcommands; run_matrix.py is exactfinaldriver. verified-results.json pins source/tool/library hashes and limits. Product source unchanged, signatures/checksums verified through existing helpers. Third-party toolsetup recipe remains local; not a new upstreamdependency mandate.

Local acceptance milestone complete. Retain task-local tool binaries and driver to address concrete feedback; private keys are gone. The concise local result is now prepared and reviewed in handoff-draft.md and HANDOFF-REVIEW.md. Next trigger: explicit publication authorization, followed by freshness/overlap checks, or substantive maintainer feedback. Do not repeat successful rows, generic signing tests or actualrelease downloads. Officialidentity/signature and producer-record gates remain external.
