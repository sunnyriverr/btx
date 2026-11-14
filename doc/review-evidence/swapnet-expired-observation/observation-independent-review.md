# Bounded independent observation-only review

14 November 2026. Reviewer: Session 1 child `/root/observation_boundary_review`; this is a bounded independent source review inside Session 1, not another peer session or independent native-platform verification. Only this report was written. No builds, test execution, source changes, wallet effects or publication.

## Verdict

One P2 reporting-contract issue should be resolved before declaring the recovered-only contract complete. No concrete signing, broadcast, financial-mutation bypass or latch-clear path was established in the declared committed/no-trusted-reference/no-fund-or-refund-WAL scope.

### P2: Preserve successful historical facts separately from current read errors

`observation-candidate/coordinator.py:397–400` replaces the sole recovery status with `unresolved` and the sole reason with the newest error code. For example, after a successful `original_refunded` or `original_claimed` result, a subsequent `driver.clock`, `driver.observe`, or live-output read raising `SwapError` overwrites that result, updates `checked_at`, and leaves only the original outpoint. The previous classified payment fact and its observation time no longer exist in the persisted record or get/recoveryinfo projection. The `not obs.present` branch at lines 382–383 similarly discards the previous classification.

The recovered-only contract explicitly says: “RPC/pruning/rescan errors retain previous original and last successful facts separately from latest error/current uncertainty.” This matters because a transient node/history outage must communicate that the current state is uncertain while retaining what was previously observed. It must not make an old success appear current or silently lose the known historical observation. Keep a separate bounded last-successful fact record, with its original observation time and public-safe classification, alongside the current status/error. Add a matched successful observation → RPC failure/unavailable observation → successful retry control, including reopen and unchanged financial rows. This is a factual-reporting defect, not a demonstrated spending-authority escape.

## Boundaries that held in source inspection

- `tick_one` selects discovery before counterparty driver lookup, normal observation/action selection, funding, refunds and terminal/unfunded cleanup; the branch returns unconditionally.
- First-latch save precedes discovery I/O. A save failure or revision conflict propagates before ordinary execution; a failed final-fact save leaves the already durable latch. No exception catch falls through into the action engine.
- Cancellation uses the stricter imported-unknown predicate before reservation settlement, even before the first tick and before maturity. Peer cancellation delegates to that same fence.
- `_prepare`, `_fund`, `_claim`, refund RPC and fee bump use the common effect predicate. Fee bump checks immediately after owner lookup, before operation construction or signing.
- Active latch is checked first and remains effective across height rollback and later references/flags. Peer hints can write only the validated counterparty reference and cannot replace the own original or clear the latch. Duplicate negotiation messages do not re-grant a committed session.
- Discovery writes facts separately from normal refs, operations and execution flags. Missing live output without sufficiently settled positive spend classification becomes `spend_lookup_pending`, not `original_unspent` or whole-swap terminal success. Established original is retained across later reads; there is no replacement history search once an original exists.
- get/list/transcript and recoveryinfo project persisted state with no implicit scan. The new recovery projection allowlists fields and disables actions. The observer preimage is not copied into this projection.
- Ordinary fresh sessions and pre-existing flags/reference/own fund-or-refund WAL bypass the new eligibility predicate. The active latch still takes precedence. Existing WAL matching/adoption remains the prior implementation's responsibility; arbitrary inconsistent or previously unmarked directories are outside this bounded claim.

## Qualification limits and useful next checks

The reported 23 focused passes and 207 existing suite passes were not independently rerun. The reviewed `test_observation_only.py` covers factual classifications, first-tick direct action fences, history misses/ambiguity, restart, stable polls, owner isolation, fresh-session execution/cancellation, owner revocation, reimport and peer hints. Its rollback test checks a sticky latch rather than actual original/spend reorganization semantics.

The written contract also names first-latch/final-fact persistence faults and actual original unavailable/conflicting transitions. Those dedicated controls were not present in the reviewed focused test file. Source is fail-closed at both saves, so this is qualification evidence still needed, not an established mutation defect. A saved valid refund/claim WAL with missing session pointer also needs the explicit preservation result already requested by the mutation audit; generic suite totals do not identify that particular control.

Read `observation-native-result.json`: it reports Core 30.4 saved-expired-refund through Coordinator, exact original `697187669970b99cf47bc76fa8953284609dca9090dec248938fa8174a3496f5:1`, bounded pending→refunded status, zero signing/broadcast/accounting calls, unchanged financial rows, direct refusal codes, stable repeated facts and DB reopen. This is reused owner evidence, not a new native run by this reviewer; its stated limits remain applicable.

## Inputs and footprint

Compared candidate coordinator to `../swapnet-spent-bitcoin-recovery/repair/coordinator.py`; compared fee-bump/application baselines using read-only `git show d7b9594b:contrib/swapnet/swapnet/...` from `work/btx-contributions`. Read recovered-only contract, mutation audit, focused tests and native result. Consulted current charter, lifecycle, selected task, latest NEXT-RUN, registry and all owner statuses/bookings. Parent Session 1 owns/reserves the task directory and candidate components; this child used no peer mutable execution resources. No bookings created or released by this review.

Candidate SHA-256 at review:

- coordinator.py: `dcf02286b42c5881e09faa370af9b59b5c4fbba8fb001dc388ba054c87ae868b`
- application.py: `e149d0f3f029db3b76f80fdf7ca32783ab23cc437e531759c91b1f927cc286e2`
- fee_bump.py: `64c52fd83182180bf0530692f5589d516d34b1c446d2321d9689172ea51e987a`

Next owner: parent Session 1. Resolve the retained-success reporting requirement and named finite qualification gaps within existing authorization; publication remains outside this review.

## Delta re-review — retained-success repair

14 November 2026, following parent request. Inspected only the coordinator delta from the reviewed candidate to `<owned-ram-runtime>/contrib/swapnet/swapnet/coordinator.py` and the added focused-test definitions. Live coordinator SHA-256: `f91ee1ccfbfabbf98f31415e1ced24e98d4479418d41a742a6cd4f5ce39ff3f3`. No tests/builds/source edits or publication by this reviewer.

**P2 resolved in the inspected live delta.** Successful unspent/claimed/refunded observations now create a bounded `last_verified` record with original, classification, checked height and observation time. Later unresolved/error/conflicting current status retains that record. `_safe_view` allowlists its projection, preserving the distinction between historical evidence and current uncertainty. Identical verified evidence does not refresh its timestamp or introduce a new revision. This change creates no action authority or new effectful path.

Added test definitions reach real injected observer RPC errors and noncanonical/conflicting reports after a successful refund observation, assert retained `last_verified` through reopen, disabled actions, zero effects and unchanged financial rows. Added final-facts IO/revision-save failure controls verify a durable latch survives and retry succeeds. Initial latch-save failure and imported prepared-refund controls are also present; parent reports those passed. This reviewer inspected definitions rather than rerunning them, and does not independently attest the final pass count or a native run of this delta. Exact mirrored candidate bytes and final qualification receipts remain the parent's responsibility.

The original P2 finding above is retained as review history; it is no longer an open finding for the live hash named here. No new concrete blocker found in this bounded delta review.
