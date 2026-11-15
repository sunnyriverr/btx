# Incorporated949 Mac command-line archive — native PASS

**Scoped PASS on `949a98e3`:** the actual archive built with the incorporated packager passes its release gate, all 86 native-image checks and producer-hidden default-off/on/restart lifecycle. No product code changed. This is supporting artifact evidence, not another merge gate or release sign-off.

## Source, binary and actual archive

Source `949a98e34222cc4cdb5b1d5bd650aa3b7bcbff72` with incorporated #708/#712, unmodified packager and source. Hosted macos-15 ARM64, Xcode16.4, Apple clang17/SDK15.5. Verified retainedf40cache supplied4,227objects/14,707matched source mtimes; actual949plan23 edges completed in 25.22s. All16 CLI executables were linked from that current-source build, with hashes in summary.json. Seven unchanged Metal libraries were reused; no GPU execution claim.

Actual archive `btx-0.34.16-arm64-apple-darwin.tar.gz`:46,410,625bytes, SHA256 `22ee49b866f7d1539387d7e30bc82b38174b0925e84a103f590d92485569de73`. Packed daemon `libexec/btxd.real`:SHA256 `ac96c05d6a83a09dbb902f0d89fd04049897a0ac659660c228926a1ed31b9e6f`. Raw pre-relocation/signing binary hashes are separately retained; those are not the same as packed-image hashes.

The same inner tar.gz was restored and hash-verified across the remaining gates; no recompile or repack between audit and lifecycle. Outer GitHub artifact ZIP metadata/digests may differ. Artifact IDs/digests/expiry are in summary.json; the retained archive is available under run43680157542, artifact14148121739 until29November2026. Build objects remain retained in14146769329, from43678751599. These are fork CI artifacts, not official releases or the unchanged published Linux download.

## What passed

- Incorporated packager assembled the isolated 16-executable CLI inventory in 17.3s, with all source/input hashes checked and no candidate overlays.
- Existing `verify_release_btxd.py --archive` passed `macos-static-zmq+launch+cli+contents` on the actual archive.
- All 86Mach-O images passed ARM64 presence, package-relative dependency closure and strict ad-hoc signature verification. This includes the deliberate Python.framework Resources/Python.app executable; there is no Qt/Atlas app in this profile.
- Relocated directory containing spaces; producer Homebrew Python framework and source checkout hidden. Default omission reports SwapNet disabled. Explicit enable and same-datadir restart report `in_process=true`, `automatic_spend_atoms="0"`, `wallet_loaded=false`. Each case answers ordinary RPC and stops cleanly, exit0. Producer paths restored; final source status clean.

## Exact executions and entrypoints

| Run | Result used | Wrapper commit / path |
| --- | --- | --- |
| [43678751599](https://github.com/sunnyriverr/btx/actions/runs/43678751599) | Current23-edge build; packaging attempt hit scope bound | b5e7fcac3680b3f6c0d3103656b1c7330718551d, ci/integrated-archives-949/integrated.py |
| [43679603417](https://github.com/sunnyriverr/btx/actions/runs/43679603417) | Actual isolated CLI archive assembled | 80676145e6cd4845db202f3ce3c88dd12f2cef16, package-only.py |
| [43679857514](https://github.com/sunnyriverr/btx/actions/runs/43679857514) | Same archive full gate and86image audit | 0476f6aebf6ae8c728c281e2d7c0ceea6b0fcbf0, finish-archive.py / clean-audit.py |
| [43680157542](https://github.com/sunnyriverr/btx/actions/runs/43680157542) | Only missing producer-hidden lifecycle | 817c9673661334221d3a4ca127d52784fa3a6a66, lifecycle-only.py / archive_restore.py / archive-runtime.py |

Paths after the first row use the same ci/integrated-archives-949/ directory. The workflow is .github/workflows/integrated-archives-949.yml at each immutable wrapper revision. These are executed recipes; artifact restoration requires access to the named GitHub artifacts while retained. Source/binaries/archive/checkpoint identity and actual per-case responses are in summary.json and native result logs below. All result artifact ZIP digests were verified before local inspection.

Unchanged packaging/functional/tamper tests were reused, not rerun or described as current native executions. Bad-load/signature controls remain the earlier43656591080 evidence; the real current86-image audit was newly run on this archive.

## Fixture errors and narrow continuations

The first invocation passed the parent build bin directory, so automatic sibling discovery pulled an old Qt app into a command-line cut and hit the300s package bound. The current build had already passed. A fixed16-file input directory corrected the profile without compilation.

The next archive assembled successfully, but a blanket*.appassert caught the intended Python.framework resource. It was not Qt content. The next continuation passed the full archive gate and86image audit, then stopped on a missing producer-framework initialization after script slicing. A complete reviewed lifecycle-only script and pure restore helper completed that sole remaining check on the same archive. Build, assembly and passed audit were not repeated. Failed badges are not counted as complete acceptance; their exact logs and states are retained.

## Scope and remaining work

Disposable wallet-disabled offline regtest with ModelNet disabled. Ad-hoc signatures only; no Qt/Atlas/installer, DeveloperID/notarization, all helper services, GPU-proof run, funded swap, full unit/functional suite or official release qualification. No user wallets, production or local native runtime changed.

Windows source adoption and earlier saved-JPP-binary packaging evidence remain separate; this is not a current949Windowsbuild or complete Windows unit run. The existing Linux download, tag and signing state were not changed. Numair's merge plan is unaffected by these artifact notes.

The Mac acceptance slice is complete. A current Windows daemon build is a separately costed cache/profile/build task, not a reason to repeat these Mac results.
