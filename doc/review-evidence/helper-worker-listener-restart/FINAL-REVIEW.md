# Current ecd9310a retarget — bounded final review

Reviewer: delegated child `/root/linux_in_tree_review`, BTX session 2, 4 November 2026. Final-delta source and artifact review only. This report is the only reviewer write. No runtime rerun, VM, product source, build, ref, GitHub or ledger mutation. Publication remains held.

**Verdict: no current-base identity, correctness or claim blocker found. The same reviewed one-file repair is on accepted ecd9310a; actual current baseline/candidate helper compilation and executable linking are evidenced, and the unchanged runtime comparison remains sensitive with legitimate controls passing.**

## Retarget and complete-source identity

Reused the earlier `../FINAL-REVIEW.md` source/contract assessment. Accepted helper.cpp is byte-identical between old46 and `ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629`. The candidate helper still hashes to `30a6b81add189cd08e59ff5677c6051722614ee11167f703fc720f285ad3c45e`; it matches the file in product commit `0c9b339e18a1a306a227c24e06aca0ee87154652`. Independently checked that this product commit's parent is exactly ecd9310a and its sole changed path is `src/modelnet/helper.cpp`. The guarded POSIX descriptor utility call and four post-stdio/pre-exec placements are unchanged from the reviewed repair.

Independently compared every entry in baseline-source-hashes.json against immutable accepted Git blobs: all **14,165 regular tracked files** match, with no missing names or hash mismatches. Also checked the ten newly accepted files against the baseline manifest and their available current worktree bytes; all match. This includes native discovery, supervisor/header/platform changes, accepted jail work and test integration. The owner's final guest-verification recipe checks the complete regular-file map against guest source with only helper.cpp's candidate hash substituted; its completed record reports all 14,165 verified. The sparse local worktree is not itself presented as the full staged guest tree. Symlinks and untracked/generated files are outside this regular-source manifest claim.

Thus this is current accepted source plus the one helper change, rather than old46 renamed as current evidence. Neither newly accepted node-to-helper changes nor the accepted jail work substitute for cleanup of descriptors created by the helper and inherited by its ordinary workers.

Metadata-only closeout amendment: inspected metadata-amendment.json and both immutable commits. Final product `ef10c7bea81a7045a471113809edf23fb4a29c0e` and previously tested `0c9b339e18a1a306a227c24e06aca0ee87154652` have the same accepted parent `ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629` and exact tested tree `d4c9fcc4824739ab99e31fa047bf9e888e14e310`. Only commit metadata changed to remove obsolete base wording; the reported-by/thanks credit remains. No source change or new execution followed, and the recorded runtime identities remain attached to that unchanged tested tree.

## Actual compile/link parity

Read retarget.json, both build result/log files, compile-parity.json, final guest verification and collection recipe, both case/driver/raw logs and archive contents. Both final raw logs contain exactly one helper.cpp compile and an actual `bin/btx-modeld` executable link. Independently extracted the raw helper commands: baseline and candidate are exactly equal and match the recorded parity commands. They retain C++20, O1, project definitions/hardening/OpenMP and the common `-include cstdint` prerequisite.

The current baseline build also compiles the affected supervisor, native_discovery and swarm_fsjail translation units, alongside the other dependency-triggered objects, before archive/executable linkage. The candidate rebuilds helper.cpp and relinks. Successful recorded times are 21.01 seconds baseline and 14.01 seconds candidate. This is qualification using the existing previously built current-project cache with accepted deltas rebuilt, **not** a fresh entire-project rebuild on ecd9310a. The earlier46 full-target build and its 21-minute duration retain their separate attribution.

The retained pilot-mtime invocation did no work because archive timestamps were older than cached objects. Its NOTE correctly excludes it from product results, and the final logs prove real compilation/linking before the current runtime cases. The binaries used by runtime differ from each other and from the earlier46 campaign; current build, case, archive and final guest hashes agree.

The common Alpine GCC14 `-include cstdint` setting remains disclosed on both sides; there is no prerequisite product-source edit. Its original membership compile failure remains the prior evidence for this prerequisite. Accordingly this is not a claim that untouched default accepted source builds on this toolchain without that setting.

## Current result and controls

The exact fixture sources and executables in the new archive match the earlier reviewed runtime manifest. They remain finite synthetic local workers, with no GPU inference or socket creation by the fixture. Both current resident records show a live non-zombie worker after the owned helper termination, so an absent/dead worker cannot satisfy the candidate observation.

Current baseline records the worker retaining its listener, replacement local RPC responding, and replacement TCP listener missing. The raw replacement log independently reports the expected bind/listen failure while Unix RPC continues. The candidate worker remains live without the inherited listener; the replacement has both local RPC and the requested TCP listener, with no bind-failure line. Subsequent baseline release/restart observations retain their original diagnostic role. These results support the narrow listener-restart effect, not a measurement of real-world failure frequency or service throughput.

Idle and explicit-unload listener/RPC recovery controls pass on both current binaries. As before, baseline unload `regression_pass=false` records the listener inherited **before** unload; replacement listener recovery itself is true. Baseline restart return 1 is the expected aggregate regression result. It is not a failed unload control being disregarded. Candidate restart returns 0 with all three regression assertions satisfied.

Inference output, adapter prompt stdin/JSON stdout, llama prompt argv/stdout and intentional worker-error handling all pass on both binaries; local RPC remains usable during active worker work and after the error. Both controls scripts return 0. There is one final execution per case/configuration on ecd9310a. The earlier46 and historical three-run observations are not additional repetitions on this base.

## Archive, cleanup and remaining limits

Independently hashed current-linux-artifacts.tgz: `b0b29bde2374579ad972e548be91a44c78327c309e4081bdfa1cdc84a7db114d`. It contains exactly **64 regular members**, with precisely the manifest's names. Checked every member against runtime-artifact-manifest.json: zero missing, extra or mismatched regular entries. All runtime fixture entries match the preceding campaign. Executed binary identities are:

- Baseline: `4c6b59419727bc5ad050ab0b46ff7abf374212a1af26f0f3525e99cbcc2070ad`.
- Candidate: `b491be34e9438fcf9ada43d6d6f04a44353f975beb526009064ad06a63c29e53`.

The final owner snapshot reports no live owned binaries. Restart cases record owned helpers exited, ports released and disposable directories removed; I/O controls record exited helpers. Final VM/cache/disk cleanup is the parent's closeout responsibility, not independently observed by this reviewer. The snapshot's pre-cleanup guest free-space count does not claim cleanup has finished.

Qualified scope is the affected actual Linux helper executable build/link and the focused process/descriptor comparison on Alpine/aarch64/musl, Linux 6.12.81, GCC14 and OpenSSL 3.5.9 with the common prerequisite flag. No native Windows/macOS, glibc, full node, full unit/functional suite, GPU/model workload, real peer/PQ1 transfer, stress, every descriptor-limit fallback or release qualification is established. The existing Windows guard remains source-preserved, not natively build/runtime-qualified here. The repair does not claim general worker termination or a new containment policy. No posting or broader investigation follows from this review.
