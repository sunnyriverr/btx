# ModelNet cloud recovery — consolidated evidence for #667

**Verdict:** missing local model pieces recover through ordinary getmodel without catalog edits; a transient origin failure after the first4MiB now resumes at the saved next piece and finishes exact-byte recovery, including helper restart. Full-file SHA-384 and pieces-root checks still gate publication.

Code: [6d81278e](https://github.com/sunnyriverr/btx/commit/6d81278e4b0384528228668d2b02f13138ed3f8f), adding the one-line resume correction and maintained regression atop original PR667commit81afbe56. Use that code commit/PR branch for review and builds; this separate branch records evidence. Native rebuilt helper2a7255a9 has identical helper bytes; the maintained Python file is identical to the executed regression. Existing MinIO fixture/report credit: [repch1c, #613](https://github.com/btxchain/btx/issues/613).

## What ran

| Scenario | Before | After |
|---|---|---|
| Catalog retained; local source/pieces gone; ordinary recovery and restart | False local status, missing bytes; [43588655872](https://github.com/sunnyriverr/btx/actions/runs/43588655872) | Exact recovery/materialization and restart; [43590785003](https://github.com/sunnyriverr/btx/actions/runs/43590785003) |
| Real MinIO piece1 withheld after checkpointing piece0; restore exact origin object, retry same model, restart | Duplicate prefix; stream longer than expected file; [43595155870](https://github.com/sunnyriverr/btx/actions/runs/43595155870) | Only2remaining origin GETs; exact8,392,777bytes in store/export, cursor removed, restart healthy; [43595218373](https://github.com/sunnyriverr/btx/actions/runs/43595218373) |
| Exact maintained in-tree MinIO integration | Fails at original partial-retry condition | Passes byte/restart checks; paired execution [43596936934](https://github.com/sunnyriverr/btx/actions/runs/43596936934) |
| Normal layout and safety controls | Earlier evidence retained | AUTO/SOURCE_FILES/PIECE_OBJECTS pass; corrupt-origin/zeroGET refused and healthy model usable in43595218373 |
| Corrupt a later origin piece after partial checkpoint, then restart | Not a new before/after claim | SHA-384 refusal, continued nonlocal/INCOMPLETE export after restart; final [43597247023](https://github.com/sunnyriverr/btx/actions/runs/43597247023) |

The standalone partial-recovery harness is byte-identical before/after (SHA256b3a1626ff21e7d2defc9107da73cda832d3eebfc97bde03901e94e3b3fc5b641). Maintained regression SHA2566bf1ec290e8edb28c8b194ecbdfb92b6a43a51f5d390c735b02103e82c39bf5f is in the code commit. No manual catalog/cursor/quarantine edits and no FakeS3 fallback in these native claims. Withholding/removing data touched only disposable fixture objects/pieces.

## Commands and provenance

Executed entry points are the immutable fork CI recipes: [build and paired runtime at f9509715](https://github.com/sunnyriverr/btx/tree/f9509715ea9877f21b4d2f33aaf63d4e11007e5b), [maintained pair at f46b4f2d](https://github.com/sunnyriverr/btx/tree/f46b4f2df0ba1fb19bf5ca7e1dcc6b4fd48e8c75), and [final specialized corruption control at bfb37540](https://github.com/sunnyriverr/btx/tree/bfb37540955186dce5eec1216a63701f19e8a177). Each pins downloads/config and propagates native exit/results. The maintained entry is test/functional/feature_modelnet_minio.py with its configfile; requires Docker and real MinIO to exercise the added row. The fallback explicitly reports that row unrun.

[Exact source/binary/artifact provenance](resume/final-evidence.json), [before](resume/paired-before.json), [after](resume/paired-after.json), [maintained before](resume/maintained-before.json), [maintained after](resume/maintained-after.json) and [resumed integrity](resume/resumed-corruption.json) accompany raw logs. Before helper SHA2567436885f08cade46ccd84d3891d06ca35f252c950a983458a4a30135548b5c60; after83fb3f0b1be5cca1e7edfaa8571e0f5c0ee53391d1303a86828e480f2cc2d99b. Ubuntu24.04x86-64 runtime; Ubuntu22/GCC11/OpenSSL3.5.9 helper build. Retained older8d6node/CLI only proxy RPCs; not a whole-current-node rebuild.

The43596936934maintained pair passed but the job overall failed in an additional control that expected identical error wording.43597082688then exposed an extra inherited fixture invocation. Both failed logs and [corrections](resume/control-corrections.md) are preserved; only that specialized wrapper was rerun, and43597247023passes. Do not infer a pass from a workflow badge or hide these fixture failures.

## Limits and remaining decisions

This repairs valid saved checkpoints. It does not repair an already-poisoned/invalid cursor/quarantine left by the old retry or corrupt origin. Corruption is still blocked after restart (short stream), but graceful recovery from that invalid state is unqualified. Recovery after deleting catalog metadata is outside this repair. Remote bytes survived the separate metadata-removal observation.

Small synthetic models; no model execution, spend, native Mac/Windows, WAN/R2, full-suite/release or large/multi-file latency qualification. Normal reads probe piece paths; completion hashes while holding the catalog mutex. The broader recovery campaign remains open. Original one-piece/matrix evidence is retained in this directory and at immutable [d8fb2e2e](https://github.com/sunnyriverr/btx/tree/d8fb2e2e9b48e7edd8632c34f026d7a7c8207615/doc/review-evidence/modelnet-cloud-missing-pieces).
