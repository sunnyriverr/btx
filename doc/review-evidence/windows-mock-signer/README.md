# Windows mock-signer fixture qualification

**Focused fix qualified: [bed7c506](https://github.com/sunnyriverr/btx/commit/bed7c5069732b42f314755468f89ffcb52ccc61d). The full Windows unit run remains incomplete; this does not close #356.**

The Windows fixture could not launch its mocks through `/bin/sh`. Three exception tests could also pass on launch failure. This one-file correction selects Git Bash explicitly, preserves LF script bytes and requires the intended helper errors. POSIX keeps `/bin/sh`; production signer code and acceptance rules are unchanged.

| Evidence | Before | After | Outcome |
|---|---|---|---|
| Original 24 affected cases | 37472d88 / binary31e45f1d | 5fd23a82 / binary789576e9 | 20 aborts + 4 failures → 24 PASS |
| Three masked error controls | 37472d88 + stronger predicates / binary3689b56d | 5fd23a82 + identical predicates / binary63b84bde | 3 FAIL → 3 PASS |

The second row requires the mock's actual exit and stderr or its parsed fingerprint rejection. A missing executable cannot satisfy it. All 33 changed callers were reviewed: the 24 path-specific passes, these three stronger controls and six early refusals. Valid passing tests were reused. Process, temporary-directory and drive-mapping cleanup passed.

## Scope and source mapping

Native execution used Windows Server 2025 x64, clang-cl 20.1.8, MSVC 14.51.36231 libraries, SDK 10.0.26100 and static CRT/OpenSSL 3.5.4. Modelnet, wallet, tests and ZMQ were ON; GUI was OFF. These were cached incremental builds.

The tested integration is `37472d88`, based on requested swarm `d522af52`, with the disclosed #436 executable-path/credential prerequisites, #437 fixtures and adopted #433 socket cleanup. These prerequisites are included in release `ff5f3f04`. **This is not a fresh stock-branch build.**

Publication commit `bed7c5069732b42f314755468f89ffcb52ccc61d` changes one file on `d522af52`. Fixture blob `6709bc98f68e5e1056901ffa5125ab6ce8db1084` exactly matches the native-after source overlay. The baseline fixture is identical on tested `37472d88`, swarm `d522af52` and release `ff5f3f04`. Only the three error predicates were strengthened after the earlier 24 passes; those 24 helpers and assertions are unchanged. Historical binaries retain their actual source identities; they are not relabelled as builds of the publication commit.

Each focused build changed the fixture object and three generated build-identity objects, preserving the other 5,881 cached objects. Original cache `10173603864` was not overwritten.

## Requirements and limits

Git Bash must be first on PATH. The existing command parser requires whitespace-free paths or available short aliases. Missing prerequisites fail explicitly. Arbitrary WSL/shell layouts, Unicode or spaced paths without short aliases, MinGW and plain MSVC are unverified.

On macOS, actual extracted helper functions produced identical script bytes and valid/error/argument outputs using filesystem/format shims. This is component evidence, not a full POSIX BTX run. No full Windows/POSIX suite, wallet/mining workflow, production signing device or release qualification is claimed.

Original fixture authorship is retained. Credit repch1c and Jpp-matata for Windows prerequisite findings and review context. The hosted runs here are ours, not attributed to them.

## Evidence and execution

- [Baseline run](https://github.com/sunnyriverr/btx/actions/runs/42436915053), [24-case repair run](https://github.com/sunnyriverr/btx/actions/runs/42440607635), [three-control qualification](https://github.com/sunnyriverr/btx/actions/runs/42442778867).
- [Caller map](caller-coverage.json), [24-case verification](launcher-verification.json), [three-control verification](qualification-verification.json), [source mapping](code-receipt.json), [file and original archive hashes](MANIFEST.json).
- `records/baseline/`: original grouped PQ test logs/XML; `records/launcher/`: 24 after-case logs/XML; `records/qualification/`: paired three-case logs/XML and exact overlaid sources. `maintained.json` files are labelled projections of relevant fields, not the complete original archive.
- `recipes/`: actually executed controllers. They require the recorded cache/profile; no fresh-machine reproduction is claimed. Exact selected commands are in the records. The maintained suite command is `test_btx.exe --run_test=pq_phase4_tests`; our private campaigns selected only the recorded cases.

The qualification manifest inherited stale 24-case descriptive counts, and its dispatch description incorrectly said saved-binary execution. Actual jobs/XML selected three and the controller built both binaries. Original descriptions and an explicitly corrected offline description are retained; no native rerun is implied.

Earlier unsuccessful pilots remain in the CI history: `42439421234` cancelled during setup; `42439488682` ran no BTX tests after a runner import error; `42440011939` failed the quoted/basename launcher attempt; `42440506327` was cancelled before tests. None counts as a qualification pass.
