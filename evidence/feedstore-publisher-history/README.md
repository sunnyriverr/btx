# FeedStore publisher history — integrated qualification

**Three publisher-history regressions fail on the release baseline and pass with the fix.** Existing feed/paging controls, genuinely new publishers, and both new/legacy unlock-only controls pass. The two registered feed CTest suites pass in 0.85 seconds.

- Accepted source: `release-0.34.17` at `1e2f8b5f12295002334d3390c12cac0bb4ae2aff` plus `product.patch`.
- Run: https://github.com/sunnyriverr/btx/actions/runs/43837500297 — CI recipe commit `d072457ce2f1f1c4389f9e9fea344b51c48e30bb`.
- Linux x86-64, Ubuntu 22.04 container on Ubuntu 24.04 runner, GCC 11.4, OpenSSL 3.5.9. Normal integrated `test_btx`, with `BUILD_TESTS`, `WITH_MODELNET` and `ENABLE_WALLET` enabled. Same maintained tests in both phases; only `feed.cpp` differs. No component class renaming or reduced target.

The fix saves known-publisher membership. New files restore that list authoritatively; old files infer membership from retained search-observation events before expiry, never from unlock/secret events alone. Legacy history already absent from the file cannot be recovered. Older binaries can discard the added field when saving; downgrade behavior is not qualified.

## Evidence

`records/build-result.json` contains exact configure/build/run commands, expected exits, durations and binary hashes. Individual logs are alongside it. `source-binary-receipt.json` pins the final sources and binary identities; `manifest.json` verifies this evidence. `recipe/` holds the executed CI recipe, including hash-verified checkpoint restore, source reconciliation and candidate rebuild. `source/` retains exact tested inputs.

Baseline failures: `publisher_observation_matches_after_reopen`, `publisher_history_survives_expired_events_and_legacy_load`, `malformed_publisher_history_keeps_valid_new_publishers` (exit201 each). Final candidate: all pass (exit0). The intermediate candidate fails `legacy_unlock_history_preserves_first_publisher_observation`; the final candidate passes, demonstrating the added control detects the review finding.

For an already configured current build, the executed focused entry points are `test_btx --run_test=modelnet_feed_tests --log_level=test_suite`, the individual `modelnet_feed_restart_tests/<case>` filters recorded in the JSON, and `ctest --test-dir <build> -R '^modelnet_feed(_restart)?_tests$' --output-on-failure`. Paths must be adapted to your configured build; the CI driver records the exact execution.

## Limits

These are store save/reopen tests in the integrated executable. No full project test-suite run, native daemon/helper restart, production network, Windows, release qualification or final-revision Mac result is claimed. Internal independent source review occurred; human peer review is pending. Earlier component and intermediate results are not substituted for this final run.

Existing FeedStore work and fixtures by repch1c (#554, #590, #649) are retained; JPP's A-STORES plan motivated the restart/paging comparisons. This is one focused fix, not completion of the full A-STORES programme.
