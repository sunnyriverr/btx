# Registry recovery: independent contract checkpoint

Owner: BTX test 1, delegated `/root/registry_recovery_review`. Source-only review at immutable Git `cbf65894e6d61084527cd93e913a00c6794418dd`; shared dirty checkout was read only. No build, test, VM, GPU, source mutation, or publication performed. Output reservation is this review directory only.

## Decision

The coordinator's cohesive boundary is justified: close the owned input before any move, use one quarantine operation for the two branches already described by the implementation as corruption, check the actual move result, and keep the first open fail closed. Documentation explicitly promises moved-aside storage and an empty later restart (`doc/pay-with-compute.md:91–95`), so fixing the skipped non-object-row move and false success diagnostic requires no new authority or admission policy.

The source checkpoint accepts that boundary. Execution acceptance remains conditional on reviewing the exact proposed harness and inputs before baseline; the actual product diff must be reviewed before application. No parser redesign, exception catch-all, typed-field relaxation, format change, partial recovery, same-open reset, destination-name/overwrite policy change, lock redesign, capacity change, or broad error cleanup is justified here.

## Authoritative state and mutation paths

`QualificationRegistry::Open` owns path, health/error and in-memory entries. It clears state, calls `Load`, and latches failure. `Load` owns the read handle, raw acquisition, parse and both existing declared-corrupt branches; the filesystem return value owns whether quarantine actually happened. Reaching EOF does not release the input handle. `Save` already closes its output before checked `RenameOver`; do not change it. `RememberIssued`, `Verify`, and `Status` reload before use and reject unhealthy instances. The RPC holder opens once per process. A new instance after successful removal of the live pathname follows `Load`'s existing absent-file empty branch; a failed rename must leave the corrupt original in place and subsequent opens unhealthy. Concurrency/independent-process handles and the Windows no-op file lock remain outside this patch.

## Smallest useful observations

Use the real public class and native filesystem, with unique isolated paths and no pre-existing quarantine artifact in successful cases. Run one identical final harness on baseline and candidate.

- Null-row differential: exact `{"schema":1,"entries":[null]}` must return false and unhealthy on the first `Open`; source must disappear, a regular quarantine file must contain exactly the original bytes, and a newly constructed registry must open healthy and empty. Baseline is expected to fail the real move/restart assertions, not merely return a nonzero exit.
- Existing invalid-top-level branch: non-JSON bytes must retain first-open rejection, move exact bytes and permit empty new-instance recovery. On native Mac this should already pass on baseline; it preserves the original branch while exercising the common helper.
- Fail-closed lifetime: after corruption rejection, ordinary qualification operations must remain refused on that instance. An implementation that immediately resets and returns success is a regression even if a later instance looks empty.
- Valid persistence and replay: use a legitimate issued challenge and the real persistence/reopen API. Preserve issued/redeemed state through a new instance, and show redeemed challenges remain rejected. If an expensive exact-work solver is avoided, disclose the actual fixture boundary rather than calling fixture-written redeemed data an executed redemption.
- Old-issuer authority after recovery: with an authentic previously recorded challenge, the empty new instance reports `unknown` and redemption returns `COMPUTE_CHALLENGE_UNKNOWN`. Never silently reinsert the old challenge before this check. This must distinguish unknown from expiry, malformed response, or unhealthy rejection.
- Genuine rename failure: put a nonempty directory at the fixed quarantine destination and preserve an identifiable marker. Require failed/unhealthy open, exact original bytes retained at the live path, marker retained, and truthful returned/Health error. A nonexistent/successfully-quarantined claim must not pass merely because `exists(destination)` is true. Prefer reporting `quarantine_path` only after an actual successful move; if retained as an attempted path, explicitly label that meaning and do not call it a move receipt. A new instance still rejects the unchanged original.

## Adversarial sensitivity

A close-only repair still skips the null-row move; byte movement, absent source and healthy new-instance checks catch it. A repair that merely sets `quarantine_path`, creates an empty quarantine file, or deletes the corrupt source fails the exact-byte comparison. A repair that ignores `ec` can pass all writable-directory cases but fails the nonempty-directory control's truthful failure and retained-marker checks. An implementation that accepts corruption and empties immediately fails the first-open/continued-unhealthy checks. An implementation that restores old authority after empty recovery fails unknown/unredeemable checks. A broad valid-file reset can pass corruption cases but fails valid issued/redeemed reopen controls.

## Platform and claim limits

repch1c's item 14 in comment `6592708241` is another contributor's actual Windows missing-quarantine observation with disclosed compatibility workarounds; its stream-sharing explanation was expressly not runtime traced. Pinned Microsoft source/documentation corroborates stream-sharing reasoning, not our native Windows execution. Native Mac differential qualifies the skipped null-row move and real POSIX recovery/error behavior. It cannot establish a Windows lifetime before/after result. No OS header or new platform conditional is needed for the proposed implementation, but the Windows execution gap must remain explicit in the handoff.
