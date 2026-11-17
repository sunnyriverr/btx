# Verified-piece cloud upload

**Bug and tested repair:** editing a source file during `importmodel` could leave `cloud_uploaded:true` with cloud bytes that differ from the imported model. Read from verified catalog pieces instead. The same actual-helper check reproduces wrong cloud bytes before and preserves the imported bytes after, for SOURCE_FILES and PIECE_OBJECTS.

[Code commit `c6b2aba6a5a2`](https://github.com/sunnyriverr/btx/commit/c6b2aba6a5a2cdafeec8e2adde1d3a661c8c5c3b) · publication parent `0afc505f3e063ff8919366464881b81d9e037638` · [rebased diff](publication.patch).

## Result

| Contract | Baseline | Candidate |
| --- | --- | --- |
| Timed same-size source edit, SOURCE_FILES | Identity check fails; helper reports upload success | Original imported bytes uploaded |
| Same source edit after first PIECE_OBJECTS PUT | Identity check fails; helper reports upload success | Original imported bytes uploaded |
| Unchanged file, both layouts | Exact bytes | Exact bytes |
| Later multipart-part failure with a good object already present | Prior object preserved, abort and same-ID retry pass | Same controls pass |

16 MiB generated SafeTensors input; source writer changes 4 KiB after the first upload request and before its response. Same native.py, fixture, origin and product flags in both phases; only the expected before/after oracle differs. Baseline exits2for the two identity-contract failures; candidate exits0. Artifact/model IDs match across paired imports. Four clean helper starts/shutdowns per phase.

**43 compiled cloud tests passed**, including four maintained reader/integrity/layout regressions. 15,604 unrelated test cases were filtered out, not executed. Missing/corrupt pieces, expected root/size/final digest, partial/full final piece, one-piece and empty identity controls pass. Retained stream/client buffer counters stay capped. The stream holds one4MiBpiece; existing proof hashing uses additional bounded scratch and piece-tree metadata, so this is not a total-RSS bound.

## Executed identities and runs

- Baseline: clean `bd847e2b986722c1723b4cd60988d4f4908452d4`, helper `2e3ac26cca88103937a11c0c771e82b96e3f055b3fe4c45f09a504ed56c29ce9`; [before run](https://github.com/sunnyriverr/btx/actions/runs/44030880116), [native result](raw/baseline-result.json). This job later stopped compiling two path joins in the new tests; those were corrected before candidate qualification.
- Candidate: that base plus [tested.patch](tested.patch), [file hashes](tested-file-hashes.json), helper `ddbdfdfacbbf305f1a4e85f9e2ffbabefb79e43e3c260452162b6a4d525e85bf`, test_btx `cf6fb8962956b24f30489bca99752c61ced40f559af2045d15d54ef8311c97b0`. [Compile and suite run](https://github.com/sunnyriverr/btx/actions/runs/44033377358).
- The suite executable exited0with zero test errors. The collector then failed: Boost put an assertion containing `]]>` inside system-out CDATA, and filtered noncloud skips needed to be distinguished from selected-case skips. Raw XML was preserved. Offline correction plus six negative controls verified43executed cloud cases; **the suite was not rerun**. [Validation receipt](suite-validation.json), [console](raw/cloud-suite-console.log), [raw report, gzip text](raw/cloud-suite.xml.gz).
- [Final native-only run](https://github.com/sunnyriverr/btx/actions/runs/44035782075) restored the compiled candidate, checked all23,753checkpoint entries and six source hashes, and ran only the remaining helper cases—no rebuild or unit rerun. [Staging](raw/candidate-staging.json), [native result](raw/candidate-result.json), [artifact digest](native-artifact.json).

Linux x86_64; Ubuntu22.04container on hostedUbuntu24.04; GCC11.4; OpenSSL3.5.9. This is a normal compiled helper with controlled loopback HTTP, **not FakeS3/MinIO/AWS native integration**. The C++ cloud suite uses the repository's existing fixtures. The local HTTP origin observes signed requests but does not validate SigV4.

## Reading or reproducing the evidence

The code branch includes the maintained regressions in `modelnet_cloud_tests`. The actual hosted entry points and commands are in the linked run logs and immutable test commits: `5aca788e71a5dcfbe26d5284d2af311847e5b850` (before), `6475579deec4175a65b6824ce665db4ba48f3683` (compile/suite), `9a37c09f70dcffce4eb1cc6e0634a076df62074c` (native-only).

The byte-identical normal-helper fixture is in [recipe/native.py](recipe/native.py), with [origin](recipe/origin.py) and [helper lifecycle](recipe/fixture.py). Reconstruct it on Linux/POSIX with a reviewed btx-modeld binary and OpenSSL3.5.9 via `BTX_OPENSSL`:

```sh
python3 recipe/native.py --helper /path/to/btx-modeld --helper-sha256 SHA256 --expect baseline --out baseline-records
python3 recipe/native.py --helper /path/to/patched-btx-modeld --helper-sha256 SHA256 --expect candidate --out candidate-records
```

These relocated commands are reconstruction recipes; their packaged paths were not executed natively. Their exact script bytes were executed from `proposal/` in the runs above. Baseline exit2is expected only with the complete two-failure result; setup/timeout/missing-result is not a pass.

The saved-suite validator **was executed from this evidence package**, with six negative controls and no native rerun:

```sh
python3 recipe/check-saved-suite.py
```

[Manifest](manifest.json) records exact binary/patch/artifact identities. Raw before/after RPC responses are under `raw/baseline/` and `raw/candidate/`. Compressed XML preserves raw bytes (SHA-256 `6165f66539de3d86f96ece3cfc7d273f01a79217a1dc3fc51da43d5c48ba5aa9`); plain receipts and code are the primary review surface.

## Publication-time rebase and limits

The code commit is based on `release-0.34.17@0afc505f3e063ff8919366464881b81d9e037638`. Qualification ran on **bd847e2b plus the repair**, not the newer integrated binary. [Source-only rebase](source-rebase.json) preserves adopted #812 detach handling/test and the newer search/health/gossip work. The upload block and catalog/store/client code are unchanged in those intervening commits. No overlapping upload-identity fix was found at publication preflight.

No current-head rebuild, production S3/MinIO/WAN, full-node, restore/restart, Mac/Windows, total-RSS or concurrent active-removal qualification. Active-reference balancing is source-reviewed; the ordinary helper success check verifies no upload reference remains. PIECE_OBJECTS retains existing per-object partial-success semantics on a later failure; no all-file transaction is claimed. Older inconsistent cloud copies are not scanned or automatically repaired.

Preserves the existing ModelNet catalog/cloud implementation, tests and original attribution from repch1c, JPP and other contributors. The repair does not change monetary validation, budgets, credentials, identities or automatic spending.
