# Linux integration PASS: #778–#780 combined

Exact accepted base `1e2f8b5f12295002334d3390c12cac0bb4ae2aff` plus:

- #778 watch rollback `5a7d9a363172b82793ca91a492e90e9338cff96c`
- #779 signed-channel rollback `93ff717b15bc71561c464047202e7380457b168d`
- #780 persist-before-live policy `45a90d024c144359e5e82d0fc861d573e143b99d`

This qualifies the **combined tree**, not three independent standalone Linux runs. No product code changed during this qualification. The two watch patches compose in separate methods; only common test includes/appends needed mechanical composition. Four exact composed file hashes are in composition-receipt.json. Accepted base feed files were restored before building; no FeedStore cap/migration change is included.

## Verdict

| Check | Base product + same six tests | Combined fixes + same six tests |
| --- | --- | --- |
| Normal integrated test_btx | Five defect cases fail (12 failed assertions); quota control passes | All six pass,174 assertions |
| Real btx-modeld/private Unix RPC | All five scenario contracts fail | All five pass through retry and clean restart controls |

Native scenarios: watch creation; deterministic mirror-backed watch replacement; genuine signed-channel creation/replacement; operator-policy rejected save. Saved-byte, unrelated-state, event, sequence, no-action-execution and retry checks remain strict. The native stage reuses the exact helpers from the paired build, hash-verified on restore:20 clean starts total. Production ML-DSA44 routines generate/sign/verify disposable public channel payloads; no wallet, monetary node or private key is in this evidence.

## Executed entry points

- [Restore/configuration pilot](https://github.com/sunnyriverr/btx/actions/runs/43870745206): exact cache/hash/manifest/toolchain/source verification,21-step dry run.
- [Normal paired build and six tests](https://github.com/sunnyriverr/btx/actions/runs/43872117053), CI commit `e3aae3355f1b7b448af5f39f3458ef7b81bae2f4`. Executed [build.py](https://github.com/sunnyriverr/btx/blob/e3aae3355f1b7b448af5f39f3458ef7b81bae2f4/build.py), [workflow](https://github.com/sunnyriverr/btx/blob/e3aae3355f1b7b448af5f39f3458ef7b81bae2f4/.github/workflows/settings-build.yml) and source snapshots in that tree. Two workers;35.73s baseline build and328.36s candidate build.
- [Native helper checks](https://github.com/sunnyriverr/btx/actions/runs/43874720119), CI commit `27ab40c081ee4abe7b1cc1192338f0aae5e772cc`. Executed [build.py](https://github.com/sunnyriverr/btx/blob/27ab40c081ee4abe7b1cc1192338f0aae5e772cc/build.py), [workflow](https://github.com/sunnyriverr/btx/blob/27ab40c081ee4abe7b1cc1192338f0aae5e772cc/.github/workflows/settings-native.yml) and fixture. Baseline3.36s/candidate3.17s. No product rebuild; only a small signing utility was compiled.

Each script writes a strict result receipt and exits nonzero on unexpected outcome. These CI entry points were executed, not a newly claimed clean-room reproduction. They depend on retained GitHub artifacts and matching absolute runner workspace/toolchain. Cache/binary artifacts expire30Nov2026; source, fixture, receipts and focused log views remain in this branch. Full original verbose logs/calls are in the linked run artifacts. Log views here remove only ANSI colour and disabled-suite lines; paired/log-index.json binds raw and filtered hashes.

Normal test invocation per case: `test_btx --run_test=SUITE/CASE --log_level=test_suite --report_level=detailed` (six exact selectors/expected exits in paired/build-result.json). Native entry: `helper-retry-restart.py --helper EXACT_BINARY --channel-fixture channel-payloads.json --out RESULTS --expect baseline|candidate`. The same signed payload file is used on both versions. The real-file failure is a disposable directory at the expected temporary-save path. No catalog flags or product admission rules are altered.

## Important limits

- Ubuntu22.04 x86-64 pinned container, GCC11.4.0/CMake3.31.6/Python3.12.16/staticOpenSSL3.5.9. Selected tests only; not full suites, default release qualification, current Mac/Windows integration or concurrent consumers.
- Direct private helper RPC, not btxd proxy or PQ peer transport. No node/wallet, model download, queued action execution, WAN or economic test.
- Clean restart is after healthy retry; no interruption during save or failed-save-to-retry restart claim. Native queues stay empty and are never drained; unchanged maintained regressions separately protect a nonempty queue.
- Direct watch RPC generates IDs. Native replacement uses the supported deterministic mirror KEEP watch. Same-key failed mirror outcome is deliberately replayed; healthy semantic retry uses a fresh idempotency key. This does not redefine the existing partial mirror-policy/watch-save contract.
- Policy startup intentionally reapplies launch settings and rewrites policy.json. We verify failed-save live state, healthy persistence before stop, then known startup reset/reapply. We do not claim saved policy overrides launch flags or global profile/background quota atomicity.

## Setup corrections retained

The first native run43874077698 stopped at signing-utility link: replacing modeld main omitted its standard null translation hook. No native cases ran there. The utility now supplies the same hook as src/modeld.cpp:28; product binaries and paired tests were unchanged. A local evidence collector also rejected duplicate verbose logs exceeding its extraction cap; selective retrieval was fixed against the same digest-verified artifact without rerunning tests. These are fixture/collector corrections, not product failures.

## Provenance and credit

qualification-receipt.json contains binary/source hashes, original+updated cache artifacts, outer digests and expiry. Original cache14211382465 remains intact; updated cache14229026757 and exact binaries14229345782 were restored and verified in the native run. Build results14229196023 and native results14230170741 were also digest-verified locally.

Preserves the existing watch/channel/policy implementations and maintained fixtures, including repch1c's watch persistence work and JPP's store/restart testing direction. Product commits and their authorship remain unchanged. This is additional integration evidence for the existing proposals.
