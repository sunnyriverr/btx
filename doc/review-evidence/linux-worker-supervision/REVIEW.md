# In-tree Linux supervision regression — bounded source and evidence review

Reviewer: delegated child `/root/linux_in_tree_review` of BTX session 2, 4 November 2026. Review only; no build, test, VM, Git, product-source or ledger changes. This file is the only reviewer output. Parent session reservations remain in force. Publication remains held.

**Verdict: no unresolved issue found in this narrow regression integration. The inspected final artifacts establish the actual root-generated production jail object build and dedicated regression build/link, with four expected report-fault failures before and all twelve cases passing after. This is artifact review of the owner's Linux run, not a reviewer rerun or a full project build/suite qualification.**

## Reviewed inputs

Read the operating charter, lifecycle, current owner/bookings and selected task, latest NEXT-RUN receipt, evidence/REPORT.md and evidence/REVIEW.md. Examined complete `src/test/swarm_fsjail_linux_tests.cpp`, `swarm_fsjail_linux_worker.cpp`, `src/modelnet/swarm_fsjail.cpp`, relevant `swarm_process_guard.h` paths, the Linux CMake block and root test/interface wiring. Final evidence review additionally inspected `run_project.py`, `compare_project.py`, `configure.log`, `comparison.json`, both build/CTest/identity logs and the retained copy-option compile pilot. No test was independently executed by this reviewer.

Reviewed source SHA256:

- `swarm_fsjail_linux_tests.cpp`: `57acc1ab8746621274f0399397e215a48c0ded558b37cbcbed87e6f208f2caf6`
- `swarm_fsjail_linux_worker.cpp`: `f1c50ea67d09c4b26f6f9e65dda67b7c430f2204801e43a8bc72e4fd9c918f1c`
- `src/test/CMakeLists.txt`: `4197a75970cf2d72dfb9dd112d7b89d762d08c9d97b465da094dc74c8b808a14`

## Oracle and fault isolation

The ordinary exit controls require JAILED, launched/jailed flags, an empty error, and exact exit status for 0, 37 and genuine worker 126. Every running-worker case additionally requires output showing PID 2, the expected soft/hard address-space limit, and successful fork/reap of a child exiting 17. Thus a generic setup refusal cannot satisfy a report-fault case. The signal case requires refusal after verified worker execution; it does not claim raw signal-status or core-bit verification.

The report-fault controls are zero report bytes, partial report, init exiting zero without a report, and a stopped-status payload. Process-local `g_reporting` is enabled after init's successful `waitpid(-1, ...)`. The host wrapper and public guard wait for specific positive PIDs, so they retain real writes, including the corrected trusted error report. The worker is a separate executable and has no link wrappers. The four faults therefore target the trusted init's int-sized report without changing namespace setup, worker behavior or the outer correction. In the reviewed TU there is no other post-wait init write competing with that report.

The added refusal controls cover an invalid executable, a regular file blocking pivot-root setup, a pre-launch tree limit, and unsupported network policy. They require exact public codes/error strings and absence of worker output. These controls supplement the legitimate-worker matrix; they do not establish timeout, surviving-descendant or general containment coverage.

## Availability, limits and cleanup

The first ordinary case returns CTest skip code 77 on JAIL_ABSENT unless `BTX_TEST_REQUIRE_LINUX_JAIL` is present. CTest explicitly recognizes 77. **Qualification on the available Linux host must set this variable**, so a setup failure or normal-path regression fails instead of skipping. Its presence is the switch: even a value of `0` requires the jail. The skip probe is intentionally coarse because the public API does not distinguish namespace unavailability from other setup failures; a skipped ordinary run is no runtime coverage, not evidence of correctness.

Expected RLIMIT_AS is `min(8 GiB, inherited hard limit)`, matching `process_guard::Limit` on the current 64-bit Linux target. The worker observes both soft and hard values without memory exhaustion. An inherited cap too low to launch the fixture can refuse; required-namespace mode exposes that as a failed qualification rather than evidence that the memory policy changed. This review does not qualify a 32-bit target.

