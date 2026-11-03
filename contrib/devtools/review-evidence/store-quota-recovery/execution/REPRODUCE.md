# Reviewer entry point

From this workspace root, run:

```sh
python3 work/btx-review-tools/store-quota-recovery/execution/build-run.py
```

The script assembles no new source and changes only its own execution directory. It validates the retained exact-baseline security object sources and repository headers against `fd3a905fed3bc4943ad24372da032af4d29304a3`, validates the identified read-only crypto/UniValue archives, compiles the fixture once, partially relinks the component and runs it synchronously. Requires Apple clang, arm64 macOS, the retained `pr275-runnable-queue/runtime/build` security objects and source, `pr362-admission/build` crypto/UniValue archives, `toolchain-2026-10-31/source` immutable Git objects and the hashed Homebrew SQLite installation. These prerequisite paths and every reused hash appear in `build-run.json`; the driver fails on source/header/archive mismatches and records reused object hashes for comparison with delivered `build-run.json`. Object byte hashes are recorded, not automatically pinned by this entry point; `prior-object-provenance.json` records the completed comparison of all 11 delivered objects with the earlier baseline manifest. It is a retained-workspace reproducer, not a claim of a portable clean build.

The complete source slice and harness are retained for inspection or a separately reviewed clean build. No Service, worker, network fill, node, VM, quota override or product patch is required. Maintain at least 1.25 GiB free host space; this task is bounded to 100 MiB owned files and 90 seconds per command. A rerun replaces its own final logs/results, so preserve the delivered files first if comparing identities. The existing two deterministic cases suffice; no automatic repetition is requested.

Expected: exit 0; `results/result.json` has `passed:2, failed:0`. `count_construction.actual_objects` and `final_proof.objects` are 16,384. Quota controls return `SEC_OBJECT_QUOTA`; pause and reopen retain revoked permit phases and deny release; direct signed resume without import succeeds, replay is refused, both old secrets remain refused, and a new harmless read dispatches at unchanged capacity. `before_quota_failures` equals `after_quota_failures`. See REPORT.md for fixture limitations and the preserved output-path pilot.

`results/result.json.records.jsonl` contains public signed synthetic envelopes only. Generated secret keys and temporary databases/workspace files are disposable and removed automatically. All persisted read output is the harmless fixture string `hello safe workspace` plus newline.
