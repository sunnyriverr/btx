# PR477: scoped native Linux packaging result

**Tested ACK `0ef96ff0` within the four maintained cases below.** This fills the native Linux bundler/gate path JPP explicitly left untested. It uses small compiled fixtures, not a full release rebuild or actual product binaries.

## Executed result

Base `dac9aee53520bd49ed320ec7a49b9072fc7d88d9`; candidate `0ef96ff0b7cfa2dfc62e35818a67fd6f6e1dd871`. Ubuntu24.04x86_64, `cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`, `ldd (Ubuntu GLIBC 2.39-0ubuntu8.9) 2.39`, `patchelf 0.18.0`. [Native run42767279516](https://github.com/sunnyriverr/btx/actions/runs/42767279516), fixture `20ba73863d2dada6085533c2275252c974e585e5`.

| Maintained case | Base with identical updated tests |477 |
| --- | --- | --- |
| Native shared/private dependency bundling |PASS |PASS; new stage gate reads8ELFs |
| Package rejects over-floor GLIBC |FAIL: RuntimeError not raised |PASS |
| Package rejects unsupported host GLIBCXX/CXXABI |FAIL: RuntimeError not raised |PASS |
| Gate rejects plugin outside bin/libexec/lib |FAIL: VerifyError not raised |PASS |

Eight individually selected unittest invocations, one per case per tree; no unittest skips and no repetitions. Exact test hashes, source hashes, command arguments/exits and cleanup are in [native/result.json](native/result.json). The three failures are intended missing-refusal assertions, not setup errors. Candidate4/4PASS. Native checks plus metadata/cleanup took6.06s; hosted setup time is separate.

The maintained positive case runs realcc/ldd/patchelf over compiled shared/private dependency graphs, stages them, launches guard/Qt-labelled fixture programs with LD_ overrides removed, and checks restored archive guard behavior. The new gate's observed log confirms8ELFsread. The fixture deliberately omits optional product helper binaries; its 'skip' messages are not skipped unit tests. New refusal cases use JPP's synthetic ELF builders, including his explicit ceiling-override control; the job environment and native positive case use the unchanged default policy. No policy was relaxed.

## Reuse and exact provenance

[Executed workflow](recipes/workflow.yml), [runner](recipes/run.py), [result classifier](recipes/result_contract.py) and [offline negative controls](recipes/test_result_contract.py). The original workflow puts these in `contrib/devtools/linux-package-gate/`; these are retained executed files, not a newly executed alternative package. The workflow checks out base and candidate separately and overlays only the two updated test files onto base. Production scripts remain byte-identical before/after each tree's execution; candidate stays Git-clean.

From either tree, after the baseline-only test overlay, the selected commands are:

```
python3 -I test/util/package_release_archive_test.py -v PackageReleaseArchiveTest.test_direct_guard_and_qt_keep_shared_and_private_dependencies
python3 -I test/util/package_release_archive_test.py -v PackageReleaseArchiveTest.test_packaging_refuses_any_elf_above_the_glibc_floor
python3 -I test/util/package_release_archive_test.py -v PackageReleaseArchiveTest.test_packaging_refuses_a_host_glibcxx_need_above_the_floor
python3 -I test/util/verify_release_btxd_test.py -v ArchiveContentGateTest.test_glibc_ceiling_reads_every_elf_not_only_bin_libexec_lib
```

[Completion receipt](provenance/completion-receipt.json), [artifact receipt](provenance/linux-package-gate-records-retry-collection.json) and [file manifest](manifest.json). Artifact digest `8c8818fd48497c5ea69f732874ab097f34d2d0a497e26db29b19545b7a1ddc92` verified on download; all20raw file hashes and eight saved result classifications rechecked offline. Six result-classifier test methods/subcontrols passed before dispatch. Owned runtime removed, no leftover processes or cleanup signals. Production, wallets, preserved binaries/cache and Session1 resources were untouched.

## Limits and credit

JPP authored PR477 and these maintained tests. This contribution adds the scoped missing Linux execution evidence; it does not change the PR or claim his fix/test authorship.

These are small compiled ELF fixtures, not BTX, Qt, Atlas or guard products. No full package/gate test suites, real release archive rebuild, actual service/GUI, Mac/Windows, GPU, mainnet or release qualification. JPP's real0552archive refusal and our prior Linux GUI/lifecycle evidence were reused, not repeated. The official archive is unchanged. This supports reviewing the protective gate; it does not claim the download is now fixed.
