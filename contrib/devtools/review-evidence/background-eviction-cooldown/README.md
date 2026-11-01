# Background eviction cooldown: review evidence

Bug: a fresh lifecycle eviction can be re-requested after its separate budget
marker is evicted. Candidate **`b37742560c62ecffce5ea29ca233c23036c9bbd2`**, on **`3c1e9b4ab4ea93ca642df079e238ac56179a9166`** (#340).

This is a **separate follow-up to unmerged #340**, not a reimplementation of it.
Review only the [candidate code/test delta](https://github.com/sunnyriverr/btx/compare/3c1e9b4ab4ea93ca642df079e238ac56179a9166...b37742560c62ecffce5ea29ca233c23036c9bbd2).
The two prerequisite commits retain their original authorship. Jpp-matata's
existing snapshot fixture and churn-review question underpin this investigation.
AI-assisted analysis, implementation and testing by Sunny River.

## Decision this evidence supports

Fix the deterministic background download cooldown bypass while allowing an
already evicted body to become the next required root. No validation, consensus,
fork-choice, signer-set, rate-budget or table-capacity change. The existing
non-bypassable store-full delay stays in place.

## Results

| Final identical test | Parent #340 | Candidate |
|---|---|---|
| 280 requested bodies, pending cap1; actual 256-entry budget table; live tombstones whose marker keys are absent | fails3/3, exactly15 premature GETDATA each | passes3/3, zero premature requests;15 fresh requests still proceed |
| Height16 evicted while ahead, then becomes the next root with live marker+tombstone | fails3/3 at required-GETDATA assertion | passes3/3, all40 bodies replay locally, snapshot validates, source connected |
| Marker-present hold/fresh-download/root-release control | passes3/3 | passes3/3 |

The diagnostic hook is read-only; real admission/retention causes marker loss.
Mac26.5.1/AppleM4, Clang17 Release, C++20. Unit execution uses a mock verifier and
null-socket serialized messages. The executable links normal CMake libraries and
three selected test objects; **not full test_btx/full suite**. Eight adjacent
candidate controls pass once each (capacity, foreground, acquisition, failed
replay, unsolicited body); existing lifecycle expiry/redelivery primitive3/3.

Native run: same immutable pinned-consensus/no-quorum strict-Metal1024-body
harness, normal snapshot loader plus exact **test-only1124 metadata**. All1024
historical local-verification flags pass, catch-up97.5s; clean restart, fresh
blocks to1130,30shealth, source connected, no historical requests after restart.
Observed runtime samples use full Metal with zero CPU/XOF fallbacks.

Recorded unpatched3c1e9b4a run vs candidate: request lines4107→1623,
mean4.010742→1.584961, max85→2, eviction messages3067→583. These are two
identified **single runs, not a general benchmark**. Baseline native execution
was reused, not rerun. Both native runs have zero store-full fallback messages;
that separate path is covered only by the focused controls.

## Reproduce

Build normal `test_btx` using repository instructions with this code commit;
`run-focused.sh /absolute/path/to/test_btx` runs the three new cases separately.
For fail-before, retain the same diagnostic/test additions but reverse only
`product-fix.patch`; apply it again for after. No private snapshot pin is needed
for these message-level fixtures. Full test_btx is a reviewer route, not a claim
that we completed that target. Our exact focused link/build input records are
included; replace documented local installation placeholders for your machine.

For the native scenario, `pinned_snapshot.py` is byte-identical to the earlier
[public baseline harness](https://github.com/sunnyriverr/btx/blob/c98a53d9f3530150baa27dc573e20f04463dec74/contrib/devtools/review-evidence/pr340-fold-recovery/pinned_snapshot.py).
It uses the existing private exact1124 fixture and recorded normal-loader patch;
this handoff does not include chain databases, snapshot or wallets. Use the
recorded fixture identity if independently reconstructing it. The directly
runnable message regressions are the primary causal reproducer.

## Limits and test development

No native Linux/Windows, mainnet, default-policy, production profile admission,
full-suite or release qualification. Product additions use platform-neutral
existing chain/lifecycle APIs under cs_main; C++20 matches the actual build.
No platform-specific headers, I/O, error APIs or conditional branches are added.
Mac compilation does not substitute for independent Linux/Windows execution.

An initial longer progress pilot left other actual requests unanswered: the
candidate connected16, then the simulated source exhausted background quota.
Final harness serves all actual GETDATA and pumps retained retries. Both sides
were rebuilt and rerun3/3 with that same final harness; the product patch did not
change. Pilot runs are excluded from final counts.

Text paths are sanitized; SHA256 identities of original source/binaries/logs are
retained. `MANIFEST.json` hashes the sanitized published bytes. No credentials,
production addresses, datadirs or binary artifacts are included.

The code/test PR branch excludes this evidence directory. Full native debug logs
are retained locally with hashes; the published net excerpt preserves their
line order and relevant scheduling categories without the unrelated trace volume.
