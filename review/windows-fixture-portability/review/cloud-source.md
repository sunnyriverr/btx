# Draft adjacent cloud fixture review

5 November 2026. Bounded source/evidence review of the current uncommitted draft in `source/`. Only this reserved report was written. No source edit, Git/network operation, compiler/build/test/CI invocation, ledger mutation or delegation. The parent will pin the final source hashes and native qualification identity. This is source-review approval, not a candidate compile/link/runtime result.

## Verdict

**PASS for the reviewed draft; no blocking issue found.** Both Windows macro guards address now-observed compiler failures while preserving the real class interface. The selected R2 case's Windows credential adaptation reuses the same supported setup contract as the already-qualified cloud10 case; no material source difference invalidates that reuse. A separate setup-only failing native run is not needed to justify drafting this adaptation. The final candidate still needs actual generated-object compilation, linking against the canonical library and execution of its maintained dispatch/byte oracles.

The prior `CLOUD-DESIGN.md` statements that these two compiler failures were not yet observed were accurate at that earlier review. The retained grouped run now resolves that uncertainty. Its actual `diagnostic/run-41994623193/candidate-unit-build.log` reports store2's invalid override and allocation of an abstract `FakeCloudObjectStore`, with canonical `CloudObjectStore::GetObject` unimplemented. The R2 error explicitly reports missing `S3PieceStore::GetObjectW`, identifies the original direct call and shows `wingdi.h:5196` expanding `GetObject`. Both object commands fail. This report read those existing records and initiated no execution.

## Macro scope and interface preservation

Each cpp has exactly one `_WIN32` push/undef block after every include, before its suite, and one matching pop after `BOOST_AUTO_TEST_SUITE_END()`. There are no includes inside either scope. R2's new environment-helper include is also above the scope. The guard saves the incoming post-include macro state, undefines it while parsing all fixture declarations and calls, then restores that state. It also preserves an initially undefined macro. POSIX skips these blocks.

Store2 retains the actual `FakeCloudObjectStore::GetObject(... ) override`, all other overrides and every fake method body. It does not remove override enforcement, make the base concrete, change virtual ordering or rename the API. Its four maintained operation/assertion bodies remain as reviewed previously. The real `TieredPieceStore` cloud read therefore still has to dispatch through the production base interface into the fake and return the asserted bytes. Cases02/03 retain both legitimate cloud-fill and corrupt-cloud rejection oracles.

R2 retains its direct canonical `store.GetObject(key, 0, 0, part, err)` calls. Its complete operation body after initialization is unchanged: source-file put/read, four piece-object put/read operations, full payload and reassembled-byte equality, SHA-384 equality, measured one-versus-four backend operation counts, key-family checks and piece-planning checks. No API shortcut, replacement client call, expected-success stub or suppressed operation was introduced. Public headers and production implementations are outside this draft correction.

## Credential reuse comparison

The reviewed R2 case still creates its fixture file and starts from the existing PATH configuration. On `WIN32` it constructs a separate `file_store`, asserts initialization refusal and the exact existing `credential file must be mode 0600` error, then changes only the successful test store's credential reference to ENV. The error is cleared before that successful store's Init. The checks use `BOOST_CHECK`, so an unexpectedly accepted file or a different failure remains a recorded test failure even if the byte body subsequently executes. The test cannot silently reinterpret file-credential success as the expected refusal.

The relevant cloud10 and R2 setup properties match:

- Both file writers close the file before requesting owner-read/owner-write permissions with `fs::perm_options::replace`; R2's fixed request equals cloud10's `mode0600=true` request. Both write the same named access/secret fields and newline-separated body format.
- Both configurations use the same endpoint, bucket, `v1` prefix, `auto` region, FakeS3 backend and AUTO provider/layout defaults. Both use the unchanged production `S3PieceStore`/`S3Client` initialization and `LoadS3Secrets` PATH permission guard.
- Both ENV bodies contain the same fixture keys they would have read from their own files. R2 retains its own existing synthetic identifiers rather than importing cloud10's identifiers. `ParseCredBody` accepts these named fields and requires nonempty values; it does not impose the cloud10 identifier's exact spelling or length. FakeS3 receives the parsed credentials as its signing context, as before.
- `BTX_R2_STORAGE_TEST_CREDS` is a valid identifier under `EnvNameOk`, and it contains none of the disallowed wallet/RPC-secret name patterns in `EnvLooksLikeWalletSecret`. It differs from cloud10's environment variable, so the two cases do not intentionally share a mutable credential slot.

The different file basename, environment-variable name, synthetic key strings and smaller payload do not change the relevant permission/parser/setup contract. Using prior native evidence to avoid a predictably identical setup-only failure is justified. This is evidence reuse for selecting the fixture setup; it does not substitute for executing R2's different full byte/hash/request-count oracle on the candidate.

`test::ScopedEnvVar` snapshots any prior value, validates mutation success, and restores the value or prior absence in its destructor while checking restoration success. The guard object is declared before the successful store and lives through the entire case, so it remains available through all operations and is restored after normal exit or an assertion exception unwinds the case. No direct persistent environment mutation was added. The variable remains process-global under the helper's existing contract; the selected runner must not run cases concurrently in the same process with a competing writer to this exact variable.

On POSIX, the Windows adaptation is absent and the same PATH configuration reaches the same store initialization. The extra local `cfg` variable and helper include do not alter the POSIX credential choice or operation/assertion bodies. This is source-semantic preservation, not an executed POSIX preprocessing/build claim. The production mode0600 guard remains unchanged on every platform. The other R2 cases retain their original PATH setup; this selected-case correction does not qualify the complete R2 suite.

## Acceptance boundary

Parent should pin the reviewed final hashes and unchanged canonical library identity, compile both maintained units with their real generated commands, and execute store2's cloud-fill/corruption cases plus R2's selected identity case through the normal linked interface. A successful R2 result must include both Windows file-refusal assertions and all original successful ENV-backed byte/hash/count assertions. Preserve any unexpected compile, link, setup or operation failure as its actual category. No repeated baseline compiler failure is needed; run41994623193 supplies it.

No live cloud service, Windows11 acceptance, full R2/full-unit acceptance or publication is qualified by this review. Resource state: no execution resources used and no other output written.
