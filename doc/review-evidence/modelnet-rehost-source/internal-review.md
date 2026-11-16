# Final internal source and evidence review

Verdict: no remaining code or executed-case blocker found for this scoped
source-path repair. One provenance record needs closeout before delivery.
This is internal review of retained source and results, not an additional native
execution or independent platform qualification.

## Evidence checked

- `candidate.patch` SHA-256 is
  `f34fe93ae1d97fd66ae6e6d102929bb99dc65da5c59c6a7f48066ceedf9b4ca6`.
  Both changed source-file hashes match `source-manifest.json`.
- Both maintained case bodies match `execution/maintained-cases.inc` byte for
  byte after surrounding whitespace removal. The include hash is
  `0334eb1b58f64c778a11cea38c9f06477d496f12f784f224225128c2b9889bb6`.
  `regression.cpp` includes those bodies and invokes both cases. This is a
  compiled focused consumer with a small assertion adapter, not the complete
  Boost test executable or the full hosting suite.
- `execution/attempt2/build-result.json` records accepted source/checkpoint
  `1e2f8b5f12295002334d3390c12cac0bb4ae2aff`, baseline and candidate compilation,
  baseline exit 1 and candidate exit 0. Logs report the same 156 assertions:
  baseline 8 failures, candidate 0. Baseline failures concern the stale path and
  absence of the new path-only persistence failure, not unrelated fixture aborts.
- The repair build restores tracked files against the accepted source, verifies
  file contents and applies the focused patch. It does not require the separate
  upload-capacity repair #754. The 16 MiB integration input does not need that
  large-file capacity change.
- The baseline and candidate `rehost_cases.py`, `minio_upload.py` and
  `base_minio.py` are byte-identical. Their five ordered case names, model URI,
  artifact ID and source SHA-384 match. All five candidate cases return HTTP 200
  with matching remote bytes; baseline relocation, post-restart relocation and
  materialized-checkout cases return 404, while its two original-path controls
  return 200. The driver removes the owned remote object and requires GET 404
  before each attempt, preventing a previous upload from masking failure.
- Candidate staging identifies the rebuilt helper SHA-256
  `6604f19ae06401b6714920e6e490adab9f539d1fcb6b8613fc58f40048965d43`, matching
  the build result. Integration framework and wrapper receipts both report 0.
  Staging's `native_execution:false` describes preparation only; the subsequent
  native log and integration receipts provide execution evidence.

## Transaction and behavior

The duplicate branch changes the authoritative source path only after normal
qualification derives the existing artifact. Path and optional pin promotion
persist together, all four fields roll back on failure, and store pin changes
follow successful persistence. A path-only change preserves pin, admission and
verification. A same-path no-op avoids persistence. Tests cover pin combinations,
failed save followed by unrelated save/reload, retry, invalid and different
inputs, and exact checkout bytes. The earlier admission concern was withdrawn:
the complete `DemandSeedLocked` already sets eligible unpinned imports to SEEDING.

## Required record closeout

At review time `source-manifest.json` still names initial run 43791539061 and
`qualification: RUNNING`. Replace those execution-status/identity fields with
the final build and native run identities and retained evidence references.
Preserve the first compilation correction and staging permission failure as
attempt history. No native rerun is warranted solely for this bookkeeping.

## Limits to retain in delivery

Native integration is bounded Linux/real-MinIO SOURCE_FILES with one 16 MiB
single-file artifact and disposable retained node/CLI fixtures; the rebuilt
helper is the relevant candidate. Baseline helper relevance rests on recorded
source equivalence, not a claim that every baseline binary was rebuilt at the
current release. Maintained tests ran through the compiled focused consumer,
not the full hosting/node suite. No native Mac/Windows, multi-file cloud, WAN,
production model, multipart-capacity, concurrent source-mutation or release
qualification was performed. Persist failure coverage uses a directory at the
atomic-save destination; it is not a power-loss durability test.

The source path is a usable verified location at import time, not a permanent
guarantee that the caller will keep those files unchanged. The repair preserves
that existing ordinary-import contract rather than altering identity, policy,
watch settings or local-piece authority.
