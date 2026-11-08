# Four-fixture continuation — independent raw review

**Full maintained candidate build passes; units have failures and remain incomplete.** The four previously failing objects compile under unchanged generated commands, and all seven maintained executables link. Actual bounded execution produces 424 passing jobs, 20 failed jobs and one timed-out job. This does not close #356 or establish stock-source/release acceptance.

Reviewer: Session 1 delegated child `current_windows_plan_review`, 7 November 2026. Read-only raw ZIP/XML/source/checkpoint comparison; no API, build, test execution or product/peer mutation by this reviewer.

## Build, source and checkpoint

- Independently recomputed archive SHA-256 `afbbf28e41074316ed272f27733f58900701188f6086c3ab8aa73fd21a98f28a`, 30417637 bytes. Run `42373148335`, CI `3bb1a9dff4559762ae76dd54a0197288950ee18e`.
- Rehashed all **466 recorded command logs**, configure diagnostics, current compile table/cache and observed manifest against native records. Actual ordinary root build exits 0 in **21.19 seconds**, without a budget stop. It compiles the four corrected objects, performs three expected metadata-object rebuilds, and links `btxd`, `btx-cli`, `btx-tx`, `btx-util`, `btx-open`, `btx-modeld`, and `test_btx`.
- Independently matched all 14318 source catalog paths/modes/blob IDs against immutable `70f1886f1028b4d78b5689f4fd2f80ba1d195d96`; seven current/full catalogs agree. The four selected working-byte hashes match actual candidate Git blobs. The candidate remains exactly the six declared fixture corrections on d522.
- All 5898 compile-table entries equal the failed parent run's entries, including all four failing targets. Those four inputs are absent in the 5881-object checkpoint, have real compile actions in the new log, and appear in the new checkpoint. This establishes actual fail-before/pass-after compiler evidence for the four corrected files; no flag/global CMake change manufactured success.
- New unit binary hash is `9792421107d90290c54ba02599a842d35b589048102f6124d6b643cfa229c3c2`, replacing old cached f13. Build metadata names exact 70f with `BUILD_GIT_DIRTY 0`; new imports, inventory and node version checks complete. Runtime is guarded by this new binary hash.
- Checkpoint SHA-256 independently recomputed as `06297cd121c4da71af90a3a69c2df0507a03f51d9df33dc8626a776c2a50e2ba`: **12838 files / 5885 objects**, exact 70f source/current configuration, captured after link and before units. Compared with the parent checkpoint: exactly four added object paths, zero removed, and only three existing metadata-object payloads changed.
- Owner cache metadata identifies successor `10162013501`, key ending `d52c34db...-42373148335`, size 487753754 bytes. This is saved metadata availability plus native checkpoint verification, not a remote payload redownload/rehash. Input caches are not overwritten by the workflow.

## Independently recomputed unit outcomes

Reparsed actual new-binary inventory independently: **15384 enabled unique cases**, covered by **2607 disjoint jobs**, with selector/case limits intact. Independently walked every available suite XML, checked reported identities and hashes, compared announced counts, and classified results against the selected case sets. No unexpected entered case or selected XML-skipped case was found.

| Observation | Count |
| --- | ---: |
| Jobs invoked | 445 |
| Passed / failed / timeout jobs | 424 / 20 / 1 |
| Selected and announced cases | 3449 |
| Selected cases with final non-skipped XML outcomes | 3429 |
| XML passed / aborted / failed cases | 3387 / 35 / 7 |
| Unique cases entered according to raw logs | 3445 |
| Enabled cases never selected | 11935 |

The 3387 case passes are derived from XML, including passed cases inside mixed-result failed jobs; they are not inferred from 424 passing jobs. Failed jobs remain failures, without an expected-failure exemption. The campaign runs **1778.16 seconds** and stops at its declared budget before selecting all jobs.

**Required wording correction:** native `unit_summary.unattempted_not_a_pass=11955` counts enabled cases **without a final XML outcome**, not 11955 wholly unattempted cases. It consists of 11935 never selected plus twenty selected by timeout job `suite-0444` (`matrict_adversarial_tests`). That job announced twenty, entered sixteen, left four unentered, and timed out after 121.22 seconds with an existing zero-byte XML file. None of those twenty receives a final XML PASS/FAIL claim. Raw-log entry count is 3445; final XML outcome count is 3429.

The timeout file's correct hash is SHA-256 of empty bytes, `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Correcting the offline verifier to distinguish an existing empty report from an absent report preserves the actual timeout; it does not change the native harness or justify a rerun.

## Controls, failures and limits

The initial real selector/XML control (`modelnet_native_http_tests`) passes both selected cases. Current WAN and AHP-comp suites pass all six cases each. AHP API and Journey each report seven passed cases and one aborted case: the raw failure is the existing `fs::exists(.../bin/btx-open)` check on the suffix-less definition, before the newly adapted Windows Spawn call. Thus the compiler repair passes, while these current end-to-end helper cases do not. The new native-helper/refusal cases in `swarm_confine_tests` and `swarm_fsjail_tests` are **not selected before the budget stops**, so this run supplies no current runtime result for them.

All twenty failed jobs and the timeout remain substantive recorded acceptance gaps; they are not twenty established product bugs. Owner classification may distinguish fixture/prerequisite failures from behavior defects, but it cannot relabel them passed. No repeat of the earlier 6250-case evidence was performed by this review.

Native finish verifies source, 6230 installed dependency files plus preserved OpenSSL identities, empty owned-process sets, removed runtime data and removed short-drive mapping. Every captured checkpoint file remains unchanged during units. These file-retention checks are runner measurements; this reviewer independently rehashed the archived checkpoint/records, not every remote cached object/dependency payload.

Verdict: **current six-fixture candidate full build PASS; bounded units FAILED AND INCOMPLETE**. Keep the new checkpoint and exact raw outcomes, correct the “unattempted” wording, and classify the existing failures before selecting further execution. No current full-unit PASS, stock-source acceptance, production/release qualification or publication approval follows.
