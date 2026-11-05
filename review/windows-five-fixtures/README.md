# Windows fixture batch and document-byte correction

**Five maintained fixture objects compile; supported native cases pass. An unchanged document-byte assertion fails before and passes after the separate Windows binary-mode correction. Full `test_btx` remains unqualified.**

Code units on swarm `666673a3153225ba264c7870e0e82e354df86765`:

- [Five test files](https://github.com/sunnyriverr/btx/commit/3b34b7cb04165403e6233ef13b60dc7497c2842d).
- [Document-byte correction](https://github.com/sunnyriverr/btx/commit/33a014c23024738b03edf766bd0a1b5f8ab8507a).

Neither clean branch alone was built. Native measurements use prerequisite integration `29d0fc8a973ff5ef92e51fa1da6ad5bab037b2d9`, containing **#411 (`362c36b2`), #415 (`a75dc8f6`), #417 (`3b453c78`), #418 (`80f7f2a3`)**. #417 supplies the direct SDK-helper dependency; others are applied context, not a proven minimal set. The five-file adaptation is required to run the Windows AHP regression. Both patches applied to 29d0 reproduce tested tree `878cac603455b1cc23e6b88215b50123750f962d`. [Source map](source-map.json).

## Native execution

Windows Server 2025 x64, clang-cl 20.1.8, MSVC 14.51.36231 library, SDK 10.0.26100. Modelnet/wallet/tests/ZMQ ON; GUI OFF. Scoped executable uses five maintained generated object commands, cached unchanged SDK helper and original library closure. Real btx-open/modeld/btxd dependencies compile/link. Not a clean standalone build or full maintained `test_btx`.

| Group | Cases / passing assertions |
| --- | --- |
| Actual unsupported Unix-RPC refusal/no new entries |1 /3 |
| Signed records/cache |5 /5278 |
| Sharing policy |1 /14245 |
| Unique workflow fixtures |34 /492 |
| AHP before |17 /399 of400; existing byte equality fails |
| Same AHP after |17 /400 of400; fixture object hashes unchanged |

First four groups pass on `f410081e`, [run 42104359495](https://github.com/sunnyriverr/btx/actions/runs/42104359495),16 planned build steps. This run remains failed on the AHP assertion. Only the same 17AHP cases rerun at `0bc4625b`, [run 42106421481](https://github.com/sunnyriverr/btx/actions/runs/42106421481),11 build/relink steps. Four unaffected groups reused by exact object identities and isolated extraction-function delta. **58 distinct qualified cases / 20,418 assertions across two binaries, not one all 58 run.** [Verification](verification.json).

`ahp_doc_11_explicit_safe_extraction` compares extracted bytes with `readme.text`. Windows CRT text translation changes LF bytes; `_O_BINARY` preserves them. Expected bytes/assertions are unchanged. Exclusive/no-follow flags, permissions, path checks and errors remain. Current callers are tests only; no live-user/CLI outage claimed. [Failure](native/42104359495/suite-3.log), [same passing suite](native/42106421481/suite-0.log).

Five original missing-header failures from native41994623193/41990045506 were reused after matching source hashes, full compile table, per-file commands and compiler/SDK/environment. [Baseline manifest](baseline-reuse.json) and [raw logs](baseline/). Compiler-before/candidate-after evidence; no baseline runtime inference.

Thirteen Unix live-helper bodies remain unchanged for POSIX and unexecuted on Windows. Windows retains signed-cache/policy/refusal checks. Real literal-argument subprocesses preserve expected errors and distinguish launch failure. Actual document symlink/overwrite/sentinel tests ran without privilege skips. The sparse file reported 429,496,729,600 logical / 0 allocated bytes and was deleted; not 400 GiB payload I/O.

## Execution entry, cleanup and limits

Exact command vectors/outcomes are in [first five.json](native/42104359495/five.json) and [document five.json](native/42106421481/five.json). Generic preparation result.json is not the fixture verdict. Shape executed:

```text
ninja -C D:\btx-native-035\project-build -f D:\btx-native-035\evidence\five.ninja --verbose -j 4 -k 1 bin/windows_fixture_five.exe bin/btx-open.exe bin/btx-modeld.exe bin/btxd.exe
D:\btx-native-035\project-build\bin\windows_fixture_five.exe --run_test=<maintained suite> --report_level=detailed --log_level=test_suite -- -testdatadir=<owned directory>
```

[Executed controls](controls/) retain exact hashed inputs/workflows, integrity bundles and shared support. They require their matching retained cache/profile, not a demonstrated standalone reconstruction. Read normal code/integration branches for review. [Manifest](manifest.json), [original archive/member hashes](archive-inventory.json); bulky generated graphs/catalogs remain in archived artifacts. Raw included logs are byte-identical; local path labels in public verification use TASK with [normalization mapping](normalization-map.json).

Both jobs completed; no owned survivors, forced kills, budget stop or read-only fallback. Data removed. Cache 10083414530 retains 3,844 objects; predecessors retained. Original graph/config stayed unchanged; a scoped link rule was added. Full maintained graph/helper registration/regeneration still needs qualification. No object-time/Ninja command-log rewrites.

Full Windows `test_btx` link/run, cl.exe arithmetic, Windows 11 interactive operation, POSIX, MinGW, hardware/live custody/scale/mixed-binary, mainnet and release qualification remain outstanding. Existing NOT_RUN paths remain unqualified. This does not close #356.

Credit: repch1c's #356 Windows audit and Jpp-matata's review/testing guidance. Original source/prerequisite authorship retained; these results are not an independent ACK by either contributor. Publication repeated no tests.
