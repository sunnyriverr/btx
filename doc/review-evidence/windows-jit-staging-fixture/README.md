# Windows POSIX staging fixture correction

**Same generated Windows compiler command: FAIL before, PASS after.** Full Windows unit build and execution remain incomplete.

## Change

Guard only `ensure_staging_dir_is_private` with `#ifndef _WIN32`. Repch1c added this regression in [#720](https://github.com/btxchain/btx/pull/720); every POSIX statement and assertion is preserved. It uses `TMPDIR`, `setenv`/`unsetenv` and POSIX group/other mode checks. The Windows production helper uses ACL checks instead; blindly substituting environment function names would not establish equivalent coverage. Production code and its safety checks are untouched. All 17 other cases remain emitted in the Windows object.

## Tested on

- Native Windows Server 2025 x64, clang-cl 20.1.8, MSVC 14.51.36231, SDK 10.0.26100.0; optimized C++20/static profile.
- Exact source `89f8f94749575fec3891bf7ea1b76f9c20169c6f` plus this fixture patch. The entire target source file is unchanged on publication base `2df837f3527da23f5040a1eb17d6d64270617915`. This is not a full build of that newer revision.
- [Executed fork run 43764371604](https://github.com/sunnyriverr/btx/actions/runs/43764371604), immutable orchestration commit `53f11df86dece6810326053d236769d05c423221`. Original compiler command fails in 13.44 seconds on the four environment calls; identical command with the patch passes in 14.61 seconds. See the paired logs and `jit-fixture-result.json` for the exact command.
- Restored and hash-verified all 12,934 files / 5,914 objects from checkpoint 10554611327. No configure, dependency rebuild or full-target build. Unrelated objects, libraries and executables remained hash-identical. `dumpbin /symbols` retains all 17 other case registrations; registrations are not runtime passes.
- Mac preprocessor-only selection check retains the unchanged POSIX case without `_WIN32` and excludes it with `_WIN32`. No fresh full POSIX suite or unit runtime is claimed.

The command was replayed from CMake's `compile_commands.json`, bypassing unrelated Ninja order-only prerequisites. `jit_fixture_native.py` and the workflow are the executed verification inputs; they require the recorded hosted cache and exact checkout layout, not a standalone clean-build recipe. The existing in-tree fixture is retained on POSIX. Earlier Windows ACL/junction/refusal controls on #724 remain separately scoped evidence; this guard does not add a Windows staging runtime test.

## Retention and next step

The corrected object and all prior progress are retained in cache 10567969135, key `btx-release17-unit-43764371604`, manifest `87e419f379c7cf086a0160141f22c6f03a71b67a0ea773fa71cade7accc8994e`. Git HEAD is 89f8 plus the explicit fixture patch; the source manifest records dirty bytes. This direct compiler diagnostic does not update Ninja's dependency log. Do not conceal a legitimate later recompile of this one object. Full test executable link, inventory and runtime remain outstanding.

Evidence artifact 14181651095 has SHA256 `b3c372892a9e5aa3da5b100c28a58d6c43f49264f0c67f63ea4363449699fd5e`; download hash and ZIP CRC verified. Old checkpoints are preserved. Next is a source-impact assessment/dry run and remaining unit build, not a repeat of prior CLI/runtime checks.

AI assisted the source review and fixture correction; native results above came from the recorded hosted run.
