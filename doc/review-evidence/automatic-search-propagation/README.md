# Automatic search propagation — scoped native PASS

**Tested ACK `ea64a31e9b4f83375746ce2e65917bcb3c2026e9` — automatic search propagation only.** Numair added the background search pull at `0afc505f`. This run builds stock release-0.34.17 at the named later revision; no product change is applied. The helper/search files are byte-identical to the reviewed0af implementation.

## Result

Normal Linux btx-modeld, Ubuntu22.04/GCC11.4/x86_64 container on Ubuntu24.04 hosted runner, UID/GID65534. One run, two local helper roles plus a no-contact control, five process starts, 22 controller RPC calls, five stages PASS in 38.79 seconds:

1. No-contact fresh observer has no publisher records during 11 seconds; no receiver RPC.
2. Configured receiver's disk index changes0 → 16 → 17 exact signed records, approximately10s after initial passive observation. **No receiver RPC runs before this success.** Identity, public key, signature, metadata sequence and all serialized record fields match publisher output.
3. Stop publisher and receiver, restart receiver while source unavailable. Explicit LOCAL search loads all 17from disk with zero connected/index/routing query and response counters. Local raw export matches exact records and saved bytes remain unchanged.
4. Restart publisher with the same identity and add record 18. Receiver disk changes 17 → 18 without another receiver RPC, passing the full cached first 16-record page; authenticated transport pin is unchanged. Approximately9.85s from reconnect observation.
5. Another 6 seconds passive stability/liveness window and all normal stops pass; owned container cleanup succeeds. This is a short check, not a soak.

The only two receiver RPCs in the complete trace are the offline LOCAL search and subsequent local export. Initial/reconnect observation is external read-only file IO; receiver mutation/import/network-search/getmodel methods are guarded out. Fresh directories contain no cloud config or saved downloads. Defaults for seed/follow remain; LAN discovery/NAT are disabled and each helper uses explicit pwcchain=regtest. That is a metadata network label, not a running blockchain. Catalogs hold no model payload. Native participation records show one authenticated peer, acquired_models0 and automatic_spend_atoms0. Offline LOCAL zero counters do not rule out independent failed background connection attempts while source is down.

## Evidence and reproduction

Start with `records/native/result.json`, signed `snapshot-2.json` through `snapshot-5.json`, participation snapshots and publisher records. `records/build-result.json` gives commands/source/binary identities. The raw snapshot hashes and exact17→18record maps were verified; the separate RESULT-REVIEW is a source/evidence audit, not an independent run.

[Run44045340230](https://github.com/sunnyriverr/btx/actions/runs/44045340230), executed controller commit a4d1044a30c4b0baa8f0962bcff1f5090df26dd6. Verified checkpoint/fullmanifest,29,776 external inputs (0differences) and exact current tracked source before build. Actual 32-action guard accepted; compile 497.08 seconds. The preliminary dispatch guard stopped before any job for an Atlas-only head advance. One actual job, no build/native failure or repeated test. This is a normal helper build, not an old executable relabelled current.

The exact standalone fixture (SHA256 `90ad5b3ddd2f931de1e7533f4ce6b13a427610ec0d44a7e4de3b4e43d65f8c32`) was staged under/tmp and executed as an unprivileged user with the matching OpenSSL environment:

```
python3 test.py PATH_TO_NORMAL_BTX_MODELD FRESH_DISPOSABLE_RUNTIME_ROOT OUTPUT_RECORDS_DIRECTORY
```

The fresh runtime root must not exist. The script launches only its own helpers, creates synthetic signed metadata and shuts them down. It uses Unix sockets/POSIX identities. Build the matching normal helper using the repository instructions and OpenSSL 3.5+ with ML-KEM-768/ML-DSA-44. This fixture is standalone, not default functional-runner coverage. The included workflow/setup/build/checkpoint scripts preserve the exact executed retained-cache layout, fixed source/absolute workspace and prerequisites; they are not a one-command clean-build promise for a different machine. No full suite was run.

Binary SHA256 `71f06f37edc1f680398ed2acf35711a38459e48e2bf7b5d84afce4e1ddf70258`. Artifact14311064724records outer digest was verified before extraction. Binary artifact14312106388 and verified private build checkpoint14312635365 remain retained remotely; neither was downloaded/restored locally. Their metadata/digests and checkpoint inner hash are in qualification-receipt. All 7 executed controller inputs were read back and hash-verified. No TLS private keys, runtime identity files, wallet data or model payloads are included in this evidence.

## Limits and decision

This supports automatic metadata ingestion, persistence and reconnect continuation for explicitly configured helpers on one Linux loopback host. Not independent physical hosts, LAN beacon discovery, WAN reachability, first-model/bootstrap, payload retrieval, inference/training, payment, nativeMac/Windows, persistence faults, large/changing indexes, long partitions, full-suite or release qualification. No defect/fix or fail-before/pass-after repair comparison is claimed. The current scoped question is resolved; a repair is not justified from this passing result.
