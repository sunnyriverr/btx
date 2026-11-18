# Linux live-module RUNPATH regression evidence

**Scoped qualification passed** on Ubuntu22.04x86-64, [run44267788274](https://github.com/sunnyriverr/btx/actions/runs/44267788274), exact executed fork commit `b21e44a8ec26106b59c177befc75f689ae0a692b`, release baseline `a97af7b3f379e33e3ec65db948468d875ade2841`. [Three-file patch](linux-runpath-fix-and-regression.patch) · [result and limits](REPORT.md) · [independent internal evidence review](EVIDENCE-REVIEW.md).

The same maintained Python test imports its source tree's production CMake helper. The actual changed CTest registration is included in a small wrapper; this is not a full BTX root configure/build/default-suite run.

| Profile | Original helper | Fixed helper |
| --- | --- | --- |
| GNU11.4 / CMake3.22.1 / Make4.3 | malformed `$$ORIGIN`, load127; intended failure | literal `$ORIGIN/../lib`, load0; both tests pass |
| GNU11.4 / CMake3.22.1 / Ninja1.13.2 | malformed `$/`, load127; intended failure | literal path, load0; both pass |
| Clang14 / CMake3.22.1 / Ninja1.13.2 | malformed `$/`, load127; intended failure | literal path, load0; both pass |
| GNU11.4 / CMake4.3.0 / Ninja1.13.2 | healthy; both pass | healthy; both pass |

Eight CTest contexts, sixteen unittest cases:13passed and3intentional baseline assertion failures. All8candidate cases passed; no unexpected failures/errors/skips. Missing/restored-library controls passed in five healthy positive contexts; all eight opt-out controls passed. Caller flags, exact source/tool binding, BUILD_TESTS=OFF registration and scratch-cleanup checks passed. Controller7.41s, not total job duration.

[Raw successful artifact](artifact14410343779.zip) contains all301record members: generated CTest files/JUnit, same before/after test and registration, live module copies, per-case observations, commands/readelf logs and summary. [Machine-readable audit](OFFLINE-AUDIT.json) and [summary](results/SUMMARY.json) are convenient indexes. Artifact344352bytes SHA256 `a08d833d3b128eed7905e7f651e49b91a81bb06ec136a6bce11d36db85e0acf5` matches GitHub metadata.

[First attempt](https://github.com/sunnyriverr/btx/actions/runs/44259884679) failed before any case because sparse checkout omitted the workflow file required by hash admission. Its [raw artifact](setup-failure/artifact14406889235.zip), logs and [summary](setup-failure/SUMMARY.json) remain preserved. The correction changed checkout selection and its recorded workflow hash only, not the product test or fix.

## Reproduction and limits

The maintained entry is `python3 test/util/install_binary_component_runpath_test.py --cmake /usr/bin/cmake --compiler /usr/bin/g++-11 --generator "Unix Makefiles" --output-dir /tmp/btx-runpath-review`. It needs native Linux, CMake>=3.22, GNU/Clang C++, matching Make/Ninja, Python and readelf; it compiles tiny probes. This is a reconstruction command; the recorded run used the actual CTest command captured in SUMMARY.json. The exact executed [workflow](recipe/linux-replacement-pilot.yml) and [controller](recipe/qualify.py) show the paired recipe at the immutable fork commit. Only that CI recipe was executed here; no additional rerun is claimed.

Not tested: full BTX build/default suite, actual libpython/desktop/archive integration, CUDA, other platforms/architectures, cross compilation, Ninja Multi-Config or release acceptance. No real wallet/keys/coins. Earlier external-fixture evidence is not silently substituted for this live-entry result.

Credit JPP's release-verification coverage, Numair's integration and preceding correction, and jarekpiot's [Ubuntu source-build report](https://github.com/btxchain/btx/pull/714#issuecomment-6964571992). [Numair's correction and CMake3.22 limit](https://github.com/btxchain/btx/pull/714#issuecomment-6965315375) supplied the follow-up question. All evidence files are content-hashed in MANIFEST.json and SHA256SUMS.
