# Independent native result and claims review

Reviewer `/root/windows_boundary_review`, 4 November 2026. Bounded artifact review of run41805139945: result.json, selected/full compile database, native-controls and standalone mode/marker records, six source catalogs, verification.json and compiler diagnostic lines in the failed Modelnet build log. No builds, network/publication, source changes or new investigation. No bounty implementation or stopped-task evidence was inspected.

**Verdict: PASS for the three complete native clang-cl translation-unit repairs and the two-compiler exact-function controls. Overall native acceptance remains BLOCKED_INTEGRATION.** No contradictory full-build claim was found in the reviewed records.

## Actual paired compilation

The source HEAD is fixed404 `1b404ed8e52eae249ac73036007ba5a382b0d3ba`, with the separately identified exact403 helper prerequisite applied to the baseline. Baseline/candidate catalog SHA-256 values for each changed file match the current source manifest.

| Generated target | Baseline exit | Candidate exit | Retained candidate object bytes |
| --- | --- | --- | --- |
| generate.cpp.obj | 1 | 0 | 245776 |
| pq1_runtime.cpp.obj | 1 | 0 | 245395 |
| helper.cpp.obj | 1 | 0 | 4212725 |

Baseline diagnostics identify the intended barriers: X_OK; popen/pclose; and helper POSIX permission/PID names. All three candidate object files are present. These are complete generated product translation units under actual native clang-cl, not merely extracted snippets. Each saved selected command is exactly an entry in the preserved compile database; runner records compile_database_unchanged=true. Commands retain Release optimization, C++20, static runtime, WIN32, the maintained forced posix_extra.h compatibility header and project/native dependency includes. Root configure exited zero with tests enabled and no Modelnet-disabling override.

The compiler/toolset profile is MSVC tools14.51.36231, Windows SDK10.0.26100.0, hosted image20261030.294.1. Full translation-unit MSVC cl.exe acceptance is not established by this run; cl.exe coverage below is the extracted-function fixture.

## Native behavioral controls and counts

Both cl and clang-cl fixture build/run exits are zero. Each compiler ran six modes: full, empty, override, infer, profile-nonexec and profile-missing. Their C++ result counts are23+5+1+3+2+2=**36 checks with zero failures per compiler**, or **72 total checks in12 mode executions**. These counts are not project-unit test counts.

Each compiler also completed **12 genuine native-worker positive launches**, two tested pathname forms for each mode, for **24 positive launches total**. All recorded zero exit, the expected JSON success, exactly one marker, marker removal before the dependent guard test and the same worker-binary hash as that compiler's receipt. After each guard-mode execution, marker invocations are empty and native_no_launch=true. Standalone results.json records exactly match the corresponding nested native-controls.json data, and all standalone case logs match the stored stdout/stderr. Both temporary roots were removed and parent environments remained unchanged.

The exercised exact functions preserve unavailable backend flags/exported capability, OpenSSL unset/empty/exact override behavior, optional inference disabled success/configured refusal, worker refusal/zero PID/unchanged output, resident-state cleanup, explicit Unix safety refusal, endpoint sentinel bytes/path, absent parent directories and private-PEM refusal before callback/truncation. This fixture does not exercise the complete helper dispatcher, scheduler slots, daemon lifecycle or a real inference backend. No acquired-slot or RPC-load admission claim follows from its direct function state.

## Integrity and restoration

Independently checked all **21 command-log hashes** against result.json. Both fixture build-log hashes also match. All **six source catalog hashes** match their recorded hashes; every catalog contains14309 tracked entries. Before/baseline-after/restored/after catalogs are identical. Candidate-before and candidate-after differ from baseline only in the intended generate.cpp, pq1_runtime.cpp and helper.cpp entries, and match one another. This agrees with parent verification.json and source_restored=true.

There are no command timeout/resource-stop results. The ignored cl /Bv exit2 is compiler metadata, separately retained; it is not counted as build success. Candidate artifacts remain candidate artifacts after baseline source restoration.

## Remaining integration gate and claim limits

The subsequent actual bitcoin_modelnet build exited1 after1327.91 seconds. The reviewed log records missing pid_t/usleep in bounty_eval.cpp at lines145,221,235 and260, then Ninja subcommand failure. This is solely the observed next compile barrier; no underlying source investigation, runtime diagnosis or repair is included here.

No daemon-build, default-all-build or unit-run command occurred. whole_node_build_run=false and unit_test_execution=false are therefore correct, as are first_failed_stage=modelnet-build and overall BLOCKED_INTEGRATION. The configure stage's administrative COMPLETE marker does not supersede those actual stage results. No completed Modelnet library/link, node link, default build, project unit suite, Windows LAN acceptance or full Windows support can be claimed. This Windows run also does not execute the POSIX PR403 child cleanup/listener-recovery paths.

Supported handoff wording: “The three native Modelnet translation-unit blockers are repaired and the guarded operations pass native exact-function controls under cl and clang-cl; the wider default-profile build remains blocked at the next Modelnet compilation stage before node or units.”

Reviewed result SHA-256: `8ddf23c85660e880f52b3c539d97d94faeb17fe2effc4af2156b69ea92611b32`; native-controls `6d99a244944c77dbc1ff724f14953dd9bfcddede2ced5b92c77bb5cbc871f58b`; selected commands `23f8a02d22286a2c49c76d80c278c3c12dbaa8b05733ff9cda4e6583f36791ab`.
