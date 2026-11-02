# Native Mac verification of the #286 sole-URI guard

**PASS: the same second-instance sole-URI test fails on acbf7efb and passes with repch1c’s 89a8c8e9 main.rs.** One native macOS arm64 sequence per variant.

## Target and decision
Baseline is the unchanged retained acbf7efb20b1b82da06affdae2ead08068cf743c Atlas app. Candidate is an isolated export of the same target, changing only main.rs to the exact file at repch1c’s 89a8c8e98a77934a02ff77dd71d0e52cfb2bf450. This answers the missing Mac runtime guard question; it does not qualify full PR286 head b7fe45c3 or its Windows changes. Credit for the implementation remains repch1c.

## Native observations
Both first instances connected normally to the same wallet-disabled, modelnet-disabled, peerless loopback regtest node. The user confirmed the native connection prompts. No queue injection, browser substitute or system handler registration was used. The exact same variant-aware launcher and inert fixtures ran in order: sole URI, mixed distinct URI plus .btx file, no arguments, sole .btx file. Only preview/close actions occurred; Parse locally was never clicked.

| Case | Baseline | Candidate |
|---|---|---|
| Sole btx:atlas-guard-sole?amount=0.125 | Absent through an advancing 00:13:06 poll, approximately 49s after launch | Exact preview once; drained and quiet through 00:18:36 |
| Mixed CLI URI + file containing distinct URI | Both exact values once | Both exact values once |
| Empty invocation | Quiet | Quiet |
| Sole .btx file | Exact preview once; quiet through 00:15:16 | Exact preview once; quiet through 00:20:36 |

Mixed previews were file value first, CLI value second; both were individually closed. No duplicates were observed through subsequent advancing refreshes/no-argument controls. All eight second processes exited zero and each original first process survived. Bounded quiet windows support no duplicate observed, not an unlimited exactly-once guarantee.

UI evidence is coordinator transcription of native CUA accessibility observations in ui-observations.json, supported by tool-call history. Raw AX files/video were not retained. Launch JSONs preserve exact arguments, times, process IDs and verified executable hashes. Observed labels are local Brisbane time; launch timestamps are UTC. No hidden backend/API queue reads were used as the runtime oracle.

## Reproduction and provenance
See source-identity.json, guard-on-acbf.patch, candidate-identity.json, variants.json and build-result.json. The candidate used the identical retained build recipe and lockfile: offline locked Rust1.95 Release, one job, isolated target. Build completed in226.4s. Source/contract/identity review is in review/REPORT.md; that review did not independently execute the runtime test.

On the same Mac/toolchain/dependency cache, build.capture.py records the local candidate build recipe. Start a disposable wallet-disabled loopback backend with lab.py; connect the chosen first app normally. Fill variants.json with that executable’s path, SHA256 and actual PID. For the original local harness, run `python3 launch_case.py before sole` (or `after sole`), observe native previews through ordinary refresh, close each preview and check later refreshes; repeat mixed, none, file. The launcher validates identity and process survival. It is not an unattended UI assertion runner. Run variants sequentially, closing the first before switching because their bundle identifiers match. Never use a production cookie.

## Limits and cleanup
One sequence per build on native macOS M4/arm64. Direct CLI second-instance dispatch only: LaunchServices/default handler, cold start, Windows/Linux, full PR286, installed release, payment parsing/execution and full-suite qualification remain untested. The older backend was only a connection/polling fixture. File-picker automation required rebinding and user confirmation; measurement began only after LIVE LOCAL/advancing refreshes.

Both apps and the disposable node exited; RPC port closed; owned scratch data removed. Source/build/evidence are retained. This subsequent evidence publication is authorized. Capture-time private labels in JSON/reports describe the earlier state. See README.md for the portable reproduction entry point; capture scripts record the actual local setup and are not portable as written.
