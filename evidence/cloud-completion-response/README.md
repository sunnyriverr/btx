# Reject false S3 multipart completion success — Linux qualification

Bug: S3 CompleteMultipartUpload can return HTTP200 with an Error body. BTX accepted status alone, returned upload success and set health.write although real HEAD/GET showed no object. The fix recognizes the first success envelope and otherwise uses the existing error/abort path. No part-sizing, ordinary PUT, endpoint, signing or retry policy changes.

Target: release-0.34.17 `371013d61dc124a363521df5b94e97f64d2464f2`. Exact product-file hashes and patch are in qualification-receipt.json/candidate.patch. The current release's S3client/header/supervisor blobs are identical to retained1e2; patch also composes textually with #754's part-size change. No combined #754 runtime qualification is claimed.

## Verdict

Same six transport cases, same client/origin/validator bodies on both versions:

| Case | Before | After |
| --- | --- | --- |
| Known-length200/Error, then sameclient/key retry | FAIL:false success | PASS:reject+abort+exactretry |
| Streaming200/Error, then sameclient/key retry | FAIL:false success | PASS:reject+abort+exactretry |
|500/Error, then retry | PASS:reject+abort+exactretry | PASS |
| Clean known-length multipart | PASS:exactbytes | PASS |
| Clean streaming multipart | PASS:exactbytes | PASS |
| Ordinary4KiB PUT | PASS:exactbytes | PASS |

Both patched200/Error paths report the fixed error, leave health.write false, send one abort, leave zero pending uploads in the fixture and subsequently upload the exact8MiB+4KiB payload with the same client and key. This is real production S3client/HTTP/signing/response/readback code with use_fake=false, against a **controlled local response origin**. It is not AWS, MinIO or FakeS3. The server observes signed headers; it does not authenticate SigV4.

Maintained test:18table-driven envelope checks added to existing modelnet_cloud_tests.cpp. The exact maintained case body ran in a standalone Boostcomponentharness:18/18PASS. Complete modified maintainedsource passed syntax checking with its actual normal compiler flags. This does not claim integrated/full test_btx execution. The new predicateAPI does not exist before the patch; fail-before/pass-after proof comes from the unchanged six transport cases, not baseline execution of those18newunitvectors.

The predicate preserves normal/defaultnamespace/prefixednamespace and declaration/whitespace/BOM/comment envelopes. It rejects ordinary/prefixedError, misleading success text insideError, empty/truncated/unknown/incorrect-closing responses. This is **success-envelope recognition, not a full XML validator**; arbitrary malformed interior content/attributes are outside its guarantee. The error is constant and does not echo provider XML.

## Executed entry point and exact identities

[Paired CI run43962846451](https://github.com/sunnyriverr/btx/actions/runs/43962846451), executed source commit `b9f816d0209ce836e678fd8a58e2d0c222bdefca`: [workflow](https://github.com/sunnyriverr/btx/blob/b9f816d0209ce836e678fd8a58e2d0c222bdefca/.github/workflows/cloud-completion-repair.yml), [build.py](https://github.com/sunnyriverr/btx/blob/b9f816d0209ce836e678fd8a58e2d0c222bdefca/build.py). The recipe files here are byte copies; refer to the immutable executed CI tree for source snapshots. The workflow was executed, not merely proposed.

Ubuntu22.04x86_64 pinned container, GCC11.4.0/CMake3.31.6/Python3.12.16/staticOpenSSL3.5.9. Restored checkpoint hashes/types/links/timestamps were verified before use. The baseline links retained normal1e2+778/779/780libraries. The entire candidate productionS3client TU is compiled with its real targetflags and explicitly linked in place of the archive implementation. Thus this is current-source-applicable **component qualification**, not a rebuilt371daemon.

Baseline executable SHA256 `43910d6681bdcac710387b5b3ed0d0e1e395daad7d2ca62ae7ba8e07a42388d9` matches the original reproduction. Candidate `59b951c5d1314cd96347f1f21efd70b1d8b92939361eaa0bdef6a885a7431557`. Source/patch/binary/artifact identities are in qualification-receipt.json. Binary artifact14275167819 and result14275137843 expire30Nov2026; source/fixture/receipts/logs remain in this branch.

Transport command (executed by build.py on each version): `python3 qualify.py --client EXACT_BINARY --probe-dir probe --out RESULTS`. The same correctness wrapper exits1 on the two baseline false-success cases and0 after all six pass. The server closes after each bounded scenario; request body<20MiB, fixture-retained data<=64MiB,120s total test bound and256MiB sum-of-observed-peak-RSS gate. Payload is8MiB+4KiB except the4KiB PUT. The unit driver compiles the exact maintained case body; no in-tree test or public API is replaced with a stub.

**Scope-label erratum:** unchanged raw observer result.scope says “unmodified real S3client” in both phases. That legacy label applies only to baseline. The after phase uses the patched full productionS3TU, identified above and in the manifest. Raw evidence is preserved; this phase-specific statement supersedes that wording. No test was repeated to fix a label.

## Supported API and limits

[AWS CompleteMultipartUpload contract](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html) permits completion errors inside HTTP200 and requires direct callers to inspect the body. This test models that documented response, not malformed network traffic.

Not tested: AWS/MinIO deployment, TLS, helper seeding/catalog-state effects, current full daemon, normal full test_btx/project suites, Mac/Windows, concurrency, release qualification or arbitrary XML well-formedness. Fixture abort/pending-state observations do not measure provider billing or orphan lifetime. Existing #754 part-capacity evidence is not repeated or claimed as a dependency.

Preserves existing BTX S3transport/cloud fixtures and their original authorship. Builds on prior storage/upload test work by repch1c, JPP and contributors; original product history remains intact. Product and evidence commits are separate.
