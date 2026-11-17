# Independent final evidence review — initial proposal retry

**Verdict: the original 28-case candidate evidence is credible for its stated scope, but one material design miss requires correction before final handoff.** This is an internal read-only source/evidence audit. I ran no tests, builds, network requests or native process, changed no product/test source, and performed no posting. This report is my only written output.

## Material finding: conflicting stored recipient is excluded from lookup

`Journal.has_proposal` selects only rows with SQL `recipient` equal to the saved peer. A same-session `swterms` proposal stored under a different SQL recipient is therefore never inspected. With no expected-recipient row, the helper treats it as a missing first send and emits a fresh envelope instead of refusing the conflicting local routing state. This violates the DESIGN requirement to refuse a same-session conflicting recipient. The envelope-recipient check cannot catch a row that the SQL predicate already excluded.

The existing conflict test changes payload nonce under the expected SQL recipient. It proves payload refusal, but does not cover this missing routing conflict. Required correction: inspect all proposal-command rows for the session and validate both stored routing recipient and envelope recipient against the saved peer, plus the frozen payload; add explicit controls for stored-recipient and envelope-recipient conflicts. Include a conflicting row alongside an exact row to preserve the requirement that all matching rows are checked before accepting deduplication. The parent acknowledged this finding and owns the correction and new executed evidence; those changes are not reviewed or qualified by this original report.

No additional material defect was identified in the reviewed coordinator changes. The prior source review's claim that all conflicting recipients are covered must be narrowed until this finding is resolved.

## Before/after evidence and identities

Both recorded executions use `run_repair.py`, which imports Application/Journal/Coordinator from the selected baseline or candidate tree, disables automatic pytest plugins, and passes the same final candidate test file to pytest. The two missing-first-send cases fail on stock at the intended observation: line 84 expects exactly one recovered proposal in outbox but finds zero. They reach the call phase after the injected first INSERT failure, fault removal, retained original intent, and explicit accept or clean-reopen resume. These are intended behavior failures, not setup failures. Baseline log: **2 failed, 26 deselected**; it is not a complete stock 28-case run.

Candidate log: **28 passed in 2.32 seconds**, exit 0. The candidate JSON has 28 passed call reports, no failed/setup-error/skip reports, matching the log. Thus zero skips is supported for these selected candidate tests. Baseline and candidate receipts pin identical test SHA-256 `ce73f1c18ca676b6d921b9e4e75acbfb88cc1efd925d3857f6e1c5a916c38a2f`; my read-only file hashing matched it. Both record Python 3.12.14 / Clang 22.1.3 and base source `bd847e2b986722c1723b4cd60988d4f4908452d4`. That source field is the base reference, not a claim that candidate modified files equal the base.

Loaded paths in both receipts are under their correct `repair/baseline/swapnet` or `repair/candidate/swapnet` trees. Independently rehashed files match every recorded loaded SHA-256:

| Module | Baseline | Candidate |
| --- | --- | --- |
| application | c9ae1468e023e0c01c011d0efddca523a2f8ced6f58a0755f589522a1ba14b61 | same |
| coordinator | eefe306dc12f57148206d7e543e23b6717237297d1a620016fd5b7a58ef2deae | de3265918f02078cf12e5ca75310797029f822c844a5c8d681bb4d1b022a6091 |
| journal | 9770efe61fc7f43e007c9605774cff0d8016c7a72fd107323a7de6c75b9d85f2 | 0795f0f59c6717c2e3d42c1db58c7261feec309829e32d9f7f5d1f0345b59aa5 |

The runner explicitly asserts those three loaded modules resolve inside the selected tree. It does not inventory/hash every transitive module at execution time. The imported support fixtures `test_runtime_recovery_v2.py` and `test_execution_v2.py` are byte-identical between the two trees on this audit (SHA-256 `47390e0e53f1d9861621be5f68819c1c75b2fcb8f2004dad167c9c25ab425549` and `b8e93f71cd261a7c0b12cd8cbba091a5693cf5ba5b9a84adbfed939e0caa8b6d`). The evidence supports the same harness comparison with specifically recorded loaded product identities; it is not a complete dependency provenance manifest.

## Controls assessed

