# Scoped source review: executable paths and synthetic credential fixtures

**Verdict: no source blocker found. Native current-binary qualification remains pending.** This review changes no code, index, ref, cache or build. No API, build, test or reproduction was executed. Sole output is this review.

## Exact attribution

- Candidate: `37472d88c1e0d7dd88ac92e1c698351a0a7e9bd7`, direct parent `70f1886f1028b4d78b5689f4fd2f80ba1d195d96`.
- Locally available release comparison: `2f3b574867c11ab79eba829123689b76e6137a38`. No remote state was queried.
- Prior qualified integration: `c660512641edf3bfb36f287e56a6fa0a8794fe64`.

The candidate differs from70f in **four files**, not three: three fixture/configuration files plus the explicitly adopted PR433 S3 prerequisite. Candidate CMake, cloud, R2 and S3 blobs all match c660 byte-for-byte. The candidate commit message discloses the adopted S3 prerequisite and makes no native-result claim.

| File | Candidate and c660 blob | Release relation |
| --- | --- | --- |
| `src/test/CMakeLists.txt` | `a56654a8b58353a50c3c6678450ab4e6a5c9ddd2` | Release still has suffix-less definitions and lacks these helper dependencies. |
| `src/test/modelnet_cloud_tests.cpp` | `9d27b14199b863b39dcf3c52c6cc9c2f40c75bf0` | Release has PR433 socket controls, but lacks the broader ENV fixture/restoration correction. |
| `src/test/modelnet_r2_storage_tests.cpp` | `53dcc8a2083304b22aa21fdbc169f7d10d60d604` | Release lacks ENV fixture/restoration correction. |
| `src/modelnet/s3_client.cpp` | `34f90b0f601d6d2494d4f65b929e20b61b4aa462` | Identical to release; adopted prerequisite, not a new product repair. |

Within these paths, candidate versus release differs only in the three fixture/configuration files (186 additions/37 deletions). `src/test/util/environment.h` remains blob `53a089961804d23fa3243b926cc6b94508a6c0c7` in70f/candidate/release/c660.

## Preserved contracts

Line references below are against candidate37472d88.

- **Executable paths and dependencies:** `src/test/CMakeLists.txt:2618,2620` uses `TARGET_FILE` for btx-open/modeld; `2629` adds their explicit test target dependencies. `2630–2635` uses target-file btxd plus dependency when available, otherwise preserves a configured binary-directory path with `CMAKE_EXECUTABLE_SUFFIX`. This follows actual suffix/output configuration, including POSIX and Windows. No launch/assertion predicate is weakened. Changing target-wide definitions legitimately changes generated unit compile commands; old configuration/object identity must not be claimed after normal regeneration. The absent-btxd fallback cannot establish a runtime helper pass when no executable was built.
- **Safe PATH refusal:** `modelnet_cloud_tests.cpp:71–95` retains WriteCreds and PATH BaseCfg. `289–321` keeps unsafe-file refusal, explicitly keeps Windows nominal0600-file refusal, preserves POSIX file success, then checks ENV success and redaction. Original product permission refusal in `s3_client.cpp:1194–1203` is unchanged relative to release. Existing cloud stream `530–574` and R2 identity `160–177` file-refusal/ENV controls are retained.
- **POSIX behavior:** ScopedCloudCredentials Config/RpcRef (`100–125`) and ScopedR2Credentials Config (`95–111`) change positive references only under WIN32. Non-Windows still receives original PATH values, endpoints/layout/use_fake and POSIX file success. This is source preservation, not a new POSIX runtime qualification.
- **Environment ownership:** Case-local ScopedEnvVar copies the value into the process environment synchronously and restores prior value or absence on destruction, including assertion unwinding (`environment.h:39–66`). New cloud restoration `1093–1119` and R2 restoration `511–537` explicitly cover prior value and absence. Fixed fixture names are process-global; do not run these bodies concurrently inside one process. Separate test processes have separate environments.
- **Distinct read/write keys:** R2 mixed-key test `446–474` preserves a separate synthetic read key and write key, including separate ENV name under Windows. It still requires Init, `write_creds_distinct`, a SigV4-rejected PUT and zero stored objects. No conflation or success-by-using-read-key is introduced.
- **Redaction and behavior:** NoSecrets (`cloud:128–135`) and all operation/budget/layout/data assertions remain. cloud03 now checks both ENV HealthJson and ConfigJson. RPC fixture references use supported `env:` syntax only on Windows; they retain PATH strings on POSIX. All credentials are existing synthetic test constants. Positive FakeS3 fixtures remain fake; the two refusal controls retain `use_fake=false`/loopback endpoints and actual ordinary transport-error checks (`cloud:1019–1045,1075–1090`). PR433 source is adopted unchanged so those formerly permission-masked cases can reach transport.
- **Native helper controls:** Existing API/journey Windows paths still call sdk_test::Spawn with argv, not a POSIX shell (`ahp_api:240–262`, `ahp_journey:325–339`). Exit0, inspect fields, preview-only, no-spend and no-AGENTS-write assertions remain. `unique_todo:223–236` requires actual modeld parser exit1 and btxd help exit0; missing/crashed executable cannot count as refusal success. AHP-DOC09 (`824–870`) requires exact native exit1 plus parsed error JSON, and includes a core-v1 exit0 valid control. Its existing fallback remains harmless when TARGET_FILE already includes.exe.

