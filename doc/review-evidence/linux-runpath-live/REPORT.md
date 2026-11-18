# Live-module CTest qualification — scoped pass

[Run44267788274](https://github.com/sunnyriverr/btx/actions/runs/44267788274) succeeded at exact fork commit `b21e44a8ec26106b59c177befc75f689ae0a692b`, against release baseline `a97af7b3f379e33e3ec65db948468d875ade2841`. One corrected attempt authorized, dispatched once, no retry. Heads were unchanged and all ten remote payloads byte-matched before dispatch. Session1 SwapNet and Session2 ModelNet ownership/bookings checked; no peer mutation or messages.

## Actual result

The same maintained test and actual `cmake/tests.cmake` registration ran in eight before/after CTest contexts. Each selected two unittest cases: sixteen executed, thirteen passing and three expected positive-case baseline assertion failures. Zero unexpected failures, errors or skips. The controller completed in7.410seconds; this is not total job duration.

| Profile | Original helper | Fixed helper |
| --- | --- | --- |
| GNU11.4 / CMake3.22.1 / Make4.3 | `$$ORIGIN/../lib`, relocated exit127; intended assertion fails | literal `$ORIGIN/../lib`, exit0; both cases pass |
| GNU11.4 / CMake3.22.1 / Ninja1.13.2 | `$/../lib`, exit127; intended assertion fails | literal path, exit0; both pass |
| Clang14.0 / CMake3.22.1 / Ninja1.13.2 | `$/../lib`, exit127; intended assertion fails | literal path, exit0; both pass |
| GNU11.4 / CMake4.3.0 / Ninja1.13.2 | healthy literal path, exit0; both pass | healthy literal path, exit0; both pass |

All eight opt-out checks passed: no RPATH/RUNPATH and unique adjacent-library lookup failure. All five healthy positive contexts passed missing-library exit127 and restored-library exit0 with expected output. Every generated tiny project verified caller flag preservation. Original build location was removed before relocated execution. Each context recorded the same maintained test hash and the correct live before/after module path/hash, unchanged after execution; scratch removal recorded. BUILD_TESTS=OFF generated no matching registration. Actual generated CTest files and eight JUnit records corroborate selection, rather than relying only on the green job badge.

## Evidence and scope

[OFFLINE-AUDIT.json](OFFLINE-AUDIT.json), `records/session3-linux-runpath-results/SUMMARY.json`, per-context SUMMARY/OBSERVATIONS/logs, generated registration, JUnit and raw job log preserve actual observations. Artifact14410343779:344352bytes, SHA256 `a08d833d3b128eed7905e7f651e49b91a81bb06ec136a6bce11d36db85e0acf5`, matching GitHub's digest. All301ZIP members extracted safely. Earlier failed run44259884679 remains preserved, explicitly a checkout setup failure before any regression case; the correction selected the workflow file and updated its manifest hash only.

This qualifies the focused maintained test through the actual registration file in a minimal CMake wrapper on Ubuntu22.04x86-64. It is not a complete BTX root configure/build/default-suite run, libpython/desktop/archive acceptance, CUDA, other architecture, cross compilation, Ninja Multi-Config or Mac/Windows qualification. No upstream PR/comment, wallet, personal keys or real coins were used.

Credit JPP's release-verification coverage, Numair's integration and preceding correction, and jarekpiot's producer report. The helper and maintained regression are now qualified for a focused local fix-plus-test handoff. Next: final consolidated patch/evidence review and one short local handoff; upstream posting remains held. No further test run is justified without a new uncertainty.
