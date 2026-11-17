# PR813 native Linux verification

Tested proposal `d87147f647b6aa20e810554c6ad39b39f7285225`; baseline release-0.34.17 `bd847e2b986722c1723b4cd60988d4f4908452d4`.

Alpine aarch64 in the existing Lima VM, Linux6.12.81, GCC14.2.0. Identical published C++ controller: baseline exits7 at original-file preservation assertion; candidate exits0/all8cases pass. Actual production ExecuteBtxAcquisition and its path/SHA384/credit dependencies execute. All44 source/controller input hashes verified before compilation; UniValue compiled from source too. One matched pair; raw commands/stdout/stderr and binary hashes are in results.json. No expected defect failure is classified as a build failure.

Cases: valid stale replacement, missing-source preservation, wrong-digest preservation, real short-write preservation, exact retry after restoring limit, matching-cache reuse, fresh destination and symlink refusal. Failure releases credits and has no ready receipt; stage cleanup checked. Disposable guest files removed and VM stopped.

Source/controller and Mac evidence are linked from the PR body. run.py is the executed Linux driver; it compiles baseline/candidate with GCC C++20 and section garbage collection. Reconstruct its directory using source paths/input-manifest.json from the baseline, candidate.cpp from the proposal's package_execute.cpp, and controller.cpp from test/standalone/modelnet_acquisition_replace.cpp. Run only as a standalone process against a disposable fixture directory because the fault changes process-local RLIMIT_FSIZE/SIGXFSZ. The recorded manifest verifies the exact materialized source set; this is not a full configured node build.

Limits: empty resource-ID plan and admission trap; no admission-registry/RPC/helper-daemon/GPU/full-suite/concurrency/process-crash/power-loss qualification. **Native Windows compilation and equivalent failure/retry verification remain pending.** This POSIX fault controller is not a Windows test. No new product change was needed for Linux. Earlier storage-blocked preparation ran no tests; after lossless old-log compression, the one final Linux build/test pair completed with no compiler diagnostics.
