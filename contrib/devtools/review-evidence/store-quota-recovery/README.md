# Object-quota containment and recovery contract

Baseline `fd3a905fed3bc4943ad24372da032af4d29304a3` (#275). This extends [Jpp-matata's findings 1/4](https://github.com/btxchain/btx/pull/275#issuecomment-6433856983); it does not claim a new quota defect or a recovery fix.

The final native Mac synchronous component invocation passes two cases: below-cap legitimate authority/read controls, then actual16,384-object containment. New signed revocation/policy imports fail atomically; pause commits and persists through true database connection close/reopen; direct signed resume preserves old-permit replay refusal but leaves capacity full. No product code changes.

- [Execution report and full limits](execution/REPORT.md)
- [Exact final harness](execution/harness.cpp), SHA256 `b164b071893ad63079e5346ac927c30f7a42272e1ff72a361000d2a7cd083870`
- [Final result](execution/results/result.json), [build/input identities](execution/build-run.json)
- [Recorded local reproduction recipe](execution/REPRODUCE.md), [recorded driver](execution/build-run.py)
- [Retention/source contract](review/RECOVERY-CONTRACT.md), [internal artifact review](review/FINAL-ARTIFACT-AUDIT.md)

The recipe is a retained-workspace partial relink requiring the named existing Mac objects/archives, not a portable clean-build entry point or a runnable-from-this-evidence-directory claim. The driver was executed in that original layout. It records object byte hashes; prior-object-provenance verifies the delivered11objects against the earlier baseline. Sanitized copies replace private local path prefixes with placeholders; normalization-manifest preserves original/published hashes. Signed public synthetic-envelope snapshots remain local and are cataloged, not included. No binaries, databases, real credentials or secret keys are published.

Boundary fixtures use unsigned inert envelopes through Database::Put for count construction and an injected executing-row phase. These do not establish signed-network filling or cancellation of a real running worker. Database close/reopen is not Service/guard/node restart. No IPC-latency, full-disk/page-limit, Linux/Windows, full-daemon, model/GPU or release qualification. The first invocation passed substantive checks but failed output persistence; the same harness/binary completed after a driver output-directory correction. Both logs/manifests are retained and distinguished.

Retention cannot merely discard expired evaluations: trust.cpp:438–447 intentionally retains a FAIL's denial while its evaluator signature remains valid under current policy after positive freshness expires. Revocations, policy-epoch/replay/budget state and journal continuity also need a defined durable contract. Moving Revoke earlier inside the same transaction still rolls back on Put failure. A fresh signed resume is not storage-capacity recovery.
