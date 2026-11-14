# macOS Python runtime packaging repair

Fix: [ddc4fee4cc7d49479200221bd87c73cfddfb805d](https://github.com/sunnyriverr/btx/commit/ddc4fee4cc7d49479200221bd87c73cfddfb805d) on `swapnet-v2` `a5d1637facc925ff176507fae87fc2042940829d`. **Uses a saved binary, not a current daemon build or full release qualification.**

## Result

Actual archives from the same disposable input: baseline `a8cb0e1c4af98e75b558cbf805b4c442919649ce1362322b748fc5770275fad5` fails127 after unpack/relocation; repaired `f27b2228b4f20c16520e6e92ec49f23a2835ce9b4708a89852b7ab3a5e9957d5` passes default-off, enabled SwapNet RPC, same-data restart and clean shutdown. Consumer path contains spaces, producer Python directory is hidden, and no DYLD/PYTHON loader overrides are supplied. Regtest, wallet disabled, ModelNet off, automatic_spend_atoms=0; no mining, funding or signing.

The Mac-only repair stages CPython framework/stdlib, selected crypto modules/licence metadata and native closure. It rewrites copies to bounded relative paths and re-signs them, checks the target architecture/signatures/closure, and runs isolated staged imports. Existing source launch and archive gates remain enabled. Credit **Jpp-matata** for #678's reused Linux import inventory/stdlib rules, and **repch1c** for the earlier native SwapNet reports. Those are different contributions; no attribution is transferred.

## Evidence and maintained entry points

- [Archive results](archive-results.json), [execution log](archive-execution.log) and per-boot logs in this directory.
- [Native gate results](native-gate-results.json): all69images verify; signature damage, missing library, existing outside target and Homebrew loads each reject.
- [Nine maintained guard tests](maintained-controls.log): ABI/import/architecture, collision, normalized path, symlink, app context and unsupported-worker refusal.
- [Existing packager tests](existing-packager-tests.log):58run,56passed,2skipped.
- [Source review](independent-code-review.md): findings corrected and rechecked; reviewer did not execute native tests. Final source-only guard rebuild produced the identical native-qualified archive, so lifecycle passes were reused.
- [Exact source/input/archive receipt](repair-receipt.json). Only an attribution docstring changed after qualification; executable AST equality verified.

From the product checkout:

```sh
python3 test/util/bundle_macos_python_runtime_test.py
python3 test/util/package_release_archive_test.py
```

Build a normal Mac archive from matching native artifacts with `scripts/release/package_release_archive.py --platform-id macos-arm64 --python /path/to/matching/python3.12` and its required `--btxd`, `--btx-cli`, `--btx-util`, `--source-root`, `--version`, `--output-dir` arguments. Then extract somewhere different, without producer dependencies, and check default-off/enabled lifecycle. The `executed/` scripts are the actual task-layout harnesses, not a claimed one-command clean-checkout reproduction; they require the retained fixtures/layout named in the receipt. No binary/fixture wallet files are added to Git.

## Saved-input provenance

JPP [run43599161832](https://github.com/Jpp-matata/btx/actions/runs/43599161832), artifact14117594575, producer64889922 mapped to70de5a45 plus CI changes. Original daemon SHA256 `2c623e1841d0aca07572d0d82c73352708733567fda226551c8478bad9eec41a` remains untouched. A disposable copy's load command points to the owned build-host-equivalent Python framework and is ad-hoc re-signed (inputSHA `abce49e600018f6fcf7f5295e1e3515efc25a63e8b2b11fbb2d3367a39848fe0`); **identical input before/after**. This satisfies the original source-binary clean-env gate without installing global Python. Consumers run while this producer tree is hidden. Runtime fixture is CPython3.12.10 ARM64 with cryptography46.0.4; transitive wheel hashes are retained in the local dependency receipt and selected metadata ships in the tested archive.

## Limits

Native macOS ARM64 plain archive, currenta5d1637f packager plus repair, saved70de-derived daemon; not a current daemon rebuild. No actual Qt/GUI archive, ModelNet coexistence, Intel Mac, Linux/Windows, DeveloperID/hardened runtime, notarization/Gatekeeper, full swap or release qualification. Signing here is ad-hoc; finalrelease signing remains a maintainer operation. No tag, release asset or production wallet/node changed. Logs have personal machine paths redacted.
