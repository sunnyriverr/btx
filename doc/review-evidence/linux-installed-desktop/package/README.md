# Installed Linux desktop acceptance evidence

**Result: PASS for this exact retained candidate on Ubuntu 24.04 x86_64 virtual X11.** This package preserves the raw records, screenshots, provenance and exact consumer recipe locally. It does not depend on an expiring CI download for offline audit. Nothing in this package has been posted upstream.

Start with [the short handoff](HANDOFF.md), [the original execution report](evidence/REPORT.md), [the machine-audit review](evidence/EVIDENCE-REVIEW.md) and [the visual review](evidence/VISUAL-REVIEW.json). Run identity: [44198893852](https://github.com/sunnyriverr/btx/actions/runs/44198893852), control `6d719e9191cea74a2e5ba7081e6beb02d7fd38bd`. The job took 230 seconds; the installed acceptance step took 72 seconds. No BTX rebuild occurred.

## What passed

| Boundary | Actual evidence |
| --- | --- |
| Exact candidate and installation | Outer and inner archive hashes, producer/patch/source records, archive metadata and file hashes passed. The exact upstream prebuilt-tree routine ran real daemon/CLI version probes. The installed bin/lib/libexec inventory matched the admitted archive. |
| Qt launch | Actual installed Qt executable and process start identity owned a visible regtest window. It closed with exit zero. `evidence/records14381370302/acceptance-records/gui/qt-main.png`. |
| Atlas local connection | Actual native cookie picker and endpoint/chain/genesis confirmation, followed by two observations about five seconds apart showing LIVE LOCAL, regtest and zero blocks. Screenshots, expected target, process ownership and normal exits are retained. |
| Ordinary helper/guard lifecycle | Two boots with one restart, ten health observations per boot and all 43 recorded checks passed. Public identities persisted; restart process identities and guard boot changed. Both boots stopped normally. |
| Cleanup and integrity | All five required phases and all three result JSON files pass. No fallback signals, surviving owned processes or private runtimes; installed files and archive identity unchanged. |

Five original screenshot hashes were verified and the images visually inspected. The Qt window extends beyond the virtual screen: this establishes launch, not layout or usability qualification.

## Exact subject and adoption

- Candidate artifact `14319148652`, producer run `44063898937`, compiled source `074dac167c26c1e091198f691ed5727817dba88a` with the explicit reviewed Python-selector packaging overlay from #822. Inner tar SHA-256: `915fae283089a325df65ef7521fffd6e30f5faa8d0bc8f2d77a2b6af52348a57`.
- Atlas was reused from the explicitly documented source88/tree-equivalent component. It was not rebuilt in this run. Complete identities and exclusions are in [provenance.json](provenance.json).
- Numair [reported incorporation of #822](https://github.com/btxchain/btx/pull/822#issuecomment-6955973729) at `c80be2e6ed4e794efdc05b952b97cd6364172e49`, preserving the author's identity. Commit metadata and the two current `release-0.34.17` file blobs were read and byte-verified against the qualified local product files. See [freshness.json](freshness.json).
- At the dated check, #822 remained open and unmerged through GitHub. The code is incorporated into the release branch; that is distinct from formal PR merge, independent maintainer acceptance of this desktop run, or an official desktop asset. The latest published v0.34.16 assets still omit Qt and Atlas.

## What was not tested

This does **not** qualify the whole current 0.34.17 tree, a new Atlas build, other distributions/platforms, physical desktops, Wayland, GPUs/CUDA, full UI usability, real wallets, payments/recovery, mainnet sync, SwapNet, model retrieval/inference or signed-updater trust/activation. GTK/WebKit/display dependencies are declared host requirements; this is not a sealed desktop image. No personal wallet, real coins or production keys were used.

All three earlier attempts remain failures or partial results with their original limits. [history/INDEX.json](history/INDEX.json) identifies the retained subset of reports, logs, receipts and raw record ZIPs. The prior producer's final metadata-GET/404 and earlier client-download timeout remain historical facts; this consumer pass does not rewrite the producer workflow. Original producer evidence is separately preserved at the [existing immutable #822 evidence commit](https://github.com/sunnyriverr/btx/blob/bfbcb2b311eb2fadb48ad4e9a77a23d4b2615002/doc/review-evidence/linux-python-site-packages/README.md).

## Contents and offline verification

- `evidence/`: all 40 files covered by the original successful qualification receipt, plus that receipt itself. It includes the original 708,633-byte ZIP and its 29 extracted records. The historical `evidence/HANDOFF-DRAFT.md` is preserved for byte identity; use root `HANDOFF.md` for the final reviewed draft.
- `recipe/`: exact consumer inputs, payload checksums and source map. Fourteen recipe/manifest files and the actual workflow copy were verified against immutable control Git blobs. The hosted workflow layout is documented by `recipe/source-map.json`.
- `product-change/`: the original narrow patch, exact bundler/test bytes and original publication receipt. This is provenance for the already incorporated fix, not a request to merge it again.
- `freshness.json`, `provenance.json` and `claims.json`: dated upstream observations, component origins, claim boundaries and evidence paths.
- `MANIFEST.json` and `SHA256SUMS`: every packaged payload file and its size/hash. The checksum file also binds the manifest; it excludes only itself.

From this directory, run `python3 verify_package.py`. It reads data, hashes files, checks the original ZIP and saved result consistency; it does not import the recipe or execute BTX. This is package validation, not a rerun of acceptance. The adjacent archive `.sha256` file binds the compressed delivery file.

The package contains no candidate BTX binaries, chain databases, wallet files or runtime cookies. The 173 MB candidate archive remains a separately retained artifact, expiring 17 December 2026 unless preserved elsewhere. The original result artifact expires 1 December 2026; all its records are now included here. This capsule is self-contained for offline evidence audit, not standalone runtime reproduction. Local preparation is not public permanent hosting or an external backup guarantee.

## Credit and remaining decision

Credit JPP for the Linux bundler, release gates and acceptance foundations; Numair for release integration and incorporation with authorship preserved; and the prior Session2 desktop recipe, reused with its original attribution. Session3 adapted the consumer fixture and collected this scoped platform evidence. Internal agent review is not a substitute for a maintainer or required human review.

Next: publish one consolidated evidence follow-up in the existing relevant thread only after authorization and another head/overlap check. Prepare an immutable public evidence commit before replacing the draft's relative link. No additional test run or code PR is needed for these passing checks. Numair's official desktop asset/version/adoption decision remains separate.
