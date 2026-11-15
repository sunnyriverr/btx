# Signature handoff — local evidence review

Verdict: ready as a bounded local component-result handoff. JPP is credited with the original request and offered fork rehearsal. This is source/document/evidence review, not independent execution or a test rerun.

Checked the final driver against retained outcomes: real signing CLI and verification helpers, primary/subkey handling, changed-message rejection, separate content validation, valid alternative-signer control, expected-pin rejection with byte-exact rollback, empty verifier, and retry on the same rolled-back fixture. G0 is setup, so the draft reports six behaviour checks plus setup rather than seven independent cryptographic tests.

All eight retained product/test source hashes still match the execution receipt. The raw log records four signing CLI exits 0/0/1/0; helper-return observations/errors are in matrix-results.json rather than separate raw subprocess entries. The complete raw log therefore is not a transcript of every verification subprocess. Final cleanup records and the prior independent absence recheck are retained; no fresh process/runtime validation was performed here.

Earlier extraction/dependency, old-library RSA/Ed25519 key-generation, agent/import and cleanup setup failures are explicitly disclosed. The passing profile is RSA2048/GnuPG 2.4.5/libgcrypt 1.11.1, not an Ed25519 or old-library result. No product defect or patch is inferred from setup faults.

The draft excludes official release authentication, producer reproducibility/provenance, full publisher/upload, installer policy, native BTX, seeds, optional malformed/missing-signature rows, and new interruption/restart testing. Prior injected controls remain simulated. Checked local evidence links and pinned evidence hashes. No GPG, tests, downloads, peer messages or publication occurred in this review. Current upstream freshness is not asserted; check it only if publication is authorized.

Next useful trigger: explicit publication authorization after reviewing this draft, or substantive feedback/source change. No repeated passing test or further generic review is indicated.
