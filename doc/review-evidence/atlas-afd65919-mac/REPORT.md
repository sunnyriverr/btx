# PASS — Atlas afd65919 native Mac sole-URI acceptance

Numair requested this exact integrated-head check on PR #273 (comments 6602199759 / 6602159992). The pre-build public discussion check found no completed matching Mac result. This is one scoped native acceptance run, not a release qualification.

Exact target: `afd6591970e7f8d65871412b9d7cf03b48f30b97`.

## Completed

- Fetched exact upstream commit and exported gui/atlas in isolation. All228files match the commit, independently source-reviewed. Shared dirty source preserved.
- Offline locked release build with Rust1.95.0, one compiler job, no incremental cache; completed exit0 in about204seconds. Minimum free space about1.94GB, above1.25GiBreserve. Only configuration override is test bundle identifier dev.btx.atlas.downloadstest. Source and build receipts retained. Initial export helper used a Python tarfile argument unavailable in installed Python; corrected safe-path extraction before build, no product failure.
- Locally ad-hoc signed Atlas Acceptance Test bundle, binary identity in app-identity.json. Exact binary SHA256: 2b3973619f7ee07e17fc2b8b9f938720dffe35c1bf4ebb18f92a592b06a1af6e.
- Disposable wallet-disabled, modelnet-disabled, peerless regtest fixture starts at height0 on127.0.0.1:64125. Existing fixture node hash03a3fb602e0a0dea77583f774ecf516f5875137829c2a9f6c03637f925300fc6; it is connection/polling infrastructure, not a newly qualified node. No production access.

## Native result

On macOS 26.5.1 arm64, the first app visibly connected as LIVE LOCAL to the disposable regtest fixture, with advancing normal refreshes. At 2026-11-03T11:33:58.890057Z the same freshly built executable was launched with exactly one argument: `btx:atlas-guard-sole?amount=0.125`. The second process exited 0 in 0.113 seconds and the original process remained alive.

The existing native app then displayed **Preview BTX resource** containing that exact URI. This visible observation is the acceptance oracle; process exit alone is not the result. We closed the preview without parsing or executing it. Subsequent AX observations at 11:36:40.913Z and 11:37:20.188Z showed no preview, LIVE LOCAL, refresh timestamps advancing from 21:36:34 to 21:37:15, and mempool sample counts from19 to23. No repeat was observed across that39.275-second interval. These are sampled UI observations, not continuous event tracing or a universal exactly-once guarantee.

The launcher also writes an unused file fixture inherited from the prior harness; the launch receipt proves that fixture was not passed in this sole-URI invocation. No mixed-argument/file test is claimed here.

## Setup obstacle and reusable lesson

The native file picker's Go To Folder interaction repeatedly reset under computer control. We switched the picker from Columns to List and selected a visible mode0600 copy of the disposable test cookie in the same owned regtest directory. This completed the normal native connection; no host-state injection or product patch was used. LIVE LOCAL, not a user acknowledgement or an attempted click, established connection success. This is an automation/setup obstacle, not demonstrated Atlas product failure. Prefer a visible disposable credential file when this picker cannot select a dotfile; remove the copy at cleanup and never expose its contents.

## Evidence and scope

`summary.json` records the original local evidence hashes; `SHA256SUMS.json` verifies this sanitized publication. The source reviewer checked all228files against the exact commit but did not independently execute the UI run. No screenshot/video artifact is claimed. AI-assisted execution and internal review are distinct from independent human or platform verification.

Scope is direct CLI second-instance delivery on native Mac, one invocation. Windows/Linux, LaunchServices/default handlers, cold-start, mixed arguments/file association, payments, validation/consensus, the full suite and release qualification remain untested by this run. The retained older node binary only supplies connection/polling infrastructure.

## Closeout

The owned app and fixture node exited cleanly; disposable fixture/cookies removed. Build/source/app retained locally. This is an AI-assisted native UI run. The internal reviewer checked source identity and test design, not an independent runtime execution. No screenshot/video is claimed; UI excerpts are transcribed from the native accessibility tool output.

Paths in this public package are sanitized. SHA256SUMS.json verifies published bytes; original-local hashes in summary.json identify the pre-sanitization records. This check answers Numair's request6602199759; the earlier guard failure/control evidence remains in the linked PR273/286 discussion.