## Minimal current-binary selection

Recommend **29 exact cases**, not whole suites: the21 actually blocked credential cases, four actual suffix-path failures, two new ENV-restoration cases, and two native helper controls. cloud03 covers preserved credential-policy refusal plus ENV/redaction success; R2 mixed-key case covers distinct signing keys. AHP-DOC09 fail-closed JSON includes both valid core-v1 success and invalid-input refusal. unique_todo exercises modeld and btxd. All expected outcomes must be checked from the new binary/raw XML; this list is not an expected-failure allowlist.

- `modelnet_cloud_tests/cloud_07b_cloud_object_store_piece_objects`
- `modelnet_cloud_tests/cloud_01_sigv4_put_get_fakes3`
- `modelnet_cloud_tests/cloud_02_head_range_path_style`
- `modelnet_cloud_tests/cloud_03_creds_0600_env_never_in_json`
- `modelnet_cloud_tests/cloud_07_cloud_object_store_source_files`
- `modelnet_cloud_tests/cloud_07c_piece_objects_hydrate_incomplete`
- `modelnet_cloud_tests/cloud_09_presign_get_exact_object`
- `modelnet_cloud_tests/cloud_11_health_json_counters`
- `modelnet_cloud_tests/cloud_12_budget_refuse_when_exhausted`
- `modelnet_cloud_tests/cloud_12b_calendar_day_budget_persists`
- `modelnet_cloud_tests/cloud_https_not_stub_error`
- `modelnet_cloud_tests/cloud_https_use_fake_false_error_is_not_stubbed`
- `modelnet_cloud_tests/cloud_rpc_set_hostmodel_events_no_secrets`
- `modelnet_cloud_tests/fullcloud_01_102400_pieces_one_source_object`
- `modelnet_cloud_tests/fullcloud_02_object_bytes_equal_fileentry`
- `modelnet_cloud_tests/fullcloud_05_fakes3_stream_hydrates_one_get`
- `modelnet_cloud_tests/fullcloud_20_budget_remaining_in_health`
- `modelnet_r2_storage_tests/r2s_04_over_budget_get_transfers_bytes_and_records_none`
- `modelnet_r2_storage_tests/r2s_05_put_path_is_not_metered`
- `modelnet_r2_storage_tests/r2s_08_write_creds_break_fake_signing`
- `modelnet_r2_storage_tests/r2s_09_physical_whole_file_and_large_extents_fakes3`
- `modelnet_ahp_api_tests/ahp_api_04_plan_execute_cancel_acquisition`
- `modelnet_ahp_journey_tests/ahp_j08_offline_and_cancellation`
- `modelnet_b0_remaining_tests/uri_12_btx_open_preview_binary_present`
- `modelnet_jit_journey_tests/jit_api_04_cli_schema`
- `modelnet_cloud_tests/cloud_fixture_credentials_restore_environment`
- `modelnet_r2_storage_tests/r2s_fixture_credentials_restore_environment`
- `modelnet_unique_todo_tests/unique_todo_a2_modelindex`
- `modelnet_ahp_doc_tests/ahp_doc_09_btx_open_fail_closed_json`

No need to repeat already-passed whole cloud/R2/AHP/JIT suites, unrelated failures, or the prior49-assertion path/lock campaign. The two unchanged PR433 HTTP/TLS cleanup controls are already qualified by their exact reused source; they are excluded from this minimal reconciliation selection. If run for a separately stated new-binary purpose, retain their real loopback transport and EOF/reset assertions and disclose the repetition.

Relative to70f, the full candidate inventory adds **four** cases: cloud/R2 ENV restoration plus the two adopted PR433 socket controls. Relative to release, only the two ENV-restoration registrations are additional. Existing case bodies are not removed. Do not require equality to the old inventory or call all four additions new credential tests.

## Result and limits

The source fixes match the observed current prerequisites without weakening security or helper outcomes. Candidate source reuse does not transfer prior c660 runtime passes onto the freshly configured current binary. Before claiming completion, bind the actual candidate tree/generated configuration/binary, confirm target paths and required helper outputs, then classify the29 selected bodies with exact selection and raw-result checks. Product S3 prerequisite adoption must remain explicit in any70f comparison; release already contains it. No full-release, successful live cloud/TLS storage, native POSIX or production acceptance follows from this source review. Preserve unrelated holds and stopped paths.

Prior evidence read for attribution: `four-fixture-repair/failure-triage-raw.json` (actual21+4 blocked cases), `cloud-r2-fixtures/observation/verification.json`, earlier source/evidence in this review chat, and exact local Git objects. No new failure hunt was performed.
