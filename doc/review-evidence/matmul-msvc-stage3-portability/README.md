# MatMul Stage 3 MSVC portability evidence

Against `c2e71aafc48a41593277e335c8bc370e45599f01`, candidate `1332e7a6545c19af3fa04da329fd55845aa1981b` changes two production files. The codec precomputes the 17-field FRI batch arity before recursive visitation. `CheckedCost` uses the existing `btx::U128` alias.

## Windows Server 2022 x64

MSVC 19.44.35230, SDK 10.0.26100.0 and Ninja Release. Both jobs restored the same verified `x64-windows-static` vcpkg cache. Their [two compiler commands](msvc-two-commands.json) and generated configuration header matched by SHA-256.

| Object | Stock | Candidate |
| --- | --- | --- |
| Bounded semantic codec | Exit 2, C1202 at line 107 | Exit 0, valid x64 COFF |
| Relation-local sharding | Exit 2, C2065 for `__uint128_t` at line 224 | Exit 0, valid x64 COFF |

[Stock run](https://github.com/sunnyriverr/btx/actions/runs/45999440521/artifacts/15196389756) · [Candidate run](https://github.com/sunnyriverr/btx/actions/runs/46082984003/artifacts/15238435219) · [Stock receipt](msvc-stock.json) · [Candidate receipt](msvc-candidate.json)

## macOS ARM64

Apple Clang 17 built the stock and patched codec translation units into focused executables. The [codec fixture](codec-fixture.cpp) seeded distinct nested FRI fields on both sides of one tile-tree edge. Both executables encoded the same 14,058 bytes and decoded each other's payloads. Both refused a bad reserved flag, trailing data and truncation. [Byte comparison](codec-comparison.log) · [Identical V1 payload](v1-envelope.bin)

The [cost harness](verify-cost.py) used the exact stock and candidate `CheckedCost` bodies with synthetic shard widths to reach overflow without large allocations. All nine cases agreed across stock native, candidate native and candidate forced onto portable arithmetic. Overflow refusals kept prior outputs intact. [Arithmetic results](checked-cost.log)

The archived harnesses record the scoped executions. Full Windows linking and tests, full Mac suites and attached-proof verification are unverified.

Repch1c reported both MSVC failures. Bas independently confirmed C1202 and suggested per-type field counts. [Repch1c's report](https://github.com/btxchain/btx/pull/714#issuecomment-7216466517) · [Bas's report](https://github.com/btxchain/btx/pull/714#issuecomment-7229637772)