Each case uses a unique canonical temporary root and RAII removal. Streams close before case teardown. The real API synchronously waits/reaps and retains its existing process-group and namespace-init cleanup. The fixture forks only one child and reaps it before reporting. No new background process was introduced by the test. The destructor deliberately ignores filesystem cleanup errors, so source review alone does not prove artifact removal; retain the parent's post-run process/filesystem inventory as cleanup evidence. Abrupt external test termination is not covered by RAII.

## CMake integration and completed narrow qualification

The dedicated target is inside the existing WITH_MODELNET/Linux/static-toolchain guard, with the static helper built separately. Fault linker options apply only to `test_swarm_fsjail_linux`; production binaries and `test_btx` are not wrapped. The regression compiles the actual jail TU with `core_interface`, which supplies project compile settings and Threads::Threads, plus the source include root. The root enables testing under BUILD_TESTS and includes this directory only then. The registered CTest command names the executable target and the generated worker path; build dependencies produce the helper and regression when `test_btx` is built. The 60-second CTest limit exceeds twelve nominal three-second API deadlines, although setup/host delays are not a hard total-time proof.

The static availability check and existing static probe remain the platform prerequisite. If static libraries are unavailable, this block supplies no regression target; qualification must verify target/test existence rather than treating an empty CTest selection as success. Final logs show the actual GNU-compatible wrapper link and CTest finding/executing the named test. The retained pilot shows the worker's separate successful static link.

The root recipe configures BUILD_TESTS=ON and WITH_MODELNET=ON. The configure log succeeds with GNU 14.2.0 and the real project's C++20/hardening settings. Both final verbose build logs show successful compilation of `src/modelnet/CMakeFiles/bitcoin_modelnet.dir/swarm_fsjail.cpp.o`, compilation of the same TU into the dedicated regression, and successful dedicated executable linkage. The production object uses the actual bitcoin_modelnet target's definitions/includes/OpenMP setting; it is not the dedicated target's object relabeled as production evidence.

The comparison recipe sets `BTX_TEST_REQUIRE_LINUX_JAIL=1` for both exact named CTest invocations. Before is the previous PID-isolation candidate with the preserved accepted cap, not stock accepted46. Its jail TU SHA256 is `2435f2b656bdc19ecdc43533a5b2bf0d39367fdb4034aa7fb80c4e0a52943b94`; corrected after is `c241070f97a58d7db9ec03b6375bc139ed3436a772e53c09d499f8e9ac90d3ec`. The three test-source/CMake hashes above and static-worker binary hash are identical on both sides. The only test-source adjustment since initial review explicitly supplies `fs::copy_options::none` to the repository's three-argument `fs::copy_file` API. The first compile failure is retained in `pilot-copy-option-build.log`; it ran no cases, and both final sides use the corrected call.

`comparison.json` matches both raw CTest logs: before CTest returns 8 with exactly scenarios 4–7 failing their refusal assertions; the other eight controls pass. Corrected after CTest returns 0 with all twelve scenarios passing. Both run the named regression, not an empty selection or a skip. All eight running-worker cases on each side report PID 2, soft/hard RLIMIT_AS 8589934592 and child=17. Ordinary exits 0/37/126, signal refusal, invalid exec, failed pivot setup, tree limit and network-policy refusal remain passing controls. The production object and dedicated binary hashes change with the TU; the worker binary is unchanged. The actual result supports the narrow defensive reporting classification and maintained Linux regression integration.

Scope remains production **object** compilation plus dedicated regression build/link/execution on the owner's Linux host. The entire bitcoin_modelnet archive, `test_btx`, full unit/functional suites, full node/helper/model workload, glibc/other-platform builds, stress, timeout/descendant cleanup and release qualification were not established. The public API exposes refusal, not numeric EIO; EIO remains source-verified. Final process/filesystem cleanup is the owner's closeout responsibility and was not independently observed here. No upstream posting is authorized by this review.
