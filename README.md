# #495 Linux full-catalog upgrade and restart

Tested ACK 591ec11e, scoped to the real Linux helper catalog/RPC journey.
Credit to repch1c for the repair and original Mac tests. This adds a full old
catalog upgrade/restart observation on Ubuntu 22.04 x86_64, GCC 11.4, C++20/O2,
with the retained OpenSSL 3.5.9 build profile.

The stock helper created the saved input through addmodelnode: 63 syntactically
valid loopback endpoints (IPv4 and bracketed IPv6), plus the invalid string zz.
The exact same catalog bytes were copied into isolated stock/candidate stores.
The same journey and acceptance function ran against both real btx-modeld
binaries through their Unix RPC socket.

| Check | Stock dac9aee5 | Exact #495 591ec11e |
| --- | --- | --- |
| Load the full old catalog | Keeps 64 including zz | Drops only zz, keeps 63 valid entries |
| Probe zz before refill | Acknowledges existing invalid entry | Refuses without consuming the free slot |
| Add valid replacement | Refuses: peer list full | Accepts, preserves all 63 valid entries |
| Duplicate / distinct 65th | Duplicate idempotent; overflow refused | Duplicate idempotent; overflow refused |
| Clean restart | Same blocked catalog | Exact 64 valid entries, including replacement, agree in RPC and on disk |
| Responsiveness / normal shutdown / cleanup | Pass | Pass |

## Executed entry point and identities

[Native run 42824148603](https://github.com/sunnyriverr/btx/actions/runs/42824148603)
used the [exact CI fixture 35830c6d](https://github.com/sunnyriverr/btx/tree/35830c6d9abdc92723b44b299a8aa50028c51124).
The executed workflow and Python recipes are preserved under recipe/ here.
Within that workflow's admitted workspace, the two executed commands were:

```sh
python3 contrib/devtools/pr495-catalog-recovery/build_helper.py
timeout --signal=TERM --kill-after=40s 300s python3 contrib/devtools/pr495-catalog-recovery/run_recovery.py
```

The workflow pins the source, immutable Linux checkpoint and stock helper
artifact prerequisites. Candidate source blobs are preserved in the exact CI
fixture; source-manifest.json pins their identities. The complete candidate
Git tree was verified against the author's commit. The maintained unit file
is included in that source identity but was not compiled or run here.

The saved stock binary was reused by SHA-256, not rebuilt. The candidate used
11 admitted compile/link/metadata actions plus ordinary glob verification,
12 Ninja actions total, with no CMake regeneration. Original checkpoint and
stock binary remained unchanged. No broad unit or #473 rerun was performed.

[Provenance](provenance.json), [actual observations](recovery-result.json),
[build identity/actions](build-result.json), [compiler log](candidate-compile.log)
and [identical saved input](old-full-catalog.json) retain the evidence.
All three disposable stores and their generated identities were removed;
normal helper shutdown succeeded without forced cleanup signals.

## Limits

One deterministic paired journey and a clean restart. Contacts are loopback
fixtures; successful peer connections or model retrieval were not qualified.
This does not establish crash durability, other-platform behavior, node,
full-unit-suite or release acceptance. Background authentication may attempt
the loopback endpoints; hosting, LAN discovery, NAT mapping and seed/follow
storage were disabled. No live node, wallet, inference or spending was used.
