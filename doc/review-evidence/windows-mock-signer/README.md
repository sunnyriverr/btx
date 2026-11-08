# Windows mock-signer fixture qualification

**Qualified focused fixture correction: [bed7c506](https://github.com/sunnyriverr/btx/commit/bed7c5069732b42f314755468f89ffcb52ccc61d). The full Windows unit run remains incomplete; this does not close #356.**

Native Windows could not launch these shell mocks through `/bin/sh`. Three generic runtime-error tests could also pass merely because launch failed. The one-file correction selects Git Bash explicitly, uses whitespace-free/short Windows paths, writes LF scripts, and makes those three tests require the intended helper error. POSIX keeps `/bin/sh`; production signer code and acceptance rules are untouched.

| Evidence | Exact before | Exact after | Result |
|---|---|---|---|
| Original 24 affected cases | 37472d88 / binary31e45f1d | 5fd23a82 / binary789576e9 | 20 aborts +4 failures →24 PASS |
| Three previously masked error controls | 37472d88 + stronger predicates / binary3689b56d | 5fd23a82 + same predicates / binary63b84bde | 3 FAIL →3 PASS |

The second row requires the mock's exit1/stderr or the parsed fingerprint error. A missing executable cannot satisfy it. All33changed callers were reviewed:24native path-specific passes, these3stronger controls, and6early request/argument refusals. Existing valid passes were reused; no valid passing test was repeated. Both campaigns verify process/temp/mapping cleanup.

## Exact scope and provenance

- Windows Server2025 x64, clang-cl20.1.8, MSVC14.51.36231 libraries, SDK10.0.26100, staticCRT/OpenSSL3.5.4; Modelnet/wallet/tests/ZMQ ON, GUI OFF. Cached incremental builds, not a clean full build.
- The native integration is based on requested swarm d522af52 with the disclosed #436 executable-path/credential prerequisites, #437 fixtures and adopted #433 socket cleanup. Source37472d88 identifies that full local integration. #436/#437 are now included on release ff5f3f04. **Neither native campaign is a new clean run of the publication commit or stock release.**
- Publication commit bed7c5069732b42f314755468f89ffcb52ccc61d is one file on swarm d522af520f55067bd470fdcc0c246e3b4d3a26fc. Its fixture blob `6709bc98f68e5e1056901ffa5125ab6ce8db1084` exactly matches the native-after qualification overlay. The original fixture blob is identical on tested baseline37472, swarmd522 and releaseff5f. Only three error predicates were strengthened after the earlier24PASS evidence; those24helpers/predicates are unchanged. Do not relabel either historical binary as a build from the final publication commit.
- Original cache10173603864 remains unchanged. Each focused build recompiles the fixture plus3generated build-identity objects and relinks dependencies; the other5881cached objects are preserved.
- Git Bash must be selected first on PATH. The command API has no quote grammar, so it needs whitespace-free command paths or short aliases. Missing prerequisites fail explicitly. Arbitrary WSL/shell layouts, Unicode/space paths without short aliases, MinGW/plainMSVC are unverified.
- macOS: actual extracted helper functions produced identical script bytes and valid/error/argv outputs using filesystem/format shims. This is component evidence, **not full native POSIX BTX execution**. No full Windows/POSIX suites, wallet/mining workflow, production signer device or release qualification claimed.

Original source/license attribution is retained. Credit repch1c and Jpp-matata for Windows prerequisite findings and review context; the runs here are our hosted Windows runs, not attributed to them.

## Executed entry points and records

The maintained `test_btx` selectors, commands, exact source/binary identities and XML are recorded below. For a configured Windows test build with Git Bash first on PATH, the affected suite is `test_btx.exe --run_test=pq_phase4_tests`; the private campaigns used **only the recorded selected cases**, not a fresh full suite. New reviewers can run those selectors from the manifests. The source-build/incremental harness depends on its recorded cache/profile; no fresh-machine reproduction is claimed.

- [Original baseline42436915053](https://github.com/sunnyriverr/btx/actions/runs/42436915053), [launcher24PASS42440607635](https://github.com/sunnyriverr/btx/actions/runs/42440607635), [missing-controls42442778867](https://github.com/sunnyriverr/btx/actions/runs/42442778867).
- [Caller map](caller-coverage.json), [24case verification](launcher-verification.json), [three-control verification](qualification-verification.json), [publication source mapping](code-receipt.json), [artifact/member hashes](MANIFEST.json).
- `records/baseline/` contains the original pq_phase4 grouped logs/XML; `records/launcher/` contains24after logs/XML; `records/qualification/` contains the paired3case logs/XML and exact overlaid sources. Full raw CI archives remain identified by SHA256 in MANIFEST.json; reviewable records are ordinary branch files.
- `recipes/` retains the actually executed controllers and original input descriptions. The qualification manifest inherited obsolete24case count/scope text and the dispatch description incorrectly said saved-binary execution. Actual jobs/XML selected3 and the controller built both binaries. Original descriptions are preserved; the corrected offline description labels these metadata mistakes without claiming a native rerun.

Earlier unsuccessful setup/launcher pilots remain in the original task evidence and CI history:42439421234(cancelledsetup),42439488682(runnerimporterror,noBTXtests),42440011939(24failedquoted/basenameattempt),42440506327(cancelledbeforetests). They are not counted as qualification passes.
