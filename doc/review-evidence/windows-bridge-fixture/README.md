# Windows bridge fixture evidence

Same generated Windows clang-cl command: baseline FAIL, candidate PASS. Base main074dac167c26c1e091198f691ed5727817dba88a; one source file, added platform guards only.

Windows Server2025x64, clang-cl20.1.8, MSVC14.51.36231, SDK10.0.26100.0. Tests-enabled Release/static configure with wallet/ModelNet/ZMQ enabled; GUI disabled. Native baseline https://github.com/sunnyriverr/btx/actions/runs/43694025473 fails at31:10 unistd.h notfound, exit1/7.06s. Candidate https://github.com/sunnyriverr/btx/actions/runs/43695054874 passes same exact generated compiler command, exit0/12.41s. 20 portable testcase symbols retained, unsupported Unixintegrationcase absent on Windows. See result JSON and compilerlogs.

The Unixcase usesmkdtemp/unlink/rmdir and helperUnixRPC; production CallUnixRpc returnsunsupported under_WIN32. Guard that case/header only. Every POSIX assertion and cleanup statement is unchanged; removing the added guards exactlyrecovers the originalsource. No freshPOSIXcompile/runtime test. Objectsymbols prove retained compilation/registration, not executed passingtestbodies. No fullWindowsunitlink or fullunitrun, nor releasequalification.

The CMake generated object target had unrelated order-only dependencies: an initial dryrun scheduled15actions and was stopped before compilation. Subsequent diagnosis/candidate invoked the exact compile_commands.json entry directly using retained headers, without alteredflags. No unrelated objects/libraries/executables changed, and immutable remote caches were not overwritten. Reproduction: use native profile/cachepreflight, configure BUILD_TESTS=ON, locate the modelnet_bridge_tests.cpp entry, run it in its directory before/after applying bridge-fixture.patch, inspect resultingobject symbols. Full Ninja target linkage remains outside this result. Included scripts/workflows pin actual inputs and show the exact path.

Credit: JPP's native Windows matrix exposed the existing unit-build gap; repch1c's earlier portability work and the retained Windows dependency/build setup were reused. This guard patch and its paired native object evidence are sunnyriverr's contribution; no reused patch authorship is implied. AI-assisted preparation/review. All native results and limits are as recorded.

No production behavior, consensus, wallet rule or helper implementation is changed. This addresses one #356 compile prerequisite; it does not close #356. #714 was open on4dc0607f during review and doesnot touch this fixture.
