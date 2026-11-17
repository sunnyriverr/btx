# Independent production repair review — 17 November 2026

**Verdict: no production-code blocker found in the supplied three-file candidate.** Read FIX-SCOPE.md, DESIGN-REVIEW.md and the exact baseline/candidate diffs for journal.py, coordinator.py and application.py. This is source review only: no product import/execution, tests, builds, network, code edits or publication. Qualification results belong to the parent's separate test receipts.

## Scheduling and terminal recovery

`candidate/swapnet/journal.py:230–238` applies eligibility before selection and decodes at most four rows per call. The `id > after` and wrap `id <= after` ranges are disjoint, so a sparse population cannot duplicate a selected session within one call. Filling the remaining allowance from the wrap range preserves cyclic traversal without a fixed eligible prefix. Both active rows and complete/refunded rows beyond4096 remain reachable; cancelled/rejected history cannot consume these selections.

`candidate/swapnet/coordinator.py:25,559–575` supplies independent string keyset cursors, selects at most four active sessions and adds at most one due terminal watch. Cursor advancement happens before dispatch just as the prior index cursor advanced before dispatch. A failed individual tick therefore does not pin the selector at that row. A removed or stage-changed cursor row does not need to exist for the next `>` query/wrap to work. A terminal session reopened as reconciling becomes eligible for the active selector; an active session made terminal becomes eligible for terminal rotation. These are eventual-reachability arguments for finite eligible populations, not strict fairness guarantees under continual adversarial insertion/churn.

Terminal cadence remains independent of active count and unsigned history: `_terminal_due` changes only when a terminal row is actually selected at a due tick. New terminal work can be selected immediately when no prior terminal row existed, matching the former behavior. Terminal selection does not consume the four-active allowance. Restart resets both cursors and due time as before; this repair does not promise preservation of cursor progress across repeated restarts. The terminal stage set and cancelled/rejected exclusion match existing semantics; funding, decision, refund, secret exposure, accounting and reorg transition logic are untouched.

The required tests should distinguish this implementation from filtered4096-only selection, exercise wrap with fewer than four active rows and multiple larger populations, stage changes, complete/refunded rotation and due/not-due behavior. These are the existing scoped qualification needs, not additional expensive gates.

## Active-asset guard

`candidate/swapnet/journal.py:239–249` streams all SQL-active bodies in batches of64, with neither the public512 limit nor an assumed128/4096 correctness cap. It preserves the long-leg/short-leg exact asset comparison. JSON/body errors remain unsuppressed; they cannot silently authorize reconfiguration. The store lock covers the cursor scan and is released on return before provider factory/readiness IO. The new query relies on the same stage-column/body-stage invariant maintained by Journal.save and terminal closeout; no new arbitrary corrupted-store compatibility claim is needed.

`candidate/swapnet/application.py:344–350` preserves owner and factory-availability gates and refuses ASSET_BUSY before factory, readiness, driver-map replacement and policy persistence. The unrelated publish-before-persist durability issue is unchanged and outside this repair. No requirement to redesign that separate campaign is introduced here.

## Event ownership and privacy

`candidate/swapnet/application.py:363–371` fetches exactly the prior bounded global audit page, decodes it once, and retains ordering, digests and next_sequence from the last raw row. It neither fills filtered pages by scanning extra events nor changes continuation to the last visible row. Owner view still sees every event in that raw page.

`candidate/swapnet/journal.py:250–257` resolves only string IDs referenced by that page against the requested principal; it does not decode financial bodies or infer ownership through operation/mandate joins. There are at most500 distinct ID parameters plus one principal parameter, within the traditional999-variable SQLite bound. Empty ID sets avoid an empty IN query. IDs/principal are bound values; only fixed stage predicates and generated placeholders enter SQL syntax.

Both collection and filtering preserve the exact `body.get('swap_id', body.get('id'))` rule. Explicit None/empty swap_id therefore does not fall back to id. An owned fallback id cannot expose another-principal swap_id event. The exact-string prefilter is defensive handling of referenced IDs and preserves generated JSON event semantics; this review does not promise compatibility with arbitrary malformed/unhashable event references, which the existing membership path already did not support.

## Scope and conclusion

Public Journal.all remains byte-for-byte unchanged in the displayed diff, including its default512 and maximum4096 display-page behavior. No schema, migration, deletion, capacity increase, signing, authority or accounting change is present. The three internal readers share one completeness problem and form a coherent repair unit.

Proceed with the parent's already scoped before/after and legitimate-control qualification. No source blocker requires a native rebuild, full settlement rerun, extra platform gate or resumption of held investigations. This review does not substitute for execution evidence or independently establish a native financial/release result.
