# Evaluation evidence timing repair

Product commit `b2e2dab120aaee027f575ff96e82fc43c8a8e8f2` on `codex/fix-security-evidence-time`, based on exact `fd3a905fed3bc4943ad24372da032af4d29304a3`. The product branch changes only five reviewed service files; this separate branch carries the regression fixture and recorded evidence.

Two concurrent valid jobs can produce a stale completion timestamp and lose a report to clock rejection. The repair uses fresh serialized time for current evaluation admission and local receipt/report persistence, retaining strict rollback checks and signed event timestamps. Current authority and expiry are rechecked before storage.

- [Recorded result and scope](recorded/REPORT.md): same harness baseline **3/7**, candidate **7/7**, combined #381 original seven-job case PASS. Each selected invocation ran once.
- [Source-only regression and reproduction entry](regression/README.md): exact tested harness and diagnostic source overlays, no binary dependencies. Dry assembly proves source identity; the newly portable build/driver recipe has not been executed end to end.
- [Results and exact identities](recorded/summary.json), [raw case artifacts](recorded/linux/results/), [internal review](review/REPORT.md).

Configured native Alpine/aarch64 component with an explicit 8 MiB ELF stack and identified reused dependency archives. No default-stack/full-daemon/macOS/Windows/stress/release qualification. The rollback control changes the persisted time bound and calls strict APIs; it does not move the operating-system clock. Shared canary/work receipt completion was source-reviewed, not separately runtime-qualified. Other explicit-time callers remain unchanged.

[Product source identities](recorded/product-files.json) and [mapping to actual compiled sources](recorded/patch-and-compiled-source-checks.json) preserve the exact tested code. The historical missing-report event remains unproved because its original failing row was not retained. This evidence establishes the newly reproduced mechanism and repair.

Unnecessary local paths in recorded documentation are normalized; `publication-manifest.json` records original and branch text hashes. Synthetic public signatures are test artifacts. No private identity keys, databases, executables or compiled archives are included. Internal agent review is not independent human/platform replication.
