# Obs01 PID repair — code and recipe preflight

**PASS for one bounded native campaign of the scoped repair. Native results remain unobserved.** Reviewed by `/root/obs01_portability_review`; no build, fixture run, source/ref change, VM or publication was performed by this reviewer.

## Product delta

`candidate.cpp` changes only the Windows/POSIX header selection and the PID query used by the existing temporary lab-directory statement. A local `const auto process_id` selects `_getpid` on `_WIN32` and `getpid` otherwise; both feed one unchanged prefix/path construction and the original TempTree lifetime. No shared macro/emulation, qualification flag, gate sequence, directory policy or cleanup implementation changes.

Independently rehashed baseline/candidate bytes and the candidate Git blob against source-manifest.json: baseline482fa81739b1cc94d1947e73fa0fad51cdf86356, candidatec6ab3b58f5eac2d5966818942e6d398408074976. The source inversion in prepare_fixture.py reconstructs the complete baseline after removing exactly the intended delta. TempTree extraction is byte-identical in both fixtures.

The selected native desktop CRT API/header are appropriate: Microsoft documents `_getpid` in `<process.h>` with an `int` process-ID result and no error return. Keeping POSIX `unistd.h/getpid` avoids a new type or API assumption there. See [Microsoft CRT `_getpid`](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/getpid?view=msvc-170).

## Fixture and existing Mac evidence

The fixture uses actual `util/fs.h`, its native path wrapper and byte-extracted TempTree rather than a mock filesystem namespace. Its PID/root block comes from each corresponding full product source. Mac's transitive immutable header closure is recorded separately; it is not silently substituted into the native project checkout. No heavy Obs01 admission/qualification gate is invoked.

The native fixture does not add `<process.h>` to the baseline. Its Win32 GetCurrentProcessId oracle is independent of the selected CRT call, and the Python launcher separately compares the emitted oracle to the actual subprocess PID. This avoids masking the missing getpid declaration merely by including the oracle's CRT header. Candidate and mutant preserve that independent oracle.

Actual assertions cover exact prefix/decimal PID suffix, stable naming within the same process, created content, normal/early-return/exception-unwind cleanup, preserved owned parent and unrelated sibling bytes, and an empty fixture parent afterward. TEMP/TMP/TMPDIR are set to a newly owned fixture parent before launch and restored afterward. Failed controls still trigger cleanup of that owned parent; no real wallet/node/temp data is targeted.

The wrong-PID mutant sets only the candidate's PID variable to zero. It must be rejected by the intended suffix assertion, so a compile-only constant-ID workaround cannot satisfy the harness. The runner also requires its nonzero result rather than counting it as a legitimate pass.

Read mac/results.json and independently rehashed all three original run logs and binaries. Baseline/candidate report37checks and0failures each; the wrong-ID control reports25checks/7failures with the intended suffix failures. No Mac test was rerun by this review. These are narrow seam controls, not a Mac full-project or complete Obs01 gate result. Preserve the two missing-transitive-header setup pilots as setup history.

## Native driver and workflow

- Exact current baseecd9310a is checked out with autocrlf disabled. No old project/object checkpoint is restored; existing pinned OpenSSL/vcpkg dependency caches are independently checked as before.
- The real root preset keeps tests/Modelnet/wallet/SQLite/ZMQ enabled, GUI disabled, Release/C++20/static CRT. The generated Obs01 target and unambiguous compile-database entry are required before testing.
- The exact same generated `obs01.cpp.obj` target/command is run on baseline and candidate. Baseline must fail specifically at the observed getpid diagnostic and leave no object. Candidate must exit0 and leave the object. The compile database must remain unchanged. There is no injected declaration, altered target, test pruning or duplicate-symbol workaround.
- Both native MSVC and clang-cl baseline fixtures must fail at the missing PID declaration; both candidate fixtures must compile and pass all37 runtime checks. The clang-cl wrong-PID fixture must compile and fail the intended control. Fixture source hashes are validated before the run.
- Candidate and restored full-source catalogs retain explicit working-blob expectations. A `finally` restores the original Obs01 bytes even after a candidate/control failure. Source verification rejects any unrelated tracked delta. Candidate source/catalog and object hash are retained before restoration.
- Commands have explicit timeouts and owned process-tree termination. Fresh resource checks require6GiB disk/4GiB RAM before the small object campaign. The legacy `native-daemon-build` live-monitor branch is unused by this recipe; it should not be cited as sampled object-stage resource monitoring. This small campaign still has its actual command bounds and preflight guard.
- The35-minute hosted workflow contains only setup/configure/scoped object and fixture work, not a full Modelnet/node/all/unit campaign. Artifact upload runs on failure. Driver status and original logs, not a green Actions badge, determine acceptance.

The dispatcher validates the exact accepted head, expected open-proposal set, completed own diagnostic runs and unchanged owned CI ref before mutation. Uploaded input hashes and the new CI commit are read back. These checks should be interpreted with their public-visibility limit; they cannot exclude private/unannounced work.

## Claims after the run

A successful campaign may establish the actual generated clang-cl translation-unit fail-before/pass-after, native MSVC/clang-cl PID/path/cleanup seam controls, source restoration and the already-run Mac equivalents. It will not establish native MSVC compilation of the whole translation unit, Modelnet archive/node linkage, test_btx execution, Linux/MinGW runtime, LAN discovery, all Obs01 qualification gates or a release. Require the explicit `PAIRED_OBS01_PID_AND_CLEANUP_PASS` result plus retained evidence; candidate-object/setup failures remain failures.

No blocking code/recipe defect found in the inspected revision. Next step is the one planned native run, followed by artifact/identity review and accurate scoped closeout. Preserve the posting hold.
