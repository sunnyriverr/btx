# Normal-helper qualification preflight

Source review only of the proposed `build.py`, `test.py` and workflow. No dispatch, build or test execution by reviewer.

## Source-identity gate — addressed

The final revision addresses the initial source-identity concern. It checks out immutable checkpoint source `89538835` separately, asserts there are no retired old tracked paths, copies and re-verifies every current tracked file, and replaces current CMake sources so the old review802 target registration is removed. Exact candidate and test SHA256 assertions pin the intended inputs. The archive/external-input checks and bounded build plan still guard reuse. No old-source deletion is attempted. This is an adequate bounded identity check for the proposed ordinary `btx-modeld` target; no pre-dispatch blocker remains from this review.

## Test discrimination and cleanup

No other concrete blocker found in the new test path. Baseline must actually reach and complete the expected workflow: `test.py` writes its result only after same-process undo, repeated post-process-restart observations, manifest recovery, recovery persistence across another process restart, metadata re-observation, lot uniqueness, fresh empty state and successful keyed replay have passed. `build.py` requires baseline exit7 with exactly four failed no-undo checks; unrelated setup/control errors cannot count as the intended before result. Candidate requires exit0 and all four no-undo checks passing.

For refusal cases, the helper RPC must return an error containing `UNDO_UNAVAILABLE`; the bounty JSON file hashes and funding snapshot must remain unchanged, and no corrective event may appear. Real helper process stop/start is exercised, improving on the direct-store diagnostic. Successful keyed replay compares exact prior result and unchanged files; it is correctly treated as a prior successful operation rather than a new false correction.

The helper has bounded startup/RPC/shutdown waits. `finally` stops its owned process, escalating to kill on a shutdown timeout and failing instead of claiming a clean stop. A failure before final result emission makes the qualification fail. The runner is disposable and uses task-specific Unix sockets/model directories, never wallets or a production node. Exact binary hashes and RPC transcripts are retained. The workflow uploads records even on failure and uses a finite job timeout. A build/test timeout is an infrastructure/control failure, not a product regression pass.

The incremental action cap is a useful resource guard; a cap/external-input mismatch must stop rather than silently switch to an unbounded build. Candidate compilation is selected by replacing only bounty.cpp after baseline completion; its guard leaves normal undo persistence unchanged.

## Reporting limits

A successful run would qualify normal linked Linux helper/UnixRPC process-restart behavior in the pinned container/profile, not Windows, mainnet, real chain observations, signing/funding or release acceptance. The RPC's observations remain operator-entered watch-only data. Recovery import still requires known-correct inputs and resets omitted height/confirmation metadata; re-observation remains necessary. Record any source/head advance or retained cache applicability precisely.
