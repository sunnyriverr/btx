# ModelNet supported recovery through local CPU use

Scoped native Linux PASS. No product correction was needed in these cases.

## Decision supported

A complete retained model directory can be reimported into a fresh catalog and used locally after its original source path becomes unavailable. With catalog metadata retained, ordinary cloud recovery also restores a model usable by the local generation adapter. Both routes continue after a clean helper restart and checkout reconstruction without the original source paths or a live cloud origin.

This closes the selected functional recovery-to-use boundary. It does not establish cloud-only catalog reconstruction, distributed inference, model quality, release readiness or qualification of an exact current release package.

## Executed result

[Native run 43801439534](https://github.com/sunnyriverr/btx/actions/runs/43801439534), immutable harness `7254717e44e53767a21fe34a51b979fc9b9f5702`, Ubuntu 24.04 x86-64.

| Case | Observation |
| --- | --- |
| Healthy control | Tiny real SafeTensors GPT2 model, tokenizer/configuration and explicit `generatemodel`; transformers CPU returned `world world world world` |
| Catalog retained, local pieces absent | Source directory preserved under another name, old checkout removed, owned pieces deleted with catalog bytes unchanged; ordinary `getmodel` used real MinIO, reported `cloud_hydrated=true` and six origin GETs; exact files/identities and generation matched control |
| Cloud case after restart | MinIO container removed and endpoint independently checked unavailable; new helper process and deleted checkout; same reconstructed files and generated output |
| Independent complete copy, fresh catalog | Verified non-aliasing complete copy imported into a new helper model directory; old catalog/store preserved off path; backup source path then made unavailable; exact IDs/files and generation matched control |
| Independent-copy case after restart | New helper process, checkout deleted and reconstructed; same files/IDs/output; original and backup copies verified before normal disposable framework cleanup |

The helper forks/execs a fresh local adapter for each call. The adapter uses `local_files_only=True`, `trust_remote_code=False`, offline Hub settings and CPU execution. No wallet or paid operation is part of this test; the observed cloud recovery returned `automatic_spend_atoms=0` and `paid_atoms=0`.

Both framework and wrapper exited zero. The native log records nodes stopped and disposable directory removed. The CPU environment occupied 1,014,138,267 bytes; pinned principal packages were torch 2.7.1+cpu, transformers 4.53.3 and safetensors 0.5.3. Full package versions are retained. No native test was rerun merely to prepare this handoff.

## Source and binary scope

Reviewed source anchor: `release-0.34.17` at `1e2f8b5f12295002334d3390c12cac0bb4ae2aff`.

Execution reuses retained helper `04b068ab4aebd2be1893268d384fe6561cfc06ee72c84f8701ee5e3dc5fe9458`, whose helper.cpp/catalog.cpp/s3_store.cpp were established identical to that source in the prior [rehosting baseline run](https://github.com/sunnyriverr/btx/actions/runs/43788621019). The retained helper producer was `61f13b8870ed98c7b10db2e32c04fb647023f4ef`; the node/CLI proxy is older and separately hash-pinned. This is relevant-path source-compatible execution, not an entire freshly built 1e2 release or installed package. The exact binary SHA-256 values and verified archive digests are in [expected-binaries](preparation/expected-binaries.sha256) and [staging](attempt2/staging.json).

No dependency on unadopted #756, #754 or #747 was introduced, and no compilation occurred.

## Reused campaign evidence

- [Independent-copy/import receipts](https://github.com/sunnyriverr/btx/blob/9cc59e0da2d2823f895352c97b9d02c4188e6ffc/doc/review-evidence/modelnet-independent-restore/README.md): #716 provides the independent-retention/import recovery instructions; Numair recorded their incorporation into #714 on [#613](https://github.com/btxchain/btx/issues/613#issuecomment-6892020751).
- [SOURCE_FILES B1/B2 receipts](https://github.com/sunnyriverr/btx/blob/200a1b503a94bb7e3f220802944ceeb67462813f/doc/review-evidence/source-files-recovery/README.md): #723 supplies the supported SOURCE_FILES recovery contract. Earlier recovery tests cover partial reads, corrected corrupt origins and budget/restart behavior; this run does not repeat those matrices.
- [Run 43499330842](https://github.com/sunnyriverr/btx/actions/runs/43499330842) already covers peer acquisition followed by CPU generation and offline restart. The new cases cover cloud and independent-copy recovery as the preceding operation.
- #756 is a separately delivered source-reference repair. Rehosting/republication is not required by the two passing cases here and is not claimed adopted.

## Setup failure and result handling

First attempt [43801127266](https://github.com/sunnyriverr/btx/actions/runs/43801127266) verified retained binary hashes but failed during Python framework import because the subclass did not explicitly redeclare `set_test_params`. Neither recovery case ran. The corrected harness adds that declaration; the principal dependency versions, binaries and workflow remain unchanged.

The final offline validator accepted one complete specimen and rejected twelve failure/missing-condition variants. The runtime harness itself requires actual origin operations, matching recovery identities, matching manifest hashes, identical CPU output and real cloud unavailability. No skipped test or missing response is treated as a pass. Setup and final receipts are retained separately.

## Evidence retention

Final artifact [14196329211](https://github.com/sunnyriverr/btx/actions/runs/43801439534/artifacts/14196329211), 5,717-byte ZIP, SHA-256:

`1adcda4af64244338bdafdd52d6f60d6833b3a3f942a2bc6ed38f9ee863296a6`

Its digest was verified against GitHub metadata before extraction. Hosted expiry: 30 November 2026, 04:02:23 UTC. The selected raw records and exact harness are retained in this evidence branch beyond the hosted artifact expiry.

## Limits

One synthetic tiny, real executable model and deterministic prompt; functional wiring only. Linux CPU, retained helper plus older node/CLI, clean restarts and disposable loopback MinIO. No native Mac/Windows/GPU run, useful-model quality/performance claim, WAN/R2/AWS/TLS qualification, large-model capacity run, physical disk-loss/power-loss simulation, full test suite, installer or exact-release package qualification. No cloud-only catalog restoration. `loadmodel`/resident GPU loading was not exercised; generation loads the restored files through the local CPU adapter.

Credit: Numair for the supported recovery contract and integration; JPP and repch1c for the existing native model/MinIO fixtures and related fixes reused by this qualification. This result adds no product code and makes no merge or release request.
