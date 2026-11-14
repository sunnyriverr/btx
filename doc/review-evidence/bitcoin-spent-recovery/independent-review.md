# Independent review — restored Bitcoin history candidate

Reviewer: `/root/history_recovery_review`; 14 November 2026. Read-only source/evidence review; no builds, native runs, product edits or publication. Reviewed candidate product hashes in repair-receipt.json and verified all three against the reserved repair files. Candidate executed in fork CI f8e0a05193643bd716e2fcfe7031f42b49df2866 on base d7b9594b; final extra marker-fault test is later test-only evidence, not the native tree.

## Verdict

No concrete newly introduced product blocker established for the bounded, **valid-deadline-window, newly restored Bitcoin-session** repeat-payment repair. Do not describe this as general backup recovery qualification. The late-restore limitation below and documented legacy/history-size limits remain. Tighten targeted test oracles and add the missing matching controls before proposing a general recovery guarantee. This is an independent code/evidence review, not independent platform verification or an ACK of all #630.

## Source conclusions

- Matching uses decoded transaction txid plus exact agreement HTLC script and atom amount; row address/label/category alone is not accepted. The script binds hashlock, keys and deadline through the existing terms. Distinct `(txid,vout)` matches are rejected; row repeats and overlaps between signer/watch/live lookup are deduplicated.
- A unique historical reference returns no raw funding bytes, preventing the coordinator from recording/rebroadcasting an old spent funding transaction as a new spend operation. The normal observer/state machine subsequently handles original claim/preimage; native evidence ends in `secret_exposed`, not a fabricated whole-swap `complete`.
- Missing/error/malformed, conflict/abandonment, unfinished bounded pages, rescan, count change and tip change refuse the lookup; it never returns a negative that authorises fresh funding on marked Bitcoin sessions. Pending candidates require mempool lookup. Normal fresh sessions skip historical scan; signed funding WAL is checked first and bypasses it.
- Restore marks every imported negotiation in staged SQLite, after existing integrity/audit/vault checks and before copying destination files. Marker-write failure occurs before destination publication; Store.close checkpoints the staged WAL. Existing signed WAL/reference paths are not replaced. Settings are local DB state, not a peer-supplied permission.
- Unreferenced marked restores with a visible unspent candidate but unreadable history now refuse conservatively; this prevents a visible newer output concealing an older spent payment. It is a deliberate behaviour change, not preservation of every old unreferenced fallback. Existing signed-WAL/reference recovery remains distinct.

## Scope issue: aged/matured restores are not qualified

History lookup is invoked only from coordinator._prepare. `machine.decide` validates remaining deadlines before returning a preparation action for a committed initiator with no original reference. Therefore a sufficiently old backup whose original funding/refund is already beyond that window can fail `UNSAFE_TIMEOUT` before any historical lookup. This is inherited from the existing adoption path, not a newly introduced regression. The current scanner can identify historical refund data but that alone does not show the restored coordinator can reach it after maturity.

Minimal bounded follow-up: build a marked committed-state restore with retained canonical historical original/refund, clocks beyond the long-leg deadline; verify whether tick reaches the history RPC or fails the deadline check. No fresh funding is needed to establish the control. Either keep the handoff explicitly scoped to valid-window repeat-payment prevention, or separately design late-state restoration that recovers factual history without weakening funding/deadline authorisation. Never solve this by bypassing normal checks for new spending.

## Test qualification improvements

1. Pin expected refusal codes. The four restored-history safety cases currently catch any `SwapError`; unrelated refusal could satisfy them. Expected current candidate results are missing RPC → CHAIN_RPC, cap/truncation → FUNDING_LOOKUP, distinct history matches → FUNDING_AMBIGUOUS, complete empty history → RECOVERY_UNRESOLVED. The success/native controls help, but exact codes make each advertised boundary meaningful.
2. Add exact matching controls not present in the new harness: repeated history rows for the same outpoint still adopt once; wrong script/amount never adopt; two matching outputs of one transaction count as ambiguity; matching historical output plus distinct live output is ambiguous. These directly challenge selection rather than repeat ordinary full swaps.
3. Pending/dropped and abandoned candidate controls would qualify the unexecuted historical branch: positive mempool lookup permits reference adoption, missing mempool entry refuses, abandoned/conflicted matching funding refuses. This remains component verification until a native endpoint is run.
4. Repeat restore/reopen marker durability and fresh-session-after-restore control would establish that imported sessions stay fenced while newly created sessions remain eligible. Existing fresh and WAL tests are useful but are separate from that migration lifecycle.

## Accepted limits, not additional defects found

- 1000 history rows per wallet is a refusal bound; there is no large-wallet continuation. Exactly at the boundary may conservatively refuse because no terminating short page was read.
- `txcount`/rescan state and chain-tip stability are not an atomic global wallet snapshot. Static native history works; do not claim arbitrary concurrent wallet metadata/reorg safety.
- Previously restored unmarked directories are not retroactively identifiable; reimport is required. Old format/schema is not silently inferred as restored.
- Native candidate verification is Core30.4 actual BTC with simulated BTX; no native Core32.1 failure injection, package or full two-chain qualification.
- History completeness depends on retained selected wallets. A missing match in those wallets does not prove no original payment existed; the marker correctly refuses fresh funding on that result.

## Recommended next step

Tighten the four error-code assertions and execute only the new matching/pending/restore-lifecycle controls needed to close these review gaps. Record the aged-restore limitation explicitly or qualify its factual-history path separately. Reuse native before/after and183 existing passes; no new broad build or repeat full suite justified by this source review alone. No upstream post authorised.
