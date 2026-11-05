# Native fixture qualification recipe review

5 November 2026. Session 1 child `/root/remaining_pid_review`. Reviewed `candidate/fixture.py`, `inputs.json`, `workflow.yml`, supporting integration/checkpoint behavior and the actual three cloud-control bodies. **No compile/link/cache-closure blocker found in the bounded recipe.** Final acceptance depends on actual records. One conditional process-cleanup evidence weakness is identified below. This is recipe review, not a new native result. Only this report was written; no source/code/Git/CI/network/ledger change, build/test or delegation.

## Exact target and normal build boundary

Inputs name candidate `473a2a0bf8e528a977d07137712d6a1d6dfc8cf6`, tree `d860c05655a867235ca38e6e78d5b2431cc24a8f`, cached integration `8a642b1ea7ed726fe527c9a6eb0f80a00da10d3f`, published prerequisite PR411 `362c36b2...`, and the exact retained checkpoint/cache key. Local dispatch records CI controls `e4c2e7b5...` for run 41997202444. The parent subsequently reports compile/link completed and selected controls are running; this reviewer did not access CI or independently verify that outcome.

Prepare checks the candidate bundle digest, verifies/fetches it, validates the full cached source catalog, restores only a checkpoint matching its original profile/catalog, then checks out the exact candidate. `s.catalog(TARGET,...)` verifies actual HEAD plus every tracked blob/symlink's working bytes. The asserted delta is twelve files: eleven fixture TUs plus the PID header. The separate tree/per-file digest input fields are not directly asserted by fixture.py, but exact commit and blob catalog verification already determine the source tree; their postrun receipt comparison remains useful for attribution.

The original generated compile-command entries for all eleven TUs must equal the baseline entries exactly. Required Modelnet/tests/wallet/ZMQ settings remain ON. There is no hand-built compiler command, model flag override or duplicate-symbol tolerance. Build-info must name the candidate and report clean Git state.

The component manifest contains the original full `build.ninja` bytes unchanged as a prefix and adds one explicitly named component executable. Its fifteen explicit objects are main, the eleven selected maintained fixture objects and three existing production/wallet-support objects retained from the original unit link. They must be unique and already present in the maintained test_btx explicit closure. Link rule, implicit library dependencies and other link settings are copied from the original unit rule; only component output/import-library/PDB/response-file names change. This is a component link using maintained objects/libraries, not a full-unit link. The original `bin/test_btx.exe` rule and graph are not replaced, pruned or invoked.

## Freeze and cache validity

Plan and actual build both use `ninja -C BUILD -f evidence/four.ninja` and the same explicit component target, preserving the mandatory frozen-manifest recipe identified in the earlier full-unit correction. A root/default Ninja invocation is not reintroduced. The plan must have 1–60 steps, reject command-line invalidation and CMake/glob-bootstrap messages; the actual build uses normal Ninja dependencies at j4 with a 900s budget. Unexpected invalidation cannot silently become accepted reuse.

The exact checkpoint marker digest is pinned to `aad9f31c...`, its profile source must be cached 8a, and the measured current profile must match the cached actual profile or the exact documented two-field host transition (runner image and Ninja file digest). No compiler/SDK/profile delta is accepted implicitly. Ninja's reported version is checked separately.

Checkpoint restore verifies the full cached file set and hashes, including objects, libraries and normal Ninja state, and verifies source bytes before restoring recorded source timestamps. Candidate checkout changes actual fixture/header bytes normally; no object/log/dependency timestamp fabrication is present in this recipe. There is no CMake-input delta. Retain rechecks original configuration/rules/cache/compile-command hashes and the final exact source catalog. New objects and updated normal Ninja metadata are saved under a separate candidate/profile/run cache key; the original immutable cache is not overwritten.

The modelnet library is checked before/after by exact SHA-256, with dumpbin evidence of canonical S3PieceStore GetObject and absence of GetObjectW, and must stay byte-identical. Since this candidate changes fixtures only, that is an appropriate reuse condition for the existing production implementation. A fixture method compiled as GetObjectW cannot silently be presented as linked canonical behavior.

`checkpoint_valid` means the retained byte/profile/source state is coherent. Retention intentionally can run after build/runtime failure and records that status; cache-save success alone is not test acceptance. Preserve failure status/logs when reporting a partial checkpoint.

## Selected runtime and cleanup oracles

The fixed input list has thirteen cases: the previously reviewed ten real PID/filesystem cases plus two store2 controls and one R2 storage control. Each invocation uses the newly linked component executable with one exact registered case filter. The recipe requires an actual one-case start observation, exactly one reported passed case and exit 0; missing filters, no tests, assertion failures, timeout or process failure cannot satisfy that gate. It does not mark whole suites or the full maintained executable passed.

The three cloud cases are meaningful existing oracles:

- `store2_02_tiered_miss_fills_local` writes through the fake cloud interface, retrieves actual bytes through the real tiered store and verifies local caching/residency.
- `store2_03_never_serve_unverified` checks invalid commitments and on-disk/cloud tampering remain refused with no returned corrupt bytes.
- `r2s_01_layout_identity_invariant_across_key_families` preserves the Windows owner-only-file refusal, uses real scoped fixture ENV credentials for FakeS3, reads whole-object and piece-object bytes, compares both to payload and SHA-384, and measures actual backend GET/PUT counts. This is not live R2/AWS qualification.

The ten PID cases exercise real temp-directory/probe paths and preserved filesystem/JSON/reload/timestamp oracles identified in PID-REVIEW; no source-design review was repeated here.

A unique per-run data root is required absent before creation. TMP and TEMP point each fresh child at a dedicated scratch tree. The script snapshots scratch paths before/after every case, requires equality and restores environment values in finally. Because scratch starts empty and each successful case must leave it empty, this adds useful absence evidence for scratch outputs. Custom `-testdatadir` data lives outside that scratch tree and remains inspectable; do not describe this comparison as removing every runtime data file. Successful native deletion also remains narrower than universal proof of zero shared-delete handles.

## Conditional cleanup evidence weakness

`integration_support.quiesce()` records any owned remaining processes, changes status to OWNED_CHILDREN_REMAINED, kills those processes and confirms a later snapshot is empty. However, fixture.run then unconditionally assigns FOCUSED_PASS. The always-run retain stage calls quiesce again and can overwrite `owned_processes_after_execution` with an empty snapshot. Therefore final status and final snapshot alone do not prove the cases exited with no surviving children.

This does not invalidate a clean observed run and was not a reason to cancel it preemptively. Before claiming natural cleanup, inspect preserved records for `owned-cleanup-*.log`, command timeout/tree-kill logs, budget-stop fields and actual process observations. If any survivor required killing, retain that event and report successful forced cleanup separately. Parent has explicitly accepted this verification requirement: archive absence of owned-cleanup/kill logs plus an empty process snapshot before a natural-cleanup claim. No reviewer changes to the running recipe are required for that evidence check.

If future automated evidence must distinguish this itself, preserve a cumulative cleanup-event record and refuse to promote a survivor/kill event to an unqualified pass. No such edit was made here.

## Truthful completion boundary

Parent verifies downloaded source/configuration/library/object identities, actual normal Ninja build log and all thirteen case logs before assigning outcomes. This run can qualify eleven maintained fixture objects, one explicit component link and thirteen selected cases on the candidate/prerequisite profile. It cannot qualify the other socket/process/security fixtures, full test_btx build/run, node relink, stock accepted source, Unix execution, live cloud, release or publication. Remaining unit barriers retain their own evidence. Parent owns final verification/resources; this child acquired/released no resources.
