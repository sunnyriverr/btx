# Independent receive-side repair evidence review

**Verdict: the supplied matched evidence establishes the narrow false-ACK repair, legacy valid-replay recovery, receipt-backed deduplication, and simulated refund safety. No product correctness blocker was found in this evidence audit. Complete the claim reconciliation below before the final local handoff.** Read-only review; no product/test execution, network, edits outside this report, or publication.

## Matched source and test attribution

Both baseline-results.json and candidate-results.json record identical maintained regression SHA-256 `04d4580f99a49b4ae3acb3dcc45586f1e1d25083739cac3f22039d9683b92fa4`; it matches the file read for this review. The baseline selected eight functional cases from this exact file; candidate ran all twenty. The baseline eight node IDs are a subset of the twenty candidate IDs. They use Python3.12.14 and the same installed pure-Python pytest path recipe. Runner preloads the selected Application/Journal/Coordinator before pytest, sets separate baseline/candidate source and fixture paths, and records/guards the actual loaded module paths and hashes.

Baseline application/journal hashes match the pinned bd847 source receipt; candidate changes those two modules, while Coordinator hash remains identical. Baseline is **5 failures / 3 passes**, with failures at intended call-phase behavior assertions rather than fixture setup, missing APIs, import or collection errors. Candidate is **20 passes / zero skips**, with no reported setup/teardown failure. The eight functional cases therefore have a genuine matched before/after observation; the twelve new-storage/refusal controls do not need to be falsely represented as independently failing on the old missing-API implementation.

## What the assertions actually establish

- Four actual fork-child cuts exercise admission-before-handler, grant-before-session-save, saved-session-before-receipt, and completed-receipt-before-ACK. The parent closes the old maker Store first; child reopens the same SQLite path, reaches the selected production operation, exits73, and parent joins/reopens with stable fixture identity. The before-ACK cut fails if processing runs again after reopen. These are actual abrupt child exits at selected deterministic boundaries, not an external native btxd/power-loss qualification.
- Valid replay reaches committed, records an ACK for the exact original digest and eventually marks the original sender outbox row acknowledged. Healthy settlement produces one funding record per leg. A product that simply ACKs without applying the original commitment fails the admission/grant/legacy-unprocessed assertions.
- Legacy handling drops the supplementary receipt table while retaining the two-column inbox, reinitializes Journal, then reopens the receiver. Unprocessed old markers reapply; already-applied old markers undergo one guarded revalidation. A second duplicate skips processing. This does not prove proactive reconstruction of an already-retired sender packet, which the design correctly excludes.
- Ordinary caught handler error removes admission and withholds ACK; completion-insert SQL-trigger failure also withholds ACK and permits a subsequent retry. ACK error is after durable completion: retry skips handler effects, records ACK and settles.
- Invalid signature/network/expiry/changed agreement/sender are rejected with unchanged grant/reservation-count/budget observations; pending revoked/expired authority and cancelled/rejected sessions do not gain completion or ACK. Envelope validation remains before the duplicate shortcut in the inspected product code.
- The capacity test checks foreign_keys enabled, retains legacy two-column insertion, refuses an additional8193rd admission, allows a duplicate inside the bound, refuses completion without a parent, and proves expiry/forget cascade cleanup with no FK violations.
- The recovered-commit refund control withholds the maker while scheduling only the initiator. Early explicit refund is refused, original output remains locked, maturity refunds the original funding, confirmations produce refunded, and original funding bytes plus stored refund txid/raw remain unchanged. No second funding, counterparty funding or exposed secret is observed.

## Claim reconciliation before final handoff

1. **The five baseline failures are not five separate financial defects.** `legacy[True]` fails on the new one-time revalidation contract for an already-applied legacy message; the baseline already avoids repeated effects there. State the aggregate as test outcomes, not a five-bug count.
2. **The new refund baseline case stops at unapplied legacy commitment.** Its before/after failure shows the recovery precondition changed, not a baseline broken refund. The earlier pilot already demonstrated stock original-refund survival; reuse it explicitly rather than claim this one case showed an unsafe refund before the patch.
3. **Exact IDs versus counts:** `counts()` captures grant/reservation counts and held/used totals. The restart/replay tests do not snapshot exact grant/reservation IDs or stored bodies. Coordinator is unchanged and deterministic-grant logic supports the design, but a public claim that the tests verified every exact grant/reservation identity would exceed these assertions. Either retain the accurate no-additional-count/budget claim and label exact-ID preservation as source reasoning, or strengthen only the relevant identity assertions before claiming that specific execution acceptance item. No unrelated test expansion is needed.

The current candidate result and test hash apply to the file reviewed here. If assertions change to settle item3, update the execution receipt and matched identity before final handoff; this review is a dated audit rather than automatic endorsement of later bytes.

## Scope

Real Mac Application/Journal/SQLite, packet validation and actual child exits; deterministic fixture transport, chain drivers, ledger transactions and Ed25519 test identities/signing. Not native BTX/BTC HTLC funding/refund or native PQ keys, C++ embedded worker lifecycle, public chain, Linux/Windows, whole suite or release qualification. The narrow correction covers `commit`; other receive kinds and historical false-ACK packets with no remaining replay are not silently qualified. Independent audit is not another execution run.

The parent’s separately planned focused recovery-bundle compatibility checks are reasonable for an additive SQLite table. They should stay distinct from this twenty-case result and should not become a full release/platform matrix.

## Final assertion-strengthening addendum

**The exact grant/reservation identity claim gap is resolved for the affected replay checks. No evidence blocker remains at this scoped handoff.** Read-only follow-up review of the updated test and saved results; no new execution by this reviewer.

The final maintained test SHA-256 is `e6bac54a084ed312e90ab4ac49d34d1808e84ea30d3cddded17ac4f2f2c7cf5d`. Updated baseline-results.json and candidate-results.json both record that exact hash, which matches the current file. The baseline still has the same eight cases and intended **5 failures / 3 passes**. Final candidate execution has **19 passes / 1 deselected**, zero skips. Candidate Application/Journal/Coordinator hashes are unchanged from the initial reviewed implementation.

`counts()` now includes ordered grant IDs and reservation IDs. Actual-exit replay checks explicitly preserve reservation IDs and any grant already persisted at the selected cut. Legacy replay checks explicitly preserve reservation IDs and, for previously applied legacy messages, the pre-existing grant IDs. Existing complete-tuple checks in completion/ACK errors and refusal controls now include these IDs too. These assertions supplement count/budget preservation without changing product behavior or authority policy.

The capacity/expiry case was deliberately not rerun. Its function AST is identical between initial-test.py and the final maintained test, and it does not call the strengthened counts helper. initial-candidate-results.json records its earlier PASS on the same unchanged candidate Application/Journal bytes. That is valid targeted reuse. Describe the combined result as **20 unique new regression cases qualified: 19 on the final assertion revision plus one unchanged capacity/expiry result reused**, not as a fresh twenty-case final run.

restore-results.json separately records four passed cases with the same candidate loaded module hashes; restore.log agrees: encrypted recovery roundtrip, wrong-password/network/nonempty refusal, documented restore command and refusal-before-writing. These are targeted existing bundle/tool compatibility controls, not a whole-suite or platform qualification.

The first two claim qualifications above remain applicable: five baseline test failures are not five independent bugs, and the prior stock pilot—not the blocked new recovery precondition—supplies stock original-refund survival. All native/simulated, legacy-no-replay and other-handler scope limits remain unchanged.
