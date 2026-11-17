# Independent candidate source review — original proposal retry

**Verdict: no blocking product defect found in the reviewed candidate. Qualification is still pending; this is source/assertion review, not an executed before/after result.** No tests, builds, network requests, product edits or publication were performed by this reviewer. Only this report was written under the reserved task root.

## Scope inspected

Compared baseline/candidate `swapnet/coordinator.py` and `swapnet/journal.py`, and read the prepared `tests/test_initial_proposal_retry.py` against the parent DESIGN and proved failure. The correction remains two product files. It uses the existing saved intent and explicit accept/resume entry points rather than a new background scheduler, outbox schema or fresh negotiation framework.

## Product findings

- `start` confines NOT_FOUND handling to the owned-session lookup. Errors from the new retry helper cannot fall through into `_save_new`, another reservation or fresh key/secret generation.
- The helper exits for non-initiator/non-proposed sessions, and an exact live already-queued proposal returns before any new signing/enqueue or authority-read effect. The Journal query includes acknowledged and not-due rows, has no due-page prefix, and checks all inspected same-session packets for conflicting frozen payload/recipient.
- New missing-send effects require no restored-session marker/recovery facts or prepared/granted/operational financial state. This is the important distinction between the proved clean reopen and an uncertain older backup. It does not claim to repair every historical backup/startup path.
- Current signed quote/network/requester/provider binding is checked against the saved payload. Changed retry mandate/caps/RFQ are rejected for a missing send. The helper reads the exact original held reservation and joined mandate instead of using the existing-reservation `reserve(check_only)` shortcut, which would bypass revocation/expiry checks. It verifies original principal/quote, deterministic mandate body identity/scope, held cost, cumulative budget and caps, with no second debit.
- Existing driver readiness/clocks validate the saved absolute deadlines; `_deadlines` is not called. Quote and mandate expiry are checked again before emission. A new transport envelope/sequence does not replace the saved proposal nonce, quote lifetime, keys or financial terms. Signature/native calls stay outside SQL transactions.
- `resume` preserves the original tick first, then reloads. Expired proposed records do not enter resend, so late cancellation remains reachable; funded/committed/terminal recovery retains its old path. Existing `_owned` owner/principal behavior is retained, while financial validation uses the saved principal.
- No original funding, refund, grant, chain-driver or financial authority behavior is changed. `has_proposal` uses existing decoding and table columns rather than adding a SQLite JSON-extension dependency or a new storage migration.

## Prepared regression assessment

The prepared suite covers missing-send accept and clean reopen/resume, exact frozen intent/keys/secret/reservation/budget equality, one funding per leg after legitimate delivery, no fresh setup helpers, already-queued/not-due/acknowledged/beyond-page deduplication, repeated save/sign failure and later retry, changed parameters, missing authority/recovery fences, wrong principal, existing owner resume with an exhausted-but-already-held budget, expiry/late cancellation, original deadline/stale-clock refusal, conflicting local outbox data, lost caller reply after enqueue, and release-once cancellation.

Those are meaningful controls for the selected helper. The negative authority/recovery cases predominantly enter through accept; both effect entry points share the helper, and the positive resume/reopen and late-resume ordering are separately represented. This is not a reason to start a native/platform matrix, but final qualification must confirm the intended assertions actually run rather than classify setup errors as product failures.

## Required final qualification / claim boundaries

The candidate has not been executed at this review checkpoint because the parent recorded the disk-reserve prerequisite. Before local handoff, require the identical final correct-behavior regression to fail on stock at the intended missing-outbox observation and pass on candidate; resolve any unexpected relevant legitimate-control failure. Pin loaded source/harness identities and report exact pass/fail/skip accounting. Reuse unaffected earlier evidence rather than rerun merely for counts.

The fixture proves real Mac Python Application/SQLite behavior with injected persistence/signing errors, clean Application reconstruction and simulated chains/signers/transport. Do not call it a native btxd process restart, real disk-full test, native funded swap, all-platform/full-suite or release qualification. Do not claim automatic recovery of old already-acknowledged packets or restored snapshots. The new retry is explicit and missing-first-send only.

No additional source-design blocker was identified; the parent owns execution, final evidence audit and any later authorized publication.