- Successful accept retry and clean Application reopen/resume preserve snapshot equality across sid, proposal hash, keys, vault entries, reservation ids/states, held/used totals, claimed quote and operation count. Guards make fresh key, secret, deadline or session creation fail immediately. Delivery then completes both sessions with exactly one simulated funding record per leg. This is a legitimate progress control, beyond merely observing an outbox row.
- Normal, future-due, acknowledged and beyond-page existing proposal cases exercise accept and resume with signing forbidden and packet ids/sequences unchanged. Post-enqueue lost caller reply followed by clean reopen also retains the exact original packet. Those partial-progress controls are credible, subject to the recipient-conflict finding above.
- Repeated INSERT failure and envelope signer refusal preserve the saved intent and permit later successful delivery. These are injected application persistence/signing failures; no physical disk-full event was executed. Repeated-failure cases use accept; clean reopen/resume is separately proved, and both entry points share the same helper. Do not describe repeated resume-enqueue failure as a separately executed case.
- Changed mandate/fee inputs refuse on the missing-send path. Revoked/expired mandate, closed reservation, restored marker, observation-only recovery facts and prepared state each refuse without packets or simulated funding. Wrong-principal resume refuses; an existing owner can resume using the saved principal's fully held budget, without a second reservation.
- Original quote expiry causes no send or deadline replacement; late resume retains cancellation and releases the hold. Mature/too-late/stale simulated clocks trigger the expected safety errors with snapshot equality. Cancel after failed retry closes the original reservation and releases the hold once across repeated cancellation.

Authority mismatch combinations, all financial flags, changed RFQ, direct grant-table presence and all refund behavior are not individually executed here. The shared helper checks and unchanged financial paths support the bounded design, but the 28-case result should not be represented as exhaustive authority, refund or concurrency qualification. The new recipient control is materially necessary because it exposes a concrete source gap, rather than merely increasing counts.

## Claim boundary and next action

The reviewed execution uses real Mac Python Application/Coordinator/Journal/SQLite and vault persistence with Ed25519 fixture packet signatures. Chains, transaction construction/signing, clocks, transport and wallet identity callbacks are test fixtures. Clean `Application` reconstruction on saved SQLite/vault files is proved; **no native btxd restart**, native funded chains/PQ signing, full build, full suite, platform matrix or release qualification is proved.

Preserve the original 28-case receipt. Resolve the routing-conflict finding, demonstrate its intended pre-fix refusal failure and post-fix pass, rerun the affected candidate regression after the product/test changes with updated hashes, and obtain a focused delta review. Final publication/handoff remains with the task owner under existing user authority; this internal report itself grants none.

## Superseding final delta review — corrected routing guard

**Updated verdict: the material recipient-conflict finding is resolved; no blocking defect remains identified in this bounded internal review.** This supersedes the earlier pending-correction verdict, not its scope limits or evidence history. This delta review read the corrected Journal/test source, new baseline/candidate and conflict-before logs/results, qualification receipt and patch identity. I executed no tests, builds or network work and made no source edits.

The corrected query reads `recipient,body` from all `swterms` outbox rows. It selects same-session proposal bodies in Python, requires both the SQL recipient and envelope recipient to equal the saved peer, and requires the frozen payload. It sets a found flag rather than returning on the first exact row, so later conflicting rows still refuse. This closes the identified source hole while preserving acknowledged/not-due/beyond-page scanning and live-envelope deduplication. Scanning all command rows uses the existing decoding and storage model without a migration.

The new conflict regression independently covers payload, stored SQL recipient and envelope recipient changes. With the previous Journal hash `0795f0f59c6717c2e3d42c1db58c7261feec309829e32d9f7f5d1f0345b59aa5`, `conflict-before.log` and `conflict-before-results.json` record **1 failed, 2 passed, 27 deselected**. The sole failure is exactly the intended stored-recipient observation: expected `RECOVERY_CONFLICT` did not raise. The new final run records all three conflict variants passing, with snapshot and outbox-id equality after refusal. A simultaneous exact-plus-conflicting-row scenario is established by the corrected no-early-return source inspection, not by a separately executed case.

The final matched harness SHA-256 is `e76abc5870223306f531870f8c771f713c3f9270528d584f15e2a2cb69e42201` for both stock and candidate. Final stock still fails only the two selected missing-first-send accept/resume cases at the intended outbox assertion (**2 failed, 28 deselected**). Final candidate log and per-case receipt agree on **30 passed in 2.39 seconds, exit 0, zero skips or setup errors**. Original 28-case and stock evidence remains preserved as `v1-*` files.

Read-only hashes match the qualification receipt: coordinator remains `de3265918f02078cf12e5ca75310797029f822c844a5c8d681bb4d1b022a6091`; corrected Journal is `059e21a05a730aedec0bd3ca6058381a326911742c037c9660c62c720d51af0b`; the maintained test is the final harness hash above. Loaded Application remains unchanged at `c9ae1468e023e0c01c011d0efddca523a2f8ced6f58a0755f589522a1ba14b61`, and loaded paths remain under the selected source trees. The final `repair/candidate.patch` hash is `3877cf3cd9c58a3024750c5669776e0419202c790852e759e20fc8f4799a69f5`. The parent reports a successful reverse-apply check; this reviewer did not independently execute it.

The existing funding, authority, deadline, cancellation, original-intent and partial-progress assessments above apply to the final 30-case result, with the recipient finding now closed. This supports internal handoff of the narrow explicit retry correction within existing authority. It remains real Mac Application/SQLite qualification with simulated chains/signers/transport and clean Application reopen, not native btxd restart, native funded-chain/PQ, full-suite or release qualification. No publication was performed by this review.
