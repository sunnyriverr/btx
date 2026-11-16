# Operator-policy save evidence

Target release-0.34.17@1e2f8b5f. Two maintained cases, identical before/after. Baseline fails two live-policy assertions/44; candidate passes44/44. The quota control passes on both. Execution is the exact compiled dispatcher/write block on Mac arm64 with real catalog/policy support libraries. **It is not a patched full-helper RPC run.**

A separate native baseline run (native-baseline/) used a hash-verified retained949a98e3 Mac helper. Dispatcher, WriteJsonFile, SetPolicy and policy serialization bodies were byte-identical to current source. Blocked policy.json.tmp caused an IO response while preserve_rare and derived propagation changed; file stayed old. Healthy same-patch retry and unrelated/zero-spend controls passed. This was an older whole binary with relevant source identity, not an untouched current build. No transfers, wallet/node or paid services.

Maintained regressions added to src/test/modelnet_first_run_tests.cpp:
- rejected_policy_save_keeps_live_settings_and_allows_retry
- saved_policy_quota_matches_catalog_normalization

The exact case bodies run in driver.cpp, redirecting DispatchHelperRpc to baseline-adapter.cpp/candidate-adapter.cpp. Each compiles the exact production policy branch, actual WriteJsonFile and actual HelperRuntimeInfo declaration, linked with real retained ModelCatalog/policy/serialization libraries. No mocked disk write. Controls preserve unchanged saved bytes and live policy on refusal, same-patch healthy retry, prior seed/follow/upload fields, refusal of auto_pay/nonzero spending, and zero/above/below-cap live/file quota agreement. Private runtime-flag assignment ordering is source-reviewed, not directly asserted after the fix.

execution.json records sanitized executed commands; placeholders denote original retained paths and are not a fresh standalone build recipe. Full candidate helper and complete modified test translation units pass syntax checking with matching immutable current ModelNet headers. The original stale-header full-helper pilot failed19 unrelated interface checks; it stopped without changing caches, current headers were overlaid only in this task, and final syntax checks passed. Internal design/repair review PASS. patch-verification.json proves exact base application/qualified result bytes; identities.json retains qualified input/binary hashes. Files listed in manifest.json are the sanitized evidence bytes.

For a normal integrated build, run the two names above in modelnet_first_run_tests through test_btx. This is an integration instruction, not a claimed execution. Unverified: normal integrated target, rebuilt full helper and after-fix private RPC/process restart, Linux/Windows, concurrent profile/background-quota mutation or release acceptance. Ordinary policy RPC setters now share the existing helper-store mutex; the broader runtime/profile synchronization contract is unchanged.

The patch normalizes candidate quota to the current hard cap, persists first, then updates catalog and two runtime flags. Existing validation/zero-spend, asynchronous profile apply and mirror partial-save contracts stay unchanged. Existing policy and first-run fixtures/original contributor history are preserved. Prepared with Codex; exact diff/results/limits reviewed. No test rerun for publication.
