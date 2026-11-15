# ModelNet operator recovery — qualified profile and limits

This guide covers supported model-data recovery, not wallet recovery. Current accepted source is swapnet-v2/f40eb37a.667and707are incorporated into that open candidate; default branch/tag/published archives have not thereby gained them. The focused current-helper Linux qualification has completed; exact scope and receipts are in REPORT.md. Use exact version/binary identities from the campaign evidence rather than assume an installed release has these fixes.

## 1. Catalog retained, model pieces missing

1. Check `getcloudstorageinfo` reaches the helper and shows the intended backend/layout. Keep credential references private; a capabilities bit alone does not prove origin access.
2. Request the same saved model URI with `getmodel`, using free-only retrieval. Preserve the same model directory and its valid partial download state.
3. Confirm the result is local and `exportmodelpath` produces a complete model directory. Compare the model/artifact IDs and file hashes against the original trusted identity/manifest. A returned plan, provider entry, healthy HTTP response or green wrapper badge is not restored-byte proof.
4. After a normal helper restart, repeat retrieval/export and confirm the same bytes remain usable. Do not delete scratch/checkpoints just to force a retry.

Evidence: repair/ and partial-retry/resume-fix/ show real-MinIO normal recovery and interrupted-prefix retry with exact bytes/restart; maintained regressions accompany667. Current helper41c07b54atf40eb37a passed the focused PIECE_OBJECTS integration in43655225026; earlier AUTO/SOURCE_FILES results retain their original profiles. This is not a new instruction to rerun the completed historical cases.

## 2. Read interrupted, budget exhausted or storage full

Correct the actual cause through normal configuration/storage management and retry the same request. Network, budget, quota and I/O failures should keep usable verified progress;707only discards an integrity-rejected checkpoint. Do not erase unrelated models or catalog data as a generic cleanup step.

The existing quota-EOF native control filled the disposable store, then removed its known disposable filler normally. The resumed file completed with zero new origin GETs and exact bytes/restart. That is evidence for valid-resume preservation, not a recommendation to delete valuable data. Current-helper run43655466244also restarted while quota-blocked, verified the checkpoint/pieces survived, then completed with0newGETs and checked exact export/returned identity after another restart.694prevents impossible peer downloads from evicting unrelated unpinned models; author/maintainer quota tests are tracked separately.

## 3. Origin bytes failed integrity verification

Correct the origin to the expected trusted bytes, then retry the same model. The accepted707path records rejection before cleanup, discards the rejected partial state, and still requires full file hash and pieces-root verification before admission. This also passed on current helper41c07b54in43655225026. A valid partial read interrupted for another reason must remain resumable.

Evidence: the published PR707 evidence contains identical before/after/corrected-origin/restart and valid controls. Numair reports component tests passed onf40eb37a, not a fresh MinIO rerun.

## 4. Catalog metadata lost, complete original/export survives

On the tested disposable setup, normal `getmodel` could not use orphan pieces after catalog.json alone was deleted. Re-importing the surviving complete exported model directory recovered without editing catalog JSON:

```json
{"method":"importmodel","params":["/path/to/surviving/model-export",{"publish":false,"pin":true}]}
```

This is an RPC request shape, not a command already executed against the reader's node. The original directory layout/content must remain intact. Check that returned model_id and artifact_id match the saved expected identities; export again, verify exact bytes, and confirm local retrieval/export after helper restart. The tested pin option requires available storage; no policy/identity bypass is implied.

Evidence: the original catalog-loss evidence receipt linked from README.md / run43651794115. Ubuntu24.04, real MinIO PIECE_OBJECTS, one4,163-byte SafeTensors model, retained707candidate helper and older RPC proxy. Source route equivalence withf40eb37a is recorded. This is not malformed-catalog, multi-file/large-model, native peer/package or full installed-node qualification.

## 5. Catalog and all complete local model files lost

Remote payload objects survived byte-for-byte in our cloud-only control, but normal getmodel with no peers returned WAIT_FREE/not_local and export returned NOT_FOUND. Do not call this remote data loss or promise automatic recovery from a bare URI plus bucket objects. Search/index records do not supply the full ordered manifest required by the traced cloud path.

A live peer manifest is a separate existing source route, not a native recovery result from this campaign. Raw saved manifest JSON/unsigned package import is not a verified substitute for a supported metadata backup/restore procedure. Do not manually promote catalog flags or bypass signature/identity checks.

The intended retention/restore contract is awaiting the maintainers on613comment6885862830. Until resolved, record this as an explicit capability/contract gate, not a successful cloud-only backup guarantee.

## Scope and stopping point

The campaign verifies the specific Linux helper profile and stated fixtures. Mac/Windows, WAN/R2, large/multi-file models, power loss, useful inference and full release/package acceptance remain separate. Stop once the documented workflow is recovered and independently checked, or the exact unsupported state is established. Do not broaden an operator incident into speculative changes or repeated tests without a concrete decision.
