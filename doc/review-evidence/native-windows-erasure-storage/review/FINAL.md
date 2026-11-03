# Independent final source and harness review

**PASS for the bounded code/test design; native result qualification remains pending artifact review.** This is a source/provenance review, not an independent native platform execution.

Reviewed local `erasure_store.cpp`, `storage_test.cpp`, `runner_template.py` and `closure.json`. Recomputed all29 immutable source/dependency hashes directly from `3c542cd6800755a891cd3ffafd839fd682e7ec40` and the candidate hash; all match. Eleven real translation units are selected, including all four UniValue implementation files and the real manifest, codec, SHA-384, type, encoding and I/O implementations. No replacement codec/reconstructability/hash definitions were found.

## Code assessment

The diff is restricted to explicit cstdio, Windows io.h/POSIX unistd.h selection, a local existing-flags value and Windows-only `_O_BINARY`. Exclusive creation, existing0644 mode, write length checking, fsync/close, temporary cleanup and rename order/error handling remain unchanged. This preserves POSIX behavior while selecting raw bytes on Windows. It is one coherent storage-portability repair, conditional on the already-delivered396 forced-header prerequisite.

The added cstdio is appropriate for rename declarations. Existing Windows compatibility still supplies ssize_t/fsync/O_NOFOLLOW behavior; the candidate does not claim to remove that prerequisite or provide no-follow enforcement on Windows. It does not change process, peer, authority, validation or consensus behavior.

## Test assessment

The actual production function runs with binary fixture files, genuine SHA-384 commitments and real manifest/reconstructability checks. The512byte expected output covers every byte value twice (ascending/descending), including LF, CRLF-related bytes, NUL and0x1a. A Windows header-only diagnostic control removes exactly the `_O_BINARY` statement, leaving the candidate include repair and all other code intact. The expected `FAIL binary bytes preserved` signature is discriminating; do not describe this intermediate as the unmodified compile-failing baseline.

The native baseline retains the original missingunistd compile failure. The candidate must compile/link and run under bothcl/clangcl with /MT. Mac baseline and candidate execute the same test. All11sources are compiled directly; there is no test-source pruning. `/Gy` and `/OPT:REF` are component linker settings, not full Modelnet qualification.

Controls exercise hash rejection, duplicate-position rejection, wrong-size and missing input, temporary path occupied by a directory, rename failure with temporary cleanup, Windows existing-destination refusal versus POSIX replacement, preserved output, subsequent successful repair and final fixture removal. These are meaningful ordinary/error/recovery checks. The duplicate-position check only asserts refusal, not an exact cause, but the primary task does not alter manifest validation; that is adequate as a nonregression control. Only systematic shard positions0/1 are used, so do not claim new parity-loss recovery coverage.

## Claims and limits to retain

- Native output must prove the candidate passes and the header-only control fails specifically at byte equality under both compilers. Do not infer the binary defect solely from CRT defaults or a green workflow aggregate.
- Verify collected source/test/runner identities, expected failure logs and emitted commands against the exact final payload. The runner records hashes but collection must compare them to the immutable closure/candidate/test; hashes are not self-validating provenance.
- The original whole-root static profile remains unqualified even if these component /MT builds pass. No complete Modelnet library/node/helper/test_btx or OpenSSL dependency qualification follows from this test.
- MinGW behavior is deliberately affected by Windows binary mode too. Do not claim its runtime preservation unless actually executed.
- Existing Windows O_NOFOLLOW=0, stale-temp unlink and platform rename differences remain. The temp-directory refusal control does not prove refusal of all pre-existing temp files. fsync success does not qualify power-loss durability.
- The fixture has no injected short-write/fsync/close failure. The unchanged error code can be source reviewed; do not claim those individual failure branches were executed.
- Native behavior of0644 must come from the actual result; no speculative mode conversion is required by this review.
- Header-only failure leaves an owned failed-fixture directory intentionally for evidence. Distinguish that from the candidate's successful cleanup assertion.

No blocking issue found in the reviewed design. No product, harness, ledger, build, VM or GitHub mutation was made by this reviewer. Existing posting hold remains.

## Final artifact verdict

**PASS, scoped native compile/runtime repair.** This supersedes the pending-native-results qualification in the opening verdict. Native run41740815956 completed successfully at CI772bb25a7d0d7c73a988c10d94e339903848ee3d.

I independently decoded the final local runner payload and verified it carries the exact reviewed storage test and candidate. All29 immutable payload files match the closure manifest. All174 native source-hash entries (29files × three variants × two compilers) match their expected baseline/header-only/candidate inputs. All12 recorded native command logs match their SHA-256 values. The coordinator's artifact receipt records that the remotely executed runner matches these local bytes; this reviewer did not make an additional GitHub API request.

Actual native results under MSVC19.51/toolset14.51.36231 and clang-cl20.1.8, Windows Server2025/SDK26100, using explicit component /MT commands:

- Both baseline builds fail with the diagnosed missingunistd header.
- Both header-only controls compile/link, then the real repair call returns success and the fixture fails specifically at `binary bytes preserved`.
- Both complete candidates compile/link and pass all18 checks, including byte identity, Windows existing-destination refusal, error cleanup, subsequent successful repair and final fixture removal. Thus0644 was accepted in the actual tested production call; no additional mode conversion is justified by these results.
- Final Mac baseline and candidate logs both pass18checks; their recorded log hashes match. The existing POSIX replacement control remains passing. These Mac results are final-harness evidence, superseding earlier pilot linkage/setup failures without relabeling those pilots.

The command list includes all11 real translation units and the fixture. A cl /Bv invocation without an input exits2 while reporting its version; that is separate from the expected baseline build failures. The result aggregate has no unexpected errors.

Executable bytes and binary hashes were **not** retained/uploaded. Exact source payload, CI revision, compiler commands and verified execution logs tie the execution; do not claim retained executable hashes or a distributable binary. All earlier limits remain: this is a statically linked CRT component run, not a root/static-profile node build, complete Modelnet link/helper qualification, fulltest_btx or release sign-off. MinGW runtime, parity-loss paths and injected write/flush/close failures were not qualified by this campaign.

No further tests are required to support this bounded code/evidence claim absent a material code or acceptance change. The remaining work is accurate packaging and the user's publication decision under the existing hold. Reviewer resources are released.
