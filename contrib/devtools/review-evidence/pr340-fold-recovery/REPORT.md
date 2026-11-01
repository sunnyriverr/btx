# PR340 integrated-head1024-body rerun — local result

**PASS on3c1e9b4a** — the unchanged pinned-consensus strict-Metal snapshot harness
finishes catchup, survives restart and stays healthy. AI-assisted testing on
macOS26.5.1/AppleM4/Clang17 Release. No publication/newPR.

## Decision and result

JPP explicitly requested this rerun at comment6557872406, after folding our
unchanged capacity code/tests with Sunny authorship. Both full product/test files
were independently compared to our supplied commit. This checks the integrated
snapshot workflow and records a churn baseline; it does not introduce a repair.

- All1024historical bodies101..1124 match the source and carry localExactReplay
  flag256, without trusted-attestation flag512. Background completes in
  188.324s including verification audit; foreground three
  normal blocks connect during catchup, reaching1127. Source stays connected.
- Exact tip/completed background/all1024flags survive clean target restart.
  Three further peer blocks reach1130, then the original30second health window
  passes. Authenticated chainwork equals chainwork. No historical re-requests
  after the restart-preserved-catchup marker; only fresh blocks requested.
- Sampled replay checks after catchup and restart are strict-device/fullMetal,
  fully accelerated, with zero recorded CPU GEMM, CPUfallback, deviceXOFfallback
  or hostXOF calls. This is sampled runtime evidence plus all per-block flags,
  not per-block exported hardware telemetry.

## JPP's requested counters

| Metric | Integrated3c1e9b4a | Original retained70e35da0run |
|---|---:|---:|
| Historical request entries |4107|4292|
| Distinct historical hashes |1024|1024|
| Mean requests per hash |4.0107421875|4.19140625|
| Maximum requests per hash |85|87|
| `Deferring requested background body` lines |0|0|
| `Evicting retained MatMul body` lines |3067|3252|
| Source connected during catchup |Yes|Yes|

Counts cover the whole target debug log across catchup/restart. Native
`Requesting block <hash>` entries include ordinary height-labelled and direct-fetch
forms, filtered to the known1024historical hashes. Deferral/eviction counts are
exact-message line counts across the whole target log. requests-per-hash.json
retains every count; requested-events.json/capacity-events.json preserve line
numbers and original text. Mean denominator is1024, also the number of distinct
requested historical hashes. This is not a wire-byte measurement.

Churn remains: a single run's smaller counts do not demonstrate a causal retry
improvement. **Zero capacity-deferral messages means this pinned workflow did not
exercise the store-full dispatcher fallback.** Its separate prior native/unit
coverage and JPP's independent4case/fulltest_btx results are distinct evidence.
The present run is the integrated recovery check/churn baseline he requested.

## Identical criteria and configuration

Original pinned_snapshot.py SHA838d2454c6e65fbc709c1e8469297ad5ea1c2492f90978121a001af17ad51678
was executed unchanged. Functional framework tree matches across the base/fold.
The launcher substitutes only binary/config/output paths and chooses unused
loopback ports. Standard loader/checksum and exact private1124UTXO/blockhash/
shielded commitments are unchanged. One secp pin/threshold1, no local signer,
zero attestations/quorums throughout, consensus validation, strictMetal/noCPU
confirmation, assumevalid0 and checkblockindex1. Mocktime follows real elapsed
seconds. Regtest's pending/global budgets are relaxed defaults, not mainnetcap1.

Fresh isolated normal CMake btxd/btx-cli Release build on the integrated head,
MetalON/runtimekernels, walletON/modelnetcompiledON; runtime modelnet0 isolates
the test. No shared archive/object substitution. Only the existing test-only
kernel/chainparams.cpp snapshot pin differs from upstream. Build988.70s; warnings
retained, not warning-free/fullsuite. Unused CMake CLI prototype/ZMQ variables are
recorded; prototype option is absent at this base, and actual config has ZMQON.
No new consensus/validation change.

## Excluded setup attempt and recovery

First invocation failed immediately at source0!=1124, before the snapshot test:
old disposable source-cache databases/blocks had previously been removed, leaving
only debug.log and the snapshot. Checking snapshot SHA alone did not establish a
usable chain cache. That invocation is preserved in setup-pilot-missing-source-cache/
and is not a product failure or counted test comparison. All its owned nodes exit.
The original source-cache files were restored from the already hash-verified
original evidence archive, SHA d82b378774f305137e5db002e74e518a60994f3e4e3619be5caa278b97babd0b.
No new chain was mined, no existing retained file overwritten, no harness criterion
changed. Final invocation confirms the exact1124tip and normal snapshot loader
checksums before recovery. fixture-restoration.json records22restoredfilehashes.

## Scope and preservation

One completed final fold run. Original baseline metrics are log reanalysis, not
a repeated run. No stale/available quorum, quiet-source startup, automatic peer
discovery, mainnet-sized profile/device admission, fullsuite, Linux/Windows,
sanitizers or release qualification. Source announces a normal block after2s;
restart explicitly reconnects the same loopback peer. The separate PR362
production-admission resource stop is not this toy-regtest result.

All owned nodes stopped, all six chosen ports closed. No resource stop; swap
stayed149.19MiB throughout. Original shared source/dirtyfiles/cache untouched.
Exact private snapshot pin and original restored disposable fixture remain for
reproduction. No production wallet/node/miner, rental, newPR, post or churnfix.
Fullsource/binary/archive/log identities and hash manifest retained locally.
