# ModelNet cloud recovery — scoped Linux qualification complete

**Verdict:** the accepted helper at f40eb37a recovers missing local pieces, resumes a valid partial read, rejects corrupt origin bytes, recovers after that origin is corrected, and preserves a quota-blocked checkpoint across helper restart. Exact bytes/materialization and post-recovery restart checks passed. The specific Linux helper outcome is qualified; cloud-only catalog reconstruction and wider release qualification remain separate open gates.

## Exact source and native profile

- Accepted source: f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6, containing667/694/707.
- Helper SHA256:41c07b549f2c1b1abfa259345267757c52d7ba7e3bf501cb6b0e68a8d6a87bb6.
- Built Ubuntu22/GCC11.4/OpenSSL3.5.9/CMake3.31.6 from verified configured checkpoint; actual52helper dependency actions,2workers,283.7seconds. No full node or GUI rebuild.
- Runtime Ubuntu24.04x86-64, pinned real MinIO RELEASE.2025-04-22T22-12-26Z, PIECE_OBJECTS, small one-file fixtures (normal~4KiB, partial~8MiB; quota filler60MiB). Older retained8d6node/CLI proxied RPCs; this is not a whole-current-daemon or installed-package test. No FakeS3 fallback.

## Actual acceptance evidence

| Case | Result | Receipt |
|---|---|---|
| Missing local pieces, catalog unchanged | Normal getmodel hydrated exact bytes; local after restart; export matched |43655225026 normal-current-result.json |
| Origin unavailable after first verified piece | Saved prefix/cursor retained; retry restored exact live/export bytes before and after restart |same run partial-valid-result.json |
| Resumed origin corrupt, then corrected | Corrupt bytes refused with no live admission; corrected origin recovered exact live/export bytes, including another restart |same run corrected-origin-result.json |
| Integrity and zeroGET-budget refusal | Intended error reached; no bad live pieces/export; unrelated healthy model exported exact bytes |same run cloud-controls.json |
| Full valid EOF checkpoint under quota pressure | Quarantine preserved; normal filler removal allowed completion with0neworiginGETs |same run quota-eof-result.json |
| Quota-blocked checkpoint across restart | Cursor/piece snapshot preserved through restart while still blocked; quota relief resumed with0newGETs; exact export and returned identities checked after another restart |43655466244 result.json |

Fresh native exits were0for every selected driver and downloaded records passed the actual validators. Those assertions, not green workflow badges, support the verdict. Current normal/partial/corrected tests reuse the accepted maintained bodies; selected wrappers avoid repeating the entire layout matrix. The two accepted partial/corrected methods use one result filename, so wrappers snapshot each immediately to retain both proofs.

Primary run: https://github.com/sunnyriverr/btx/actions/runs/43655225026 . Extra quota restart control: https://github.com/sunnyriverr/btx/actions/runs/43655466244 . Build: https://github.com/sunnyriverr/btx/actions/runs/43654513467 . Full machine receipts and checksums: build/verified-build.json, primary/qualification-receipt.json, quota-restart/qualification-receipt.json.

## Review and retained evidence

An independent read-only reviewer found no blocking filename/parser flaw. It correctly limited the original quota test: that run resumed before restart and only checked local status afterwards. The extra quota-only run closes that gap on the same unchanged helper; other passing cases were not rerun. Identity is bound through the original URI/expected artifact paths and exact byte proofs; only specified cases independently compare returned identity fields. Do not claim independent returned-ID assertions in every maintained case.

All matching667/707before-controls, native layouts and catalog-deletion/reimport evidence remain reused. Current source and613/667/707feedback were refreshed; no review request or source delta reopened those tests. Credits: repch1c's real-MinIO fixture/694quota repair, existing667/707source authors, and Numair's integration/component evidence remain attributed. Internal review is not independent platform execution.

Retained build binary14137827346 and records14137901738 were downloaded and verified against GitHub ZIP digests; inner binarySHA matches build/result/source manifest. Cache14137812368retains producer-verified archiveSHA f273aa4bdabef3aff92dde54b55aabd8b36f54cd5243529c794effe7d6b47852 through2026-11-28T23:48:17Z. The cache ZIP was not downloaded locally; future reuse must check both ZIP and inner manifest/archive. Original caches/working node are untouched. Runtime records14137294505/14137218662 downloaded/hashverified. See artifact receipts for exact expiry/digests.

## Operator guidance and open gates

The source-attributed guide is OPERATOR-RECOVERY.md. Existing complete export/original reimport was already qualified on retained707candidate bytes with source-path equivalence to current; do not mislabel it a fresh current-binary catalog-loss run. Cloud-only payload objects with no catalog or complete export and no peer did not recover metadata, although remote bytes survived. The intended backup/restore contract remains with Numair/recovery maintainers on613comment6885862830; no protocol or policy was invented.

Not qualified: full current daemon/installed archive, Mac/Windows, current-binary SOURCE_FILES matrix, multi-file/large-model scaling, native peer/package metadata restore, malformed catalog/power-loss, WAN/R2, useful inference, full suite or release/default-branch/tag/officialasset. Earlier positive SOURCE_FILES evidence keeps its recorded source/profile, not a broadened current-binary claim.

The scoped Linux helper qualification is complete with the external metadata contract and wider platform/release limits above. No product patch accompanies this qualification.
