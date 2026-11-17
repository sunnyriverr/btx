# Proposed bounded Ubuntu qualification — not dispatched

This is G3 of the existing wallet goal. Local source preparation and controller-only checks are complete; actual artifact restoration, executable entrypoint construction and native case results remain unexecuted. No BTX module was imported or daemon started on the Mac. No workflow/ref/job has been published.

## Concrete proposed action

One dedicated public-fork branch **`sunnyriverr/btx:codex/ci-wallet-payment-preview`**, workflow `.github/workflows/session3-wallet-payment-preview.yml`; files in this directory under `proposal/` on that branch. One Ubuntu24.04 job, no configure/build, one normal-runner descriptor test. Unique concurrency group and cancel-in-progress=false; neither peer's branch/job/cache is reused or altered.

The user explicitly approved one bounded public-fork job after local preparation/review. The initial source-head gate stopped before publication, so that one job remains unused. Recheck the assessed head/inputs and dispatch once after roll-forward review. No upstream PR/comment is included.

## Inputs and ordered gates

1. Native binary baseline **371013d61dc124a363521df5b94e97f64d2464f2**. Current test-context/control head **bd847e2b986722c1723b4cd60988d4f4908452d4** is stored separately as upstream_head/functional_source_head/control_base. Verify live release head matches upstream_head before restore and launch; otherwise stop for another impact assessment. No whole-current-head native binary claim.
2. Retained artifact **14284330090** from build43978863702; ZIP SHA256 **1f9dbc07d7ce15f01ddbe2d90e192b53444aad2b3f073d95f0c180d6ff2ba8d8**, size215419343. Metadata still unexpired through2026-11-23T23:47:14Z at preparation. Producer/inner-checkpoint digests, source tree and daemon/CLI hashes remain fixed in manifest.json. Fresh metadata is not new downloaded-byte verification; the future restore repeats the actual full byte checks before using anything.
3. Restore only immutable original source, exact binaries and generated test configuration; no object/library/cache/build graph, node state or wallet database. Verify every producer/original critical source hash first, then apply all16exact current functional updates from the assessed head, then our two reviewed test-only files.
4. Apply exactly the candidate script and runner from overlay/, checking input/output SHA256 and mode755. Preserve explicit overlay identity in restoration, construction, invocation and qualification receipts. Product source/binaries remain unchanged; never describe the overlaid test tree as an unmodified source checkout.
5. Inspect SQLite/wallet/CLI/daemon component flags and static ELF dependency closure. Use the provisioning line from the successful earlier sendall run, including libevent-extra. Actual host closure remains unqualified until that job runs.
6. Construct the actual SendPSBTPreviewTest entry point, initialize binary-path selection and confirm one clean regtest node/configuration without calling setup/main/run_test or creating a node. Construction is not a native pass. If construction fails, the native stage does not run.
7. Invoke the normal runner with explicit script, descriptor filter, jobs1 and the exact config/private scratch. No method overrides, custom wrapper of assertions, policy repair or test skips. Strip controller read tokens from the child environment; retain ordinary framework node startup and recorded isolation flags.

## Runtime and result contract

- One attempt, no retry/rebuild. **900seconds** for the runner including its serial cache preparation; five-second resource samples plus mandatory final check. Monitored scratch cap512MiB, free-host start4GiB, stop floor1.25GiB. These are monitored bounds, not a filesystem quota or measured future cost.
- Configured shutdown waits are20seconds direct-child TERM,5seconds KILL wait and up to30seconds group retries:55seconds of configured waits plus scheduling/inspection overhead. The17minute workflow step is the separate wall-clock limit; no30second total-cleanup promise. Whole job40minutes covers provisioning, restoration, preflight, test, collection and upload.
- Require unchanged critical candidate/parent framework and binary hashes, exact static four-case option inventory, one named Passed CSV row plus Passed ALL row, no skip/missing/duplicate selection, framework success and cache success. Require each of four exact publication and post-confirmation log stages once; require all three preview-stage logs once. Those log stages follow the assertions in the frozen candidate, not substituted outcomes.
- Require affirmative final bounds and owned process-group/listener/daemon shutdown. Preserve raw logs/CSV/identities/state before deleting only disposable scratch. Never upload wallet databases or full RPC configuration/passwords. If the controller is interrupted or cannot prove cleanup, it does not claim qualification or delete potentially live data.
- Preserve and classify failures as setup/runner/test/controller/evidence until diagnosed. A successful Actions badge alone is insufficient. No product defect, whole default-suite, GUI/Windows/Mac/current-ModelNetON or release qualification is claimed.

## Local evidence and remaining gate

`../controlled-source-preflight.json` records nine non-native controls for changed log/selection handling: invented complete input accepted, missing/duplicate/wrong-case/absent-success/unregistered/changed-option inputs rejected as expected. They use AST-extracted side-effect-free control functions; no test/framework import or native execution. Independent `REVIEW.md` additionally challenges source and controller semantics. Reused prior native controller evidence is separate from this candidate's future construction/run.

`payload-hashes.json` freezes all dispatch payload bytes, including exact overlay files. Source/JSON/AST checks and controller controls are not a substitute for the future entrypoint/native stages. The provisional default runner entry is subject to actual case success and measured cost before handoff.

Next action after roll-forward source review: use the already approved single Ubuntu job for those ordered gates. Recheck source/artifact/refs/bookings; follow that exact job to terminal, preserve evidence, and do not create an automatic rerun or upstream post.

## Reviewed source-head movement before publication

The initial publisher stopped at its very first release-head assertion, before external writes or native jobs. The approved single job remains unused. New release headbd847e2b986722c1723b4cd60988d4f4908452d4 incorporates19commits, including JPP795 and our807. Exact source comparison confirms236wallet/RPC/validation/policy/script/kernel/primitive/init-related Git blobs unchanged. Other changed product areas are compiled-out ModelNet, disabled SwapNet, and peer-message handlers outside this isolated no-peer fixture. This supports scoped wallet-path reuse, not whole-current-head binary qualification. The retained native pair remains built from3710, explicitly recorded as such.

Preserve the verified full3710baseline first, then apply the16exact current functional source updates (including JPP's framework and newly registered test files) from current-functional/, and finally our same167line fixture plus rebased runner. The candidate runner preserves807 and both new networking entries. All changed/current critical functional hashes are checked before/after execution. Separate source/upstream_head/control_base/functional_source_head fields prevent a native binary source from being mistaken for the current test context. See ../hosted/roll-forward-assessment.json and head-move.json. The workflow, artifact/binaries, fourcases,900second limit, isolation and single-job authority are unchanged; no rebuild or new test scope.
