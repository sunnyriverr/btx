# Independent final receive-side commitment code review

**Verdict: no blocking product defect found in the narrow two-file repair. The code and recorded focused tests support local handoff at the stated Application/SQLite scope.** Read-only review of baseline/candidate diff, receive_commit/Authority/Store contracts, maintained test file, and baseline/candidate result records. No tests, builds, product edits, network requests or publication by this reviewer.

## Repair correctness

The change is limited to commit packets after the existing full packet validation, recipient/relay decision and ACK-only branch. All other handlers retain their prior behavior. Existing inbox admission still precedes effects and bounds the admitted set. A commit now skips its handler only for a durable successful-completion receipt. An old admitted-but-unapplied row therefore re-enters receive_commit instead of producing the reproduced false ACK.

The receipt is recorded after successful handling and before ACK generation. A receipt-store error follows the existing caught-failure cleanup and cannot send a success ACK. A crash after the handler but before receipt persistence re-enters the existing agreement/signature and stage checks. receive_commit uses the same deterministic grant and only changes an offered negotiation; a committed-or-later session returns without creating another grant or funding. The code does not add a signature/network call inside a SQL transaction, change signing authority, refund timing, fee scope or payment identities.

Completed repeats still pass envelope signature/network/expiry checks before the receipt shortcut. ACK generation remains outside the processing try/transaction, so a failed ACK does not erase a valid completion. Restarted ACK retry can use the receipt without repeating handler effects.

## Bounds and compatibility

The supplementary table is created after sn_inbox and references its exact ID with ON DELETE CASCADE. Store explicitly enables foreign_keys. Thus the completion cache is a subset of the same admitted set: expiry/forget deletion prunes receipts, and there is no independent second quota or retention window. The existing two-column sn_inbox INSERT remains valid; no implicit column migration or unsafe completion backfill is added. Unknown Journal user versions remain refused before migration.

For legacy rows, success must be revalidated once because old storage cannot distinguish admission from completion. The existing receive_commit guards make an already-applied legacy commit a financial no-op; the new receipt then permits future deduplication. Existing cancelled/rejected or expired/revoked pending authorization still refuses. The additive table does not repair a sender packet already retired by an old false ACK, and older binaries still have their old behavior on downgrade. Keep both limits explicit; do not claim retrospective reconciliation or a whole-message-engine repair.

## Evidence and test review

The recorded common baseline selection has five expected behavior failures and three passes; candidate records twenty passing cases. The same maintained test file and loaded-product provenance are recorded by the runner. Baseline failures cover pre-handler/pre-session interruption and legacy seen-only cases; baseline passes appropriately include already-durable session/ACK boundaries and ordinary caught-error retry. These are differentiated results, not a claim that all twenty candidate-only storage checks were run on stock.

Four deliberate child-exit cuts stop after admission, after grant/pre-session, after session/pre-receipt and before ACK; the parent checks exit73 and reopens the receiver. The post-completion duplicate guard fails if _process runs again after reopen. Counts check one grant/reservation and unchanged held/used amounts at replay; healthy completion verifies one funding per leg. Legacy tests retain the old table shape without receipts, reopen and require one guarded handler pass followed by deduplication. Completion-write and ACK-error tests distinguish durable completion from reply delivery. The capacity/expiry test verifies the actual8192 cap, two-column insertion, foreign-key configuration, cascade and missing-parent refusal.

The refund control withholds the maker after replay recovery, checks REFUND_EARLY one block before maturity, then refunds the same original payment at maturity with unchanged funding/refund records, no second funding and no secret exposure. This is production Coordinator logic with simulated ledgers/signers, not native funded-chain or C++ worker qualification.

## Minor optional test strengthening

The invalid-packet parameter test uses broad pytest.raises(SwapError). Pinning the expected BAD_SIGNATURE / NETWORK / MESSAGE_EXPIRED / AGREEMENT_BINDING / SESSION_BINDING codes and unchanged outbox state would make its exact refusal path more explicit. Source review shows validation precedes completion handling and the current fixtures reach those branches; this is not a discovered product defect or a blocker requiring another full run. If strengthened, rerun only those changed cases, not all passing tests.

## Scope and handoff

No evidence here qualifies other message kinds, native PQ signatures, actual Bitcoin/BTX/EVM transactions, embedded worker shutdown, all platforms or a release. The commit-only scope is justified by the proved funded-negotiation consequence and existing idempotent receive_commit contract. Preserve the documented residual risks for other handlers instead of saying the entire common admission class is fixed. No additional product change or execution is required solely for this code-review verdict. Parent owns final evidence reconciliation and any separately justified recovery-bundle compatibility checks.
