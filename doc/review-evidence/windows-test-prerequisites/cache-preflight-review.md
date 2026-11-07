# Executable-path / credential-fixture cache preflight

**Prefer exact c660 cache `10155086005` as the candidate input for the central path correction.** Its objects already use the desired target-derived executable definitions. Do not pay another global test rebuild from current-flags cache `10162013501`, and do not combine objects with mixed command provenance. A cheap current-candidate build plan remains an inference until exact native restoration, normal configure and Ninja observation succeed.

Reviewer: Session 1 delegated child `current_windows_plan_review`, 8 November 2026 Brisbane. Read-only existing source, ZIP/checkpoint, profile, report and receipt inspection; no API/download/build/source/index/cache mutation. This is cache/contract preflight, not current native qualification.

## Observed evidence

| Cache | Exact source / checkpoint | Objects | Relevant commands |
| --- | --- | ---: | --- |
| `10162013501` | 70f / `06297cd1...` | 5885 | Current suffix-less path definitions; actual full build and bounded runtime observed |
| `10155086005` | c660 / `89f67291...` | 5885 | `$<TARGET_FILE:...>`-derived `.exe` paths and test-target dependencies; prior native integration observed |

Independently compared both archived checkpoints: the complete 5885 object-path sets are identical. All 6230 compared installed dependency files have identical paths/hashes, excluding the declared compiler file-hash cache. Root CMake/vcpkg inputs match. The same native compiler/SDK/dependency profile has already been used through the verified cache transitions; future reuse still requires exact restore/profile validation.

Their CMake cache and rules hashes match, but graph/compile-table hashes differ:

| Configuration | c660 | Current 70f |
| --- | --- | --- |
| `build.ninja` | `0d0453e5...` | `59d09908...` |
| `compile_commands.json` | `5d33b0ee...` | `096e03d2...` |

Native run `42365244708` independently supplies **observed**, not inferred, transition evidence: restoring c660 then normally configuring stock current source changes 2607 compile entries, all in `test_btx`. Actual definitions change from `bin/btx-open.exe`, `btx-modeld.exe`, `btxd.exe` to suffix-less paths. This global definition change drove the costly current rebuild; its subsequent ordinary run took 3785.66 seconds. Restoring proper definitions on top of current-flags objects would again change those test commands, even though only a handful of runtime cases need qualification.

The central existing CMake correction also restores real executable target dependencies and handles optional daemon-OFF configuration without requiring a nonexistent target. It preserves configured output names/directories rather than merely guessing a suffix.

## Current candidate and inferred cheaper route

During this review the owner assembled `37472d88c1e0d7dd88ac92e1c698351a0a7e9bd7` on 70f. Independent Git comparisons confirm its root CMake, vcpkg manifest, `src/test/CMakeLists.txt`, both cloud/R2 fixture files and S3 client file are byte-identical to c660. The remaining c660-to-candidate delta is **22 files**, including changed headers/product/test source that may legitimately invalidate dependent objects. No native plan for this candidate/cache pairing has yet been observed.

The smallest honest route is therefore:

1. Restore exact immutable cache `10155086005`, source c660 and checkpoint `89f67291...`; verify the full source/profile/configuration/dependency/file catalog before restoring timestamps.
2. Check out the exact reconciled candidate, retaining its declared source delta. Normally regenerate with preserved supported arguments. Compare the complete new compile table with the correct-flags cached table; require no unexpected global command change, unchanged dependencies and correctly resolved target paths/dependencies.
3. Observe the fresh current native plan before compilation. Permit the real changed source/header closure and normal metadata/link work within a bounded plan; stop if it becomes another broad rebuild. Do not promise a specific object count/duration from file counts alone.
4. Compile/link the maintained target with one coherent configuration. Run only the newly affected path/credential cases and their relevant refusal/environment-restoration controls, preserving the existing current baseline and all unrelated passing evidence.

This route is **strongly supported as a reuse candidate**, not proved cheaper/compatible by source equality alone. Cached Ninja log/dependency state, transitive headers, regeneration and current host/profile validation still decide the actual work. Saved remote metadata is not fresh availability or a post-run payload rehash; the owner must confirm availability and verify the payload on restore. No cache should be deleted or rewritten.

## Code alternatives and claim boundaries

The clean correction is the existing central `TARGET_FILE` plus dependency change. Appending `.exe` per fixture, creating extension-less copies, overriding macros only for selected objects or suppressing assertions would either duplicate naming policy, retain output-layout assumptions, or manufacture mixed configuration evidence. The existing executable review already rejects those substitutes. A broad redesign moving all executable paths into a compiled utility could reduce future definition fan-out, but requires consumer/dependency migration and is unnecessary for this authorized reconciliation; do not invent it to avoid using the compatible cache.

Credential reconciliation should keep the supported case-local synthetic ENV source on Windows, retain strict PATH permission refusals and POSIX file paths, preserve distinct read/write credentials and restore previous environment values. Reuse of a prior corrected file does not waive any current assertion.

The current candidate includes two previously qualified S3 cleanup test bodies through its whole cloud-file reuse, and takes `s3_client.cpp` from accepted release `2f3b574867c11ab79eba829123689b76e6137a38`; the latter independently byte-matches c660. Record that as **accepted S3 adoption**, not a newly invented credential repair or a full build of the release. Do not repeat unchanged S3 cleanup tests merely because their source is present. If the two ordinary nonfake transport cases now progress past credential initialization, their outcomes may also depend on the adopted S3 cleanup correction; do not attribute the complete result solely to the ENV fixture change.

This review approves no native outcome, stock/release claim, further product fix or upstream posting. The native exact-candidate plan is the next discriminating observation.
