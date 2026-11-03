# Boost Multiprecision dependency check

Code: 106a697bdd093d193871771815ee6e2ef86b15d2, parent cbf65894e6d61084527cd93e913a00c6794418dd. One unconditional dependency added to vcpkg.json. Native Windows discovery and missing-header reproduction: repch1c, https://github.com/btxchain/btx/issues/356.

## Measured result

Native macOS 26.5.1 arm64, official vcpkg 2024-09-30-ab8988503c7cffabfd440b243a383c0a352a023d; registry c82f74667287d3dc386bce81e44964370c91a289. Official executable checksum verified against pinned scripts/vcpkg-tool-metadata.txt.

Real dependency plans with default features disabled and tests enabled:
- Original: resolver exit 0,49 target packages, required Multiprecision absent.
- Corrected: resolver exit 0,59 target packages, Multiprecision 1.85.0#2 present.
- All 49existing package versions preserved. Additions are Multiprecision and the same nine extra Boost ports identified by the Windows reporter.

The missing-dependency acceptance fails before and passes after. Neither resolver command fails; no compiler failure/pass is claimed locally. Both manifests retain identical baselines, overrides and features apart from the one dependency.

## Repeat the resolver check

Use an official vcpkg checkout/bootstrap at the registry commit above, with metrics disabled. In a BTX checkout containing code commit 106a697b and its parent, create two disposable manifest directories:

```sh
mkdir -p original corrected
git show cbf65894e6d61084527cd93e913a00c6794418dd:vcpkg.json > original/vcpkg.json
git show 106a697bdd093d193871771815ee6e2ef86b15d2:vcpkg.json > corrected/vcpkg.json
```

For each directory, run from outside it, replacing MANIFEST_DIRECTORY with its absolute path:

```sh
vcpkg install --dry-run --triplet=arm64-osx --host-triplet=arm64-osx --x-no-default-features --x-feature=tests --x-manifest-root=MANIFEST_DIRECTORY
```

The corrected output must contain boost-multiprecision:arm64-osx@1.85.0#2; original must not. Complete recorded plans and checked results are alongside this README. This is dependency planning only; no packages were built or installed.

## Limits and Windows verification still required

- No native Windows compilation or installed-header test. Windows-target dry-run on this Mac is blocked by the Windows compiler-environment requirement. No substitute Windows triplet was used.
- The default-feature manifest also fails independently on unavailable miniupnpc 2.3.2 in the pinned registry. Both original and corrected plans show that same error. This patch preserves that override and does not fix the full default Windows preset.
- BerkeleyDB in the wallet feature is marked unsupported on this pinned Mac triplet; the measured Mac profile is core+tests, not wallet.
- On a supported Windows machine, compare original/corrected manifest resolution and then compile the affected pow.cpp target using the same valid toolchain/profile. Preserve other local build workarounds in the evidence and distinguish this header from the other #356 failures. No full-node build or all-Windows-issues claim follows from this patch.
