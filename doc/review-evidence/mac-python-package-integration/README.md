# Mac Python package integration — native qualification

The stock f40eb37a packager fails before creating an archive. The exact two-correction candidate in ae9c9414cd932b8a3ac013cb10646490ee0bd48b creates a Mac ARM64 command-line archive that passes native dependency, architecture, ad-hoc signature and relocated offline lifecycle checks.

## Correction and regression results

- Defer Mac input checks until Python is bundled; run the unchanged shipping gates on real daemon/CLI/util/helper images. The same maintained ordering test fails stock and passes candidate, including four invalid-final-image refusals (run43655829259).
- Track the exact source of standalone native modules copied from outside the framework. Homebrew's _cffi_backend reproduces the failure; the same maintained full-bundle-flow test fails before and passes after (run43656330354). Its loader/subprocess calls are mocked; the actual archive below supplies native qualification.
- Existing packaging suite:59 tests,57 passed and2 native-Linux-tool cases skipped on Mac;9 original Mac runtime tests passed in43655829259. These unchanged passes are reused, not claimed as rerun after the later four-line mapping correction.

## Actual archive and final gates

Source f40eb37a6fb8b665340fe92a2f248ff3f23ec7f6 plus the exact four candidate files in source-identities.json. Build43653926982 supplied16 current binaries and7 unchanged-source Metal libraries; no later recompilation. Original daemon SHA-256 a9d9bc54d745020edf3c3959517f52b84fe7a2373949a2755a8ceabcbb715a8e.

Archive produced by43656330354: btx-0.34.16-arm64-apple-darwin.tar.gz,46,406,984bytes, SHA-256 f1d531d160ac5b5b745dae99466b6ee952976fd163e5fe3574f0a2c4e31a77fa. The identical archive was restored and hash-verified in43656591080, not repacked.

All86 Mach-O paths passed ARM64 presence, strict signature verification with ad-hoc identity, and bounded relative dependency closure. A deliberately changed/re-signed Homebrew load was rejected independently of a separate corrupted-signature control. Original bytes were restored.

From a relocated directory containing spaces, with producer Python framework and source checkout unavailable: ordinary RPC and exact default SwapNet-off response passed; explicit -swapnet=1 and same-datadir restart reported in_process=true, automatic_spend_atoms="0", wallet_loaded=false. All three RPC stops exited0, no forced cleanup. Framework and source were restored. Final result.json records each response, image hash and command.

## Executed entrypoints and reusable evidence

- [Stock native package failure](https://github.com/sunnyriverr/btx/actions/runs/43654912794).
- [Ordering regression and original maintained suites](https://github.com/sunnyriverr/btx/actions/runs/43655829259).
- [Standalone-module pair and actual combined archive](https://github.com/sunnyriverr/btx/actions/runs/43656330354), wrapper commit a724bb359068b620b2f61acefb646924c2c52fe9, contrib/devtools/mac-backports/archive-package.py.
- [Same-archive all-image controls and lifecycle](https://github.com/sunnyriverr/btx/actions/runs/43656591080), wrapper commit607e7f07530e66a97e3a638f0a9fc90c4ffe707a, archive-package.py, archive-audit.py and archive-runtime.py in the same directory.

Maintained tests are test/util/package_release_archive_test.py PackageReleaseArchiveTest.test_macos_checks_finished_images_after_runtime_bundling and test/util/bundle_macos_python_runtime_test.py MacRuntimeTest.test_standalone_native_module_outside_framework_is_relocated. Artifact IDs/digests/expiry are in artifact-retention.json; archives expire28–29November. Reviewable code and logs are retained here; archives are not the primary review surface.

Native macos-15 ARM64, Xcode16.4/SDK15.5 build, Python3.12, cryptography46.0.4. Runtime was wallet-disabled offline regtest with ModelNet disabled. No Qt/Atlas app, signed/notarized release, full unit/functional suite, funded swap, native Linux/Windows or GPU-proof execution qualification. Existing #705 runtime work and Jpp-matata's #678 inventory/exclusions are preserved.
