# Missing-piece cloud recovery

Product 81afbe56647f72c2fcf5dac3ebf808370cf76511 on `swapnet-v2` 70de5a454b4263c929b0162af6615c9dd756becd. This follows the upstream MinIO fixture and #613 reports from repch1c; original fixture attribution is preserved. This is a focused repair within a broader recovery campaign.

## Native verdict

| Boundary | Actual observation |
|---|---|
| Before, run43588655872 | Healthy upload/read succeeded; after deleting source/pieces and restarting, getmodel falsely said local/seeded. No restored bytes; export IO:missingpiece. |
| After, run43590785003 | Identical direct fixture: bytes restored by one cloud GET, exact materialization, local usability retained after another helper restart. |
| Maintained test, run43592347962 | Real MinIO AUTO/SOURCE_FILES/PIECE_OBJECTS matrix passed using the strengthened in-tree fixture, without manual catalog flag edits. |
| Corrupt origin | file SHA-384 mismatch; no live pieces, export INCOMPLETE. |
| Zero GET budget | cloud origin budget exhausted; no live pieces, export INCOMPLETE. |
| Unaffected model | Existing healthy model stayed local and materialized matching bytes under both refusal conditions. |

Both refusal tests completed; the candidate did not accept corrupt/unbudgeted bytes. Direct, maintained and refusal logs plus JSON are adjacent. No FakeS3 fallback or model execution. Small synthetic safetensors files (the maintained restore was8,259bytes).

## Exact executable boundaries

Native runtime: Ubuntu24.04 x86-64, disposable regtest, real MinIO RELEASE.2025-04-22T22-12-26Z in loopback Docker; executable checksum verified before use. The before control used retained8d6d8b1a node/helper binaries. Relevant catalog, hydration, getmodel and export sections matched d7b9594b (source comparison retained). Candidate helper came from d7b9594b plus the tested production patch, source8033fe4e20c887287b2e4c11db12ef3b10bf52a5, compiled with the restored Ubuntu22/GCC11/OpenSSL checkpoint. Its libraries were built with the candidate; its unchanged RPC proxy remained the older retained node. This is not a same-toolchain whole-daemon pair or a full release rebuild.

Helper SHA-256: `7436885f08cade46ccd84d3891d06ca35f252c950a983458a4a30135548b5c60`.
Candidate artifact14112398679 ZIP SHA-256: `d601dfa7a162cdce03c524d703cd7b160ccfc218ddcaf259463f09eaa1adf138`.
The identical direct Python fixture hash is `60dbaf974670f72b01ef96bb3b6db9e1fb431d7a87bc4f2a8f1fe949fdca0671`.

Executed workflow entry points:
- https://github.com/sunnyriverr/btx/actions/runs/43588655872 (baseline)
- https://github.com/sunnyriverr/btx/actions/runs/43590785003 (helper build/direct test, exact workflow394878526ac011bdfc6dcb34d662516fc36707b2)
- https://github.com/sunnyriverr/btx/actions/runs/43592347962 (maintained/refusal controls, exact workflow75e689894f7f95faf78afb4f00b1cc0f201f7146)

The workflow source contains the dependency/configuration, binary verification, real MinIO setup and bounded commands actually executed. `direct-recovery.py` and `refusal-controls.py` were copied beside the unchanged test framework; the maintained test uses this PR's modified feature_modelnet_minio.py. Placeholder paths in sanitized receipts/logs are not a fresh portable build recipe. Published and original hashes are distinguished in manifest.json.

## Limits and remaining campaign

No Windows/Mac native run, full unit/functional suite, multi-file/large-model throughput, WAN/R2, model runtime execution or power-loss qualification. Normal getmodel now probes expected piece paths; completion hashes files while holding the catalog mutex. Large-model latency is not measured.

The repair needs retained catalog metadata. A separately measured removemodel→getmodel path discarded that metadata and did not recover from PIECE_OBJECTS despite remote bytes remaining intact. Recovering missing metadata, origin-outage retry/interrupt boundaries and wider platform/scale acceptance remain broader campaign questions; this PR does not close them or introduce a remote manifest protocol.

Current 70de5a454b4263c929b0162af6615c9dd756becd affected source originals remain byte-identical to the tested d7b9594b base. Publication preserves the exact tested product and maintained-test bytes. No release acceptance is requested.
