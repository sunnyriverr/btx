# Integrated native Windows qualification for #356

**Full maintained build PASS at 4609dde6; full unit acceptance INCOMPLETE.** A separate bounded local model-file recovery check passes on the identical retained full binary.

## Exact source and prerequisites

Tested source: `4609dde66f1da8023927196a55b6332dbcbeff3e`, tree `a504cc26ddcbad20bf1acbac498daa9d48e7e332`. It is the parent of this evidence commit. The branch root contains the exact integrated source; this commit adds evidence only.

This is **not unchanged upstream 666673a3**. It includes pending #411/#415/#417/#418/#420/#421 plus the already-tested five-file, WAN and AHP fixture corrections (64c248b1/a504fc85/4609dde6). See [integration-scope.json](integration-scope.json) for all 18 commits and 74 changed files. Preserve these prerequisites when interpreting or reproducing the result; this is not a request to merge the evidence branch as a unit.

Original code authorship is retained in history. Credit to repch1c and JPP for the Windows defect/qualification groundwork and existing #356 results. Native execution was GitHub's Windows Server 2025 x64 runner; preparation/review was assisted by Codex.

## Build result

clang-cl 20.1.8, MSVC 14.51.36231 libraries, SDK 10.0.26100, Ninja 1.13.2. Modelnet/tests/wallet/ZMQ ON; GUI OFF. Normal generated graph and all 5,898 compile entries unchanged. No duplicate-symbol tolerance or pruned maintained test list.

The cached 13-step build exits 0 in 18.58s and links `btxd`, `btx-cli`, `btx-tx`, `btx-util`, `btx-open`, `btx-modeld` and full `test_btx`. Actual imports/inventory and node `-version` succeed. Build metadata has the exact source and `BUILD_GIT_DIRTY 0`.

[Executed build/unit run](https://github.com/sunnyriverr/btx/actions/runs/42175854206) · [build log](logs/full/candidate-unit-build.log) · [actual unit inventory](logs/full/unit-inventory.log) · [verification](full-verification.json).

## Full unit run: incomplete, with observed failures

The unfiltered invocation announces 15,377 enabled cases. At the global 2,700.61-second limit, 1,693 case-entry events and 1,692 case-exit events are observed; **these are not pass counts** and no aggregate completion summary exists. It stops while `matmul_v4_rc_air_episode_tests/honest_compact_accepts_and_measures_toy` is active. This establishes a global-budget stop, not a product hang or per-case timeout.

Four cases report six assertion diagnostics: the lightwatch truncated-line check, worker stop/drain completion counts, and two RC alternate-provider registration checks. All four case names already appear in [repch1c's #356 report](https://github.com/btxchain/btx/issues/356#issuecomment-6635802518). Different source/features do not establish identical root causes or new regressions.

[Full runtime log](logs/full/candidate-unit-run.log) · [case diagnostics/timings](full-runtime-analysis.json) · [unentered coverage map](full-runtime-coverage.json). 13,684 enabled cases were not entered in that run, including 187 Modelnet suites. Existing disabled inventory entries remain separate.

## Bounded local file recovery: pass

Using the same full `test_btx` binary, four previously unentered existing cases complete with 35/35 assertions. The whole test step takes 14s (9.15s across monitored test commands), within 15s per case / 60s aggregate. No BTX configure, build, relink or source modification occurs.

| Existing case in modelnet_file_stream_tests | Assertions | Log |
| --- | ---: | --- |
| fullcloud_04_05_stream_segments_and_verifies | 9/9 | [case1](logs/recovery/file-case-1.log) |
| fullcloud_06_mid_file_corruption_fails | 3/3 | [case2](logs/recovery/file-case-2.log) |
| fullcloud_08_resume_is_one_range_not_per_piece | 6/6 | [case3](logs/recovery/file-case-3.log) |
| fullcloud_09_helper_restart_one_range | 17/17 | [case4](logs/recovery/file-case-4.log) |

This proves ordinary callback-fed bytes are verified into real temporary piece files, partial progress resumes with one range read, and a saved job loads into a new hydration object and completes. Checksum rejection remains. Despite the existing case name, **no actual helper process was restarted**; no live peer/origin transfer or real model/GPU workload was exercised.

[Executed focused run](https://github.com/sunnyriverr/btx/actions/runs/42187109387) · [result and binary identity](recovery-verification.json) · [executed focused controller](slice.py) · [selected-case inputs](slice-inputs.json).

## Identity, retained state and scope

Unit binary SHA-256: `c2d4e9fdd24c74699a9c559234cce371bfcf8e93bb22a7c9ac27050fd7837dfb`. The focused run verifies all 12,837 cached-file hashes, including all 5,885 compiled objects and this binary, unchanged afterward. Source catalogs match; owned data is removed and no owned processes remain.

The full-build run retains all 5,885 prior object paths (5,884 identical; one normally generated golden-manifest object rebuilt) and seven binaries in cache 10104985408. [Retention receipt](retained-cache-receipt.json). Cache service existence was checked; a later consumer must verify its payload. The explicit existing host-image/Ninja-wrapper pair transition is recorded in the verification receipts; compiler/SDK/dependency identity checks remain matched.

The two CI entry points are retained-cache qualifications, not independently executed fresh-build instructions. Their immutable executed definitions are [full workflow](https://github.com/sunnyriverr/btx/blob/0c6e1d5eea723d0a418e3f8db09c23bdea1d5ccb/.github/workflows/windows-root-configure.yml) and [focused workflow](https://github.com/sunnyriverr/btx/blob/868c859a3f713d54b071c3431fd949acd586aab0/.github/workflows/windows-root-configure.yml). Cache keys can expire. To inspect/build the tested code, check out 4609dde6 from this branch and follow the repository's normal Windows instructions. From a compatible built full binary, the focused controller's four exact `--run_test=modelnet_file_stream_tests/<case>` selections are the reproduced test entry points. Its CI environment and cleanup requirements are explicit in the linked executed workflow; no different local recipe is claimed executed.

No full-suite success, native MSVC-cl build, native POSIX run, real helper/network/GPU, production wallet/node, mainnet or release qualification follows. #356's runtime gate remains open. No additional test repetition is requested by this report.

`manifest.json` hashes every evidence file. Runtime logs are readable here; downloading a ZIP is unnecessary.
