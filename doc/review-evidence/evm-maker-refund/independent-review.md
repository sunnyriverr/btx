# Bounded independent source review

Reviewed 14 November 2026 by the Session 1 delegated review agent. Sole output: this report. No product mutation, build, test execution, peer contact or publication.

Verdict: no concrete safety defect or missing essential component-level control found in the one-line repair. Appropriate to advance to the already identified native EVM qualification gate; this is not a native acceptance verdict.

## Scope and reasoning

Compared `source/contrib/swapnet/swapnet/coordinator.py` with `candidate/contrib/swapnet/swapnet/coordinator.py` at task base f08e0b4be0eea06152ad83e47311ff8907f9c25d. The sole product delta removes `agr.long_leg.lock_domain == 'height'` from the existing unfunded-responder cleanup condition (candidate lines 362–367). Reviewed candidate timestamp tests, existing height-maker tests, journal closure, reservation transaction, decision engine, reference admission, EVMDriver and EVMAdapter.

The cleanup still requires `wait_for_chain`, committed responder, absent local leg, refunded remote leg and `LegObservation.settled`. Settled requires fresh, present, exact, canonical, nonconflicting evidence and sufficient family confirmations; EVM finality remains required by the default policy. Conflicting or stale observations cannot reach cleanup. EVMAdapter always reads the finalized block, validates historical runtime and the seven ABI words/terms/state, and rereads the block hash; missing finalized support has no latest fallback. Thus removing a deadline-domain restriction does not remove the evidence qualification that makes a timestamp refund usable.

The real EVM reference admission binds salt/lock ID to the session, chain, contract and funder. Finalized contract storage is the remote-refund authority, rather than the peer's txid alone. If optional remote observation fails, the coordinator supplies an absent observation, which cannot satisfy cleanup's settled-refund gate. A refund credits the counterparty's beneficiary; this unfunded local responder has no withdrawal obligation on that remote refund.

`close_unfunded_responder` rereads durable state/revision inside the existing immediate SQLite transaction. It refuses secret exposure, funding/recovery flags, funding operation/reference, every durable operation, coin lock, consumed or mismatched grant, and any reservation except held. Closing the reservation/held budget, revoking the grant and cancelling the negotiation share the transaction and audit. Cancelled sessions return before observation/funding on future ticks. These checks remain unchanged and conservatively retain ambiguous local obligations. Existing transaction rollback test covers interrupted cleanup without relying on the removed lock-domain predicate.

## Test review and limits

The new fixture reaches signed negotiation and real coordinator/journal/SQLite accounting with EVM timestamp terms. It deliberately substitutes contract/reference/finality behavior. Reviewed controls cover nonfinal refund, durable funding WAL despite old flags, stale/noncanonical/conflicting/inexact observations, reopen persistence, valid new admission at 127 other active slots and no reauthorization after remote rollback. Existing height tests cover funded-maker recovery and closure rollback. No essential new control was identified that must precede the next qualification step.

The repair receipt reports identical eight tests: two failures/six passes before, eight passes after; full candidate 165 passes. Those are owner-executed results, not executions independently reproduced by this reviewer. The two failures concern the same closure defect. This review supports their stated component-level interpretation only.

Remaining material gate: run the actual repaired EVMDriver/EVMAdapter against a native finalized timestamp refund, using the exact built/embedded candidate identity. Verify maker has no local prepared/broadcast funding, durable operations or coin locks; reservation/held budget and active slot close once, unused grant revokes, reopen remains cancelled and a new proposal succeeds. Reuse existing funded/recovery evidence unless the native run exposes a specific gap. Simulator assertions do not establish native ABI layout, sender-scoped lock binding, runtime identity, finalized RPC behavior or daemon embedding. No claim of native repaired-EVM success is warranted yet.

No resources or runtime jobs created. No further source review action remains absent a material patch delta or native finding. Publication hold preserved.
