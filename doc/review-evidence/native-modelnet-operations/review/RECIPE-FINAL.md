# Final native recipe source review

Reviewer `/root/windows_boundary_review`, 4 November 2026. Read-only review of current runner/workflow and now-present native.py, run.py, candidate-controls.cpp and input-manifest.json. No fixture execution, build, dispatch, network action or product mutation. Only this review written. Parent remains responsible for final manifest regeneration/hash validation before dispatch.

**Assessment: PASS for the final targeted corrections and bounded diagnostic dispatch readiness**, subject to parent manifest generation/validation. The native marker and outer timeout issues described in the historical review below are resolved by the final addendum. Exact-function scope and other stated evidence limits remain. This is source review readiness, not a passing Windows result.

## Corrected findings

- run() shares a persisted 65-minute budget across runner stages and clamps each subprocess timeout to remaining budget. Commands are not started with under 30 seconds left. This leaves a nominal ten-minute margin under the workflow's 75-minute ceiling for cleanup/upload, subject to pre-runner checkout/cache time. The counter starts at the first runner invocation, not the Actions job start; do not describe it as an exact global job deadline. The 30-second check is a launch threshold, not thirty seconds subtracted from every command timeout.
- A disk stop now raises after recording the original command result and before baseline diagnostic assertions can count it as an intended compiler failure. Candidate restoration executes through the existing try/finally.
- whole_node_build_run is set on the actual daemon attempt. Unit status now requires zero command exit and a positive announced test-case count, recording the announced count. Unfiltered unit invocation is preserved.

## Native fixture assessment

native.py compiles the generated candidate fixture with **both cl and clang-cl**, C++20, optimization and static runtime; it explicitly defines WIN32 and each compiler supplies _WIN32. It uses the actual source fs/generate/UniValue types and actual UniValue implementation. Logging is the stated substituted dependency. Platform-conditioned wrapper code omits POSIX-only auxiliary networking dependencies from this fixture on Windows; the complete product helper translation unit is separately compiled by the generated-object gates.

run.py supplies isolated child environments and temporary roots. It tests unset, empty and exact OpenSSL override states, empty/configured inference, existing/missing/nonexecutable backend profiles, direct runner refusal, zero CUDA output PID, unchanged result object, empty resident map, false native PID checks, stale-record removal, explicit Unix adoption/peer/listen/RPC refusal, unchanged endpoint bytes/path, no missing parent creation and private PEM refusal before callback/truncation. Each C++ Check contributes to process failure; no failed assertion is ignored. Python preserves each mode's output, return status, markers, parent-environment equality and temporary-root cleanup. The aggregate result requires all mode exits zero.

The generated C++ contains extracted product functions plus a harness; it does not exercise the full helper RPC dispatcher, scheduler/slot acquisition, Modelnet library or node lifecycle. In particular its empty-resident assertion is direct function state, not proof of loadmodel/RPC admission, and no actual acquired-slot assertion exists here. Full generated object/library/node/default/unit gates are distinct evidence. POSIX descriptor and real listener/worker controls exist in the conditional fixture source, but native.py does not run them on Windows and they do not replace the actual affected Linux PR403 restart acceptance.

## Remaining useful corrections or claim limits

1. **Marker control limitation:** run.py creates a POSIX shell script as the existing worker on every platform. On Windows this is not a valid native executable. An incorrect implementation that attempted native launch, then failed to execute this file, could return false with no marker and pass the current direct-runner checks. Thus these tests establish the exact guarded return/output/state behavior, but marker absence alone does not establish absence of a process-launch attempt. Use a tiny valid native marker executable if the deliverable claims a discriminating native non-execution control; otherwise state the narrower evidence explicitly. The profile test still catches false capability advertising with an existing regular file.
2. **Nested timeout coherence:** native.py permits 150 seconds build plus 150 seconds run for each of two compilers (600 seconds total), while the parent native-controls command permits 360. Ordinary quick controls are fine, but the inner maxima cannot all be consumed successfully. Reduce/share those inner budgets or increase the parent cap within the overall shared budget. Preserve a timed-out fixture as incomplete controls, not a candidate product failure.
3. Inner subprocess.run timeout handling kills the direct child, while the parent's timeout path kills the process tree. A native compiler's own timeout may leave a linker descendant until hosted-job teardown; make timeout cleanup tree-aware if complete process release is claimed. The current ordinary-success cleanup removes each fixture exe/objects and run.py removes each temporary tree.
4. Startup overlay application remains outside the top-level save/error handler; the full candidate phase is protected. This nonblocking evidence limitation remains from RECIPE.md. Full tracked source identity excludes arbitrary untracked files, so the fixture must continue to avoid injecting product build inputs.

