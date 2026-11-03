# Emergency authority persistence — tested private candidate

Verdict: scoped native macOS component fail-before/pass-after at fd3a905f.

The candidate preserves ordinary 16,384 admission, adding 129 fixed shared slots
only through explicitly verified policy/revocation writers. Exhaustion refuses
atomically with SEC_CONTROL_QUOTA. No record pruning or authorization change.
One policy plus 128 principal revocations explains the count; other subjects and
peer traffic can exhaust it. Long-term retention and physical-space recovery
remain separate. CONTRACT.md records the full scope.

## Observed results

The identical final harness source and object were linked once against the 11
identified baseline component objects and once with database.cpp/trust.cpp
recompiled; the other 9 component objects, crypto/UniValue archives and SQLite
were retained and hash checked. This is a partial relink, not a clean BTX build.
Database instance layout is unchanged. Source slice and exact build inputs are
in build-run.json; immutable baseline is fd3a905fed3bc4943ad24372da032af4d29304a3.

- Original: below-cap control PASS; full-cap policy FAIL SEC_OBJECT_QUOTA;
  full-cap revocation/tail sequence FAIL SEC_OBJECT_QUOTA; invalid-authority
  and rollback control PASS. Patched: all four same named cases PASS.
- Candidate commits valid policy and revocation effects at the original cap.
  Ordinary genuinely new signed challenge still refuses after entering the tail.
- Two threads/two SQLite connections race for the final slot: exactly one succeeds,
  one gets SEC_CONTROL_QUOTA, total remains16,513. The next revocation and policy
  refuse with identical complete persistent snapshots.
- Duplicate signatures merge to 16 without another row; a 17th signature refuses
  atomically. A public duplicate preserves private visibility.
- An expired retained signed FAIL still denies its affected model before and
  after emergency writes/reopen. Permits for the revoked grant remain unusable.
- Policy survives connection close/reopen. Tail remains fixed across reopen;
  final slot works, later controls refuse, journal verifies and pause commits.
- Wrong signer/root, wrong epoch and expired revocation refuse without protected
  state change. A test-only BEFORE INSERT journal trigger makes both candidate
  authority paths reach SEC_DATABASE_WRITE; all prior transaction changes roll
  back. Driver explicitly distinguishes baseline SEC_OBJECT_QUOTA from that
  injected late failure. This is not an actual disk-full simulation.

## Limits and review

One final paired native macOS arm64 run. Fixtures use unsigned inert objects for
count construction and genuinely signed authority/evidence at production import
entry points. No network filling, actual worker cancellation, service/guard
restart, mainnet, Windows/Linux, full unit suite or clean-build qualification.
Valid peer input exercises ImportRecord(peer=true), not a full signed exchange.
Expired negative evidence is exercised; transport nonce/rate bookkeeping lies
outside the policy/revocation transaction invariant. No sustained normal-space
recovery, local priority under peer reserve exhaustion, physical disk-full or
page-cap recovery is established. Wrong realm/revoked signer and populated-budget
faults have source-preservation review, not new dedicated executions.

Independent review found three fixture/oracle defects before final execution;
all were corrected. First compile-only pilot failed on unused Refuse under
-Werror; it ran no product test. Final proof includes explicit aggregate checks.
Review/REVIEW.md verifies final sources, binaries, oracles and these limits.
The runner docstring was corrected after the successful run to describe its two
harness threads; execution code did not change.

Owned growth peaked 17.56 MiB; minimum measured host free 1.346 GiB exceeded 1.25 GiB
reserve. Owned temporary fixture data and generated keys were removed. Lossless
log archives and inactive Rust cache removal are recorded in space receipts;
pr286 Cargo target requires rebuilding. Tested apps/source/log content retained.

## Reproduce and next step

From the retained workspace run:

    python3 work/btx-review-tools/store-quota-recovery/upgrade/build-run.py

Requires documented original baseline object/archive/source paths. Preserve
current results first because this recipe replaces its own outputs. It enforces
1.25 GiB free reserve, 100 MiB owned growth and 90 seconds per command. This is a
retained-workspace reproducer; transferring the fixture alone is not a portable
clean build. No additional execution is requested by this report.

Next: deliver the focused code/fixture branch for #275 author review, with the
emergency-only scope and native-platform/integration gaps explicit.
