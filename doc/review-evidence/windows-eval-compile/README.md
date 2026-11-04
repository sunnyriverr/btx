# Windows evaluation compiler repair

**Same generated Windows object fails before and passes after; ordinary component controls pass. Full native Windows build and unit qualification remain open.**

Code: `c3707c5c4b1eb76a7ec85175f9a248c7ad08cc5a`, one independent commit/one file directly on accepted `ecd9310a8b35dbf1260d1a64e0ff39bb50e7a629`. No other product prerequisites were needed for this isolated object. Credit: repch1c's Windows inventory and Jpp-matata's platform-review/contribution guidance; original source attribution is retained.

## Behavior

The native compatibility fork already refuses with ENOSYS. The patch guards the POSIX-only private helpers/process bodies, preserves common plan/profile validation and logical cancellation, and explicitly refuses unsupported isolated execution on Windows with FAILED. The supported caller premarks RUNNING, so refusal must set a terminal state. This does not implement a native evaluator, change profile readiness, permit an in-process fallback or change validation/monetary rules. The entire POSIX-selected source is unchanged.

## Executed qualification

Native [run41820342690](https://github.com/sunnyriverr/btx/actions/runs/41820342690), immutable CI inputs [`e292540f961f8f51e4e4550fa334f5e530f4d929`](https://github.com/sunnyriverr/btx/tree/e292540f961f8f51e4e4550fa334f5e530f4d929/contrib/devtools/windows-root-configure), ran on Server2025/x64, MSVC toolset14.51.36231, SDK10.0.26100.0 and clang20.1.8. Root Release/static-CRT preset: Modelnet, wallet, tests, SQLite, ZMQ ON; GUI OFF. Verified cached dependency binaries, fresh project objects.

| Check | Original | Final patch |
| --- | --- | --- |
| Same root-generated bounty_eval.cpp.obj, clang-cl | pid_t/usleep compile failure | Compiles |
| Real full-module MSVC controls | Original cannot compile | 15 checks pass |
| Real full-module clang-cl controls | Original cannot compile | 15 checks pass |
| Mac full-module ordinary POSIX controls | 24 checks pass | 24 checks pass |

Native controls require an ordinary valid plan and caller-shaped RUNNING job to return false with explicit unsupported error, become FAILED, preserve its plan/sentinel and create no process/report/success claim. Logical cancellation, common guards, preparation permissions/limits, unchanged input and owned-file cleanup pass. Removing only FAILED produces exactly one failed terminal-state assertion, with the other14 passing. This demonstrates the state control detects an incomplete refusal.

Mac controls use the entire real translation unit and real UniValue/hash/types dependencies. Owned-file/golden-digest success, normal missing-file/checksum failure, pre-cancellation/child reaping, logical cancellation and cleanup pass. Baseline and final Mac binaries/output are identical. The reused immutable Mac snapshot has one unrelated Obs01 file change from ECD, outside this component; its compiled sources/headers match ECD. Original baseline was retained; only the changed final candidate was rechecked.

The final candidate has no source warnings; the preexisting clang-cl /Zc:preprocessor driver warning remains. The first candidate's two unused-helper warnings were removed before this final run. Earlier inputs/results remain in the local task archive and [run41819112180](https://github.com/sunnyriverr/btx/actions/runs/41819112180); they are not substituted for final-byte qualification.

## Reviewer entry points

- `candidate.patch`, `source-manifest.json` and `branch-receipt.json`: exact code/base/identity.
- `native/baseline-eval-object.log`, `native/candidate-eval-object.log` and `native/target-compile-command.json`: the same actual generated target and compiler command before/after.
- `native/result.json`, `native/candidate-cl/`, `native/candidate-clang-cl/`, `native/mutant-clang-cl/` and `mac/`: actual command/control records; binary hashes were captured before execution.
- `verification.json` and `native/provenance-summary.json`:18 original command logs, artifact digest, compile database/object hashes and14309source entries verified; exact accepted source restored.

The original workflow placed the inputs beside runner.py at controls/contrib/devtools/windows-root-configure, checked out immutable ECD under btx/, then ran its openssl/vcpkg/configure stages with a configured native compiler environment. `workflow.yml`, `runner.py` and `dependency-identity.json` retain that executed cache-based recipe; this is not an empty-machine dependency bootstrap. The original native artifact retains the full catalogs, compile database and object (metadata/digest in native/artifacts.json, hashes in provenance-summary.json). This readable branch retains code, commands, controls and text logs beyond the artifact's14-day retention.

For the ordinary full-module control, from this directory:

```sh
python3 component.py /absolute/isolated/ECD/source /absolute/owned/output baseline
python3 component.py /absolute/isolated/ECD/source /absolute/owned/other-output candidate
```

On configured native Windows, use `python component.py SOURCE OWNED_OUTPUT candidate cl` or `clang-cl`; the original Windows module is demonstrated by the generated-target failure rather than a passing component. These commands are the retained executed script interface with caller-provided paths; the published directory itself was not rerun on native hardware. `check_inputs.py` checks packaged hashes/identities without building. Mac personal paths are redacted and original record hashes retained; native original logs are byte-preserved.

## Limits and next decision

This proves a compiler repair and ordinary component controls, not a native isolated evaluator, full node/default build, project test_btx, Windows11, native Linux/MinGW, wallet/live-network/GPU or release qualification. Existing tests requiring successful isolated execution still need an explicit Windows support decision. Issue356 remains open for the full native node build and unit run. No full integration result is inferred from this one-object pass.
