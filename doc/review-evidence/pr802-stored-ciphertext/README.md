# PR802 stored-ciphertext test evidence

**Scoped Tested ACK895388354cd8b07a947ee245dc555eb02f0e96f6.** Additional Linux byte-binding evidence for repch1c's fix. Numair subsequently reported incorporation at9161a3da; that commit was not executed in this run.

## Observed result

Same production-linked standalone component, two synthetic single-file models with distinct32-byte secrets:

| Control | Result |
| --- | --- |
| Without802's production change | FAIL at ciphertext artifact differing from plaintext artifact |
| With802 | PASS: verified stored pieces decrypt with their own secret to exact original bytes |
| Other model's secret | Refused, no plaintext |
| Distinct IDs/canonical ciphertext filename; first artifact rechecked after second creation | PASS |
| Fresh ModelCatalog + campaigns.json reload | PASS |

Actual executed commands were `built/candidate/review802` (exit0) and `built/baseline/review802` (exit1). See component logs and result.json for exact absolute commands. Controller SHA2566a9caa43e38da4fb445502ca1a706c6b6ab37e11cde85a15fed20897c6205f1f; maintained case body SHA256e0c43cfa066aeeba41f383dc246d64c71ca29cba1daf9cd5e398233a83102b84. The maintained test.patch is provided for review/adoption; it was not executed through the normal Boost runner.

## Platform and provenance

[Run44002524681](https://github.com/sunnyriverr/btx/actions/runs/44002524681), CI8561e0ee1ff994830d4bf8292d896b756ad60c9f. Ubuntu22.04 pinned container on Ubuntu24.04 hosted runner; GCC11.4. Real production helper/catalog/crypto, authenticated catalog pieces and actualBasicTestingSetup. Fresh3321-action build1477.988s; baseline10planned/6executed actions369.662s. Old native objects were invalidated because their external-input identities were incomplete. All owned process groups exited.

The baseline swaps exactly helper.cpp/catalog.cpp back to371013d61dc124a363521df5b94e97f64d2464f2 inside the candidate qualification tree. It is a controlled production-code comparison; Git/build-info remains candidate+dirty, not a clean baseline release binary. Exact input hashes are in inputs.json. Fix and original supporting test helpers are repch1c's; this additional case/controller is Sunny River's review evidence.

Records artifact14294846962 and binaries14295075686: ZIP digests, retained record entries and allfourELF hashes verified. Verification receipts are included; no compiled binaries are committed here. Candidate checkpoint is phasecandidate; final checkpoint is phasebaseline—do not interchange them. Build/checkpoint/workflow recipes are the executed harness; this evidence-directory layout is not a separately executed reconstruction.

## Limits

No actual helper process restart, concurrent RPC/race, full claim/unlock/funding, real wallet, GPU/mainnet, Mac/Windows, full suite or release qualification. Catalog/file reload is not process recovery. btx-modeld was built and hash-verified but not run in this check.

One earlier pilot44001918366 failed before compilation on root-container checkout ownership. The final recipe corrected that and test-entrypoint/CMake wiring; the maintained test body stayed unchanged. No product defect is inferred from those setup corrections. Qualification.json, raw logs and manifest.json preserve scope and hashes; path redactions/compression are recorded.
