# Current BTX install docs verification

The docs patch separates stable v0.34.16 (`074dac16`) and prerelease v0.34.17 (`3808e2a9`) from the live release branch (`2c4da891`). Both published uploads use unsigned checksum files. The prerelease manifest also lacks a snapshot manifest. The current docs use manual download and verification for these assets, and make the signed installer conditional on its required files.

- [Complete asset hashes](asset-verification.json) match the published checksum files and GitHub asset metadata for all four CPU/CUDA archives. The two CUDA archives were read in byte-range order and hashed in full. Static inventory confirmed the daemon and CLI in all four.
- The [published metadata](published-assets.json), [prerelease manifest](prerelease-manifest.json) and [snapshot header](snapshot-header.json) record the verified inputs. The complete 228000 snapshot matched the published digest. Its mainnet header identifies block `0104909051a017c9045faf7382627e89c5b83c4bbd3c1270706d5d2ef2ab0c87`, the compiled pin in both release sources and the docs base.
- [Documentation checks](documentation-check.txt) record the link and anchor review, shell syntax, checksum controls with stand-in archives, and preservation of historical sections. [Exact docs patch](install-docs.patch)

To verify the asset bytes independently, fetch the archive and its release's `SHA256SUMS` using the documented manual example. For the snapshot, use the separate published snapshot URL and pinned SHA-256 in Download-and-Go. Computing those digests verifies file identity. The checksums are unsigned.

No install, node start, runtime compatibility test or snapshot load was performed.

Credit [JPP](https://github.com/Jpp-matata) for flagging the version drift in [#714](https://github.com/btxchain/btx/pull/714#issuecomment-7050187269) and documenting the 228000 pin in [#364](https://github.com/btxchain/btx/pull/364).
