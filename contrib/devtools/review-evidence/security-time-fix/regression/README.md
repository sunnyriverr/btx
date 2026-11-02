# Security timing regression source package

This source-only package reconstructs the exact recorded harness, diagnostics and baseline/candidate/combined security sources. It contains no compiled archives, executables or duplicate production translation units. The timing product patch is over `fd3a905fed3bc4943ad24372da032af4d29304a3`; the combined variant adds #381's service-only scheduling change while retaining the timing fix.

Prerequisites: an exact clean checkout or source archive of that revision; native Linux; Python3.9+; CMake3.22+; a C/C++20 compiler; SQLite development files; pthreads; and a static libc toolchain for the real probe. The recorded execution used aarch64 Alpine/musl/GCC14.2. Source bytes are checked before assembly; the source tree is read only. Choose a new or empty work directory outside the checkout.

One entry point:

```sh
python3 reproduce.py --source /path/to/exact-fd3a-source --work /path/to/new-private-work
```

The command validates681 required input files, applies strict source patches without Git writes, and checks all72 reconstructed source/harness hashes against recorded tested inputs. It then builds the official upstream standalone crypto/JSON targets from source, compiles the same timing object/executable composition, and runs the fixed15-invocation sequence: seven cases per baseline/candidate and one combined #381 seven-valid-job case. Reports and snapshots go under the selected work directory. The driver records each result, including intended baseline failures; judge the matrix in `final-sequence.json`, not orchestration exit status alone.

Recorded result: baseline3/7, timing candidate7/7, combined affected case PASS with seven genuine native PASS/dispatched reports. Baseline pause denied through its stale-clock failure; that does not establish a working late permission check. Candidate refusals use the intended rollback, expiry, pause, revocation and local-permission checks. The clock guard remains strict.

The explicit8MiB ELF stack configuration is material. This is component evidence, not default-stack, full-daemon, other-platform, stress or release qualification. Canary/remote-work receipt scope was source-reviewed; those whole workflows were not run. Historical missing-report causality remains a separate limitation.

**The packaged entry point is now verified end to end.** The exact package from evidence commit `d7dd7974` was run once against clean exact `fd3a905f` source in the native Alpine/aarch64 VM. It rebuilt the official crypto/JSON dependency targets from source, then ran the fixed 15-invocation sequence: baseline 3/7, candidate 7/7 and the combined seven-valid-job case PASS. No package, product or oracle edit and no retry was required. See [the verified execution receipt](../verified-entrypoint/REPORT.md).

The earlier `self-assembly-receipt.json` records the source-only preparation stage and remains historical evidence. This README and the package file catalogue were updated after execution; CMake, driver, assembler, harness and patch bytes remain identical to the executed sealed package. The normalized reference files under `provenance/` identify the earlier private build and retain its original hashes. The packaged run independently builds dependencies from source and makes no binary-identity claim across those two builds.
