# ModelNet helper release version

The published Linux CPU archive from `932a0238` reported `0.34.8-dev` in the help or version output of `btx-hcpd`, `btx-capabilityd`, and `btx-capability`. Repch1c reported the packaged behavior on #714. [Original report](https://github.com/btxchain/btx/pull/714#issuecomment-7098719845)

On Linux x86-64, 15 stock diagnostics printed the stale release string. A targeted build on the same source base with the [three-file patch](candidate.patch) passed all 15 comparisons. The changed output matched the stock streams byte for byte after replacing the stale token with `v0.34.17`, the value reported by the unchanged `btx-modeld` control. Exit codes, existing flag aliases and the HCP protocol suffix were preserved. The unsupported capabilityd flag still failed with the same diagnostic and usage output apart from the version.

The stock stage used the published CPU archive with SHA-256 `e93be7a55b6f786ec0147aa7b02c06fdaf8e7a04dd1d748a47b2ccd9662a4d9d` on Ubuntu 24.04. The candidate was built and run with a verified Ubuntu 22.04 x86-64 build container on the same runner. Ninja planned 20 actions for the three executables and the unchanged helper control. This run did not rebuild the full archive, start services or cover macOS and Windows.

[Stock output](stock.json) · [Patched output](candidate.json) · [Result and provenance](verified.json) · [Build record](build-result.json) · [Comparison program](diagnostics.py) · [CI run](https://github.com/sunnyriverr/btx/actions/runs/45172433013)
