# PR386 source and oracle checkpoint

Verdict: PASS for the proposed test-only source, subject to coordinator resource gate and final artifact review. BTX test 1 delegated reviewer `/root/channel_recovery_revision_review`; no builds, tests, VM use, source mutations, or external publication performed by this reviewer.

Exact product source: `b1be792041f9337b4d8e1156f8b6aa76b8e09277` on `fd3a905f`, read through immutable Git objects in `toolchain-2026-10-31/source`. Feedback: repch1c comment 6592257368 from `priority-after-storage/386-comments.json`. His Mac reproduction and mutants are independent contributor reports, not this reviewer's runtime result. Review candidate SHA256: `c50765e3b6502811c67c619de0bbc40a068aeb2cd5c7a6686d79336aba37aedb`.

## Authoritative state and mutation paths

`Database` owns durable SQLite `channels`, `permits`, `meta`, and revoked-subject rows. `Meta`/`SetMeta` read/write persisted rows, so an in-memory acknowledgement alone is insufficient. Acknowledgement key is channel name and its value is the active capsule ID (or `none`); it suppresses repeated incident side effects, never Broker admission.

`Follow` can replace owner mandate and reset phase/candidate but retains active/previous/sequence. `Stage` validates signed release sequence, previous binding, owner mandate and candidate admission; it stages a canary and can freeze equivocation. `Activate` validates canary, admission, owner/release authority and resident bytes; changes active binding, clears acknowledgement, revokes prepared permits. `Tick` reevaluates owner and active eligibility, retries qualified rollback even after acknowledgement, rearms an acknowledged generation after eligibility recovery, freezes/revokes first incidents, and quarantines invalid candidates. `RunChannelCanary` can also freeze/remove a failed candidate. Broker resolves active/canary channel bindings and independently validates capsule/mesh admission on Prepare and Execute; direct grants do not inherit follow-mandate revocation.

## New regression oracle

The proposed new case uses an active, still-admissible capsule and revokes only the follow mandate. First Tick must freeze channel and revoke an already prepared direct-grant permit. A channel grant works before this incident and fails afterward. The unchanged capsule must still pass `AdmitCapsule`, preventing an expired-active duplicate from masquerading as owner coverage. A fresh unrelated direct-grant permit must remain prepared after repeat Tick and again after a true destruction/recreation of the Database connection; actual Broker Execute must dispatch read and return the exact expected digest. The original Broker boot value is intentionally reused: this is Database reopen, not Service restart or new-boot bearer survival.

Fixture cleanup ownership is safely transferred by swapping `Temp.root` paths. Fixture Database destruction occurs before its Temp destructor; the original fixture directory remains owned by outer Temp. Reopened Database is destroyed before that outer Temp. No production path is used and no SQL fixture-state injection is needed.

Realistic broken implementation: remove the acknowledged frozen/no-candidate `continue` (line241 of exact source). Owner-current remains false each Tick, entering global revoke despite the existing acknowledgement. All old six cases can pass; the new fresh-permit assertion fails and execution would otherwise receive `SEC_PERMIT_REPLAY`. A fake fix skipping every incident is caught by first-freeze/preincident-revoke assertions. An acknowledgement kept only in memory is caught after actual close/reopen. The oracle observes externally useful dispatch as well as database phase.

## Remaining three surviving mutants

- `||active_invalid` in candidate quarantine is behaviorally meaningful and currently unasserted: an expired retained active plus later revoked candidate must produce frozen phase after candidate removal. Without this expression phase incorrectly becomes active. One added Phase assertion at the existing checkpoint covers this without another fixture/case/matrix. Broker independently rejects invalid active admission; do not call this a demonstrated dispatch bypass.
- Activation clear protects same-binding recovery: explicit Stage/Observe/Activate may reactivate the exact same capsule after a transient eligibility recovery before any Tick rearm. A later incident can otherwise match the stale acknowledgement. Stage permits an unchanged capsule ID at the next sequence and Service exposes explicit activation. This is source rationale for retaining the clear, not runtime proof or a present-head defect; current new case does not cover it. No automatic extra fixture is justified by mutant survival alone.
- Rollback clear maintains a clean acknowledgement invariant. For ordinary distinct-binding rollback, old acknowledgement differs from restored active and later return through Activate clears it anyway. Individual mutant survival is consistent with redundancy on those paths. This review does not claim universal redundancy across all same-binding/authority-recovery edge combinations, or a separate supported safety failure. No product cleanup or test-per-line work is warranted here.

No material supported current-head product failure was identified. The concrete feedback is addressed by one maintained owner-revocation case plus one assertion in an existing case. Full Service maintenance, native workers, other OSes and full daemon remain unqualified. Final review must map the executed exact source, known-bad target, input objects/libs, output hashes and cleanup to the reported result; only coordinator may acquire resources or promote further work.

## Reviewed selector delta

The final candidate adds optional exact-name selection as argv[2], leaving ordinary no-selector CTest execution unchanged. Nonmatching selection exits2 instead of reporting a vacuous success. This supports one focused owner-revocation execution per source variant plus the existing candidate-quarantine case, without a redundant full six-case baseline matrix. Accepted source-only delta; no execution performed by reviewer.

## Pilot correction reviewed

The source gate missed an accessor error: `Text` requires a nonempty string, so it cannot check an intentionally empty candidate. The pilot failed with SEC_TEXT before reaching the fresh-permit oracle and produced no product result; the correct accessor is the existing `get_str().empty()` idiom. Current source now uses that accessor. The driver additionally creates result directory with private0700 rather than0755, as required by WritePrivate; pilot original sources, binary/logs and manifest are retained. These corrections preserve the acceptance condition. Reviewer acknowledges this avoidable source-review miss. Source gate applies to corrected hash above; no execution result inferred and resource floor must be restored by coordinator before any run.
