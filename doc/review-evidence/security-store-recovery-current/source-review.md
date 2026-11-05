# Final bounded source and fixture review

**PASS for the scoped component repair. No concrete correctness or acceptance blocker found.** This is source/fixture/artifact review by delegated agent `/root/current_store_acceptance_review` for Session 2, 5 November 2026; it is not a second native execution. The reviewer changed only this report and ran no build, product test, ref/network/VM/publication action.

Reviewed isolated `implementation/source` at Git HEAD `e9c1e364262543a3a7543885e55fd6c2849bf1c0`, its product/CMake diff and untracked maintained test, `implementation/run.py`, source-assembly manifest, execution record, baseline/candidate logs and CTest `LastTest.log`. At review time the execution record was complete.

## Product preservation

The product diff has the intended small footprint: existing Database writer delegates to the same body with the ordinary limit; the new trusted control writer guards policy/revocation kinds and selects a fixed absolute 16,513-object ceiling. Ordinary new IDs still use 16,384. Duplicate signature merge/limit, body integrity, visibility handling and insert logic remain the existing implementation. No schema, pruning or retention change appears.

Only authenticated `InstallPolicy` and revocation in shared `StoreImport` receive the privileged writer. Existing root/owner/epoch/realm/freshness checks, transaction boundaries, metadata, tombstones, prepared-permit invalidation, clock and journal remain in place. The helper declaration explicitly documents authentication and enclosing-transaction obligations. The accepted SQLite load-extension portability guard is retained.

An exact extraction comparison confirmed the entire `ImportCurrentEvidence` function is byte-identical to accepted source. Receipt/evaluation restriction, serialized policy load and expected-ID check, `ValidateImport`, observational release callback, fresh commit sampling, both freshness rechecks, store and commit are preserved. `StoreImport` routes every non-revocation kind to ordinary `Put`. This does not change the explicit-time `ImportRecord` validation-before-transaction contract or establish a new concurrent-authority guarantee.

## Fixture and observed result

The maintained regression directly calls the current live-evidence API with genuinely signed local receipt/evaluation envelopes. The small fixture supplies valid root pins, roles, policy limits and field shapes; normal imports use fresh time without the historical future-clock advance. Bulk unsigned rows construct only the quota count. Evaluation construction has no hidden receipt import. Each quota probe changes a body field and asserts its ID is absent.

Exact-error and callback-count checks distinguish current-policy, binding, role/signature-threshold, initial expiry, record revocation, release denial and quota paths. Evidence-expiry-at-commit is exercised for both kinds; separate policy expiry keeps the evidence fresh. The callback confirms initial freshness before observing time pass and performs no database mutation. Refusals compare complete paginated table snapshots, including clock/meta and journal, avoiding the per-query row limit above the ordinary cap.

Baseline log shows three PASS and precisely the two recovery cases failing with `SEC_OBJECT_QUOTA`. Candidate CTest raw output shows all five named cases PASS; its process exit and CTest result are zero. The same regression SHA-256 is recorded and still matches the reviewed file. Recorded command-log hashes and baseline/candidate binary hashes match retained files.

The before/after repair observations are exact-cap policy installation and peer-flag revocation through production authority entry points. Candidate checks policy ID/epoch, authoritative revocation, counts and journal; both live evidence kinds are refused with ordinary quota at the cap and after the revocation enters the tail. Baseline's revocation case necessarily stops at its failed recovery write: assertions after that point are candidate-only execution, not paired baseline passes.

`run.py` builds the maintained component target from a selected accepted-source/dependency snapshot, using native Apple clang 17 on arm64 and the selected Homebrew SQLite. Baseline starts a fresh component build; candidate rebuilds affected current components within that build. No historical fd3 objects are reused. It runs only the new CTest target, and records bounded resource checks and empty owned runtime afterward.

## Claim limits and closeout

The evidence supports a coherent current macOS component fail-before/pass-after plus the new serialized live-evidence routing controls. It does not newly execute prepared-permit invalidation, finite-tail exhaustion, duplicate union/privacy, retained negative evidence, last-slot contention or injected late-write failure: those remain unchanged-source review plus the separately attributed historical fd3 evidence. The current test's referenced hashes are valid at this import boundary; it does not qualify a completed worker run, capsule admission or real physical-host independence.

Do not describe this as a clean full root/node build, full maintained suite, service/guard restart, mesh exchange, physical disk-full recovery, native Linux/Windows or release qualification. The 129 rows remain finite shared headroom, with no reset, reclamation or local-priority guarantee. Source and evidence are ready for the owner's scoped local closeout; publication authority remains the parent's responsibility.

Reviewed source SHA-256 identities:

| File | SHA-256 |
| --- | --- |
| database.cpp | `08947892fecfe2b27b3fc336c3674ee0250b2038e7f5fe0e43b0a84ee07f811c` |
| database.h | `1658b1e07cb6b129feeae7091685d1a6a99eacb0e9c170dcda072b811b40b143` |
| trust.cpp | `a5ca26e787b9582d492137fab0cd25c728b1f06d1ee0e5087898f9414312cd83` |
| full_store_recovery_tests.cpp | `8b172e71f87d7f307836b235c087e3c69635ed901248a0a80a8eeeb708094c41` |
| test CMakeLists.txt | `fbd7fadc4bc6e09dc4feee008bdb2709368a67d5c344ca1f7ff3c5f1551e671e` |
| run.py | `7873515e088f2846b9217a33b8456877e5e3f13daae03a154b773ecd3909e7d9` |
