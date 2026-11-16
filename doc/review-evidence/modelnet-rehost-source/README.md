# Verified source-path refresh for ordinary model rehosting

**Scoped PASS:** the same maintained cases report156 assertions/8 failures on release1e2f8b5f and156 / 0 with the two-file patch. Real Linux/MinIO rehosting changes from three relocation failures to five exact-byte successes. [Manifest](manifest.json), [patch](candidate.patch).

Tested source: [87ff65f46c72](https://github.com/sunnyriverr/btx/commit/87ff65f46c72f2966838162c5994a8e9a95354e7), identical to the qualified two-file patch on `1e2f8b5f12295002334d3390c12cac0bb4ae2aff`.

## Supported defect and repair

An operator imports a model, moves its source files, then calls hostmodel on a verified byte-identical copy (or exportmodelpath checkout). ImportPath recognizes the existing artifact but returns the stale catalog source_path. Cloud publication tries the missing old source and reports source file size unavailable. Local pieces and IDs remain intact; restoring the old pathname is a demonstrated workaround. This is failed cloud replenishment, not demonstrated data loss.

After normal qualification derives the same artifact, refresh its durable source_path and optional pin promotion in one catalog save. Failed persistence restores source_path, pin, admission and byte-verification state. Same-path/no-change imports do not save; pin=false never demotes an existing pin. No identity, cloud-layout, budget or monetary rule changes. Existing BTX author notices and fixture provenance are preserved.

## Evidence

- [Compiled maintained baseline](maintained-baseline.log) / [candidate](maintained-candidate.log): four initial/requested pin combinations, catalog reopen, forced actual atomic-save failure, immediate rollback, unchanged disk bytes, unrelated later save+restart, successful retry, same-path import with saving unavailable, distinct valid content, invalid input, exact materialized bytes. These are the exact maintained case bodies linked to production archives through a qualification-only consumer; **not the full Boost test_btx suite**.
- [Native baseline](native-baseline.json) / [candidate](native-candidate.json): same 16 MiB safetensors file, same IDs andSHA-384, same five-case driver. Same-path/restored-original controls pass both; relocated copy, helper restart and exported-checkout rehost fail baseline and pass candidate. Each attempt deletes only its disposable cloud object and proves 404 before upload; successful GET 200 bytes match exactly. Originals retained and restored; no catalog-flag edits.
- Paired compiled run: https://github.com/sunnyriverr/btx/actions/runs/43792637242 at a4ef63c09e4490e2b37fab0957ab5f71bd341bfb. [Build result](build-result.json).
- Native candidate: https://github.com/sunnyriverr/btx/actions/runs/43793130265 at f1338cc46376b20395ffe438ad8b1d57d4ec423f. [Staging/binary verification](native-staging.json), [runtime/cleanup log](native-candidate.log). Native baseline: https://github.com/sunnyriverr/btx/actions/runs/43788621019 at57ff1464f86b614b434a9de74c60490e2c83a14b.
- HelperSHA2566604f19ae06401b6714920e6e490adab9f539d1fcb6b8613fc58f40048965d43 was rebuilt from accepted1e2 plus this patch and rehashed before integration. Saved cache's previous754 changes were reset to accepted source first. Retained node/CLI reused unchanged; relevant baseline helper files were source-equivalent to1e2. No754 dependency.
- [Internal source/evidence review](internal-review.md); this is not a second platform replication. [Offline result controls](offline-validator.json) reject failed upload, missing/incomplete cases and wrong bytes.

The CI harness commits contain the executed build and runtime recipes. For a normal in-tree build, the two added cases are in modelnet_hosting_tests.cpp; running them through full test_btx is a reconstruction route, not an execution claimed here.

## Limits and setup corrections

Linux x86-64 only; one synthetic16 MiB model and real local MinIO. No native Windows/macOS, external R2/AWS/TLS, giant transfer, whole-release rebuild or release qualification.

Initial compile pilot stopped at a test dirname's implicit conversion, corrected to BTX's explicit fs::PathFromString. A later staging step could not write into container-owned source. The passed compiled results and helper were retained; integration alone used a runner-owned exact framework checkout. Neither setup failure was called a product failure or pass, and no passed test was rerun for that staging correction. The earlier baseline observation's directory-hashing correction is documented in its retained run.

Next decision: review/adopt the focused catalog repair with maintained regressions. No release sign-off requested.