## Exact identity and restoration

Fixed404 HEAD, exact403 helper overlay and manifest-qualified candidate blobs remain checked against full tracked source. Paired targets retain the same compile database and verbose command capture. Candidate writes remain inside try/finally, which restores all three baseline-overlay bytes and rechecks full tracked identity on ordinary failures/timeouts. The outer taskkill path and original log hashes are retained. Source restoration does not turn candidate object files into baseline objects.

Native fixture input-manifest scope correctly says exact extracted functions rather than whole-project qualification. It records extraction ranges/content hashes, variant source hashes, generated output hashes, real source dependencies and harness hashes. Native.py itself is not currently in that harness-hash subsection; retain its exact identity with the controls revision or the hashes below. Parent's final generation/validation remains necessary before dispatch.

Reviewed hashes:

- `runner.py`: `2e2110dff1260fe0076de746c0ca0974e5345b3fc69300c1971ee05b58aa8a65`
- `workflow.yml`: `03375e9816d87003a0a2d709931b64b08e344eba6e4694c73835bf0b09ede56a`
- `fixtures/native.py`: `6d7bfd52ae81591405630fd2d3762112b3f818acc14c5d50d161b8b2a161f67f`
- `fixtures/run.py`: `d116e1e20369e05c2afc84ab1a57b8ec0f762a1f433ef89207b5544b4a95c63f`
- `fixtures/candidate-controls.cpp`: `70e0302f9815ced2088d0529fea12ac632453d851eedab5f42d55f4589ac2fd6`
- `fixtures/input-manifest.json`: `a77b988dcff1cc40e55b53687ce4838e4c9e9f9879f9c50dbcfbe9aab4acb3ba`

## Final targeted correction addendum — PASS

The two outstanding fixture issues are resolved in the current inspected files. No new blocker was found in these deltas. No runtime, build, dispatch or network actions were performed during this review.

native.py now compiles native-worker.cpp separately with each actual native compiler and records the command and resulting worker binary SHA-256. That worker appends one marker line, verifies its write and emits a JSON success object. run.py requires this compiled worker on Windows, copies real PE bytes to both worker.exe and the exact extensionless worker pathname used by the direct-function fixture, and positively launches both paths before each mode. Positive acceptance requires exit zero, exactly one marker invocation and JSON ok=true. Each positive marker is removed and its removal checked before guard tests. A positive setup failure prevents the dependent guard test and makes the summary fail.

After the product-function fixture, native_no_launch records marker absence and participates in aggregate pass rather than being an informational field. Thus the former invalid-shell-file ambiguity is removed: marker absence is now tested against a known launchable native worker at both tested path forms, with the same marker environment. This is a discriminating successful-worker-execution control; it does not prove absence of every possible low-level launch attempt or expand coverage to the full dispatcher/node.

The parent's native-controls command now permits 720 seconds, matching two times the inner 60-second marker build, 150-second fixture build and 150-second fixture run maxima. Ordinary orchestration overhead and any smaller remaining shared job budget can still cause intentional timeout; such a result remains incomplete acceptance, with parent process-tree cleanup/restoration, and is not converted into a product pass. No extension to the shared 65-minute cap was introduced.

Current targeted-review hashes (supersede matching earlier-file hashes above):

- `runner.py`: `feccd256923504c4277d0add9424ff461ba665dcc9268fbf96466e049589b46e`
- `fixtures/native.py`: `5dfdc8979836fe84c5a5c925f1bc7187fe38111d7151a73ccb1db59f90446ec7`
- `fixtures/native-worker.cpp`: `bdd7df5a3c337c1f1db2e02088f86cdf8718b600c3ef669986f6c605db042705`
- `fixtures/run.py`: `d8187ae26ff87763ed22d1af700062d419f699118a605520de5e51a85cdab771`
- `fixtures/candidate-controls.cpp`: `70e0302f9815ced2088d0529fea12ac632453d851eedab5f42d55f4589ac2fd6`
- `fixtures/input-manifest.json`: `fa4d976d6bdc578f01021a6597c619bedb6d9128bdf23701598144052aa7458b`
