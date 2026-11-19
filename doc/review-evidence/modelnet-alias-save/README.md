# ModelNet alias save evidence

The same external fixture ran on the stock and patched standalone Linux x86-64 helper on `c97c9a8d`, Ubuntu 22.04 and OpenSSL 3.5.9. The saved baseline was reused. [Paired verification receipt](VERIFIED-QUALIFICATION.json) records the tested binary, patch and fixture hashes.

| Case | Baseline | Candidate |
| --- | --- | --- |
| Readable index with blocked save | Both mutations acknowledged and visible only in memory | Both returned a write error. The live aliases and saved bytes stayed unchanged |
| First clean reopen | New alias gone, removed alias back | Original aliases preserved |
| Identical retry after writes recover | Both saves and final reopen passed | Both saves and final reopen passed, with one sequence advance per saved edit |
| Unrelated alias | Preserved | Live and signed disk record unchanged |

The [alias fixture](observe-alias-save.py) extends repch1c’s [#644](https://github.com/btxchain/btx/pull/644) healthy-save checks and reuses the existing [local RPC driver](observe.py) and [helper lifecycle](pr495.py). [Baseline raw result](before.json) · [Candidate raw result](after.json). The CI steps are named **Observe alias writes, retry and clean restarts** and **Run the identical alias fixture on the candidate**. [Baseline run](https://github.com/sunnyriverr/btx/actions/runs/44522442459) · [Candidate run](https://github.com/sunnyriverr/btx/actions/runs/44526957414).

The [Mac component result](component-result.json) checks event ordering using the exact commit blocks, a stub search index and event collector, and temporary filesystem writes. #800’s unreadable-load guard is unchanged. The published release base `26d5d2dd` was reviewed in source only. Linux evidence covers the standalone helper and clean restart. Full node, packages, other operating systems, peer propagation and peak memory on large indexes remain outside scope.
