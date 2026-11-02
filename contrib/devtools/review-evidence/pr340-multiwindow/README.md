# #340 folded-head four-window native recovery

**One clean-build macOS/M4 strict-Metal toy-regtest run passed on5deb3278. Regtest pending/global/per-peer budgets are unthrottled (UINT32_MAX). This does not qualify mainnet's one-pending-slot/rate-limited/default policy or production-size proofs.**

Source/fold: b3774256+5deb3278, original authorship preserved in340.370closed as superseded after exact verification; not merged. JPP's fixture/base work and reviews credited; Sunny River's AI-assisted experiment extends the prior1024-body run to4096. This branch adds evidence only; no product change/new PR.

Read REPORT.md and summary.json. All4096historical bodies match, local replay flags persist, strict-device Metal has zero CPU fallback, foreground/restart/health pass.6023historical GETDATA request lines, max2/hash, mean1.47046;1911evictions remain. No new fix follows from this successful scoped test; timing is not a mainnet benchmark.

## Inputs and reproduction

- Base:5deb327871efbca832e1a4e420f76dad74ff6b41.
- exact-regtest4196.patch adds only the exact4196test snapshot pin; real download window1024unchanged. Never use this test-only pin patch in production.
- pinned-window4196.dat is the executed synthetic snapshot. fixture.json/fixture-validation.json record its hash and exact metadata. Legacy generator1124labels are disclosed; actual4196height is verified.
- fixture-blocks.dat is a de-XORed standard block-file stream of the4196linked active regtest blocks (genesis excluded), ancestry checked to the snapshot tip and all4096executed historical status hashes. Sibling records and all wallet/config/identity/index/undo files are excluded. fixture-blocks.json records its digest. This is a publication-time deterministic data export, not a new node test.
- pinned_snapshot.executed.py is the executed harness. pinned_snapshot.py changes only SOURCE to BTX_REVIEW_SOURCE; raw/final hashes are retained. Other *.executed.py files record actual local preparation/launch/analysis; path placeholders are not portable executable paths.

Build the exact source in a disposable worktree with the private snapshot patch. configure-command.json records actual flags; replace local path placeholders. Clean btxd/btx-cli targets were built, then kernel metadata patched/relinked. Build warnings are retained; this is not a warning-free/full-suite claim.

The executed harness starts node0from a stopped retained fixture directory at fixture-run/node0/regtest, with the snapshot file inside that directory. For independent reconstruction, the public active block stream can be imported through normal -loadblock into an empty disposable regtest source using the same test consensus flags, then stopped/copied there and paired with pinned-window4196.dat. Verify source height4196and base hash from fixture.json. This normal-import reconstruction route was NOT re-executed for publication; the executed run copied the retained source fixture. Do not claim it as additional qualification. No private source wallet is needed: raw block/snapshot data are supplied separately, never the original source datadir.

Set BTX_REVIEW_SOURCE to that exact checkout, BTXD/BTXCLI to its two binaries, BTX_MATMUL_BACKEND/BTX_MATMUL_V4_BACKEND/BTX_MATMUL_REQUIRE_BACKEND=metal, and PINNED_VARIANT=folded-four-window. Invoke pinned_snapshot.py with the built test/config.ini, a fresh tmpdir, --nocleanup and an unused --portseed. run-invocation.json records the exact measured command. Keep1.5GiBfree; the measured launcher bounds logs600MiB and total runtime1500s, with1200scatchup/45sno-progress limits inside the harness. Reserve the ports before running.

The harness itself asserts hashes/body bytes,4096flags, no quorum/local signer, fresh blocks, restart and30shealth. analyze.executed.py records how request/log counters are computed. All requested lines are counted once and filtered by the4096historical hashes; evictions/deferrals are whole-target-log counts. No network bytes inferred. Source/header fixture adaptations are in REPORT.md; no manually rescued or paced body delivery.

No Linux/Windows, cap1policy, mainnet, multiple-netgroup churn, production profile admission, arbitrary larger ranges, fullsuite or release qualification. All owned test nodes stopped; shared source/build/wallets/miners were untouched. Public observations redact peer endpoints/identity fields; local absolute paths are replaced. Historical reports describe capture-time no-post status; this publication was authorized afterward.
