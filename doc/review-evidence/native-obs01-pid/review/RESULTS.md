# Obs01 PID repair — final code, artifact and claims review

**PASS for the scoped native PID portability fix and its tested limits.** Reviewed by `/root/obs01_portability_review`; no builds, fixture reruns, product edits, GitHub writes, VM activity or changes outside review/ were performed by this reviewer. This is independent inspection of retained execution evidence, not independent execution on another Windows machine.

## Exact product and native target

The prepared one-commit product branch is `1b404ed8e52eae249ac73036007ba5a382b0d3ba`, parent `ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629`. The only changed file is `src/modelnet/obs01/obs01.cpp`; candidate blobc6ab3b58f5eac2d5966818942e6d398408074976 matches the tested SHA-2566d99bda4088f5f2cdee7d7596771edc7169b92b8aa46b570234025178719df80. Source-manifest bytes/blob and final Git diff were inspected. The commit preserves the original file attribution and credits repch1c's Windows inventory and Jpp-matata's build investigation without claiming either performed these new tests.

The patch includes `<process.h>` and calls `::_getpid()` only on Windows; POSIX retains `<unistd.h>`/`::getpid()`. A local auto variable feeds the one existing `btx-obs01-` path expression. The original TempTree, LabDir/PrepareLab implementation, gate ordering and qualification state/flags remain unchanged. There is no shared compatibility alias, global emulation or unrelated repair.

Native run41790329187, controlsbd06c940138482ee8588dc7b81a5ba0289695573, ran the actual current-base generated target:

```text
src/modelnet/CMakeFiles/bitcoin_modelnet.dir/obs01/obs01.cpp.obj
```

The accepted baseline exits1 with the intended diagnostic at obs01.cpp120: global getpid is missing. The candidate exits0 and produces the retained project object. Independently compared the actual logged clang-cl invocation before/after: identical, not merely similarly named CMake targets. It uses clang-cl20.1.8, native Windows/MSVC ABI, C++20, /MT, the real project include paths and forced compatibility prelude. No source declaration was injected through altered compiler flags.

Root configure exits0. CMakeCache and the5897-entry compile database retain Release, tests/Modelnet/wallet/SQLite/ZMQ enabled and GUI disabled. There is no old project checkpoint restore or pruned target list in this narrow campaign. All command timeouts are false. The resource claim is the actual pre-object guard, not the unused legacy daemon live-monitor branch.

## Runtime controls

Both baseline extracted native fixtures fail at getpid specifically: MSVC C2039/C3861, clang-cl the missing-global-member error. Neither baseline has an unconditional process.h oracle include that could hide the defect.

Candidate MSVC and clang-cl fixture builds exit0; each runtime reports37checks/0failures. Their independent Win32 PID oracle equals the launcher's actual Popen PID (8164 and5592 respectively). The fixture incorporates the actual product PID/root block and byte-identical TempTree, uses real util/fs.h and verifies prefix/suffix, repeated same-process naming, owned content and normal/early-return/exception cleanup while preserving an unrelated sibling and owned parent.

The wrong-PID constant mutant compiles, then exits1 with the intended PID-derived-prefix/suffix failures. It is an expected rejection, not a legitimate-control failure. The original Mac baseline/candidate likewise report37checks/0failures and their wrong-PID mutant is rejected; those retained logs/binaries were rehashed in the earlier recipe review and were not rerun. All five Mac fixture header files match both their immutable header manifest and the actual native accepted-source catalogs.

These runtimes execute the extracted PID/path/cleanup seam, not the complete Obs01::Pass gate sequence. They establish neither full lab admission nor all recovery/qualification behavior.

## Provenance and restoration

Independently rehashed all23 native command logs, all three retained native fixture executables and the actual project object against result.json. Independently verified the retained ZIP SHA-256 against the GitHub artifact digest62470d09c27b6452550dfa329e88deb2e47a138b1cf14ab3e2f938e4d7f3322d. The actual baseline/candidate target command arrays and logged compiler command are identical.

The14309-entry before, baseline-after, restored and final-after catalogs agree. Candidate-before and candidate-after agree with each other and differ from baseline only at Obs01's expected working blob/SHA. The product file was restored to accepted-base bytes. Parent verification.json's scoped verdict is supported by these retained artifacts. The differently counted14307-entry older13bb integration evidence remains historical; it is not mixed into the currentecd source identity.

## Delivery limits and next step

This evidence supports a currentecd actual clang-cl translation-unit fail-before/pass-after plus native MSVC/clang-cl extracted runtime controls and Mac POSIX seam controls. It does not establish a complete native MSVC Obs01 translation-unit build, a linked Modelnet archive or node, full test_btx, Linux/MinGW execution, LAN discovery runtime, all Obs01 qualification gates, GPU behavior or release qualification. A green Actions run alone would not establish those outcomes; the explicit paired status and original logs establish the narrower result here.

No blocking defect found in the final code or tested scoped handoff. Parent should finish evidence/owner/wiki closeout, preserve the no-posting hold and perform any fresh adoption/coverage check before authorized delivery. The full #356 native node/unit acceptance gate remains open.
