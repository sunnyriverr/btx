# Hydration cleanup recovery: Linux before/after evidence

**Same interruption/restart fixture: baseline FAIL, candidate PASS.** Candidate code: [3f6849bd](https://github.com/sunnyriverr/btx/commit/3f6849bd57811942e5965d93dd6f75ef9ff1f492), one production file plus two maintained regressions, based on release-0.34.17 `1e2f8b5f`.

Follow-up to [JPP's quarantine cleanup, #737](https://github.com/btxchain/btx/pull/737), incorporated as `726c4fa9`. The checkpoint support from #707 is preserved. This is a local recovery failure: verified live bytes remain present, but a saved EOF job points at removed temporary data and ordinary retrieval remains `not_local`.

## Results

| Check | Before | After |
| --- | --- | --- |
| Kill helper at successful cleanup/job-unlink boundary; three retries and another restart | `not_local / WAIT_FREE / missing piece` | Local, original IDs/exact bytes; no new origin GETs |
| Old stranded EOF state created by ORIGINAL baseline binary; restart tested binary | Same failure | Fresh verified fetch, one origin GET; local after another restart |
| Valid 4 MiB partial prefix; refuse second piece, restart/resume | Pass; prefix not fetched again | Same pass |
| Corrupt retained prefix, then healthy-origin retry | SHA refusal/no live admission, recovery and restart pass | Same pass |
| Normal recovery/restarts/unrelated model | Pass | Pass |
| Two new maintained regression bodies | Both fail at intended assertions | Both pass |
| Existing quota, SHA/root, completed-quarantine-release bodies | Three pass | Three pass |

## Execution and CI reporting failure

[Original-helper final native fixture, run 43873349021](https://github.com/sunnyriverr/btx/actions/runs/43873349021); [candidate build/component/native results, run 43874995738](https://github.com/sunnyriverr/btx/actions/runs/43874995738), executed fixture commit `2847d3a054139fb0a20ef35c2cee22fd95c50984`. Native fixture bytes are identical across baseline and candidate. Baseline native results were reused after the auxiliary component-link correction, not rerun. Legacy-state creation always uses the original baseline binary.

**The latter workflow is red because its final summary write failed, after all native assertions passed.** The host attempted to overwrite Docker-owned `records/build-result.json` and raised `PermissionError`. [Exact traceback](raw/wrapper-failure-excerpt.txt), [native baseline](raw/native-baseline.json), [native candidate](raw/native-candidate.json), [build/component record](raw/build-result.json), and [offline audit](validated-result.json) retain this split verdict. The corrected summary destination is in `fixture/workflow.corrected.yml`; that workflow correction was not hosted-executed. No native rerun was done to change a badge. Raw `build-result.json` deliberately retains its pre-summary status.

`fixture/validate.py` was executed against the retained records locally; it accepts the saved result and rejects an injected candidate FAIL. The source-relative layout it expects is the original execution/collection layout; this evidence directory is a curated publication, not a claim that its different layout was independently rerun. [Manifest](manifest.json) binds all published files, executed inputs, binaries, artifacts and test-body equivalence.

## Scope

Runtime Ubuntu 24.04 x86-64, direct real helper UNIX RPC and actual S3 client against an owned recording HTTP object-store fixture on permitted loopback. Tiny PIECE_OBJECTS models and a roughly 4 MiB partial model. A libc hook stops only the disposable helper at the source-identified boundary, then the fixture kills it; restarted helpers have no hook. No catalog/cursor mutation creates the crash state.

Build Ubuntu 22.04/GCC 11.4/OpenSSL 3.5.9 from a verified retained checkpoint using normal CMake/Ninja targets. The production delta is only `file_stream.cpp`. A qualification-only executable links actual production archives and runs five exact maintained case bodies through throwing assertion adapters. **The full Boost `test_btx` target/translation unit and full suite were not built or run.** Existing test headers and case bodies remain in-tree. The retained link profile includes `--unresolved-symbols=ignore-in-shared-libs`; this repair did not add it, and it did not suppress the missing static-archive translation definition encountered in the failed fixture link. This is not a clean release-link qualification.

Not qualified: full daemon proxy, SOURCE_FILES execution, real-provider authentication/TLS/WAN, native Windows/macOS, large-model, GPU/financial or release acceptance. Present pieces are only an availability check; final SHA/root verification remains required. General inaccessible/corrupt metadata and orphan quota cleanup after an already-removed job are outside this repair.

The inherited native receipt field `product_patch:false` is stale for the candidate. Its helper SHA and the executed build/source hashes establish the candidate identity; raw receipts are retained rather than silently edited.

## Reviewer entry points

The commands actually executed are in the [recorded workflow](fixture/workflow.executed.yml), [build runner](fixture/build.py), and linked run logs. To exercise the same native test entry point with your own separately built baseline/candidate helpers, compile the small hook in `fixture/`, set `BTX737_HELPER`, `BTX737_CREATOR` (original baseline), `BTX737_HELPER_SHA` and `BTX737_OUTPUT`, then run `python3 native.py` there. The original executed recipe verifies its immutable baseline artifact in `stage.py`; independently built binaries require their own source identity. No production wallet or node is used.

The maintained new cases are `modelnet_file_stream_tests/job_cleanup_failure_preserves_valid_eof_checkpoint` and `modelnet_file_stream_tests/missing_eof_quarantine_does_not_advance_resume_cursor`. Running them in your normal full `test_btx` build is separate review evidence, not something claimed here.

## Retained failures

The first component build used the wrong filesystem conversion and saved-job function signature; the next lacked the normal application's translation global. Corrected test adapters are retained; no product failure was inferred from them. The second run preserved compilation, so final baseline/candidate incremental builds took 2.619/3.471 seconds. Those are incremental timings, not clean-build benchmarks. Records and binaries were downloaded/hash-verified; no checkpoint archive was redundantly restored on the Mac.
