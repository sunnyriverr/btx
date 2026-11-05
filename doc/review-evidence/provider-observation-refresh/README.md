# Signed provider observation refresh

**Before: newer signed provider records update the cache but leave views stale. After `a457c09e`: the same final regression passes 102/102 assertions.**

Code: `a457c09ec9e0ff933dfa5e1440c4295ba383c385` on accepted `666673a3153225ba264c7870e0e82e354df86765`. The PR contains only `src/modelnet/helper.cpp` and the maintained regression in `src/test/modelnet_search_tests.cpp`.

## Behavior and result

A provider advertises sequence 10, then a correctly signed sequence 11 with changed completeness and direct/relay reachability. Native PUT accepts it and GET returns 11. Before repair, a LOCAL search refresh keeps the old observation; afterward search cards, provider details, availability and peer counts follow the accepted record. Both complete-to-partial and partial-to-complete are exercised. A signed sequence 9 is rejected with `sequence rollback`, and 11 remains in the cache.

| Scoped native run | Before | After |
|---|---|---|
| Final maintained case body, accepted-base helper | 14/102 assertion failures; exit 201 | 102/102 pass; exit 0 |
| Same body with pending #413 | 14/102 failures; exit 201 | 102/102 pass; exit 0 |
| Original probe, both completeness directions | Earlier baseline exit 1 each | Exit 0 each |
| Separate timed-history and #413 adapter | Initial stale-view failure established | 138/138 assertions pass |

These are assertions, not 102 or 138 distinct test cases. The separate adapter includes the initial 124-assertion body and 14 local-projection assertions. It verifies that an expired cache record disappears while its historical observation remains, and that local seed/unseed projection does not lose remote observations. The timed check is deliberately excluded from the final maintained regression; that deterministic body adds search-card assertions.

## How it was executed

Native Alpine 3.22/aarch64/musl, GCC 14.2, existing retained CMake O1 profile including its `-include cstdint` prerequisite. A fresh byte audit matched all 14,310 tracked source files. The component runner executes the exact new in-tree case body; only `BasicTestingSetup` is replaced by a disposable root. Real helper handlers, signature generation/verification, provider cache, catalog and serialization run.

The retained build source is `5eb69ade93cf148edb693fa6dadbe54db9bccb17` (accepted base plus unmerged #413). That source differs from the accepted base only in `helper.cpp` and its Python test. For the standalone pair, the **entire** accepted-base helper translation unit and then its repaired version were compiled as isolated object overrides before the unchanged archives. Other C++ and headers are identical. Thus the final standalone case does not depend on #413. This was a partial compile/relink, not a clean full-tree build. Fourteen retained library hashes and the original helper bytes remained unchanged.

`result.json` records the exact compiler/link/run commands, source/object identities and the standalone executable hashes captured before execution and checked afterward. `component.cpp` contains the final maintained case body; `history-413-adapter.cpp` is the separate integration check. The four `*_guest.py` files are the actual executed phase drivers for that retained build, not a portable one-command wrapper. Their temporary workspace prerequisites have since been removed. The first helper compile was killed with 1 GiB of VM memory; unchanged code/profile compiled with 3 GiB. No kernel OOM trace was available, so memory pressure is an inference. A resumed metadata write was repaired from retained evidence before the final pair; initial and final harness hashes are distinct and preserved.

For a normal maintained unit build, the intended entry point is:

```
build/bin/test_btx --run_test=modelnet_search_tests/search_refreshes_signed_provider_observations
```

That full-suite entry point was **not executed here**; the logs establish the exact component-body runs described above. `standalone_guest.py` records the actual standalone execution; `guest-preflight.json` and `native-build-profile.json` retain its build prerequisites.

## Boundaries and credit

No full `test_btx`, node/helper transport, PQ1 handshake, remote transfer, Atlas UI, macOS/Windows, concurrency stress, live-network or release qualification. Snapshot serialization has source review; it does not promise that each PUT updates views before a search refresh. Existing equal-sequence acceptance and cache-expiry policy are unchanged. Absent historical entries are retained rather than assigned a new TTL.

Existing BTX copyright/authorship is retained. This repair is by Sunny River. The integration control preserves #413's local-provider correction; that earlier finding and review are credited to repch1c in #413. No external contributor's new authorship or independent replication is claimed here.

Logs have only ANSI color escapes removed. `manifest.json` records public hashes; `source-map.json` maps them to local evidence hashes. Public JSON contains synthetic fixture advertisements and signatures, not private keys or wallet data. No tests were repeated for publication.
