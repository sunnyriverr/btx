# Reorg save-failure repair — implementation preflight

Source review of the final `repair/candidate-bounty.cpp` against the #815-guard baseline and final `repair/test.py`. No build, test execution, product edits or publication by reviewer.

No concrete blocker found before the proposed normal-helper qualification.

## Transaction correctness

The implementation copies the complete `BountyChainIndex` before mutation, including facts, bounded undo deque, undo-byte count, height and epoch. It also retains the store sequence and local event-vector size. The store mutex covers the whole operation. A failed `PersistLocked` restores the copied index by move, restores sequence, truncates only newly appended local events, clears the result and returns the original IO error. This preserves the exact observation/undo state needed for a retry rather than rebuilding from `SaveState`, which would lose undo history.

The exception path performs the same rollback for pre-commit failures. The rollback flag is disabled immediately after successful persistence, before `Remember` and shared-journal publication. Thus a later journal/remember exception cannot make memory contradict an already committed bounty store. This does not promise all post-commit exceptions are safely retryable: the focused guarantee is returned bounty-save IO failure. Keep the existing broader exception/journal/crash-window limits explicit.

`MakeBountyEvent` prepares the same event fields and increments the supplied sequence. Reorg stages this event locally before saving and calls `PublishBountyEvent` only after commit. Failed saves therefore do not notify the bound journal/listener. Existing `Event` callers still make, append and immediately publish an event in the original order, preserving #468's deliberate memory-on-failed-save policy for other methods. Generic `ok()` is not called after the explicit persist, so there is no double save. Successful idempotent results are remembered only after durable commit; a refused request is not falsely cached.

The prior #815 empty-history guard remains in both before/after targets. This test must be described as guard-baseline versus guard-plus-save-retry repair, not stock bd847 versus only this patch unless source identities separately establish that claim.

## Fixture discrimination

The same final seven-case helper test is suitable for baseline/candidate qualification:

- Healthy undo still consumes the latest B observation, then the remaining A observation, while unrelated S50 remains; restart retains the committed result.
- Permission-denied marker, exact IO code, byte-identical store and no leftover temporary file prove the intended save refusal. Candidate checks require live facts/undo epoch, local events and shared-journal events unchanged.
- Unkeyed and same-key exact retries must undo only once to A100. The overwritten-fact case checks restoration of the previous A100 value rather than merely deletion of a new key. Successful keyed replay must preserve exact result, disk, funding and journal.
- The journal filter matches the current event schema (`bounty_id`, provenance `bounty_kind=REORG`). `getmodelevents` initializes the journal under `M/events`; chmod500 on the bounty store's parent M still permits writes inside that existing writable child, so baseline premature journal publication is not masked by the fault.
- Conditional re-observation and restart controls do not pretend to complete an uncommitted undo automatically. Candidate retains300 after IO; re-observing A preserves that complete live view. The known-correct-single-A recovery observed on the old helper is not being incorrectly required from a rolled-back candidate.
- The unrelated draft case requires the existing failed-save memory policy to remain visible in process and absent after restart, while ordinary draft creation/local event behavior still works.

Checks aggregate contract failures while allowing valid controls to finish; unrelated startup/transport/control errors raise and must not count as expected baseline failure. The test currently asserts successful journal count; comparing its sole successful event's provenance ID with `retry_reply['event']['event_id']` would be a useful optional tightening, but the preceding no-failed-event check plus unchanged production conversion already establishes the relevant boundary.

## Cost and scope

One transient full index copy per explicit undo adds O(facts + bounded undo) peak memory. It does not add per-observation accumulated quadratic history or change the persisted format. Snapshot allocation happens before mutation; move restoration avoids another map allocation after IO. The existing complete-store serialization is already O(facts), but this is not constant-space and should not be described as such.

The planned run qualifies actual normal-helper Linux UnixRPC behavior with operator-entered synthetic facts, not wallets, real chain state, signing/funding, Windows, power loss, arbitrary post-commit exception retries or full-suite/release acceptance. A cross-store crash window remains between bounty commit and shared-journal delivery; no durable outbox is added. Publication stays held.
