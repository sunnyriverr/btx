# Atlas #286 Mac guard: contract/source review

**Verdict:** the proposed native second-process before/after test directly distinguishes the sole-URI guard fix. No blocking source or setup error found in the inspected artifacts. This is an internal read-only review, not a runtime ACK. Owner: BTX test 1 delegated reviewer `/root/atlas_guard_review`; model/effort inherited, exact setting unverified.

Baseline: `acbf7efb20b1b82da06affdae2ead08068cf743c`. Candidate: that exported Atlas source plus repch1c's `89a8c8e98a77934a02ff77dd71d0e52cfb2bf450` main.rs. This is not full PR286 head `b7fe45c339b0dade34d804083dd263a366ee80d2` qualification.

## Checks and mechanism

- Independently hashed all 231 manifest files: only `gui/atlas/src-tauri/src/main.rs` differs, matching candidate SHA256 `a764008374aa5208929e5cec8968a5173b94159e01798de94a93e754bf309fb5`. Baseline manifest exactly matches the retained Downloads manifest. Guard patch SHA256: `1dabb7dd806fa1dfba0ea8840912b412fc4b2655e4a9239c0aebd78c87e2a04c`.
- Retained baseline executable SHA256 is still `df4f93614300fcd240169c930eb6835c201f3435a4395ae9bd45010ef8296e5c`. Both build scripts are byte-identical: Rust 1.95.0, offline/locked release, one job, separate target directory, `dev.btx.atlas.downloadstest` override. Cargo.lock bytes match. Candidate build completion and binary hash remain execution-owner checks.
- Inspected cached single-instance 2.5.4 and deep-link 2.6.2 sources. The Mac single-instance callback receives actual second-process argv; deep-link `handle_cli_arguments` emits only on Windows/Linux. Baseline skips a sole scheme URI regardless of platform. Candidate `plugin_forwards` is false on Mac, so `Host::receive_link` receives it. Mixed/file/no-argument Mac dispatch remains equivalent.
- The authoritative pending queue is `Host::links`. `receive_link` appends accepted previews up to eight; the connected ordinary UI refresh drains through `atlas_pending_links` and opens previews. Therefore an unconnected first instance, unresolved initial connection modal, or a stalled refresh is not an interpretable missing-preview result.

## Acceptance and limits

Use sequential variants with a verified first instance, invoking that variant's same executable directly for each second process. Record first PID survival, second PID/exit, exact argv and fixture bytes. Do not run baseline and candidate simultaneously under their shared identifier. A new primary instance accidentally receiving startup argv would test a different path.

Use the same sole URI, fixture contents, observation rule and launch mechanism before/after. Expected signature: baseline sole URI absent during advancing ordinary polls while a subsequent sole-file recovery preview arrives; candidate sole URI visibly arrives exactly once within the bounded window. Mixed URI plus a file containing a distinct URI must expose both exact values when previews are individually closed. Sole-file and no-argument quiet cases are valid controls. Close existing previews and observe further advancing polls to bound duplicate claims; exit zero alone proves neither delivery nor correctness. If reusing the old `launch_case.py`, its hard-coded first PID and baseline hash require variant-aware inputs before execution.

The old report supplies one Mac baseline sequence and a valid recovery control, not a candidate result. A finite quiet window supports “no duplicate observed in that window,” not an unlimited exactly-once guarantee. Keep scope to direct CLI second-instance preview delivery in the native Tauri app: no LaunchServices/default-handler, cold-start, Windows/Linux, payment parsing/execution, installer/release, or full PR286 claim. The older wallet-disabled backend is acceptable for connection/polling but is not qualified by this test.

No tests, builds, UI actions, VM operations, publication or product edits were performed by this reviewer. Only this report was written. Review output reservation is released on handoff; BTX test 1 retains runtime/build ownership and should record final binary identity, observations and cleanup before promoting a native result.
