# Corrected live-module qualification evidence review

Independent bounded child review, 18 November 2026. Offline source and retained-evidence inspection only; no candidate import/execution, configure/build/CTest, network, wallet access or fork mutation. Only this report was written. No correctness or evidence-consistency finding.

Run44267788274, exact commit `b21e44a8ec26106b59c177befc75f689ae0a692b`, completed successfully. This review verified the downloaded344352-byte artifact against SHA256 `a08d833d3b128eed7905e7f651e49b91a81bb06ec136a6bce11d36db85e0acf5` and compared all301ZIP members with the extracted records.

## Independently checked result

| Profile | Variant | Verdict | CTest exit |
| --- | --- | --- | --- |
| gcc-minimum-make | before | EXPECTED_BASELINE_FAILURE | 8 |
| gcc-minimum-make | after | PASS | 0 |
| gcc-minimum-ninja | before | EXPECTED_BASELINE_FAILURE | 8 |
| gcc-minimum-ninja | after | PASS | 0 |
| clang-minimum-ninja | before | EXPECTED_BASELINE_FAILURE | 8 |
| clang-minimum-ninja | after | PASS | 0 |
| gcc-modern-ninja | before | PASS | 0 |
| gcc-modern-ninja | after | PASS | 0 |

Eight CTest contexts selected sixteen unittest cases: thirteen successful cases plus three deliberate baseline positive-case failures. All four candidate contexts pass both cases. The three minimum-CMake baseline contexts each fail exactly one assertion with malformed RUNPATH and relocated exit127; their opt-out case still passes. The modern baseline remains healthy. No setup errors or skips; all scratch-removal flags true. The outer controller completed in7.41seconds, with30commands and no recorded timeout.

Actual retained before/after source bytes confirm the same maintained test (`19966d727ef9b4e421c3eea03d3521fdada0868cc614dff3a5029818726aedb3`) and actual CMake registration on both sides. Only the module differs: before `37ee13e64da0c6560bb471f19499a125e017ead1f0853cd6230e2d98665ca440`, after `408f103c99df4e3a3f7938b2aea4ee2799afbff3703034d43c3b13d262f7d53e`. All eight observation reports bind the expected live path and unchanged module hash. All discovery records select one correct maintained entry and120-second timeout; BUILD_TESTS=OFF discovery selects zero entries. JUnit agrees with the expected three failing/five successful CTest contexts.

The real readelf logs match all observed RUNPATH/RPATH values. Successful positive controls have literal `$ORIGIN/../lib`, exact marker output, missing-library exit127, and restored output/exit0. Every opt-out probe has no RUNPATH/RPATH and fails to load its unique shared dependency. All tiny builds completed, and build logs retain the caller's `-Wl,--as-needed` flag. Command output records, not only aggregate summary flags, support the key boundary observations.

## Limits

This qualifies the new maintained test through the actual changed CMake registration included in a small wrapper. It does not show a full BTX root configure/build/default-suite run or whole release acceptance. No libpython/desktop/archive integration, CUDA, other architecture, Mac/Windows, cross build, Ninja Multi-Config or actual wallet result. Inner scratch removal is supported by test receipts; no probe binaries survive for a second offline ELF examination. Earlier original run44259884679 remains a preserved setup failure with zero cases; this corrected success must not rewrite it.
