# Local handoff — real-signature component checks

Following [JPP’s signed-checksum/fingerprint request and fork-rehearsal offer](https://github.com/btxchain/btx/pull/432#issuecomment-6881907467), this adds offline helper-level evidence alongside the existing mocked tests. It does not complete the offered fork-publication rehearsal.

Unchanged BTX helpers at `074dac167c26c1e091198f691ed5727817dba88a`, macOS arm64, isolated GnuPG 2.4.5/libgcrypt 1.11.1/libgpg-error 1.55, and disposable RSA2048 keys: **six behaviour checks plus setup passed** using a tiny inert bundle:

- Signing-subkey signature accepted with the expected primary fingerprint.
- Changed signed checksums rejected by GPG.
- Changed asset retained a valid checksum signature but failed bundle hash validation.
- Valid alternative signer accepted with its own pin, rejected with the other pin; failed signing restored unsigned manifest/checksum bytes and removed the signature.
- Missing public key rejected without automatic retrieval.
- The same rolled-back fixture signed and verified successfully on retry.

Earlier setup attempts failed before the matrix: extraction/dependency issues, key-generation faults with libgcrypt 1.10.3 (RSA and exploratory Ed25519), agent/path/import configuration, and an intermediate cleanup error. These are retained separately; they establish no BTX defect or Ed25519 pass. The final RSA run completed with verified cleanup; disposable private homes and owned agents were removed. No product patch resulted.

**Not tested:** official keys or releases, full publisher/upload flow, installer policy, producer provenance/reproducibility, native BTX or seed work, optional missing/truncated signatures, or new interruption/crash/restart cases. Earlier injected interruption results remain simulated evidence.

Evidence: [execution report](EXECUTION.md), [results](matrix-results.json), [raw subprocess log](matrix-raw.json), [source/tool receipt](verified-results.json), [driver](run_matrix.py). Local draft only; no new tests or posting during handoff review.
