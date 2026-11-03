# Verified emergency authority persistence

Tested candidate de797bbd20c9a0836ab5a166df18a89669acc51c on security-v2
fd3a905fed3bc4943ad24372da032af4d29304a3. This follows JPP's #275 findings 1/4.

The ordinary new-object cap remains 16,384. The existing authenticated policy
and revocation writers alone gain 129 fixed shared tail slots. This budgets one
policy plus 128 principal revocations; valid peer revocations share the allowance
and other subjects can exhaust it. The 130th tail record refuses atomically with
SEC_CONTROL_QUOTA. No evidence is pruned and no signature/epoch/freshness/realm
rule is changed. See [contract](CONTRACT.md) and the operator documentation.

## Executed result

Native macOS 26.5.1 arm64, Apple clang 17/C++20, Homebrew SQLite. One final paired
component run, partially relinked from hash-identified baseline dependencies.
The same final [harness](harness.cpp) and compiled harness object served both
binaries. [Baseline](baseline-result.json): two valid controls PASS, full-cap
policy and revocation progress FAIL with SEC_OBJECT_QUOTA.
[Candidate](candidate-result.json): all four same named cases PASS.

- Valid signed policy and revocation commit at the original cap; a genuinely new
  ordinary signed record still refuses after entering the tail.
- Two threads on two SQLite connections compete for the final slot: exactly one
  success, one SEC_CONTROL_QUOTA, final total 16,513. Subsequent policy/revocation
  refusals preserve complete persistent table snapshots.
- Duplicate signatures merge up to 16, a 17th distinct signer refuses atomically,
  and a public duplicate preserves private visibility without another row.
- Policy and revocation state survive connection reopening; the reserve does
  not reset. Old grant authority stays denied, an expired retained signed FAIL
  still denies its affected model, and the journal verifies.
- Wrong signer/root, wrong epoch and expired revocation refuse. Test-only late
  journal-insert failures in both authority paths produce SEC_DATABASE_WRITE,
  with prior transaction changes rolled back. The driver checks that the
  candidate reaches this injected failure rather than the old quota gate.

[Build inputs and checked aggregates](build-run.json), [recipe and limits](BUILD.md).
The initial compile-only pilot stopped on an unused fixture helper under
-Werror; no product test ran then. Three fixture/oracle problems were corrected
before the final execution. Internal source/artifact review verified the scoped
result; it was not an independent native-platform execution.

## Scope

Count construction uses unsigned inert fixture rows; the operations under test
use genuinely signed controls through production authority entry points. No
network filling, actual worker cancellation, full guard restart, Linux/Windows,
full unit suite or clean whole-branch build is claimed. Passing peer=true covers
ImportRecord restrictions, not a complete authenticated mesh exchange. Wrong
realm/revoked signer and populated-budget fault cases were source-reviewed,
not separately exercised here.

This is finite emergency persistence. It does not restore ordinary capacity,
reserve disk bytes, give local policy priority over peer revocations, or qualify
physical disk/page exhaustion. A test-triggered late write error is not an actual
disk-full test. Old binaries use the same schema but lose emergency admission
at/above 16,384. Long-term retention/compaction remains a separate design.
