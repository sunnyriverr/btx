# Bounded known-length cloud upload — Linux qualification

**Fail before / pass after: code `109a4e6bcfad72ac1fd04d91415bfd1787c9ac09`, based on release-0.34.17 `1e2f8b5f12295002334d3390c12cac0bb4ae2aff`.**

The original live uploader used 8 MiB parts for every file. An individual file above 78.125 GiB exhausted the 10,000-part ceiling only after transferring the first 78.125 GiB. The proposed upload-only selector keeps 8 MiB for currently fitting files and grows to 16/32/64 MiB only when needed. It refuses above 625 GiB before stream reads or multipart initiation and reuses one bounded upload buffer. The 64 MiB ceiling is a payload-buffer bound, not total process RSS. Unknown-length streams, FakeS3 selection, shared read thresholds, cloud layout/keys and model identity remain unchanged.

This extends the existing R2 storage finding and regression by repch1c. The original copyright notices and unrelated accounting tripwires are preserved.

## Executed evidence

[CI run 43779884495](https://github.com/sunnyriverr/btx/actions/runs/43779884495), tested harness commit `6994227bb7d505c6141dfe9ac378fdb1d07181c3`. The exact candidate patch is [candidate.patch](candidate.patch); its digest and source identities are in [verified-result.json](results/verified-result.json). The proposed product commit contains identical bytes; tests were not repeated for commit packaging.

| Check | Before | After |
| --- | --- | --- |
| Known 78.125 GiB + 1 byte | Aborts after 10,000 parts | Completes 5,001 parts, 16 MiB buffer, exact one-byte final part |
| Known 400 GiB | Same late ceiling failure | Completes 6,400 parts with 64 MiB buffer |
| 625 GiB + 1 byte and UINT64_MAX | Late part-limit failure | Zero bytes read, zero multipart starts/parts |
| Original exact limit, small multipart/direct PUT, short read, backend failure, unknown-length controls | Existing behavior | Preserved |
| Linked actual client: oversize requests against owned loopback listener | Not claimed | No stream calls, no payload allocation or connection |
| Actual FakeS3 normal 16 MiB | Existing coverage retained | Exact bytes and 8 MiB buffer preserved |
| Rebuilt helper → real MinIO, valid 16 MiB model | Prior baseline receipt retained | Two actual 8 MiB parts; exact bytes/config/model identity after helper restart |

The large streams are **virtual, not giant network uploads**. Their buffers are filled/read through complete, unchanged/exactly patched production method definitions, using actual 10,000-part constants. HTTP/signing/response adapters record operations; this is a component control-flow result. The separate MinIO check supplies real small-transfer/signing/restart evidence, not proof of a real 400 GiB upload.

Raw [before](results/baseline-observations.jsonl), [after](results/candidate-observations.jsonl), [component receipt](results/component-result.json), [native MinIO receipt](results/bounded-upload.json) and [native log](results/native.log) are retained. Final framework and wrapper exits are both zero; the strict saved-result validator was rerun after downloading the SHA-256-verified evidence archive.

## Build and maintained test scope

A verified retained cache was overlaid with exact current tracked source, removing earlier unrelated qualification changes. Ubuntu 22.04 x86-64, GCC 11.4, OpenSSL 3.5.9; a 34-action incremental plan was inspected before the helper and focused executable built in 280.94 seconds. [Build receipt](results/build-result.json), [dry run](results/candidate-dry.log), [build log](results/candidate-build.log).

The linked executable executes the new maintained boundary-case assertion body against actual production policy symbols. It additionally checks real-client zero-work refusal and FakeS3 bytes. [Source](recipe/policy_test.cpp), [maintained assertions](recipe/maintained-boundaries.inc), [execution log](results/candidate-production-policy.log).

The full Boost fixture/test_btx was **not** executed. The product patch adds/updates the maintained `modelnet_r2_storage_tests/r2s_02_*` cases for normal repository unit runs; do not equate the focused executable with the full suite. Physical-layout estimates remain informational outside the checked 400 GiB example.

The MinIO integration ran on Ubuntu 24.04 x86-64 using the newly built helper and the earlier verified disposable node/CLI fixture. It used the same MinIO RELEASE.2025-04-22T22-12-26Z executable/hash as the preceding qualification, not FakeS3. It verifies existing-object readback after helper restart, not a fresh upload after restart or missing-piece hydration.

## Reviewer entry points

- Maintained unit cases: apply the product commit in a normal BTX build and select `modelnet_r2_storage_tests/r2s_02_*`. This is the intended maintained regression, not an execution claim for that full target here.
- Exact executed component entry point: `python3 component.py` from the CI root, with the files now under [component/](component/). The baseline-reuse gate is pinned to the saved binary/method hashes and Ubuntu 24.04 GCC 13.3.0; a different compiler must not silently accept that binary identity. The candidate method and real part limit are never replaced by miniature constants.
- Exact executed native/build entry point: the [saved workflow](recipe/workflow.yml) on harness commit above. The [build script](recipe/build.py), [cache verifier](recipe/checkpoint.py), [native wrapper](recipe/native.sh) and MinIO fixtures are included. The cache recipe requires its pinned absolute runner workspace/toolchain and retained artifacts; it is not advertised as a portable one-command clean build. Use a normal source build when that cache is unavailable.

The successful component reused the baseline from [run 43779345103](https://github.com/sunnyriverr/btx/actions/runs/43779345103) only after recompilation proved identical binary/method hashes. That earlier run is overall failed: its original candidate reached the resource bound in the 400 GiB case with repeated 64 MiB allocation/free. Buffer reuse resolved the resource-bound case without loosening the limits. The passing baseline was not rerun. Candidate component elapsed 21.604 seconds under a 120-second wall/110-second CPU/256 MiB address-space bound. Peak RSS was not measured; timings are not a throughput comparison.

## Retained binaries and limitations

[Final CI artifacts](https://github.com/sunnyriverr/btx/actions/runs/43779884495): records 14188566007, binaries 14188570970, checkpoint 14188536130, retained until 30 November 2026. Binary ZIP and both members were actually downloaded and hash-verified; new checkpoint availability/digest were checked without redundantly downloading/restoring it locally. [Artifact verification](results/final-verification.json).

Helper SHA-256: `012e0e9386e842c9a80ecc44bf734e83cc99a022d3bc43382169acafbbdf2a74`.

Not qualified: giant real-provider transfer, full test_btx, native Windows/macOS, external R2/AWS/TLS, mainnet, release acceptance, 5 TiB client support or a process-wide 64 MiB memory cap. No cloud layout/default migration, budget relaxation, consensus or monetary-policy change is part of this patch.
