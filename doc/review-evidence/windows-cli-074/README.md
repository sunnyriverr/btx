# Final acceptance review — 15 November 2026

Verdict: **bounded Windows CLI campaign acceptance PASS; full Windows unit/release qualification excluded.** The useful consolidated report is prepared in HANDOFF.md. Publication held. This review executed no native tests, builds or reruns.

| Original gate / row | Disposition | Evidence and limit |
| --- | --- | --- |
| Exact source/profile/cache | PASS |074dac16, clang-cl20.1.8/MSVC14.51/SDK26100, original cache hashes checked |
| Eight selected executables link | PASS |43687743717, j2, ~450s; full test_btx explicitly excluded |
| Preserve compiled objects | PASS |successor10546633105, independently restored/12921file hashes verified in43688614528 and43689575654 |
| Actual archive gate and PE closure | PASS |43688614528, e10c6c94 ZIP, no dependency problems |
| Pinned Python/OpenMP packaging and isolation | PASS within scope |Official pinned input hashes; isolatedPython origins and loadedruntime modules in archive. Does not physically remove producer |
| Supported shipped executable probes | PASS |CLIversion reused; daemon/modeld/util version, tx/open help, guardstdioEOF, securityusage. Embedded python isolation reused |
| Relocated path with spaces | PASS |43689575654, exact e10c6c94 ZIP, all8selectedhashes match savedbuild |
| Default-off ordinaryRPC | PASS |ready, disabledSwapNet error, cleanstop |
| Explicit-on ordinaryRPC/SwapNet | PASS |in_process true, spend0, no wallet, cleanstop |
| Same-datadir restart | PASS |RPCready and intendedstate after reopen, cleanstop; no stale lock prevented this reopen |
| Tracked process cleanup | PASS within scope |All3ownednodeprocesses exited0 viaRPC; guardstdioEOF exited0; no forcedcleanup |
| Owned descendant/guard tracking | PASS within tested path |43691799053: node and guard assigned before resume to Windows Job Object; root/descendants tracked, job empty on five post-stop polls; ModelNet disabled |
| Physically unavailable producerPython | PASS |43691799053: selected producer directory absent before/after node run; archive-local runtime/RPC/spend0/cleanstop; producer restored in finally |
| Owned TEMP/TMP override | PASS within focused final control |Job-owned workspace/tmp used in43691799053; not exhaustive pathlength qualification |
| Restore/cache instructions | PASS with caveat |Originalmarker preserved; successor has distinct btx-successor.json; use its exact filehash/source/profile manifest, not oldbaseline restore's marker expectations |
| Consolidated local handoff | READY |HANDOFF.md + evidence-index.json; publication held |

All planned bounded CLI rows now have results. Final controls used the exact retained ZIP with no compilation, assembly, gate/isolation/tool/restart reruns. One additional producer-unavailable startup/RPC/stop and guard EOF were necessary to test the changed condition and owned-job cleanup. Job membership observed one node at pre-stop; no node-owned guard was spawned in this ModelNet-disabled profile. This does not establish cleanup for unexercised helper workloads or arbitrary third-party processes.

## Evidence and review decisions

The inner retained archive is SHA-identical to the prior gated archive, so the native gate/isolation passes apply to these exact bytes. Avoided repeating them. Corrected probes use source-reviewed command contracts and exact expected exit/output; no general ignore-failure logic. No product patch.

First workflow artifact upload failed due to mixed root paths; next run retained logs. Unsupported guard-version probe then blocked lifecycle. Both were fixture defects; original objects remained cached. Final run retained the ZIP before fallible probes and completed only missing checks. The older report's 'Gate3 unrun' status is superseded by this row table. Earlier cache contains old unit/fixture binaries; those were not rebuilt or qualified and are not shipped in this archive.

Fresh main remains074dac16. #356 has no new answer to the earlier target/compiler question in the queried discussion; these scoped results do not settle it or ask to close the issue. Session2/3 current selected deliveries are independent and not gates on this report.

## Restore and retention

Cache10546633105: `btx-main074-successor-43687743717`, branchscope `refs/heads/codex/ci-windows-root-configure`, 494869171 compressedbytes. Restores project-build and vcpkg-installed at D:/btx-native-035. No overwrite. Follow archive-workflow/lifecycle-workflow Verify saved successor bytes step. It validates all files against project-build/btx-successor.json and BUILD_PASS/source before use; retain exact compiler/dependency inputs before future compiling. Do not use original baseline-marker verification on a successor without adapting its source/profile check.

Artifact14151084362: windows-main-lifecycle, expires29Nov07:22:54UTC, outerSHA05b406a64173d8aa1e45a93d660aa0990cd0f7e55022b84019871dfbf5d4e157, innerZIPe10c6c94. Local lifecycle-evidence.zip outer/inner hashes verified. APIcache retention is not permanent storage; no expiry assumed beyond service metadata.

## Final controls and next

43691799053/163eccdc: exact retained outer/inner archive hashes verified, no source checkout/build/cache restore or assembly. Selected hosted-job producerPython3.12.10 directory physically renamed only on disposable github-hosted runner, then restored in finally. Controller ran under archivePython in isolatedmode. Node/guard assigned suspended to non-breakaway Job Object before resume; guardEOFclean, nodeRPC/SwapNet/spend0/noWallet, app-localPython/OpenMP loaded, RPCstop0, five empty ownedjob polls and no forced cleanup. Input/results/restoration retained in final-controls-evidence.zip; its artifact digest verified locally. Five polls are a bounded observation window, not a promise about unexercised services.

Finalhandoff prepared. No native acceptance row remains open for this scoped campaign. Publication still held; next authorized step is one consolidated evidence/results handoff, without new tests, compilation or extra product PR. Full units/nativeModelNet/GUI/GPU/funded/release qualification stay excluded.


## Native run provenance

Build: https://github.com/sunnyriverr/btx/actions/runs/43687743717
Archive gate/isolation: https://github.com/sunnyriverr/btx/actions/runs/43688614528
Tools/restart: https://github.com/sunnyriverr/btx/actions/runs/43689575654
Producer/descendants: https://github.com/sunnyriverr/btx/actions/runs/43691799053

JPP prior build/cache evidence and repch1c portability work are credited as prior inputs, not execution of these runs. AI-assisted preparation/review; actual native results and fixture mistakes are recorded above.
