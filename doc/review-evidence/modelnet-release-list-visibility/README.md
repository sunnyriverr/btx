# Release-list visibility: tested follow-up to #853

**Verdict:** the same maintained regression fails in four intended places on repch1c's exact #853 and passes with three additional filters. The real helper changes from eight hidden-model listing violations to zero across normal restart; unaffected models, unhide, direct lookup and campaign state are preserved.

## Code and prerequisite

- Prerequisite: [repch1c's #853](https://github.com/btxchain/btx/pull/853), exact original commit `ea79c62407d04b6b37e55d8121c463cb13aadb7c`, retained unchanged.
- Follow-up: `3ad745734a7cd161a87b3e78d139b14db6cf53ac`. [Only our follow-up diff](https://github.com/sunnyriverr/btx/compare/ea79c62407d04b6b37e55d8121c463cb13aadb7c...3ad745734a7cd161a87b3e78d139b14db6cf53ac).
- Own production change: three calls to #853's unchanged `FeedHidesModel`, for LOCAL `getrecentreleases`, `getfundablemodels` and `getrecentlyunlockedmodels`. The maintained regression is `modelnet_economy_tests/release_lists_respect_local_hide_without_changing_campaigns`.
- Existing locks, campaign sorting/limits, feed cursor, direct-by-ID lookup and stored campaigns remain unchanged. Original #853 attribution and tests belong to repch1c; our commit also credits the reused fixture/predicate work.

## Actual execution

[Run 44235389425](https://github.com/sunnyriverr/btx/actions/runs/44235389425), [immutable recipe 9b8423b6](https://github.com/sunnyriverr/btx/tree/9b8423b62868904a525ac86769a43d168319badb/proposal). Linux x86_64, Ubuntu 22.04 container on Ubuntu 24.04 runner, GCC 11.4, OpenSSL 3.5.9. Compiled normal `btx-modeld` and a qualification-only executable containing the complete maintained economy test translation unit, normal test main and support libraries. It is not aggregate `test_btx`.

Executed in both phases:

```text
gui-pilot-runtime/qtbuild/bin/s2_visibility_tests --run_test=modelnet_economy_tests/release_lists_respect_local_hide_without_changing_campaigns --log_level=test_suite --report_level=detailed
python3 -B proposal/observe.py --helper <that phase's btx-modeld> --sha256 <recorded binary hash> --out records/<phase>-native
```

The native fixture and maintained test are identical between phases; only the three helper filters differ. [Exact commands and identities](attempt2/records/qualification.json), [own source diff](candidate.patch), [source hashes](changes.json).

| Check | #853 baseline | Follow-up |
|---|---|---|
| Maintained new regression | Exit 201, exactly four hidden-target failures | Exit 0 |
| Actual helper, hide then normal restart | Eight listing violations | Zero violations |
| Unrelated models, search, unhide, direct-ID, unchanged campaign file | Pass | Pass |
| Helper starts/shutdowns | Two clean exits | Two clean exits |
| Full focused economy suite | Not run | 26 cases / 577 assertions pass, exit 0 |

The focused suite includes #853's original feed hide/mute case and existing cursor, query/limit, card and funding-view controls. [Baseline native result](attempt2/records/baseline-native/result.json), [candidate native result](attempt2/records/candidate-native/result.json), [raw suite report](attempt2/records/candidate-economy-suite.log).

## Failed job badge and offline validation

The GitHub job **remains failed**. All product commands above completed as expected, then the wrapper looked for the short `No errors detected` banner despite requesting Boost's detailed report. The saved report explicitly gives 26/26 cases and 577/577 assertions passed. Original `qualification.json.complete=false` is preserved.

The [offline validator receipt](suite-offline-receipt.json) verifies exact entered/left/passed case sets and detailed totals, and rejects failed exits, real assertion errors, missing cases or reports, duplicates and wrong totals. Eleven offline controls passed; **no native/unit rerun or raw-log modification**. Recheck from this evidence directory with:

```text
python3 -B -m unittest discover -s . -p test_detailed_suite.py
```

An earlier preparation run [44234661846](https://github.com/sunnyriverr/btx/actions/runs/44234661846) stopped before compilation or product tests: a nested-workspace patch command skipped the #853 prerequisite. Exact GitHub blob/postimage verification corrected that input before the paired run. It is a preparation failure, not evidence about BTX behavior.

## Scope and retention

No actual Qt/Atlas window, full node, aggregate `test_btx`, native macOS/Windows, WAN or release qualification. New-reader distinct-publisher muting was not executed; the existing #853 mute case passed within its own scope. No wallet/funding transaction was involved; model-plane fixture disclosures only.

Tested source is exact #853 plus the follow-up, based on `23ee567e`. Current release `a97af7b3` has no relevant ModelNet source changes; that applicability is source-reviewed, not a fresh full current-tree build. Qualified binaries, raw records and updated checkpoint are retained through 2 December: [artifact metadata](qualified-artifacts.json). Large binary/checkpoint archives were not downloaded locally; raw evidence archive was downloaded and digest-verified. The checkpoint preserves `qualification_complete=false` from the original wrapper; this offline audit does not rewrite producer history.

[Qualification snapshot and exact binary hashes](RESULT.json), [raw evidence hashes](evidence-sha256.json), [executed payload hashes](attempt2-qualification-preparation.json), and [full evidence manifest](manifest.json). No implication of independent human ACK or additional platform execution.
